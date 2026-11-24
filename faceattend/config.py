"""Central settings. Every threshold lives here so it can be tuned during the pilot."""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    # --- models (OpenCV Zoo: YuNet = MIT, SFace = Apache-2.0, both fine for commercial use)
    detector_model: Path = ROOT / "models" / "face_detection_yunet_2023mar.onnx"
    recognizer_model: Path = ROOT / "models" / "face_recognition_sface_2021dec.onnx"
    detector_score_threshold: float = 0.8

    # --- matching (SFace cosine; OpenCV's recommended cutoff is 0.363)
    match_threshold: float = 0.45  # stricter than 0.363: a wrong "present" is worse than a retry
    match_margin: float = 0.08  # best person must beat the runner-up by this much
    duplicate_threshold: float = 0.55  # enrollment: refuse a face that already belongs to someone
    votes_required: int = 3  # k ...
    votes_window: int = 5  # ... of the last m frames must agree

    # --- quality gates
    min_face_px: int = 80
    min_blur_var: float = 60.0
    brightness_range: tuple = (50.0, 210.0)
    max_yaw_frontal: float = 0.25

    # --- entrance events
    event_cooldown_s: int = 45  # ignore the same person/direction again within this window
    auto_close_hour: int = 23  # day with no OUT is closed at this hour and flagged

    # --- storage
    db_path: Path = ROOT / "data" / "attendance.db"
