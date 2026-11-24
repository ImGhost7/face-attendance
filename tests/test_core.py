import random
from datetime import date, datetime, time

import numpy as np

from faceattend.attendance.presence import Event, dedupe, summarize_day
from faceattend.attendance.schedule import Schedule, evaluate
from faceattend.config import Settings
from faceattend.db import connect, pack, unpack
from faceattend.recognition.liveness import HeadTurnChallenge
from faceattend.recognition.matcher import Gallery, VoteTracker
from faceattend.recognition.quality import estimate_pose

S = Settings()
D = date(2026, 11, 24)


def at(h, m=0):
    return datetime(2026, 11, 24, h, m)


def unit(seed, d=128):
    v = np.random.default_rng(seed).normal(size=d).astype(np.float32)
    return v / np.linalg.norm(v)


def noisy(v, amount, seed=99):
    n = v + amount * np.random.default_rng(seed).normal(size=v.shape).astype(np.float32)
    return n / np.linalg.norm(n)


# ---------- matcher ----------
def test_identify_accepts_same_person_rejects_stranger():
    g = Gallery(S)
    g.set_person(1, [unit(1)])
    g.set_person(2, [unit(2)])
    assert g.identify(noisy(unit(1), 0.02)).person_id == 1
    assert g.identify(unit(777)).person_id is None


def test_identify_rejects_ambiguous_match():
    a = unit(1)
    twin = noisy(a, 0.02, seed=5)  # two enrolled people who look almost identical
    g = Gallery(S)
    g.set_person(1, [a])
    g.set_person(2, [twin])
    r = g.identify(a)
    assert not r.accepted and r.person_id is None  # margin rule: better to retry than guess


def test_duplicate_enrollment_detected():
    g = Gallery(S)
    g.set_person(1, [unit(1)])
    assert g.find_duplicate(noisy(unit(1), 0.02)) == 1
    assert g.find_duplicate(noisy(unit(1), 0.02), exclude_id=1) is None
    assert g.find_duplicate(unit(50)) is None


def test_multiple_poses_use_best_sample():
    g = Gallery(S)
    g.set_person(1, [unit(10), unit(11), unit(12)])
    assert g.identify(noisy(unit(12), 0.02)).person_id == 1


def test_vote_tracker_needs_agreement():
    v = VoteTracker(k=3, m=5)
    assert v.push(1) is None
    assert v.push(2) is None  # a stray frame must not confirm anyone
    assert v.push(1) is None
    assert v.push(None) is None
    assert v.push(1) == 1


# ---------- liveness ----------
def landmarks_with_yaw(yaw):
    re, le = np.array([40.0, 50.0]), np.array([80.0, 50.0])
    nose = np.array([60.0 + yaw * 40.0, 70.0])
    return np.array([re, le, nose, [45.0, 95.0], [75.0, 95.0]], dtype=np.float32)


def test_pose_proxy_signs():
    assert abs(estimate_pose(landmarks_with_yaw(0.0))[0]) < 1e-6
    assert estimate_pose(landmarks_with_yaw(0.4))[0] > 0.3
    assert estimate_pose(landmarks_with_yaw(-0.4))[0] < -0.3


def test_headturn_passes_only_after_center_then_turn():
    c = HeadTurnChallenge(direction="image_right")
    assert not c.update(landmarks_with_yaw(0.4))  # a photo already "turned" at the start must not pass
    assert not c.update(landmarks_with_yaw(0.0))
    assert not c.update(landmarks_with_yaw(-0.4))  # wrong way
    assert c.update(landmarks_with_yaw(0.4))


def test_headturn_times_out():
    t = [0.0]
    c = HeadTurnChallenge(direction="image_left", timeout_s=5, clock=lambda: t[0])
    c.update(landmarks_with_yaw(0.0))
    t[0] = 10.0
    assert not c.update(landmarks_with_yaw(-0.4)) and c.expired


def test_challenge_direction_is_random():
    dirs = {HeadTurnChallenge(rng=random.Random(i)).direction for i in range(20)}
    assert dirs == {"image_left", "image_right"}


# ---------- presence ----------
def ev(d, h, m=0):
    return Event(1, d, at(h, m))


def test_dedupe_cooldown():
    out = dedupe([ev("in", 9, 0), Event(1, "in", datetime(2026, 11, 24, 9, 0, 20)), ev("in", 9, 5)], 45)
    assert len(out) == 2


def test_inside_outside_time_and_exits():
    events = [ev("in", 9, 30), ev("out", 13, 0), ev("in", 14, 0), ev("out", 18, 30)]
    s = summarize_day(events, now=at(20), day_end=at(23))
    assert s.first_in == at(9, 30) and s.last_out == at(18, 30)
    assert s.inside_seconds == (3.5 + 4.5) * 3600
    assert s.outside_seconds == 3600 and s.exits == 1 and not s.flags and not s.inside_now


def test_still_inside_counts_until_now():
    s = summarize_day([ev("in", 10)], now=at(12), day_end=at(23))
    assert s.inside_now and s.inside_seconds == 2 * 3600


def test_missing_out_is_closed_and_flagged():
    s = summarize_day([ev("in", 10)], now=at(23, 30), day_end=at(23))
    assert "missing_out" in s.flags and s.inside_seconds == 13 * 3600 and not s.inside_now


def test_out_without_in_flagged():
    s = summarize_day([ev("out", 9), ev("in", 10), ev("out", 12)], now=at(20), day_end=at(23))
    assert "out_without_in" in s.flags and s.inside_seconds == 2 * 3600


# ---------- schedules ----------
FIXED = Schedule("fixed", start=time(10, 0), end=time(18, 30), grace_min=10)
FLEX = Schedule("flexible", required_hours=8, core_start=time(11, 0), grace_min=0)


def day(first, last):
    return summarize_day([Event(1, "in", first), Event(1, "out", last)], now=at(23, 59), day_end=at(23, 30))


def test_fixed_on_time_within_grace():
    assert evaluate(FIXED, day(at(10, 8), at(18, 30)), D).status == "present"


def test_fixed_late_and_overtime():
    e = evaluate(FIXED, day(at(10, 25), at(19, 0)), D)
    assert e.status == "late" and e.late_min == 25 and e.overtime_min == 30


def test_flexible_hours_short_and_overtime():
    assert evaluate(FLEX, day(at(9, 0), at(16, 0)), D).short_min == 60
    assert evaluate(FLEX, day(at(9, 0), at(18, 15)), D).overtime_min == 75


def test_flexible_late_only_after_core_start():
    assert evaluate(FLEX, day(at(10, 0), at(19, 0)), D).status == "present"
    assert evaluate(FLEX, day(at(11, 20), at(20, 0)), D).status == "late"


def test_absent_vs_field_duty():
    empty = summarize_day([], now=at(20), day_end=at(23))
    assert evaluate(FIXED, empty, D).status == "absent"
    e = evaluate(FIXED, empty, D, on_field_duty=True)
    assert e.status == "present" and "field_duty" in e.flags


# ---------- db ----------
def test_db_roundtrip(tmp_path):
    con = connect(tmp_path / "t.db")
    con.execute("INSERT INTO persons(code,name,kind,status) VALUES('E001','Test','employee','active')")
    v = unit(3)
    con.execute("INSERT INTO face_templates(person_id,embedding,pose) VALUES(1,?,?)", (pack(v), "front"))
    row = con.execute("SELECT embedding FROM face_templates").fetchone()
    assert np.allclose(unpack(row["embedding"]), v)


# ---------- quality gates ----------
def test_quality_gates():
    from faceattend.recognition.quality import check_quality

    rng = np.random.default_rng(0)
    sharp = rng.integers(60, 200, size=(300, 300, 3), dtype=np.uint8)  # noisy = high detail
    flat = np.full((300, 300, 3), 20, dtype=np.uint8)  # dark and featureless
    lm = landmarks_with_yaw(0.0)
    assert check_quality(sharp, (80, 80, 140, 140), lm, S) == []
    bad = check_quality(flat, (80, 80, 140, 140), lm, S)
    assert "Too dark" in bad and any("blurry" in p for p in bad)
    assert "Move closer to the camera" in check_quality(sharp, (100, 100, 40, 40), lm, S)
    assert "Keep your whole face inside the frame" in check_quality(sharp, (250, 80, 140, 140), lm, S)
    assert "Look straight at the camera" in check_quality(sharp, (80, 80, 140, 140), landmarks_with_yaw(0.5), S)
