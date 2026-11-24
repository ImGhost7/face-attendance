# Handoff prompt - paste this into a NEW Claude Code chat opened in the project folder

---

You are continuing a project I (the user) started in an earlier Claude Code chat. Read this whole message, then read `docs/PLAN.md` and `README.md` in the project folder before doing anything.

## Project
Build, from scratch, a **face-recognition attendance + office entrance tracking system** for my company **SmartAds** (an advertising company, Borivali, Mumbai, India). It must go live in the real office. My earlier 2025 attempt was only a beta and its files are lost, so everything is new. I am **not the owner**; the **owner has approved a pilot**.

## What the system must do
1. **Kiosk attendance screen** (external camera): detect face -> check liveness -> match against stored employee faces -> if confident, mark present for the day and greet by name.
2. **If face matching fails:** ask "Employee or new employee?"
   - Employee -> own ID + PIN (fallback). Save a snapshot, flag the record "manual" for admin review. Face matching is the main path; this must be rare.
   - New employee -> registration with Face-ID-like quality checks (several poses, blur/light/size checks, duplicate-face check) and store the face data. **Registration must NOT be open to anyone:** admin creates the employee first and issues a one-time invite code/QR; admin approves the enrollment.
3. **Entrance cameras (later phase):** one entrance (basement, artificial lighting, no sunlight glare), an IN camera and an OUT camera. Auto-detect faces, log IN/OUT events.
4. **Admin side:** the company already has an admin/CCTV control with all live camera feeds. I want a separate widget (bottom-right) listing employee names with In/Out status, and an **end-of-day summary** per person: first in, last out, time in office, time out of office, exits, late arrival, short hours, overtime.
5. **Non-employees:** customers, daily tea distributor, banner-holding partners, etc. The system cannot guess these from appearance. Design: categories (employee / vendor / partner / visitor / unknown); regular vendors are enrolled once with a role tag and get a visit log (no attendance); unknown faces are logged as "Unknown #N" with a snapshot, repeat visits are grouped automatically, admin can name them with one click; unnamed visitor data auto-deletes after N days; optional pre-registration of expected guests.
6. **Phone app (last phase):** for field staff. "Field Duty" start/stop; **location tracked ONLY while on duty** (GPS at start/stop + a ping every 10-15 min), clear in-app consent notice, no tracking outside duty. Reaches the office server via VPN (WireGuard/Tailscale), because the system is local-only. Field staff count as present (not absent) while on duty.

## Facts about the company/environment
- 25-30 employees. Some have **flexible hours**, some **fixed hours** - model this as a **work schedule assigned per employee** (fixed: start/end/grace; flexible: required hours + optional core start). Never key rules to a personal attribute. Exact rules, holidays and weekly offs are still to be given by me.
- Late arrival must be tracked.
- A **company server PC** (Windows, on 24/7, local only) runs the CCTV and has main access to the cameras. CCTV has IR night vision and microphones. **Specs and camera brand/model are unknown yet** - collect them (see below). **Do not use or record audio.**
- There is an existing **fingerprint attendance** device; it stays running in parallel during the pilot.
- I can install an **Android tablet** at the entrance as the kiosk. Everything stays on the local office network (Windows). Run the system on the company server if its specs allow, otherwise on a dedicated mini PC.
- Location: India -> **DPDP Act 2023** applies: written consent, purpose limitation, retention limits, encrypted storage, restricted access. Draft a one-page employee consent notice and a vendor/visitor notice (I will have a lawyer/CA review them).
- Dev machine: my Windows PC, project folder `C:\Users\Taanshu\Documents\projects\Face Attendance`. GitHub repo: `ImGhost7/face-attendance`, work was pushed to branch `claude/epic-bell-98oxzx`.

## Decisions already made (do not re-litigate without a reason)
- **Models: OpenCV Zoo YuNet (detector, MIT) + SFace (recognizer, Apache-2.0).** Do **not** use InsightFace's pretrained models (buffalo_*): they are non-commercial-research-only and SmartAds is a business. Check the licence of anything else before adopting it.
- Matching: cosine similarity, threshold 0.45 (stricter than OpenCV's 0.363), margin 0.08 over the runner-up, 3-of-5 frame voting. A wrong "present" is worse than a retry. Tune on real data in the pilot.
- Liveness: random head-turn challenge for now (stops photos, NOT video replay). Later evaluate a passive anti-spoof model (e.g. MiniFASNet, Apache-2.0) or a depth/IR camera.
- Use **dedicated face-height entrance cameras with steady white light**, not the ceiling IR CCTV (greyscale + high angle ruin recognition).
- Storage: SQLite on the server, store embeddings (not just photos), encrypted data folder, daily backup, everything in Git.
- Backend Python (FastAPI, OpenCV) as a Windows service; kiosk/admin = web UI (kiosk in a full-screen browser on the tablet; camera access over LAN needs HTTPS with a local certificate); phone app = Flutter, last.

## What already exists in the repo (read it)
`faceattend/recognition/` (engine.py wrappers for YuNet/SFace, quality.py gates + pose proxy, matcher.py with Gallery/identify/find_duplicate/VoteTracker, liveness.py head-turn), `faceattend/attendance/` (presence.py event dedupe + daily summary, schedule.py fixed/flexible rules), `faceattend/db.py` (SQLite schema), `faceattend/config.py` (all thresholds), `scripts/download_models.py`, `scripts/check_engine.py`, `tests/test_core.py` (21 passing tests of the pure logic), `docs/PLAN.md`.
**Not yet verified:** `engine.py` has never run against the real model files (they could not be downloaded in the earlier cloud sandbox). Treat it as untested.

## Your first steps (in order)
1. Confirm which machine you are running on (`hostname`, `systeminfo`, current folder). Say clearly whether this is my dev PC or the company server. If I want work done on the server and you cannot reach it, tell me exactly what you need (e.g. start Claude Code there, or share a folder/Remote Control) instead of guessing.
2. Make sure the project is here (if the folder is empty: `git clone -b claude/epic-bell-98oxzx https://github.com/ImGhost7/face-attendance.git .`). Create the venv, `pip install -r requirements.txt`, `python scripts/download_models.py`, `python -m pytest`. Fix anything that breaks on Windows.
3. **Verify the engine for real:** run `scripts/check_engine.py` on photos of me/colleagues (same person vs different people) and then a live webcam test. Report detection, quality messages and similarity scores, and tune the thresholds in `faceattend/config.py` from the evidence.
4. **Collect hardware facts (read-only, tell me before changing anything):** CPU, RAM, GPU, Windows version, free disk (`Get-ComputerInfo`, `Get-CimInstance Win32_Processor`, `Win32_VideoController`, `Get-PSDrive`). If you are on the server: find the CCTV software/NVR, camera brand/model and whether RTSP streams are available. **Do not change CCTV settings, passwords, or stop the CCTV service. Do not touch audio.**
5. Then continue the plan in `docs/PLAN.md`: Phase 1 finish (backend API + live camera loop) -> Phase 2 kiosk UI + enrollment wizard -> Phase 3 admin panel -> Phase 4 entrance IN/OUT + summaries -> Phase 5 vendors/visitors -> Phase 6 pilot next to the fingerprint system -> Phase 7 phone app.
6. For UI, design the kiosk and admin screens as a clickable mockup first (kiosk states: idle/scanning, recognised + greeting, liveness prompt, not recognised -> employee/new -> ID+PIN, enrollment wizard, success; admin: dashboard with live in/out list, employee page, daily summary/reports, visitors & vendors, fallback review, settings/cameras). Show me before building.

## Working rules
- Commit often and push to the branch (the previous system's files were lost). Do not create a pull request unless I ask.
- Keep biometric data private: no face images, embeddings or personal details in logs, external services, or commits. Add `data/` and model files to `.gitignore` (already done).
- Ask before anything outward-facing or hard to reverse (sending emails, deleting data, changing the server/CCTV, installing system-wide services).
- Report honestly: if something fails or is untested, say so.

My first request: do steps 1-4 and tell me what you found.
