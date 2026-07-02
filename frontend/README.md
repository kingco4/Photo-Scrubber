# Scubber Frontend (React + Vite)

## Setup

```bash
cd frontend
npm install
```

## Run

```bash
npm run dev
```

By default it calls `http://localhost:8000`. To change:

```bash
VITE_API_BASE=http://localhost:8000 npm run dev
```

Before processing images, sign in through the UI using the backend credentials set with:

- `PHOTO_SCRUBBER_AUTH_USERNAME`
- `PHOTO_SCRUBBER_AUTH_PASSWORD`

The UI validates that login fields are non-empty and reasonably bounded, checks blur strength, and rejects uploads outside the supported JPG/PNG/WebP/HEIC/HEIF set. It also tolerates browsers that report an empty or generic MIME type for valid image files, as long as the filename extension is supported. HEIC and HEIF files are accepted for server-side validation even when the browser cannot preview them locally.

The app also includes a live webcam scrub panel that captures frames with `getUserMedia`, sends them to `/process/live`, and displays the scrubbed result continuously.

If the backend enables `PHOTO_SCRUBBER_AUTH_ACCESS_CODE`, the login form will automatically show an extra access-code field based on `/auth/settings`.

Login state is now maintained by an HTTP-only cookie, so the frontend no longer stores the auth token in `localStorage`.

The page also shows how many standard uploads have been made in the current authenticated session, without any database schema changes.

After 20 successful standard uploads from the same IP address, the UI stops running pre-upload validation checks and lets the backend handle the remaining core safety checks.
