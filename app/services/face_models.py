import os
import shutil
from pathlib import Path


_MODEL_FILES = {
    "pose_predictor_model_location": "shape_predictor_68_face_landmarks.dat",
    "pose_predictor_five_point_model_location": "shape_predictor_5_face_landmarks.dat",
    "face_recognition_model_location": "dlib_face_recognition_resnet_model_v1.dat",
    "cnn_face_detector_model_location": "mmod_human_face_detector.dat",
}


def prepare_face_recognition_models() -> None:
    """Expose dlib model files from an ASCII-safe Windows path.

    dlib can fail to open model files when the installed package lives under a
    Unicode-heavy path such as OneDrive/Desktop folders with accents. Copy the
    model files once to LOCALAPPDATA and redirect face_recognition_models to
    those copies before importing face_recognition.
    """
    import face_recognition_models

    src_dir = Path(face_recognition_models.__file__).resolve().parent / "models"
    cache_root = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    dst_dir = cache_root / "TourAllianz" / "face_models"
    dst_dir.mkdir(parents=True, exist_ok=True)

    resolved_paths: dict[str, str] = {}
    for attr_name, filename in _MODEL_FILES.items():
        src = src_dir / filename
        dst = dst_dir / filename
        if not src.exists():
            raise FileNotFoundError(f"Modelo nao encontrado: {src}")
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            shutil.copyfile(src, dst)
        resolved_paths[attr_name] = str(dst)

    for attr_name, resolved_path in resolved_paths.items():
        setattr(face_recognition_models, attr_name, lambda p=resolved_path: p)
