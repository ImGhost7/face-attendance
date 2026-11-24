"""SQLite schema (single file, easy to back up). Move to PostgreSQL later if it ever outgrows this."""
import sqlite3

import numpy as np

SCHEMA = """
CREATE TABLE IF NOT EXISTS schedules (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('fixed','flexible')),
  start_time TEXT, end_time TEXT, grace_min INTEGER DEFAULT 10, required_hours REAL DEFAULT 8, core_start TEXT
);
CREATE TABLE IF NOT EXISTS persons (
  id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('employee','vendor','partner','visitor','unknown')),
  role_tag TEXT,                      -- e.g. 'Tea distributor', 'Banner partner'
  schedule_id INTEGER REFERENCES schedules(id),
  pin_hash TEXT,                      -- fallback ID+PIN login (employees only)
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','active','disabled')),
  consent_at TEXT,                    -- when the person agreed to face data being stored
  retain_until TEXT,                  -- visitors/unknown: auto-delete after this
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS face_templates (
  id INTEGER PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
  embedding BLOB NOT NULL, pose TEXT, quality REAL, created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS enrollment_invites (
  code TEXT PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES persons(id), expires_at TEXT NOT NULL, used_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY, person_id INTEGER REFERENCES persons(id),
  camera TEXT NOT NULL, direction TEXT CHECK (direction IN ('in','out','checkin')),
  ts TEXT NOT NULL, method TEXT NOT NULL CHECK (method IN ('face','manual_pin','fingerprint','admin','phone')),
  score REAL, snapshot_path TEXT, flagged INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_events_person_ts ON events(person_id, ts);
CREATE TABLE IF NOT EXISTS field_duty (
  id INTEGER PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES persons(id),
  started_at TEXT NOT NULL, ended_at TEXT
);
CREATE TABLE IF NOT EXISTS location_pings (   -- only written while a field_duty row is open
  id INTEGER PRIMARY KEY, duty_id INTEGER NOT NULL REFERENCES field_duty(id), ts TEXT NOT NULL, lat REAL, lon REAL, accuracy_m REAL
);
"""


def connect(path) -> sqlite3.Connection:
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    return con


def pack(emb: np.ndarray) -> bytes:
    return np.asarray(emb, dtype=np.float32).tobytes()


def unpack(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)
