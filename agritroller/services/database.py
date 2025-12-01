"""SQLite database service."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from agritroller.config import DatabaseConfig
from agritroller.db import get_migrations
from agritroller.services.base import BootstrapContext, Service


class DatabaseService(Service):
    """Handles storage and retrieval of system state."""

    def __init__(self, context: BootstrapContext, config: DatabaseConfig) -> None:
        super().__init__("database", context)
        self.config = config
        self.connection: sqlite3.Connection | None = None

    async def _start(self) -> None:
        db_path = Path(self.config.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger.info("Opening SQLite database at %s", db_path)
        self.connection = sqlite3.connect(
            db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self.connection.row_factory = sqlite3.Row
        self._configure_connection(self.connection)
        self._apply_migrations(self.connection)
        self.context.state["db_conn"] = self.connection
        self.context.state["db_path"] = db_path

    async def _stop(self) -> None:
        if self.connection:
            self.logger.info("Closing SQLite database")
            self.connection.close()
        self.context.state.pop("db_conn", None)
        self.context.state.pop("db_path", None)
        self.connection = None

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        applied = {
            row["id"]
            for row in conn.execute("SELECT id FROM schema_migrations ORDER BY id").fetchall()
        }
        for migration in get_migrations():
            if migration.id in applied:
                continue
            self.logger.info("Applying migration %s - %s", migration.id, migration.description)
            migration.handler(conn)
            conn.execute("INSERT INTO schema_migrations (id) VALUES (?)", (migration.id,))
            conn.commit()
