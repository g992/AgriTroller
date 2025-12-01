"""Template management service backed by SQLite."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agritroller.config import TemplateConfig
from agritroller.services.base import BootstrapContext, Service


class TemplateService(Service):
    """Loads template catalogs and exposes constructor metadata."""

    def __init__(self, context: BootstrapContext, config: TemplateConfig) -> None:
        super().__init__("templates", context)
        self.config = config
        self._conn: sqlite3.Connection | None = None

    async def _start(self) -> None:
        template_dir = Path(self.config.templates_dir)
        template_dir.mkdir(parents=True, exist_ok=True)

        conn = self.context.state.get("db_conn")
        if conn is None:
            raise RuntimeError("Database connection not ready for TemplateService")
        self._conn = conn

        await asyncio.to_thread(self._seed_from_disk_if_needed, template_dir)
        self.context.state["template_root"] = str(template_dir)
        self.context.state["template_service"] = self
        self.logger.info("Template service connected to SQLite catalog")

    def list_templates(self) -> List[Dict[str, Any]]:
        if not self._conn:
            return []
        rows = self._conn.execute(
            "SELECT id, slug, name, content, updated_at FROM templates ORDER BY name ASC"
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_template(self, slug: str) -> Optional[Dict[str, Any]]:
        if not self._conn:
            return None
        row = self._conn.execute(
            "SELECT id, slug, name, content, updated_at FROM templates WHERE slug = ?",
            (slug,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def upsert_template(self, slug: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._conn:
            raise RuntimeError("TemplateService is not initialized")
        name = payload.get("name") or slug
        content = json.dumps(payload, ensure_ascii=False)
        self._conn.execute(
            """
            INSERT INTO templates (slug, name, content)
            VALUES (?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                name=excluded.name,
                content=excluded.content,
                updated_at=CURRENT_TIMESTAMP
            """,
            (slug, name, content),
        )
        self._conn.commit()
        updated = self.get_template(slug)
        if not updated:
            raise RuntimeError("Failed to retrieve template after upsert")
        return updated

    def _seed_from_disk_if_needed(self, template_dir: Path) -> None:
        if not self._conn:
            return
        count = self._conn.execute("SELECT COUNT(*) AS c FROM templates").fetchone()["c"]
        if count > 0:
            return
        self.logger.info("Seeding templates from %s", template_dir)
        seed_files = sorted(template_dir.glob(self.config.seed_glob))
        if not seed_files:
            self.logger.warning("No template JSON files found under %s", template_dir)
            self._insert_placeholder()
            return
        for path in seed_files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self.logger.error("Failed to load template %s: %s", path, exc)
                continue
            slug = path.stem
            name = payload.get("name") or slug
            self._conn.execute(
                "INSERT INTO templates (slug, name, content) VALUES (?, ?, ?)",
                (slug, name, json.dumps(payload, ensure_ascii=False)),
            )
        self._conn.commit()

    def _insert_placeholder(self) -> None:
        if not self._conn:
            return
        payload = {"name": "default", "devices": [], "registers": []}
        self._conn.execute(
            "INSERT INTO templates (slug, name, content) VALUES (?, ?, ?)",
            ("default", payload["name"], json.dumps(payload)),
        )
        self._conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        raw_updated = row["updated_at"]
        updated = (
            datetime.fromisoformat(raw_updated).isoformat() + "Z"
            if isinstance(raw_updated, str)
            else str(raw_updated)
        )
        return {
            "id": row["id"],
            "slug": row["slug"],
            "name": row["name"],
            "content": json.loads(row["content"]),
            "updated_at": updated,
        }
