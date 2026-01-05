A web-app using React + Python (FastAPI) to scrub unwanted content from photos:

- **Remove text**: OCR (Tesseract) → mask → OpenCV inpaint
- **Blur people**: face detection and optional full-body detection

## Project layout

- `backend/` FastAPI API (`POST /process`)
- `frontend/` React UI (upload → options → process → download)

## Quickstart (local)

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Notes / limitations

This is a starter implementation:
- OCR text removal depends on Tesseract accuracy; low-contrast or stylized fonts may be missed.
- Face/body detection is best-effort; crowded scenes can yield missed/extra detections.
- For production, consider stronger detectors (e.g., modern segmentation models) and configurable inpainting methods.
