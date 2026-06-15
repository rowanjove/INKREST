import logging
import threading
from pathlib import Path
from typing import Dict

from novel_agent.state.clear_state import NARRATIVE_STATE_TABLES, OPERATIONAL_TABLES
from novel_agent.state.sqlite_schema import (
    SchemaMixin,
    safe_connection,
    db_write_lock,
    SQLiteWriteQueue,
)
from novel_agent.state.state_repository import StateRepositoryMixin
from novel_agent.state.history_repository import HistoryRepositoryMixin

logger = logging.getLogger("novel_agent.state.sqlite_store")


class SQLiteStateStore(SchemaMixin, StateRepositoryMixin, HistoryRepositoryMixin):
    """Unified entry point for database state store.

    Combines schema management, state candidates, metrics,
    costs, versions, and tasks into logical repository Mixins.
    """
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.db_path = self.root_dir / "data" / "novel.sqlite"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    @db_write_lock
    def clear_narrative_state(self, *, include_operational: bool = False) -> Dict[str, int]:
        """Delete narrative rows via the single-writer queue (safe under concurrent tasks)."""
        if not self.db_path.is_file():
            return {}
        tables = list(NARRATIVE_STATE_TABLES)
        if include_operational:
            tables.extend(OPERATIONAL_TABLES)
        cleared: Dict[str, int] = {}
        with safe_connection(self.db_path) as conn:
            existing = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            for table in tables:
                if table not in existing:
                    continue
                cur = conn.execute(f"DELETE FROM [{table}]")
                cleared[table] = cur.rowcount
            conn.commit()
            if include_operational:
                conn.execute("VACUUM")
                conn.commit()
        logger.info(
            "Cleared narrative SQLite state (%s tables, operational=%s)",
            len(cleared),
            include_operational,
        )
        return cleared
