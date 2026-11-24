"""Smoke test for the real models. Usage:  python scripts/check_engine.py path/to/photo.jpg [other_photo.jpg]

With two photos it prints their similarity (same person should be > ~0.45, different people < ~0.3).
"""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from faceattend.config import Settings  # noqa: E402
from faceattend.recognition.engine import FaceEngine  # noqa: E402
from faceattend.recognition.quality import check_quality, estimate_pose  # noqa: E402

s = Settings()
engine = FaceEngine(s)
embs = []
for path in sys.argv[1:]:
    img = cv2.imread(path)
    faces = engine.detect(img)
    print(f"{path}: {len(faces)} face(s)")
    if not faces:
        continue
    f = faces[0]
    print("  score", round(f.score, 3), "box", f.box, "pose(yaw,pitch)", [round(v, 2) for v in estimate_pose(f.landmarks)])
    print("  quality problems:", check_quality(img, f.box, f.landmarks, s) or "none")
    embs.append(engine.embed(img, f))
if len(embs) == 2:
    print("cosine similarity:", round(float(embs[0] @ embs[1]), 3))
