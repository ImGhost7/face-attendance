"""Download the two OpenCV Zoo models (run once, on a PC with normal internet access).

    python scripts/download_models.py
"""
import sys
import urllib.request
from pathlib import Path

BASE = "https://github.com/opencv/opencv_zoo/raw/main/models"
FILES = {
    "face_detection_yunet_2023mar.onnx": f"{BASE}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx": f"{BASE}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}
MIN_BYTES = 100_000  # a Git-LFS pointer / error page is tiny; a real model is not

dest = Path(__file__).resolve().parent.parent / "models"
dest.mkdir(exist_ok=True)
for name, url in FILES.items():
    out = dest / name
    if out.exists() and out.stat().st_size > MIN_BYTES:
        print(f"ok   {name} (already present)")
        continue
    print(f"get  {name} ...")
    urllib.request.urlretrieve(url, out)
    if out.stat().st_size < MIN_BYTES:
        out.unlink()
        sys.exit(f"FAILED {name}: downloaded file is too small (blocked or LFS pointer). Download it manually from the OpenCV Zoo.")
    print(f"ok   {name} ({out.stat().st_size // 1024} KB)")
