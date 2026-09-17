"""Small JSON-file persistence layer.

This is intentionally simple: a single JSON file on disk, guarded by an
in-process lock and written atomically (write to a temp file, then rename)
so a crash mid-write can never corrupt the store. It is not meant to scale
to concurrent multi-process writers -- for this project's purposes it just
needs to demonstrate a real Docker volume mount with real persistence.
"""

import json
import logging
import os
import tempfile
import threading
from pathlib import Path

from app.schemas import Item

logger = logging.getLogger("app.storage")


class ItemStore:
    """Thread-safe JSON file store for Item records."""

    def __init__(self, data_file: str):
        self._path = Path(data_file)
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            logger.info("Data file not found, creating a new one at %s", self._path)
            self._write_raw([])

    def _read_raw(self) -> list[dict]:
        try:
            with self._path.open("r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Data file was unreadable or corrupted (%s); starting empty", exc)
            return []

    def _write_raw(self, records: list[dict]) -> None:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._path.parent), prefix=".items-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, default=str)
            os.replace(tmp_path, self._path)
        except OSError:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def list_items(self) -> list[Item]:
        with self._lock:
            return [Item(**record) for record in self._read_raw()]

    def get_item(self, item_id: str) -> Item | None:
        with self._lock:
            for record in self._read_raw():
                if record.get("id") == item_id:
                    return Item(**record)
        return None

    def add_item(self, item: Item) -> Item:
        with self._lock:
            records = self._read_raw()
            records.append(json.loads(item.model_dump_json()))
            self._write_raw(records)
        return item

    def delete_item(self, item_id: str) -> bool:
        with self._lock:
            records = self._read_raw()
            filtered = [r for r in records if r.get("id") != item_id]
            if len(filtered) == len(records):
                return False
            self._write_raw(filtered)
        return True
