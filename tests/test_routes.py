import io
import os
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import server


SESSION_COOKIE = server.SESSION_COOKIE
UPLOADS_DIR = server.UPLOADS_DIR
OUTPUT_DIR = server.OUTPUT_DIR


@pytest.fixture
def client():
    server.sessions.clear()
    server.scan_jobs.clear()
    with TestClient(server.app) as c:
        yield c


@pytest.fixture
def existing_session_path():
    if not os.path.isdir(UPLOADS_DIR):
        pytest.skip("uploads dir not present")
    for name in sorted(os.listdir(UPLOADS_DIR)):
        path = os.path.join(UPLOADS_DIR, name)
        if os.path.isdir(path):
            return path
    pytest.skip("no session subfolders in uploads")


def _png_bytes(width=8, height=8, color=(200, 0, 0)):
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# --- Cookie / session ---

def test_session_cookie_set_on_first_request(client):
    r = client.get("/api/sessions")
    assert r.status_code == 200
    assert SESSION_COOKIE in r.cookies


def test_session_cookie_reused_on_subsequent_requests(client):
    r1 = client.get("/api/sessions")
    sid1 = r1.cookies[SESSION_COOKIE]
    r2 = client.get("/api/sessions")
    # No Set-Cookie a second time means cookie reused
    assert SESSION_COOKIE not in r2.cookies
    # Same client keeps the cookie
    assert client.cookies.get(SESSION_COOKIE) == sid1


def test_request_id_header_echoed(client):
    r = client.get("/api/sessions", headers={"x-request-id": "deadbeef"})
    assert r.headers.get("x-request-id") == "deadbeef"


def test_request_id_generated_when_absent(client):
    r = client.get("/api/sessions")
    rid = r.headers.get("x-request-id")
    assert rid and len(rid) == 8


# --- Validation (Pydantic) ---

def test_session_select_missing_path_is_422(client):
    r = client.post("/api/session/select", json={})
    assert r.status_code == 422


def test_session_select_empty_path_is_422(client):
    r = client.post("/api/session/select", json={"path": ""})
    assert r.status_code == 422


def test_session_select_nonexistent_returns_ok_false(client):
    r = client.post("/api/session/select", json={"path": "Z:\\does\\not\\exist"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "não encontrada" in body["message"].lower() or "nao encontrada" in body["message"].lower()


def test_compose_accepts_empty_request(client):
    r = client.post("/api/compose", json={"selected": [], "orientations": {}})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "files": []}


def test_print_accepts_empty_files(client):
    r = client.post("/api/print", json={"files": []})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["printed"] == 0


# --- Upload validation ---

def test_capture_face_empty_file_returns_400(client):
    r = client.post(
        "/api/face/capture",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert r.status_code == 400
    assert r.json()["ok"] is False


def test_capture_face_invalid_image_returns_400(client):
    r = client.post(
        "/api/face/capture",
        files={"file": ("not-an-image.jpg", b"this is not an image", "image/jpeg")},
    )
    assert r.status_code == 400
    assert r.json()["ok"] is False


def test_capture_face_oversize_returns_413(client):
    big = b"\x00" * (server.MAX_UPLOAD_BYTES + 1)
    r = client.post(
        "/api/face/capture",
        files={"file": ("big.jpg", big, "image/jpeg")},
    )
    assert r.status_code == 413


def test_capture_face_valid_image_no_face_returns_200_ok_false(client):
    r = client.post(
        "/api/face/capture",
        files={"file": ("flat.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "rosto" in body["message"].lower()


# --- Path traversal / file access ---

def test_photo_endpoint_requires_session(client):
    r = client.get("/api/photo", params={"filename": "x.jpg"})
    assert r.status_code == 400


def test_photo_endpoint_rejects_traversal(client, existing_session_path):
    client.post("/api/session/select", json={"path": existing_session_path})
    r = client.get("/api/photo", params={"filename": "../../../etc/passwd"})
    assert r.status_code == 400


def test_photo_endpoint_rejects_unsupported_ext(client, existing_session_path):
    client.post("/api/session/select", json={"path": existing_session_path})
    r = client.get("/api/photo", params={"filename": "evil.exe"})
    assert r.status_code == 400


def test_output_endpoint_allows_subpath_but_404_when_missing(client):
    # Per-session subfolders are valid; the file just doesn't exist here.
    r = client.get("/api/output/sub/x.jpg")
    assert r.status_code == 404


def test_output_endpoint_rejects_dotdot_segment(client):
    # A `..` path segment is the actual traversal vector and must be banned.
    r = client.get("/api/output/..%2Fetc%2Fpasswd")
    # Either 400 (segment ban) or 404 (resolves outside OUTPUT_DIR) is acceptable;
    # what matters is we never serve a file from outside OUTPUT_DIR.
    assert r.status_code in (400, 404)


def test_output_endpoint_rejects_unsupported_ext(client):
    r = client.get("/api/output/evil.exe")
    assert r.status_code == 400


def test_output_endpoint_404_for_missing_file(client):
    r = client.get("/api/output/nope_does_not_exist_12345.jpg")
    assert r.status_code == 404


# --- Async scan job lifecycle ---

def test_scan_post_without_session_returns_400(client):
    r = client.post("/api/scan")
    assert r.status_code == 400
    assert "sess" in r.json()["message"].lower()


def test_scan_post_without_face_returns_400(client, existing_session_path):
    client.post("/api/session/select", json={"path": existing_session_path})
    r = client.post("/api/scan")
    assert r.status_code == 400
    assert "refer" in r.json()["message"].lower()


def test_scan_get_unknown_job_returns_404(client):
    r = client.get("/api/scan/nonexistent_job_id")
    assert r.status_code == 404


def test_scan_get_other_session_job_returns_403(client, existing_session_path):
    """Job started by sid_a should be inaccessible to sid_b."""
    # Client A: select session, inject a fake encoding, start scan
    client.post("/api/session/select", json={"path": existing_session_path})
    sid_a = client.cookies.get(SESSION_COOKIE)
    server.sessions[sid_a]["reference_encodings"] = [np.zeros(128, dtype=np.float64)]

    # Stub scan_session so we don't actually run face recognition
    original = server.face_service.scan_session
    server.face_service.scan_session = lambda path, encs, progress_callback=None: []
    try:
        r = client.post("/api/scan")
        assert r.status_code == 200
        job_id = r.json()["job_id"]

        # Wait briefly for the worker thread to complete
        for _ in range(20):
            if server.scan_jobs[job_id]["status"] in ("done", "error"):
                break
            time.sleep(0.05)

        # Client B: fresh client, different cookie
        with TestClient(server.app) as client_b:
            client_b.get("/api/sessions")  # establish a session cookie
            assert client_b.cookies.get(SESSION_COOKIE) != sid_a
            r2 = client_b.get(f"/api/scan/{job_id}")
            assert r2.status_code == 403
    finally:
        server.face_service.scan_session = original


def test_scan_full_lifecycle_with_stubbed_scan(client, existing_session_path):
    """POST /api/scan → poll GET /api/scan/{id} → status done with matches."""
    client.post("/api/session/select", json={"path": existing_session_path})
    sid = client.cookies.get(SESSION_COOKIE)
    server.sessions[sid]["reference_encodings"] = [np.zeros(128, dtype=np.float64)]

    fake_match = type("M", (), {
        "file_path": os.path.join(existing_session_path, "fake.jpg"),
        "sha": "deadbeefcafe",
        "best_distance": 0.42,
        "face_locations": [],
    })()

    def fake_scan(path, encs, progress_callback=None):
        if progress_callback:
            progress_callback(1, 2)
            progress_callback(2, 2)
        return [fake_match]

    original = server.face_service.scan_session
    server.face_service.scan_session = fake_scan
    try:
        r = client.post("/api/scan")
        assert r.status_code == 200
        job_id = r.json()["job_id"]

        for _ in range(40):
            poll = client.get(f"/api/scan/{job_id}").json()
            if poll["status"] == "done":
                break
            time.sleep(0.05)
        else:
            pytest.fail(f"scan job did not finish: last={poll}")

        assert poll["progress"] == 2
        assert poll["total"] == 2
        assert len(poll["matches"]) == 1
        assert poll["matches"][0]["filename"] == "fake.jpg"
        # Confidence: (1 - 0.42) * 100 = 58
        assert poll["matches"][0]["confidence"] == 58
        # New shape: thumbnail served by URL, not embedded as base64
        assert poll["matches"][0]["thumbnail_url"] == "/api/thumbnail/deadbeefcafe.jpg"
        assert poll["matches"][0]["sha"] == "deadbeefcafe"
        assert "thumbnail" not in poll["matches"][0]
        # match_results stored on session for /api/compose
        assert len(server.sessions[sid]["match_results"]) == 1
    finally:
        server.face_service.scan_session = original


# --- Helpers ---

def test_is_within_blocks_traversal():
    base = os.path.abspath(UPLOADS_DIR)
    assert server._is_within(os.path.join(base, "a.jpg"), base) is True
    assert server._is_within(os.path.join(base, "..", "etc", "passwd"), base) is False


def test_cleanup_old_outputs_removes_stale(tmp_path):
    old = tmp_path / "old.jpg"
    new = tmp_path / "new.jpg"
    old.write_bytes(b"x")
    new.write_bytes(b"x")
    # Backdate `old` 10 days
    long_ago = time.time() - 10 * 86400
    os.utime(old, (long_ago, long_ago))
    deleted = server._cleanup_old_outputs(str(tmp_path), ttl_days=7)
    assert deleted == 1
    assert not old.exists()
    assert new.exists()


def test_cleanup_old_outputs_handles_missing_dir():
    assert server._cleanup_old_outputs("Z:\\does\\not\\exist", ttl_days=7) == 0


def test_cleanup_old_outputs_recurses_into_subdirs(tmp_path):
    sub = tmp_path / "sessionA"
    sub.mkdir()
    old = sub / "old.jpg"
    new = sub / "new.jpg"
    old.write_bytes(b"x")
    new.write_bytes(b"x")
    long_ago = time.time() - 10 * 86400
    os.utime(old, (long_ago, long_ago))
    deleted = server._cleanup_old_outputs(str(tmp_path), ttl_days=7)
    assert deleted == 1
    assert not old.exists()
    assert new.exists()
    # Subdir kept because new.jpg still lives there
    assert sub.exists()


def test_cleanup_old_outputs_removes_empty_session_subdirs(tmp_path):
    sub = tmp_path / "sessionEmpty"
    sub.mkdir()
    old = sub / "old.jpg"
    old.write_bytes(b"x")
    long_ago = time.time() - 10 * 86400
    os.utime(old, (long_ago, long_ago))
    server._cleanup_old_outputs(str(tmp_path), ttl_days=7)
    assert not sub.exists()


# --- Thumbnail endpoint ---

def test_thumbnail_endpoint_404_for_missing(client):
    r = client.get("/api/thumbnail/nonexistent000.jpg")
    assert r.status_code == 404


def test_thumbnail_endpoint_rejects_invalid_sha(client):
    r = client.get("/api/thumbnail/..%2Fpasswd.jpg")
    assert r.status_code in (400, 404)


def test_thumbnail_endpoint_serves_cached(client, tmp_path, monkeypatch):
    fake_sha = "abc123def456"
    fake_path = str(tmp_path / f"{fake_sha}.jpg")
    Image.new("RGB", (10, 10), (1, 2, 3)).save(fake_path, format="JPEG")
    monkeypatch.setattr(
        server.encoding_cache, "thumbnail_path", lambda sha: fake_path if sha == fake_sha else "/nope"
    )
    r = client.get(f"/api/thumbnail/{fake_sha}.jpg")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/jpeg")
    assert "max-age" in r.headers.get("cache-control", "")
