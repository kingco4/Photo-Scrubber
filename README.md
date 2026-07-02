A web-app using React + Python (FastAPI) to scrub unwanted content from photos:

- **Remove text**: OCR (Tesseract) → mask → OpenCV inpaint
- **Blur people**: face detection and optional full-body detection

## Project layout

- `backend/` FastAPI API (`POST /process`)
- `frontend/` React UI (upload → options → process → download, plus live webcam scrub)
- `backend/schema.sql` starter database schema for users, sessions, and scrub job history

## Quickstart (local)

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export PHOTO_SCRUBBER_AUTH_USERNAME=admin
export PHOTO_SCRUBBER_AUTH_PASSWORD='change-this-password'
export PHOTO_SCRUBBER_AUTH_SECRET='replace-with-a-long-random-string'
uvicorn app.main:app --reload --port 8000
```

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Authentication

The API now requires login before image processing.

- `POST /auth/login` accepts `username` and `password` as form fields and sets an HTTP-only session cookie.
- `GET /auth/settings` returns whether an extra access code is required.
- `GET /auth/me` validates the current token.
- `POST /auth/logout` revokes the current token.
- `POST /process` requires `Authorization: Bearer <token>`.
- `POST /process/live` requires `Authorization: Bearer <token>` and is optimized for live webcam frames.

Backend credentials are configured through environment variables:

- `PHOTO_SCRUBBER_AUTH_USERNAME`
- `PHOTO_SCRUBBER_AUTH_PASSWORD`
- `PHOTO_SCRUBBER_AUTH_SECRET`
- `PHOTO_SCRUBBER_AUTH_ACCESS_CODE` (optional second factor)
- `PHOTO_SCRUBBER_TOKEN_TTL_HOURS` (optional, defaults to `12`)
- `PHOTO_SCRUBBER_LOGIN_MAX_ATTEMPTS` (optional, defaults to `5`)
- `PHOTO_SCRUBBER_LOGIN_BLOCK_SECONDS` (optional, defaults to `300`)
- `PHOTO_SCRUBBER_MAX_UPLOAD_BYTES` (optional, defaults to `15728640`)
- `PHOTO_SCRUBBER_MAX_IMAGE_PIXELS` (optional, defaults to `20000000`)
- `PHOTO_SCRUBBER_MIN_IMAGE_WIDTH` (optional, defaults to `16`)
- `PHOTO_SCRUBBER_MIN_IMAGE_HEIGHT` (optional, defaults to `16`)
- `PHOTO_SCRUBBER_MAX_IMAGE_WIDTH` (optional, defaults to `8000`)
- `PHOTO_SCRUBBER_MAX_IMAGE_HEIGHT` (optional, defaults to `8000`)
- `PHOTO_SCRUBBER_LOG_LEVEL` (optional, defaults to `INFO`)
- `PHOTO_SCRUBBER_TEXT_DETECTION_MAX_DIMENSION` (optional, defaults to `1800`)
- `PHOTO_SCRUBBER_FACE_DETECTION_MAX_DIMENSION` (optional, defaults to `1600`)

If you do not set them, the backend falls back to development defaults:

- username: `admin`
- password: `changeme`
- secret: `replace-this-secret`

Additional auth protections:

- optional second-factor access code via `PHOTO_SCRUBBER_AUTH_ACCESS_CODE`
- login rate limiting with temporary lockout after repeated failures
- token revocation on logout
- frontend session state now uses an HTTP-only auth cookie instead of storing the token in `localStorage`
- upload count is tracked per client IP address in memory, without any schema changes
- after 20 successful standard uploads from the same IP address, non-critical upload validations are skipped for faster repeat use

## Validation

The app now validates input on both the client and server:

- login usernames must be non-empty and at most 256 characters
- login passwords must be non-empty and at most 256 characters
- uploads must be JPG, PNG, WebP, HEIC, or HEIF
- uploads may still be accepted when the browser reports an empty or generic MIME type, as long as extension and file signature validation succeed
- filename extensions must match the uploaded MIME type
- uploaded file signatures must match the declared image type
- uploaded content must match the declared image type
- uploads must include a non-empty filename up to 255 characters
- uploads must use a safe filename without control characters or path segments
- uploads must be non-empty and at most 15 MB by default
- animated or multi-frame image uploads are rejected
- images must be valid decodable images, at least 16x16 by default, at most 8000x8000 by default, and at most 20,000,000 pixels by default
- at least one processing option must be enabled
- `blur_strength` must be an odd integer between `3` and `151`

## iPhone Images

HEIC and HEIF uploads are supported through `pillow-heif` on the backend. After changing Python dependencies, reinstall `backend/requirements.txt` before running the API.

## Performance

The API is faster than before in two ways:

- face and body detectors are initialized once at process startup instead of on every request
- OCR and face detection run on downscaled analysis images for large uploads, then map results back to the original image
- live webcam scrubbing uses a dedicated endpoint that resizes frames and returns JPEG output for lower latency

## Logging

The backend now emits additive request logs at startup and for each HTTP request. Set `PHOTO_SCRUBBER_LOG_LEVEL` to values like `DEBUG`, `INFO`, or `WARNING` to adjust verbosity.

## Notes / limitations

This is a starter implementation:
- OCR text removal depends on Tesseract accuracy; low-contrast or stylized fonts may be missed.
- Face/body detection is best-effort; crowded scenes can yield missed/extra detections.
- For production, consider stronger detectors (e.g., modern segmentation models) and configurable inpainting methods.
