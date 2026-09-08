# Homians Education — Attendance Backend

Django REST API for student attendance (Present / Leave / Absent), monthly summary, and student history export.

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

API base: `http://127.0.0.1:8000/api/`

### Main endpoints
- `GET/POST /api/students/`
- `GET/POST/PATCH /api/attendance/`
- `GET /api/attendance/monthly-summary/?year=2026&month=9`
- `GET /api/students/{id}/history/`
- `GET /api/students/{id}/download-history/`
