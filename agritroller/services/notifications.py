"""Notification subscriber that persists selected events."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import sqlite3

from agritroller.services.base import BootstrapContext, Service
from agritroller.services.event_bus import EventBus, EventPayload, EventSubscription


class NotificationService(Service):
    """Subscribes to the event bus and stores notification-worthy events in SQLite."""

    VALID_SEVERITIES = {"ok", "warning", "error"}

    def __init__(self, context: BootstrapContext) -> None:
        super().__init__("notifications", context)
        self._subscription: EventSubscription | None = None
        self._task: Optional[asyncio.Task[None]] = None

    async def _start(self) -> None:
        bus = self._get_event_bus()
        self._subscription = await bus.subscribe()
        self._task = asyncio.create_task(self._consume_events())
        self.context.state["notification_service"] = self
        self.logger.info("Notification service ready")

    async def _stop(self) -> None:
        self.context.state.pop("notification_service", None)
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        if self._subscription:
            await self._subscription.close()
        self._task = None
        self._subscription = None

    async def _consume_events(self) -> None:
        subscription = self._subscription
        if not subscription:
            return
        try:
            while True:
                event = await subscription.get()
                self._handle_event(event)
        except asyncio.CancelledError:
            raise

    def _handle_event(self, event: EventPayload) -> None:
        if not event.get("notify", False):
            return
        notification = event.get("notification")
        if not isinstance(notification, dict):
            self.logger.warning("Notification event missing payload: %s", event)
            return
        severity = notification.get("severity")
        if severity not in self.VALID_SEVERITIES:
            self.logger.warning("Unsupported notification severity: %s", severity)
            return
        message = notification.get("message")
        source = notification.get("source")
        if not message or not source:
            self.logger.warning("Notification missing message/source fields: %s", event)
            return
        created_at = notification.get("created_at") or event.get("timestamp")
        if not isinstance(created_at, str):
            created_at = datetime.now(tz=timezone.utc).isoformat()
        event_type = event.get("type", "event.unknown")
        conn = self._get_conn()
        with conn:
            conn.execute(
                """
                INSERT INTO notifications (event_type, severity, source, message, created_at, is_read)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (event_type, severity, source, message, created_at),
            )

    def list_notifications(self, *, limit: int = 20, include_read: bool = True) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        query = """
            SELECT id, event_type, severity, source, message, created_at, is_read
            FROM notifications
        """
        params: List[Any] = []
        if not include_read:
            query += " WHERE is_read = 0"
        query += " ORDER BY datetime(created_at) DESC, id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def mark_read(self, notification_id: int) -> bool:
        conn = self._get_conn()
        with conn:
            cursor = conn.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = ?",
                (notification_id,),
            )
        return cursor.rowcount > 0

    def mark_all_read(self) -> int:
        conn = self._get_conn()
        with conn:
            cursor = conn.execute("UPDATE notifications SET is_read = 1 WHERE is_read = 0")
        return cursor.rowcount

    def delete(self, notification_id: int) -> bool:
        conn = self._get_conn()
        with conn:
            cursor = conn.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
        return cursor.rowcount > 0

    def delete_all(self) -> int:
        conn = self._get_conn()
        with conn:
            cursor = conn.execute("DELETE FROM notifications")
        return cursor.rowcount

    def _get_event_bus(self) -> EventBus:
        bus = self.context.state.get("event_bus")
        if not isinstance(bus, EventBus):
            raise RuntimeError("Event bus unavailable for notifications service")
        return bus

    def _get_conn(self) -> sqlite3.Connection:
        conn = self.context.state.get("db_conn")
        if not isinstance(conn, sqlite3.Connection):
            raise RuntimeError("Database connection unavailable for notifications")
        return conn

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "event_type": row["event_type"],
            "severity": row["severity"],
            "source": row["source"],
            "message": row["message"],
            "created_at": row["created_at"],
            "is_read": bool(row["is_read"]),
        }
