# Scubber Backend (FastAPI)

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Database Schema

A starter relational schema is included in [schema.sql](/Users/king/Photo-Scrubber/backend/schema.sql) for future persistence work. It defines:

- `users` for application accounts
- `auth_sessions` for issued tokens or session tracking
- `scrub_jobs` for upload/live processing history and outcomes

The `scrub_jobs` table now enforces that failed jobs carry an `error_message`, while completed jobs carry an `output_content_type`.

It is not wired into the current FastAPI app yet.

## Run

```bash
export PHOTO_SCRUBBER_AUTH_USERNAME=admin
export PHOTO_SCRUBBER_AUTH_PASSWORD='change-this-password'
export PHOTO_SCRUBBER_AUTH_SECRET='replace-with-a-long-random-string'
export PHOTO_SCRUBBER_AUTH_ACCESS_CODE='optional-second-factor'
export PHOTO_SCRUBBER_LOG_LEVEL=INFO
uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /health`
- `GET /auth/settings`
- `POST /auth/login` (`username`, `password` form fields)
- `GET /auth/me` (requires `Authorization: Bearer <token>`)
- `POST /auth/logout` (requires `Authorization: Bearer <token>`)
- `POST /process` (requires `Authorization: Bearer <token>`, multipart form):
  - `file` (image)
  - `blur_people` (bool)
  - `remove_text` (bool)
  - `blur_strength` (int, 3..151)
  - `detect_bodies` (bool, slower but can catch full-body people)
- `POST /process/live` (requires `Authorization: Bearer <token>`, multipart form):
  - `file` (frame image)
  - `blur_people` (bool)
  - `remove_text` (bool)
  - `blur_strength` (int, 3..151)
  - `detect_bodies` (bool)
  - `max_dimension` (int, 160..1920, capped by server)
  - `jpeg_quality` (int, 40..95)

## Validation

- login usernames: non-empty, up to 256 characters
- login passwords: non-empty, up to 256 characters
- accepted upload content types: `image/jpeg`, `image/png`, `image/webp`, `image/heic`, `image/heif`
- browser uploads with empty or generic MIME types can still be accepted when extension and file-signature checks agree
- filename extensions must match the declared content type
- file signatures must match the declared content type
- uploaded content must match the declared content type
- uploaded files must include a non-empty filename up to 255 characters
- uploaded filenames must not contain control characters or path segments
- max upload size: `PHOTO_SCRUBBER_MAX_UPLOAD_BYTES` or `15728640` by default
- animated or multi-frame images are not supported
- min image width and height: `PHOTO_SCRUBBER_MIN_IMAGE_WIDTH` and `PHOTO_SCRUBBER_MIN_IMAGE_HEIGHT` or `16`
- max image width and height: `PHOTO_SCRUBBER_MAX_IMAGE_WIDTH` and `PHOTO_SCRUBBER_MAX_IMAGE_HEIGHT` or `8000`
- max image area: `PHOTO_SCRUBBER_MAX_IMAGE_PIXELS` or `20000000` by default
- text detection analysis max dimension: `PHOTO_SCRUBBER_TEXT_DETECTION_MAX_DIMENSION` or `1800`
- face detection analysis max dimension: `PHOTO_SCRUBBER_FACE_DETECTION_MAX_DIMENSION` or `1600`
- at least one of `blur_people` or `remove_text` must be `true`
- `blur_strength` must be an odd integer from `3` to `151`

## HEIC / HEIF

The backend registers HEIC/HEIF support through `pillow-heif`. Install or reinstall `requirements.txt` after pulling these changes so iPhone photo uploads can be decoded.

## Logging

The backend logs startup plus one line for request start and completion. Use `PHOTO_SCRUBBER_LOG_LEVEL` to control verbosity.

## Performance

For lower latency, the backend reuses OpenCV detectors across requests and exposes `/process/live` for resized JPEG webcam frames.
It also downsizes large images for OCR and face-detection analysis before mapping the results back to the original resolution.

## Authentication Hardening

- Optional second-factor access code through `PHOTO_SCRUBBER_AUTH_ACCESS_CODE`
- Login rate limiting through `PHOTO_SCRUBBER_LOGIN_MAX_ATTEMPTS` and `PHOTO_SCRUBBER_LOGIN_BLOCK_SECONDS`
- Token revocation on `/auth/logout`
- Login now sets an HTTP-only session cookie. Configure `PHOTO_SCRUBBER_AUTH_COOKIE_NAME` and `PHOTO_SCRUBBER_AUTH_COOKIE_SECURE` if needed.
- Standard image uploads are counted per client IP address in server memory and exposed through `/auth/me` plus the `X-IP-Upload-Count` response header on `/process`.
- After `20` successful standard uploads from the same IP address, the backend skips non-critical upload validation checks while still enforcing core safety checks like file size, decoding, and image dimension limits.
