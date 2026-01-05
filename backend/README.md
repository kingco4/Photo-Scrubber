# Scubber Backend (FastAPI)

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /health`
- `POST /process` (multipart form):
  - `file` (image)
  - `blur_people` (bool)
  - `remove_text` (bool)
  - `blur_strength` (int, 3..151)
  - `detect_bodies` (bool, slower but can catch full-body people)
