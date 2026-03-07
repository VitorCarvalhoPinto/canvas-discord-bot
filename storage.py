"""Persistência de IDs já enviados (avisos e lembretes) para evitar duplicatas."""
import json
import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).parent / "data" / "sent_ids.json"


class Storage:
    """Simple JSON file storage for sent announcement and reminder IDs."""

    def __init__(self, path: Path = DEFAULT_DB_PATH):
        self.path = path
        self._announcement_ids: Set[int] = set()
        self._reminder_keys: Set[str] = set()  # e.g. "assignment_123_course_456"
        self._load()

    def _load(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save()
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._announcement_ids = set(data.get("announcement_ids", []))
            self._reminder_keys = set(data.get("reminder_keys", []))
        except Exception as e:
            logger.warning("Could not load storage %s: %s", self.path, e)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "announcement_ids": list(self._announcement_ids),
            "reminder_keys": list(self._reminder_keys),
        }
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def announcement_sent(self, announcement_id: int) -> bool:
        return announcement_id in self._announcement_ids

    def mark_announcement_sent(self, announcement_id: int) -> None:
        self._announcement_ids.add(announcement_id)
        self._save()

    def clear_announcement_ids(self) -> None:
        """Clear all announcement IDs so they can be re-sent (e.g. for debug refresh)."""
        self._announcement_ids.clear()
        self._save()

    def reminder_sent(self, key: str) -> bool:
        """Key e.g. 'assignment_123_course_456' or 'planner_789_course_456'."""
        return key in self._reminder_keys

    def mark_reminder_sent(self, key: str) -> None:
        self._reminder_keys.add(key)
        self._save()

    @staticmethod
    def reminder_key(plannable_type: str, plannable_id: int, course_id: int) -> str:
        return f"{plannable_type}_{plannable_id}_course_{course_id}"
