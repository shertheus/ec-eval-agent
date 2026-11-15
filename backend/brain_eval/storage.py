"""Single-host persistence; files are committed before run success is recorded."""
import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


def root():
    p = Path(os.environ.get("BRAIN_EVAL_WORKSPACE", "workspace")).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def identifier(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def checked_id(value):
    if not re.fullmatch(r"[a-z]+_[a-f0-9]{16}", value):
        raise ValueError("invalid identifier")
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    with tmp.open("w") as f:
        f.write(canonical(value) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path):
    return json.loads(Path(path).read_text())


@contextmanager
def db():
    conn = sqlite3.connect(root()/"state.sqlite", timeout=20)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize():
    with db() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript("""
        CREATE TABLE IF NOT EXISTS experiments (
          id TEXT PRIMARY KEY, idem TEXT UNIQUE, protocol_hash TEXT,
          protocol TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS runs (
          id TEXT PRIMARY KEY, experiment_id TEXT, config TEXT,
          status TEXT, attempt INTEGER DEFAULT 0, pid INTEGER,
          started REAL, ended REAL, error TEXT);
        CREATE TABLE IF NOT EXISTS events (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          run_id TEXT, status TEXT, time REAL, detail TEXT);
        """)


def event(c, run_id, status, detail=""):
    c.execute("INSERT INTO events(run_id,status,time,detail) VALUES(?,?,?,?)",
              (run_id, status, time.time(), detail))


def experiment_dir(exp_id):
    return root()/"experiments"/checked_id(exp_id)


def attempt_dir(exp_id, run_id, attempt):
    return experiment_dir(exp_id)/"runs"/checked_id(run_id)/f"attempt-{int(attempt)}"
