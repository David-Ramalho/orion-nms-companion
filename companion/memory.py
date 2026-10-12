from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .config import DATA_DIR

DB_PATH = DATA_DIR / "memory.sqlite3"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY, content TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL)")
    db.commit()
    return db


@contextmanager
def session():
    db = connect()
    try:
        yield db
        db.commit()
    finally:
        db.close()


def add_message(role: str, content: str):
    with session() as db:
        db.execute("INSERT INTO messages(role,content,created_at) VALUES(?,?,?)", (role, content, datetime.now(timezone.utc).isoformat()))


def history(limit=16):
    with session() as db:
        rows = db.execute("SELECT role,content FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in reversed(rows)]


def add_fact(content: str):
    content = content.strip()
    if not content:
        return
    with session() as db:
        db.execute("INSERT OR IGNORE INTO facts(content,created_at) VALUES(?,?)", (content, datetime.now(timezone.utc).isoformat()))


def facts():
    with session() as db:
        return [r[0] for r in db.execute("SELECT content FROM facts ORDER BY id DESC LIMIT 40")]


def clear_history():
    with session() as db:
        db.execute("DELETE FROM messages")
