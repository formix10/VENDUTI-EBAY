import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(os.getenv("DB_PATH", "data/venduti.sqlite3"))

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS categories (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      min_price REAL NOT NULL DEFAULT 0,
      enabled INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS sales (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      category_id TEXT NOT NULL,
      external_id TEXT,
      title TEXT NOT NULL,
      price REAL NOT NULL,
      currency TEXT NOT NULL DEFAULT 'EUR',
      sold_at TEXT,
      url TEXT,
      image_url TEXT,
      captured_at TEXT NOT NULL,
      UNIQUE(category_id, external_id)
    );
    CREATE TABLE IF NOT EXISTS api_calls (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at TEXT NOT NULL,
      category_id TEXT,
      status TEXT NOT NULL,
      http_code INTEGER
    );
    """)
    return con

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def monthly_calls(con):
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return con.execute("SELECT COUNT(*) FROM api_calls WHERE substr(created_at,1,7)=?", (month,)).fetchone()[0]
