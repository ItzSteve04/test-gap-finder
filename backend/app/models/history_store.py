"""
Persistent analysis history store backed by SQLite (stdlib sqlite3).

DB file: backend/data/history.db  (created on first use)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "history.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS analyses (
  id                     TEXT PRIMARY KEY,
  title                  TEXT NOT NULL,
  repository             TEXT NOT NULL,
  source_type            TEXT,
  status                 TEXT NOT NULL,
  error_message          TEXT,
  created_at             TEXT NOT NULL,
  updated_at             TEXT NOT NULL,
  python_files           INTEGER,
  test_files             INTEGER,
  gaps_count             INTEGER,
  generated_tests_count  INTEGER,
  coverage_before        REAL,
  coverage_after         REAL,
  tests_passed           INTEGER,
  tests_failed           INTEGER,
  result_json            TEXT
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init_db() -> None:
    """Ensure backend/data/ exists and create the table/index if missing."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute(_CREATE_TABLE)
        conn.execute(_CREATE_INDEX)
        conn.commit()


def create_running_entry(id: str, title: str, repository: str, source_type: str) -> None:
    """Insert a new row with status='running'."""
    now = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO analyses
              (id, title, repository, source_type, status, error_message,
               created_at, updated_at)
            VALUES (?, ?, ?, ?, 'running', NULL, ?, ?)
            """,
            (id, title, repository, source_type, now, now),
        )
        conn.commit()


def complete_entry(id: str, result: dict) -> None:
    """Mark an entry as completed and store the full result payload."""
    test_results = result.get("test_results") or {}
    with _connect() as conn:
        conn.execute(
            """
            UPDATE analyses SET
              status                = 'completed',
              updated_at            = ?,
              python_files          = ?,
              test_files            = ?,
              gaps_count            = ?,
              generated_tests_count = ?,
              coverage_before       = ?,
              coverage_after        = ?,
              tests_passed          = ?,
              tests_failed          = ?,
              result_json           = ?
            WHERE id = ?
            """,
            (
                _now(),
                result.get("python_files"),
                result.get("test_files"),
                len(result.get("gaps") or []),
                len(result.get("generated_tests") or []),
                test_results.get("coverage_before"),
                test_results.get("coverage_after"),
                test_results.get("passed"),
                test_results.get("failed"),
                json.dumps(result),
                id,
            ),
        )
        conn.commit()


def fail_entry(id: str, error_message: str) -> None:
    """Mark an entry as failed."""
    with _connect() as conn:
        conn.execute(
            "UPDATE analyses SET status='failed', updated_at=?, error_message=? WHERE id=?",
            (_now(), error_message, id),
        )
        conn.commit()


def list_entries(query: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    """Return summary rows (no result_json), newest first."""
    with _connect() as conn:
        if query:
            pattern = f"%{query}%"
            rows = conn.execute(
                """
                SELECT id, title, repository, source_type, status, error_message,
                       created_at, updated_at, python_files, test_files, gaps_count,
                       generated_tests_count, coverage_before, coverage_after,
                       tests_passed, tests_failed
                FROM analyses
                WHERE LOWER(title) LIKE LOWER(?) OR LOWER(repository) LIKE LOWER(?)
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (pattern, pattern, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, title, repository, source_type, status, error_message,
                       created_at, updated_at, python_files, test_files, gaps_count,
                       generated_tests_count, coverage_before, coverage_after,
                       tests_passed, tests_failed
                FROM analyses
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
    return [dict(row) for row in rows]


def get_entry(id: str) -> dict | None:
    """Return the full row with result_json decoded, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM analyses WHERE id = ?", (id,)
        ).fetchone()
    if row is None:
        return None
    data = dict(row)
    if data.get("result_json"):
        data["result_json"] = json.loads(data["result_json"])
    return data


def rename_entry(id: str, title: str) -> bool:
    """Update the title. Returns False if id not found."""
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE analyses SET title=?, updated_at=? WHERE id=?",
            (title, _now(), id),
        )
        conn.commit()
    return cursor.rowcount > 0


def delete_entry(id: str) -> bool:
    """Delete the row. Returns False if id not found."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM analyses WHERE id=?", (id,))
        conn.commit()
    return cursor.rowcount > 0
