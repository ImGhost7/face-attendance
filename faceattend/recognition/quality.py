"""Quality gates + head-pose proxies from the 5 YuNet landmarks.

Bad enrollment photos are the #1 reason face attendance "stops working",
so these checks run on every enrollment sample and on every kiosk frame.
"""
import cv2
import numpy as np

from ..config import Settings


def estimate_pose(landmarks: np.ndarray) -> tuple[float, float]:
    """Return (yaw, pitch) proxies, ~0 yaw / ~0 pitch for a frontal face.

    Image coordinates: yaw > 0 means the nose is displaced toward the RIGHT of the image.
    pitch > 0 means looking down. Roughly +-0.3 yaw is a clear head turn.
    """
    re, le, nose, rm, lm = landmarks
    eye_mid = (re + le) / 2
    mouth_mid = (rm + lm) / 2
    eye_dist = max(float(np.linalg.norm(le - re)), 1e-6)
    yaw = float((nose[0] - eye_mid[0]) / eye_dist)
    vert = max(float(mouth_mid[1] - eye_mid[1]), 1e-6)
    pitch = float((nose[1] - eye_mid[1]) / vert - 0.55)  # 0.55 ~ frontal nose position
    return yaw, pitch


def check_quality(frame_bgr: np.ndarray, box: tuple, landmarks: np.ndarray, s: Settings, frontal: bool = True) -> list[str]:
    """Return a list of human-readable problems; empty list = good enough."""
    problems = []
    x, y, w, h = box
    if min(w, h) < s.min_face_px:
        problems.append("Move closer to the camera")
    H, W = frame_bgr.shape[:2]
    if x < 0 or y < 0 or x + w > W or y + h > H:
        problems.append("Keep your whole face inside the frame")
    x0, y0 = max(x, 0), max(y, 0)
    crop = frame_bgr[y0 : max(y + h, y0 + 1), x0 : max(x + w, x0 + 1)]
    if crop.size == 0:
        return problems + ["No face visible"]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    if cv2.Laplacian(gray, cv2.CV_64F).var() < s.min_blur_var:
        problems.append("Image is blurry - hold still")
    mean = float(gray.mean())
    lo, hi = s.brightness_range
    if mean < lo:
        problems.append("Too dark")
    elif mean > hi:
        problems.append("Too bright")
    if frontal:
        yaw, _ = estimate_pose(landmarks)
        if abs(yaw) > s.max_yaw_frontal:
            problems.append("Look straight at the camera")
    return problems
