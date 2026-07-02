PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_fingerprint TEXT NOT NULL UNIQUE,
    issued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    last_seen_at TEXT,
    client_ip TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scrub_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    source_filename TEXT NOT NULL,
    source_content_type TEXT NOT NULL,
    source_size_bytes INTEGER NOT NULL CHECK (source_size_bytes >= 0),
    image_width INTEGER NOT NULL CHECK (image_width > 0),
    image_height INTEGER NOT NULL CHECK (image_height > 0),
    blur_people INTEGER NOT NULL CHECK (blur_people IN (0, 1)),
    remove_text INTEGER NOT NULL CHECK (remove_text IN (0, 1)),
    blur_strength INTEGER NOT NULL CHECK (blur_strength >= 3 AND blur_strength <= 151 AND blur_strength % 2 = 1),
    detect_bodies INTEGER NOT NULL CHECK (detect_bodies IN (0, 1)),
    request_mode TEXT NOT NULL DEFAULT 'upload' CHECK (request_mode IN ('upload', 'live')),
    output_content_type TEXT,
    output_size_bytes INTEGER CHECK (output_size_bytes >= 0),
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    error_message TEXT,
    processing_ms INTEGER CHECK (processing_ms >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    CHECK (
        (status = 'failed' AND error_message IS NOT NULL)
        OR (status IN ('queued', 'processing'))
        OR (status = 'completed' AND output_content_type IS NOT NULL)
    ),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at ON auth_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_scrub_jobs_user_id ON scrub_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_scrub_jobs_created_at ON scrub_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_scrub_jobs_status ON scrub_jobs(status);
