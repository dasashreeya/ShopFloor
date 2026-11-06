"""Tiny SQLite document store: one table, (collection, id) -> JSON. Swap for Postgres later."""

import json
import sqlite3
import threading
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


class Store:
    def __init__(self, path: str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS docs (collection TEXT, id TEXT, body TEXT, PRIMARY KEY (collection, id))"
        )

    def put(self, collection: str, doc: BaseModel, key: str | None = None) -> None:
        key = key or getattr(doc, "id")
        with self._lock, self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO docs VALUES (?, ?, ?)", (collection, key, doc.model_dump_json())
            )

    def get(self, collection: str, key: str, model: type[M]) -> M | None:
        with self._lock:
            row = self._db.execute(
                "SELECT body FROM docs WHERE collection = ? AND id = ?", (collection, key)
            ).fetchone()
        return model.model_validate(json.loads(row[0])) if row else None

    def delete(self, collection: str, key: str) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM docs WHERE collection = ? AND id = ?", (collection, key))

    def list(self, collection: str, model: type[M], **where) -> list[M]:
        with self._lock:
            rows = self._db.execute("SELECT body FROM docs WHERE collection = ?", (collection,)).fetchall()
        docs = [model.model_validate(json.loads(r[0])) for r in rows]
        return [d for d in docs if all(getattr(d, k) == v for k, v in where.items())]
