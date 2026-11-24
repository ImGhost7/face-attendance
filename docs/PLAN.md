# SmartAds Face Attendance - Plan & Decisions

Status: planning agreed with the project lead; owner approval for a pilot confirmed.

## Facts
- ~25-30 employees, one basement entrance (artificial lighting, no sunlight glare).
- Company server: Windows PC, on 24/7, runs the CCTV (specs unknown - to be collected).
- Cameras: CCTV with IR night mode + microphones (brand unknown). **Audio is out of scope.**
- Location: Mumbai, India -> DPDP Act 2023 applies (consent, purpose limitation, retention, security).
- Existing fingerprint attendance stays running in parallel during the pilot.
- Some staff have flexible hours, some fixed hours -> modelled as a *schedule assigned per employee*.
- Field staff exist -> "Field Duty" status; phone app tracks location **only while on duty**.
- Everything runs locally on the office network (phone app later via VPN).

## Decisions
| Topic | Decision | Why |
|---|---|---|
| Models | OpenCV Zoo YuNet (detect) + SFace (recognise) | MIT / Apache-2.0: safe for commercial use, CPU-friendly. InsightFace's pretrained models are **non-commercial only**, so they are not used. |
| Matching | cosine, threshold 0.45, margin 0.08, 3-of-5 frame vote | A wrong "present" is worse than a retry. Tune in the pilot. |
| Liveness | Random head-turn challenge (Phase 1) | Stops photo attacks. Video replay needs depth/IR or an anti-spoof model (evaluate later). |
| Enrollment | Admin creates employee -> one-time invite -> face wizard -> admin approves | Stops visitors registering as employees. |
| Fallback | ID + PIN, snapshot saved, flagged for review | Audit trail; fallback rate = health metric of the face system. |
| Entrance | Dedicated face-height cameras (IN + OUT) with steady light; do not reuse IR ceiling CCTV | IR greyscale + high angle ruin recognition. |
| Kiosk | Android tablet, browser kiosk, talks to the server over LAN | Needs HTTPS on LAN for camera access (local certificate) - Phase 2 task. |
| Storage | SQLite file on the server, embeddings (not photos) + encrypted folder + daily backup | Simple, easy to back up. |
| Repo | Git + remote branch from day one | The previous system's files were lost. |

## Phases
1. **Recognition engine** - detect, embed, quality gates, matcher, vote, liveness. *(code + tests written; real-model check pending)*
2. Kiosk UI + enrollment wizard (5 poses, duplicate check, quality feedback).
3. Admin panel: employees, schedules, late/short/overtime, corrections, fallback review.
4. Entrance IN/OUT cameras (RTSP), presence logic, live in/out widget, daily summary + emailed report.
5. Vendors / partners / visitors, unknown-face grouping, retention auto-delete.
6. Pilot (3-5 people, 2-4 weeks next to the fingerprint system), threshold tuning, liveness upgrade, rollout.
7. Phone app: field duty start/stop, location pings only while on duty, consent screen.

## Done so far (this repo)
- `faceattend/recognition/` engine wrappers, quality gates, matcher + duplicate guard, vote tracker, head-turn liveness.
- `faceattend/attendance/` event dedupe, daily presence summary (inside/outside time, exits, missing OUT), schedule rules.
- `faceattend/db.py` full schema (persons, templates, invites, events, field duty, location pings).
- 21 unit tests (pure logic).
- `engine.py` verified against the real models on the dev laptop (OpenCV 5.1, Py 3.14, webcam): same-person similarity 0.68-0.93,
  detect ~35-100 ms + embed ~11-38 ms per frame on CPU. **Still unverified:** impostor (different-person) similarity,
  and the yaw proxy under real head turns (frontal baseline reads about +0.12, not 0).

## Needed from the office
1. Server specs (Task Manager -> Performance: CPU, RAM, GPU; Windows version; free disk).
2. CCTV brand/model and whether it is an NVR/DVR or software; is an RTSP stream available?
3. Android tablet model for the kiosk; location for the dedicated entrance cameras and lights.
4. Written owner approval + employee consent notice (draft to be prepared).
5. Fixed/flexible schedule rules in detail, holidays, weekly offs.
