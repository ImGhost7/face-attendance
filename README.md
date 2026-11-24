# SmartAds Face Attendance

Face-recognition attendance, entrance IN/OUT tracking and visitor logging for the SmartAds office.
See [docs/PLAN.md](docs/PLAN.md) for the plan and decisions.

## Setup (Windows PC)
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_models.py
python -m pytest
python scripts/check_engine.py photo_of_person_a.jpg photo_of_person_b.jpg
```
`check_engine.py` prints face detection, quality problems and the similarity between two photos.
