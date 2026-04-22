import os
import io
import time
import uuid
import json
import hashlib
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

from app.config import UPLOADS_DIR, OUTPUT_DIR, PRINT_DPI

STATIC_DIR = Path(__file__).parent / "static"

from app.services import face_service, composition_service
from app.services import cache as encoding_cache

_INDEX_CACHE: dict = {"html": None, "mtime": 0.0}

BOOT_ID = str(int(time.time()))


# ---------- Logging + per-request context ----------
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
session_id_var: ContextVar[str] = ContextVar("session_id", default="-")
SESSION_COOKIE = "app_session_id"


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


_LOG_FMT = logging.Formatter(
    "%(asctime)s [%(request_id)s] %(levelname)s %(name)s: %(message)s"
)
_REQ_FILTER = RequestIdFilter()

_handler = logging.StreamHandler()
_handler.setFormatter(_LOG_FMT)
_handler.addFilter(_REQ_FILTER)

from logging.handlers import RotatingFileHandler
_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.log")
_file_handler = RotatingFileHandler(
    _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_file_handler.setFormatter(_LOG_FMT)
_file_handler.addFilter(_REQ_FILTER)

_root = logging.getLogger()
_root.handlers.clear()
_root.addHandler(_handler)
_root.addHandler(_file_handler)
_root.setLevel(logging.INFO)

log = logging.getLogger(__name__)


# ---------- App + middleware ----------
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_IMAGE_EXTS = (".jpg", ".jpeg", ".png")
OUTPUT_TTL_DAYS = 7


def _cleanup_old_outputs(directory: str, ttl_days: int) -> int:
    """Delete files in `directory` (recursive) older than `ttl_days`. Returns count deleted.

    Walks subdirectories so per-session output folders are pruned, and removes
    empty session subfolders left behind.
    """
    if not os.path.isdir(directory):
        return 0
    cutoff = time.time() - (ttl_days * 86400)
    deleted = 0
    for root, dirs, files in os.walk(directory):
        for name in files:
            path = os.path.join(root, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    deleted += 1
            except OSError as e:
                log.warning(f"cleanup: could not remove {path}: {e}")
    for root, dirs, files in os.walk(directory, topdown=False):
        if root == directory:
            continue
        try:
            if not os.listdir(root):
                os.rmdir(root)
        except OSError:
            pass
    return deleted


@asynccontextmanager
async def lifespan(app: FastAPI):
    deleted = _cleanup_old_outputs(OUTPUT_DIR, OUTPUT_TTL_DAYS)
    if deleted:
        log.info(f"startup: cleaned {deleted} composed file(s) older than {OUTPUT_TTL_DAYS} days")
    yield


app = FastAPI(title="Tour Allianz Parque - Photo Manager", lifespan=lifespan)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:8]
    sid = request.cookies.get(SESSION_COOKIE) or uuid.uuid4().hex
    set_cookie = SESSION_COOKIE not in request.cookies

    rid_token = request_id_var.set(rid)
    sid_token = session_id_var.set(sid)
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        if set_cookie:
            response.set_cookie(
                SESSION_COOKIE, sid,
                max_age=30 * 86400, httponly=True, samesite="lax",
            )
        return response
    finally:
        request_id_var.reset(rid_token)
        session_id_var.reset(sid_token)


# ---------- Per-session in-memory state ----------
sessions: dict[str, dict] = {}


def _new_session_state() -> dict:
    return {
        "session_path": None,
        "reference_encodings": [],
        "match_results": [],
    }


def get_state() -> dict:
    """Return the state dict for the current request's session."""
    sid = session_id_var.get()
    if sid not in sessions:
        sessions[sid] = _new_session_state()
    return sessions[sid]


# ---------- Async scan jobs ----------
SCAN_JOB_TTL_SECONDS = 600  # 10 min — older finished jobs are GC'd
_scan_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="scan")
scan_jobs: dict[str, dict] = {}
_scan_jobs_lock = threading.Lock()


def _gc_scan_jobs() -> None:
    """Remove finished scan jobs older than SCAN_JOB_TTL_SECONDS."""
    cutoff = time.time() - SCAN_JOB_TTL_SECONDS
    with _scan_jobs_lock:
        stale = [
            jid for jid, j in scan_jobs.items()
            if j["status"] in ("done", "error") and j["finished_at"] and j["finished_at"] < cutoff
        ]
        for jid in stale:
            del scan_jobs[jid]
    if stale:
        log.info(f"scan jobs GC: removed {len(stale)} stale job(s)")


def _run_scan_job(job_id: str, sid: str, session_path: str, encodings: list) -> None:
    """Worker thread body — runs face_service.scan_session with progress updates."""
    job = scan_jobs[job_id]
    job["status"] = "running"
    try:
        def cb(done: int, total: int) -> None:
            job["progress"] = done
            job["total"] = total

        results = face_service.scan_session(session_path, encodings, progress_callback=cb)
        matches = _build_local_matches(results)

        if sid in sessions:
            sessions[sid]["match_results"] = results

        job["matches"] = matches
        job["status"] = "done"
    except Exception as e:
        log.exception(f"scan job {job_id} failed")
        job["status"] = "error"
        job["error"] = str(e)
    finally:
        job["finished_at"] = time.time()


# ---------- Pydantic request models ----------
class SelectSessionRequest(BaseModel):
    path: str = Field(..., min_length=1)


class ComposeRequest(BaseModel):
    selected: list[str] = Field(default_factory=list)
    orientations: dict[str, str] = Field(default_factory=dict)


class PrintFile(BaseModel):
    output: str
    original: Optional[str] = None
    filename: Optional[str] = None


class PrintRequest(BaseModel):
    files: list[PrintFile] = Field(default_factory=list)


# ---------- Helpers ----------
def _is_within(child: str, parent: str) -> bool:
    """Return True iff `child` resolves to a path inside `parent`."""
    try:
        child_real = os.path.realpath(child)
        parent_real = os.path.realpath(parent)
        return os.path.commonpath([child_real, parent_real]) == parent_real
    except (ValueError, OSError):
        return False


def _fix_orientation(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation so phone photos aren't sideways."""
    try:
        from PIL import ExifTags
        exif = img.getexif()
        orientation_key = next(k for k, v in ExifTags.TAGS.items() if v == "Orientation")
        orientation = exif.get(orientation_key)
        rotations = {3: 180, 6: 270, 8: 90}
        if orientation in rotations:
            img = img.rotate(rotations[orientation], expand=True)
            log.info(f"_fix_orientation: rotated {rotations[orientation]}°")
    except Exception as e:
        log.debug(f"_fix_orientation: skipped ({e})")
    return img


def _build_local_matches(results):
    matches = []
    for r in results:
        confidence = max(0, min(100, int((1 - r.best_distance) * 100)))
        matches.append({
            "file_path": r.file_path,
            "filename": os.path.basename(r.file_path),
            "thumbnail_url": f"/api/thumbnail/{r.sha}.jpg",
            "sha": r.sha,
            "confidence": confidence,
        })
    return matches


# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
def root():
    idx = STATIC_DIR / "index.html"
    icons = STATIC_DIR / "_icons.svg"
    if not idx.exists() or not icons.exists():
        raise HTTPException(status_code=500, detail="UI assets missing")
    mtime = max(idx.stat().st_mtime, icons.stat().st_mtime)
    if _INDEX_CACHE["html"] is None or _INDEX_CACHE["mtime"] != mtime:
        html = idx.read_text(encoding="utf-8")
        svg = icons.read_text(encoding="utf-8")
        _INDEX_CACHE["html"] = html.replace("<!--ICONS-->", svg)
        _INDEX_CACHE["mtime"] = mtime
    return HTMLResponse(_INDEX_CACHE["html"])


@app.get("/api/boot-id")
async def get_boot_id():
    return {"boot_id": BOOT_ID}


@app.get("/api/sessions")
async def get_sessions():
    """List available session folders."""
    items = []
    if not os.path.exists(UPLOADS_DIR):
        return items
    for name in sorted(os.listdir(UPLOADS_DIR), reverse=True):
        path = os.path.join(UPLOADS_DIR, name)
        if os.path.isdir(path):
            count = sum(1 for f in os.listdir(path) if f.lower().endswith(ALLOWED_IMAGE_EXTS))
            display = name
            try:
                if len(name) == 12:
                    display = f"{name[0:2]}/{name[2:4]}/{name[4:8]} {name[8:10]}:{name[10:12]}"
            except (ValueError, IndexError):
                pass
            items.append({"name": name, "display_name": display, "path": path, "count": count})
    return items


@app.post("/api/session/select")
async def select_session(req: SelectSessionRequest):
    """Select a session folder by path."""
    try:
        path = req.path.strip()
        if not path or not os.path.isdir(path):
            return JSONResponse(
                {"ok": False, "message": f"Pasta não encontrada: {path}"},
                status_code=200,
            )

        count = sum(1 for f in os.listdir(path) if f.lower().endswith(ALLOWED_IMAGE_EXTS))

        state = get_state()
        state["session_path"] = path
        state["reference_encodings"] = []
        state["match_results"] = []
        log.info(f"Session selected: {path} ({count} photos)")
        return {"ok": True, "path": path, "count": count}
    except Exception as e:
        log.exception("select_session failed")
        return JSONResponse(
            {"ok": False, "message": f"Erro ao selecionar sessão: {e}"},
            status_code=500,
        )


@app.get("/api/browse-folder")
async def browse_folder():
    """Open a native OS folder picker dialog and return the selected path."""
    result = {"path": None}
    ready = threading.Event()

    def open_dialog():
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="Selecionar pasta de fotos")
        root.destroy()
        result["path"] = path or None
        ready.set()

    t = threading.Thread(target=open_dialog, daemon=True)
    t.start()
    ready.wait(timeout=120)

    if not result["path"]:
        return {"ok": False, "path": None}
    return {"ok": True, "path": result["path"]}


@app.post("/api/face/capture")
async def capture_face(file: UploadFile = File(...)):
    """Receive a webcam frame or gallery photo, detect and encode faces."""
    try:
        contents = await file.read()
        if not contents:
            return JSONResponse({"ok": False, "message": "Arquivo vazio"}, status_code=400)
        if len(contents) > MAX_UPLOAD_BYTES:
            return JSONResponse(
                {"ok": False, "message": f"Arquivo excede {MAX_UPLOAD_BYTES // (1024 * 1024)} MB"},
                status_code=413,
            )

        try:
            with Image.open(io.BytesIO(contents)) as probe:
                probe.verify()
        except (UnidentifiedImageError, Exception):
            return JSONResponse(
                {"ok": False, "message": "Arquivo não é uma imagem válida"},
                status_code=400,
            )

        raw_img = Image.open(io.BytesIO(contents))
        raw_exif = raw_img.getexif()
        exif_orientation = raw_exif.get(274)
        exif_timestamp = raw_exif.get(36867) or raw_exif.get(306)
        img = raw_img.convert("RGB")
        img = _fix_orientation(img)
        img_array = np.array(img)
        capture_diag = {
            "hash": hashlib.sha256(contents).hexdigest()[:12],
            "received_at": datetime.now(timezone.utc).isoformat(),
            "exif_orientation": exif_orientation,
            "exif_timestamp": exif_timestamp,
            "size": f"{img.size[0]}x{img.size[1]}",
            "mode": img.mode,
            "base": face_service.get_detection_diagnostics(img_array),
            "clahe": face_service.get_detection_diagnostics(
                face_service.enhance_for_detection(img_array),
                upsample=min(face_service.FACE_UPSAMPLE + 1, 3),
                model=face_service.FACE_DETECTION_MODEL,
            ),
        }
        log.info("CAPTURE_DIAG %s", json.dumps(capture_diag, ensure_ascii=False))

        encodings = face_service.encode_faces(img_array)
        log.info(f"capture_face: detected {len(encodings)} face(s)")
        if not encodings:
            return JSONResponse({"ok": False, "message": "Nenhum rosto detectado na foto"}, status_code=200)

        state = get_state()
        for enc in encodings:
            state["reference_encodings"].append(enc)

        locations = face_service.get_face_locations(img_array)
        face_rects = [{"top": t, "right": r, "bottom": b, "left": l} for t, r, b, l in locations]

        return {
            "ok": True,
            "faces_count": len(encodings),
            "total_references": len(state["reference_encodings"]),
            "face_rects": face_rects,
        }
    except Exception as e:
        log.exception("capture_face failed")
        return JSONResponse(
            {"ok": False, "message": f"Erro ao processar imagem: {e}"},
            status_code=500,
        )


@app.post("/api/face/clear")
async def clear_faces():
    """Clear all reference face encodings."""
    state = get_state()
    state["reference_encodings"] = []
    return {"ok": True}


@app.post("/api/scan")
async def start_scan():
    """Start an async scan job. Returns {job_id} immediately."""
    state = get_state()
    if not state["session_path"]:
        return JSONResponse({"ok": False, "message": "Nenhuma sessão selecionada"}, status_code=400)
    if not state["reference_encodings"]:
        return JSONResponse({"ok": False, "message": "Nenhum rosto de referência"}, status_code=400)

    sid = session_id_var.get()
    job_id = uuid.uuid4().hex
    encodings = list(state["reference_encodings"])
    session_path = state["session_path"]

    scan_jobs[job_id] = {
        "session_id": sid,
        "status": "pending",
        "progress": 0,
        "total": 0,
        "matches": [],
        "error": None,
        "started_at": time.time(),
        "finished_at": None,
    }
    _gc_scan_jobs()
    _scan_executor.submit(_run_scan_job, job_id, sid, session_path, encodings)
    log.info(f"scan job {job_id} queued (sid={sid[:8]}, path={session_path})")
    return {"ok": True, "job_id": job_id}


@app.get("/api/scan/{job_id}")
async def get_scan_status(job_id: str):
    """Poll scan job status. Returns progress; when done, includes matches."""
    job = scan_jobs.get(job_id)
    if not job:
        return JSONResponse({"ok": False, "message": "Job não encontrado"}, status_code=404)

    sid = session_id_var.get()
    if job["session_id"] != sid:
        log.warning(f"scan job {job_id} access denied (session mismatch)")
        return JSONResponse({"ok": False, "message": "Acesso negado"}, status_code=403)

    payload = {
        "ok": True,
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "total": job["total"],
    }
    if job["status"] == "done":
        payload["matches"] = job["matches"]
    elif job["status"] == "error":
        payload["message"] = job["error"]
    return payload


@app.get("/api/photo")
async def get_session_photo(filename: str = ""):
    """Serve a photo from the current session by filename (validated against session dir)."""
    state = get_state()
    session_path = state["session_path"]
    if not filename or not session_path:
        return JSONResponse({"error": "filename and active session required"}, status_code=400)

    if not filename.lower().endswith(ALLOWED_IMAGE_EXTS):
        return JSONResponse({"error": "Unsupported file type"}, status_code=400)

    candidate = os.path.join(session_path, filename)
    if not _is_within(candidate, session_path):
        log.warning(f"Photo path traversal attempt: filename={filename!r}")
        return JSONResponse({"error": "Invalid filename"}, status_code=400)

    if not os.path.exists(candidate):
        log.warning(f"Photo not found: filename={filename}, session={session_path}")
        return JSONResponse({"error": "File not found"}, status_code=404)

    media = "image/jpeg" if candidate.lower().endswith((".jpg", ".jpeg")) else "image/png"
    return FileResponse(candidate, media_type=media)


@app.get("/api/thumbnail/{sha}.jpg")
async def get_thumbnail(sha: str):
    """Serve a cached thumbnail by sha. Long browser cache since contents are immutable."""
    if not sha or not sha.isalnum() or len(sha) > 64:
        return JSONResponse({"error": "Invalid sha"}, status_code=400)
    path = encoding_cache.thumbnail_path(sha)
    if not os.path.isfile(path):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )


@app.post("/api/compose")
async def compose_photos(req: ComposeRequest):
    """Compose selected photos with footer template, grouped by session in output/."""
    try:
        state = get_state()
        face_lookup = {}
        if state["match_results"]:
            for mr in state["match_results"]:
                if hasattr(mr, "file_path"):
                    face_lookup[mr.file_path] = mr.face_locations

        session_name = None
        if state.get("session_path"):
            session_name = os.path.basename(state["session_path"].rstrip("\\/"))

        composed_files = []
        for photo_path in req.selected:
            orientation = req.orientations.get(photo_path, "landscape")
            face_locs = face_lookup.get(photo_path, None)
            composed = composition_service.compose_photo(photo_path, orientation, face_locs)
            out_path = composition_service.save_composed(composed, photo_path, session_name)
            rel = os.path.relpath(out_path, OUTPUT_DIR).replace("\\", "/")
            composed_files.append({
                "original": photo_path,
                "output": out_path,
                "filename": rel,
            })
        return {"ok": True, "files": composed_files}
    except Exception as e:
        log.exception("compose_photos failed")
        return JSONResponse(
            {"ok": False, "message": f"Erro ao compor fotos: {e}"},
            status_code=500,
        )


@app.get("/api/output/{filepath:path}")
async def get_output_file(filepath: str):
    """Serve a composed output file (validated against OUTPUT_DIR).

    Supports per-session subfolders, e.g. `/api/output/<session>/<file>.jpg`.
    """
    if not filepath or ".." in filepath.replace("\\", "/").split("/"):
        return JSONResponse({"error": "Invalid filename"}, status_code=400)

    if not filepath.lower().endswith(ALLOWED_IMAGE_EXTS):
        return JSONResponse({"error": "Unsupported file type"}, status_code=400)

    file_path = os.path.join(OUTPUT_DIR, filepath)
    if not _is_within(file_path, OUTPUT_DIR):
        log.warning(f"Output path traversal attempt: filename={filepath!r}")
        return JSONResponse({"error": "Invalid filename"}, status_code=400)

    if not os.path.exists(file_path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    return FileResponse(file_path, media_type="image/jpeg")


@app.post("/api/print")
async def print_photos(req: PrintRequest):
    """Bundle all composed photos into a single PDF and trigger the print dialog once.

    Generates a multi-page PDF (one photo per page at PRINT_DPI) under
    `output/_prints/` and invokes the Windows shell "print" verb on it. The
    default PDF handler (Edge, Acrobat, etc.) opens its print dialog where the
    user picks printer, copies and layout for all photos at once.
    """
    try:
        import win32api
        import win32con
        import win32print
    except ImportError:
        return JSONResponse(
            {"ok": False, "message": "pywin32 não instalado — rode: pip install pywin32"},
            status_code=500,
        )

    try:
        log.info(f"print_photos: received {len(req.files)} file(s)")
        valid_paths: list[str] = []
        for f in req.files:
            path = f.output
            if not path:
                log.warning("Print rejected (empty output path)")
                continue
            if not _is_within(path, OUTPUT_DIR):
                log.warning(f"Print rejected (outside OUTPUT_DIR): {path!r}")
                continue
            if not os.path.exists(path):
                log.warning(f"Print rejected (file missing): {path!r}")
                continue
            valid_paths.append(os.path.abspath(path))

        if not valid_paths:
            log.warning("print_photos: no valid paths after filtering")
            return {"ok": True, "printed": 0, "printer": None,
                    "message": "Nenhuma foto composta válida para imprimir. Recomponha as fotos e tente novamente."}

        try:
            printer = win32print.GetDefaultPrinter()
        except Exception:
            printer = None

        prints_dir = os.path.join(OUTPUT_DIR, "_prints")
        os.makedirs(prints_dir, exist_ok=True)
        pdf_path = os.path.abspath(
            os.path.join(prints_dir, f"bundle-{int(time.time())}-{uuid.uuid4().hex[:6]}.pdf")
        )

        images: list[Image.Image] = []
        try:
            for p in valid_paths:
                img = Image.open(p)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                images.append(img)
            images[0].save(
                pdf_path,
                save_all=True,
                append_images=images[1:],
                resolution=PRINT_DPI,
            )
        finally:
            for img in images:
                try:
                    img.close()
                except Exception:
                    pass

        try:
            win32api.ShellExecute(0, "print", pdf_path, None, ".", win32con.SW_SHOWNORMAL)
        except Exception as e:
            log.exception("ShellExecute 'print' failed on PDF bundle")
            return JSONResponse(
                {"ok": False,
                 "message": (
                     "Falha ao abrir o diálogo de impressão. Verifique se há um "
                     f"app padrão associado a .pdf. Detalhe: {e}"
                 )},
                status_code=500,
            )

        log.info(f"Print dialog opened for bundled PDF with {len(valid_paths)} page(s) -> {pdf_path} (printer={printer!r})")
        return {"ok": True, "printed": len(valid_paths), "printer": printer, "bundle": pdf_path}
    except Exception as e:
        log.exception("print_photos failed")
        return JSONResponse(
            {"ok": False, "message": f"Erro ao preparar impressão: {e}"},
            status_code=500,
        )


# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser(description="Tour Allianz Parque - Photo Manager")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run("server:app" if args.reload else app, host=args.host, port=args.port, reload=args.reload)
