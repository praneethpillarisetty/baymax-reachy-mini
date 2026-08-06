from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class LocalStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY, title TEXT NOT NULL, due_at TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0);
              CREATE TABLE IF NOT EXISTS wellness(id INTEGER PRIMARY KEY, kind TEXT NOT NULL, value TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
              CREATE TABLE IF NOT EXISTS appointment_notes(id INTEGER PRIMARY KEY, note TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            """)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def export(self, destination: Path) -> None:
        data: dict[str, list[dict[str, Any]]] = {}
        with self.connect() as db:
            for table in ("reminders", "wellness", "appointment_notes"):
                data[table] = [dict(row) for row in db.execute(f"SELECT * FROM {table}")]  # noqa: S608
        destination.write_text(json.dumps(data, indent=2))

    def delete_all(self) -> None:
        with self.connect() as db:
            for table in ("reminders", "wellness", "appointment_notes"):
                db.execute(f"DELETE FROM {table}")  # noqa: S608
