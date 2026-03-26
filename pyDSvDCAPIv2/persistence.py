import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_AUTO_SAVE_DELAY = 1.0  # seconds


class PropertyStore:
    """Atomic YAML persistence with .bak backup and debounced auto-save."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._tmp = self._path.with_suffix(".yaml.tmp")
        self._bak = self._path.with_suffix(".yaml.bak")
        self._pending: dict[str, Any] | None = None
        self._save_task: asyncio.Task | None = None

    def load(self) -> dict[str, Any]:
        """Load state from YAML. Falls back to .bak if primary is corrupt/missing."""
        for candidate in (self._path, self._bak):
            if candidate.exists():
                try:
                    with open(candidate, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        return data
                except Exception as e:
                    logger.warning("Failed to load %s: %s", candidate, e)
        return {}

    def save(self, data: dict[str, Any]) -> None:
        """Write data to YAML atomically with backup.

        On each save the previous primary file (if any) is copied to .bak
        before being replaced.  On the very first save, the newly-written
        file is also copied to .bak so that a valid backup always exists.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._tmp, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
        if self._path.exists():
            shutil.copy2(self._path, self._bak)
        os.replace(self._tmp, self._path)
        # Ensure a .bak always exists (covers first-ever save).
        if not self._bak.exists():
            shutil.copy2(self._path, self._bak)

    def stage(self, data: dict[str, Any]) -> None:
        """Stage data for debounced auto-save (call flush() or await auto-save)."""
        self._pending = data

    def flush(self) -> None:
        """Immediately save any staged data."""
        if self._pending is not None:
            self.save(self._pending)
            self._pending = None

    async def schedule_save(self, data: dict[str, Any]) -> None:
        """Debounced save: waits AUTO_SAVE_DELAY seconds then saves."""
        self._pending = data
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
        self._save_task = asyncio.create_task(self._delayed_save())

    async def _delayed_save(self) -> None:
        try:
            await asyncio.sleep(_AUTO_SAVE_DELAY)
            if self._pending is not None:
                self.save(self._pending)
                self._pending = None
        except asyncio.CancelledError:
            pass
