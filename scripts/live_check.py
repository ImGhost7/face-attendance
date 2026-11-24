"""Live webcam check of the real models. Nothing is saved: frames stay in memory only.

    python scripts/live_check.py            # you alone
    python scripts/live_check.py --other    # adds a final stage where a second person steps in

Stages (a beep + printed prompt marks each start):
  1 ENROL    look straight at the camera      -> builds a mini "gallery" from good frames
  2 PROBE    look straight again, relax       -> similarity vs gallery (should be high)
  3 LEFT     slowly turn head to your left    -> pose values + similarity under rotation
  4 RIGHT    slowly turn head to your right
  5 OTHER    (--other) second person looks at the camera -> similarity vs you (should be low)
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from faceattend.config import Settings  # noqa: E402
from faceattend.recognition.engine import FaceEngine  # noqa: E402
from faceattend.recognition.quality import check_quality, estimate_pose  # noqa: E402

try:
    import winsound
except ImportError:  # not Windows
    winsound = None


def beep():
    if winsound:
        winsound.Beep(1000, 250)


def say(msg):
    print(msg, flush=True)


def run_stage(cap, engine, s, name, prompt, seconds, gallery=None):
    say(f"\n=== {name}: {prompt} ({seconds}s) ===")
    beep()
    t_end = time.time() + seconds
    rows = []  # dicts per frame
    frames = 0
    while time.time() < t_end:
        ok, frame = cap.read()
        if not ok:
            continue
        frames += 1
        t0 = time.perf_counter()
        faces = engine.detect(frame)
        det_ms = (time.perf_counter() - t0) * 1000
        if not faces:
            rows.append({"face": False})
            continue
        f = faces[0]
        yaw, pitch = estimate_pose(f.landmarks)
        problems = check_quality(frame, f.box, f.landmarks, s, frontal=False)
        frontal_problems = check_quality(frame, f.box, f.landmarks, s, frontal=True)
        t1 = time.perf_counter()
        emb = engine.embed(frame, f)
        emb_ms = (time.perf_counter() - t1) * 1000
        row = {
            "face": True, "n": len(faces), "score": f.score, "w": f.box[2], "h": f.box[3],
            "yaw": yaw, "pitch": pitch, "problems": problems, "frontal_ok": not frontal_problems,
            "det_ms": det_ms, "emb_ms": emb_ms, "emb": emb,
        }
        if gallery is not None and len(gallery):
            row["sim"] = float(np.max(gallery @ emb))
        rows.append(row)
    faced = [r for r in rows if r["face"]]
    say(f"frames read: {frames}   frames with a face: {len(faced)}")
    if faced:
        arr = lambda k: np.array([r[k] for r in faced], dtype=float)  # noqa: E731
        say(f"detector score  min/mean: {arr('score').min():.2f} / {arr('score').mean():.2f}")
        say(f"face size px    min/mean: {min(arr('w').min(), arr('h').min()):.0f} / {arr('w').mean():.0f} wide")
        say(f"yaw   min/mean/max: {arr('yaw').min():+.2f} / {arr('yaw').mean():+.2f} / {arr('yaw').max():+.2f}   (gate |yaw|<={s.max_yaw_frontal})")
        say(f"pitch min/mean/max: {arr('pitch').min():+.2f} / {arr('pitch').mean():+.2f} / {arr('pitch').max():+.2f}")
        say(f"timing ms  detect mean: {arr('det_ms').mean():.1f}   embed mean: {arr('emb_ms').mean():.1f}")
        say(f"frames passing frontal quality gate: {sum(r['frontal_ok'] for r in faced)}/{len(faced)}")
        probs = {}
        for r in faced:
            for p in r["problems"]:
                probs[p] = probs.get(p, 0) + 1
        say(f"quality problems (excluding pose): {probs or 'none'}")
        if any(len(r) and r.get("n", 1) > 1 for r in faced):
            say(f"NOTE: more than one face seen in {sum(r['n'] > 1 for r in faced)} frames")
        sims = np.array([r["sim"] for r in faced if "sim" in r])
        if len(sims):
            say(f"similarity vs gallery  min/mean/max: {sims.min():.3f} / {sims.mean():.3f} / {sims.max():.3f}")
            say(f"  frames >= match_threshold {s.match_threshold}: {(sims >= s.match_threshold).sum()}/{len(sims)}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--other", action="store_true", help="add a stage for a second person")
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()

    s = Settings()
    engine = FaceEngine(s)
    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    if not cap.isOpened():
        sys.exit("Could not open the camera.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    say(f"camera opened: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    say("Get ready - first stage starts in 5 seconds. Sit about 60-80 cm from the screen, face the camera.")
    t_end = time.time() + 5
    while time.time() < t_end:  # warm-up: lets auto-exposure settle
        cap.read()

    try:
        r1 = run_stage(cap, engine, s, "1 ENROL", "look STRAIGHT at the camera", 6)
        good = [r["emb"] for r in r1 if r["face"] and r["frontal_ok"] and not r["problems"]]
        say(f"-> usable enrolment frames: {len(good)}")
        if len(good) < 3:
            say("Too few good frames to build a gallery; check the problems above (light/blur/size) and re-run.")
            return
        gallery = np.stack(good[:: max(1, len(good) // 5)][:5])  # up to 5 spread-out samples
        say(f"-> gallery built from {len(gallery)} frames")

        # self-consistency of the gallery
        sim_matrix = gallery @ gallery.T
        off = sim_matrix[~np.eye(len(gallery), dtype=bool)]
        say(f"-> gallery self-similarity min/mean: {off.min():.3f} / {off.mean():.3f}")

        run_stage(cap, engine, s, "2 PROBE", "look straight again, relax your face, maybe lean a little closer/further", 6, gallery)
        run_stage(cap, engine, s, "3 LEFT", "slowly turn your head to YOUR LEFT, hold, come back", 6, gallery)
        run_stage(cap, engine, s, "4 RIGHT", "slowly turn your head to YOUR RIGHT, hold, come back", 6, gallery)
        if args.other:
            say("\nSwap: a SECOND person should take the seat now. Starting in 8 seconds.")
            t_end = time.time() + 8
            while time.time() < t_end:
                cap.read()
            run_stage(cap, engine, s, "5 OTHER", "second person looks STRAIGHT at the camera", 6, gallery)
    finally:
        cap.release()
        say("\nDone. No images or embeddings were saved.")


if __name__ == "__main__":
    main()
