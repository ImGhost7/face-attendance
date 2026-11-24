"""Thin wrappers around OpenCV's YuNet (detector) and SFace (recognizer).

Verified on a Windows dev laptop (OpenCV 5.1.0, Python 3.14) with the real model files and a
live webcam (scripts/live_check.py): loads, detects, embeds; same-person similarity ~0.8-0.93.
STILL UNVERIFIED: different-person (impostor) similarity - needs a second person / photos.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from ..config import Settings


@dataclass
class Face:
    box: tuple  # x, y, w, h (pixels)
    landmarks: np.ndarray  # 5x2: right eye, left eye, nose tip, right mouth, left mouth (image coords)
    score: float
    raw: np.ndarray  # the 15-value YuNet row, needed for alignment


class FaceEngine:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or Settings()
        for p in (self.s.detector_model, self.s.recognizer_model):
            if not p.exists():
                raise FileNotFoundError(f"{p} missing - run scripts/download_models.py")
        self._det = cv2.FaceDetectorYN.create(
            str(self.s.detector_model), "", (320, 320), self.s.detector_score_threshold, 0.3, 5000
        )
        self._rec = cv2.FaceRecognizerSF.create(str(self.s.recognizer_model), "")

    def detect(self, frame_bgr: np.ndarray) -> list[Face]:
        h, w = frame_bgr.shape[:2]
        self._det.setInputSize((w, h))
        _, rows = self._det.detect(frame_bgr)
        if rows is None:
            return []
        faces = []
        for r in rows:
            faces.append(
                Face(
                    box=tuple(int(v) for v in r[:4]),
                    landmarks=r[4:14].reshape(5, 2).astype(np.float32),
                    score=float(r[14]),
                    raw=r,
                )
            )
        return sorted(faces, key=lambda f: f.box[2] * f.box[3], reverse=True)  # biggest = closest first

    def embed(self, frame_bgr: np.ndarray, face: Face) -> np.ndarray:
        aligned = self._rec.alignCrop(frame_bgr, face.raw)
        vec = self._rec.feature(aligned).reshape(-1).astype(np.float32)
        return vec / (np.linalg.norm(vec) + 1e-9)
