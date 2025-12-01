"""Device registry backed by SQLite."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from typing import Any, Dict, List, Literal, Optional, Sequence

from agritroller.config import RS485Config, SerialConfig
from agritroller.services.base import BootstrapContext, Service

DeviceKind = Literal["rs485", "peripheral"]


class DeviceRegistryService(Service):
    """Persists RS-485 and peripheral controller metadata in SQLite."""

    def __init__(
        self,
        context: BootstrapContext,
        serial_config: SerialConfig,
        rs485_config: RS485Config,
    ) -> None:
        super().__init__("device_registry", context)
        self.serial_config = serial_config
        self.rs485_config = rs485_config
        self._conn: sqlite3.Connection | None = None

    async def _start(self) -> None:
        conn = self.context.state.get("db_conn")
        if conn is None:
            raise RuntimeError("Database connection not ready for device registry")
        self._conn = conn
        await asyncio.to_thread(self._seed_defaults)
        self.context.state["device_registry"] = self
        self.logger.info("Device registry ready with %d records", len(self.list_devices()))

    async def _stop(self) -> None:
        self.context.state.pop("device_registry", None)
        self._conn = None

    def list_devices(self, kind: Optional[DeviceKind] = None) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        query = "SELECT * FROM devices"
        params: tuple[Any, ...] = ()
        if kind:
            query += " WHERE kind = ?"
            params = (kind,)
        query += " ORDER BY id ASC"
        rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_device(self, device_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def create_device(
        self,
        *,
        kind: DeviceKind,
        name: str,
        port: str,
        baudrate: int,
        metadata: Optional[Dict[str, Any]] = None,
        device_type_slug: str = "generic_empty",
        mapping: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        self._validate_kind(kind)
        self._ensure_device_type_exists(device_type_slug)
        self._ensure_unique_port(port)
        conn = self._get_conn()
        meta = json.dumps(metadata or {}, ensure_ascii=False)
        mapping_json = json.dumps(mapping or {}, ensure_ascii=False)
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO devices (kind, name, port, baudrate, metadata, enabled, device_type_slug, mapping)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    kind,
                    name,
                    port,
                    baudrate,
                    meta,
                    1 if enabled else 0,
                    device_type_slug,
                    mapping_json,
                ),
            )
        device_id = cursor.lastrowid
        device = self.get_device(int(device_id))
        if not device:
            raise RuntimeError("Failed to read device after insert")
        return device

    def update_device(
        self,
        device_id: int,
        *,
        kind: Optional[DeviceKind] = None,
        name: Optional[str] = None,
        port: Optional[str] = None,
        baudrate: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        device_type_slug: Optional[str] = None,
        mapping: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        conn = self._get_conn()
        updates = []
        params: List[Any] = []
        if kind is not None:
            self._validate_kind(kind)
            updates.append("kind = ?")
            params.append(kind)
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if port is not None:
            self._ensure_unique_port(port, exclude_id=device_id)
            updates.append("port = ?")
            params.append(port)
        if baudrate is not None:
            updates.append("baudrate = ?")
            params.append(baudrate)
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata, ensure_ascii=False))
        if device_type_slug is not None:
            self._ensure_device_type_exists(device_type_slug)
            updates.append("device_type_slug = ?")
            params.append(device_type_slug)
        if mapping is not None:
            updates.append("mapping = ?")
            params.append(json.dumps(mapping, ensure_ascii=False))
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)
        if not updates:
            device = self.get_device(device_id)
            if not device:
                raise LookupError(f"Device {device_id} not found")
            return device
        updates.append("updated_at = CURRENT_TIMESTAMP")
        set_clause = ", ".join(updates)
        params.append(device_id)
        with conn:
            cursor = conn.execute(
                f"UPDATE devices SET {set_clause} WHERE id = ?",  # noqa: S608 - safe set clause
                tuple(params),
            )
        if cursor.rowcount == 0:
            raise LookupError(f"Device {device_id} not found")
        device = self.get_device(device_id)
        if not device:
            raise RuntimeError("Device disappeared after update")
        return device

    def delete_device(self, device_id: int) -> bool:
        conn = self._get_conn()
        with conn:
            cursor = conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        return cursor.rowcount > 0

    def update_device_status(
        self,
        device_id: int,
        *,
        status: str,
        status_message: Optional[str],
    ) -> Dict[str, Any]:
        conn = self._get_conn()
        with conn:
            cursor = conn.execute(
                """
                UPDATE devices
                SET status = ?, status_message = ?, status_checked_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, status_message, device_id),
            )
        if cursor.rowcount == 0:
            raise LookupError(f"Device {device_id} not found")
        device = self.get_device(device_id)
        if not device:
            raise RuntimeError("Device disappeared after status update")
        return device

    def _seed_defaults(self) -> None:
        conn = self._get_conn()
        existing = {
            row["kind"]: row["total"]
            for row in conn.execute("SELECT kind, COUNT(*) AS total FROM devices GROUP BY kind")
        }
        if existing.get("peripheral", 0) == 0:
            conn.execute(
                """
                INSERT INTO devices (kind, name, port, baudrate, metadata, device_type_slug, mapping)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "peripheral",
                    "Peripheral Controller",
                    self.serial_config.port,
                    self.serial_config.baudrate,
                    json.dumps({"timeout": self.serial_config.timeout}),
                    "generic_actuator",
                    "{}",
                ),
            )
        if existing.get("rs485", 0) == 0:
            conn.execute(
                """
                INSERT INTO devices (kind, name, port, baudrate, metadata, device_type_slug, mapping)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "rs485",
                    "RS-485 Gateway",
                    self.rs485_config.port,
                    self.rs485_config.baudrate,
                    json.dumps({"default_template": self.rs485_config.default_template_slug}),
                    "generic_empty",
                    "{}",
                ),
            )
        conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        metadata = {}
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except json.JSONDecodeError:
                metadata = {}
        kind = row["kind"]
        if kind == "esp":
            kind = "peripheral"
        columns = row.keys() if isinstance(row, sqlite3.Row) else []
        return {
            "id": row["id"],
            "kind": kind,
            "name": row["name"],
            "port": row["port"],
            "baudrate": row["baudrate"],
            "metadata": metadata,
            "enabled": bool(row["enabled"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "status": row["status"] if "status" in columns else "unknown",
            "status_message": row["status_message"] if "status_message" in columns else None,
            "status_checked_at": row["status_checked_at"] if "status_checked_at" in columns else None,
            "device_type_slug": row["device_type_slug"] if "device_type_slug" in columns else "generic_empty",
            "mapping": self._safe_load_json(row["mapping"]) if "mapping" in columns else {},
        }

    def _get_conn(self) -> sqlite3.Connection:
        if not self._conn:
            raise RuntimeError("Device registry is not initialized")
        return self._conn

    @staticmethod
    def _validate_kind(kind: DeviceKind) -> None:
        if kind not in ("rs485", "peripheral"):
            raise ValueError(f"Unsupported device type: {kind}")

    def _ensure_unique_port(self, port: str, exclude_id: Optional[int] = None) -> None:
        conn = self._get_conn()
        query = "SELECT id FROM devices WHERE lower(port) = lower(?)"
        params: List[Any] = [port]
        if exclude_id is not None:
            query += " AND id != ?"
            params.append(exclude_id)
        row = conn.execute(query, tuple(params)).fetchone()
        if row:
            raise ValueError(f"Port {port} is already assigned to another device")

    @staticmethod
    def _safe_load_json(raw: Any) -> Dict[str, Any]:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _ensure_device_type_exists(self, slug: str) -> None:
        conn = self._get_conn()
        row = conn.execute("SELECT 1 FROM device_types WHERE slug = ?", (slug,)).fetchone()
        if not row:
            raise ValueError(f"Device type {slug} not found")

    # Device type helpers
    def list_device_types(self) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT slug, name, description, sensor_fields, actuator_fields, error_fields,
                   settings_schema, mapping_defaults, builtin, created_at, updated_at
            FROM device_types
            ORDER BY builtin DESC, name ASC
            """
        ).fetchall()
        return [self._type_row_to_dict(row) for row in rows]

    def get_device_type(self, slug: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        row = conn.execute(
            """
            SELECT slug, name, description, sensor_fields, actuator_fields, error_fields,
                   settings_schema, mapping_defaults, builtin, created_at, updated_at
            FROM device_types
            WHERE slug = ?
            """,
            (slug,),
        ).fetchone()
        return self._type_row_to_dict(row) if row else None

    def create_device_type(
        self,
        *,
        slug: str,
        name: str,
        description: Optional[str] = None,
        sensor_fields: Sequence[Dict[str, Any]] = (),
        actuator_fields: Sequence[Dict[str, Any]] = (),
        error_fields: Sequence[Dict[str, Any]] = (),
        settings_schema: Sequence[Dict[str, Any]] = (),
        mapping_defaults: Optional[Dict[str, Any]] = None,
        builtin: bool = False,
    ) -> Dict[str, Any]:
        self._validate_slug(slug)
        conn = self._get_conn()
        with conn:
            conn.execute(
                """
                INSERT INTO device_types (
                    slug, name, description, sensor_fields, actuator_fields, error_fields,
                    settings_schema, mapping_defaults, builtin
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    slug,
                    name,
                    description,
                    json.dumps(list(sensor_fields), ensure_ascii=False),
                    json.dumps(list(actuator_fields), ensure_ascii=False),
                    json.dumps(list(error_fields), ensure_ascii=False),
                    json.dumps(list(settings_schema), ensure_ascii=False),
                    json.dumps(mapping_defaults or {}, ensure_ascii=False),
                    1 if builtin else 0,
                ),
            )
        created = self.get_device_type(slug)
        if not created:
            raise RuntimeError("Failed to create device type")
        return created

    def update_device_type(
        self,
        slug: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sensor_fields: Optional[Sequence[Dict[str, Any]]] = None,
        actuator_fields: Optional[Sequence[Dict[str, Any]]] = None,
        error_fields: Optional[Sequence[Dict[str, Any]]] = None,
        settings_schema: Optional[Sequence[Dict[str, Any]]] = None,
        mapping_defaults: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        conn = self._get_conn()
        current = self.get_device_type(slug)
        if not current:
            raise LookupError(f"Device type {slug} not found")
        if current.get("builtin"):
            raise ValueError("Builtin device types cannot be modified")
        updates = []
        params: List[Any] = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if sensor_fields is not None:
            updates.append("sensor_fields = ?")
            params.append(json.dumps(list(sensor_fields), ensure_ascii=False))
        if actuator_fields is not None:
            updates.append("actuator_fields = ?")
            params.append(json.dumps(list(actuator_fields), ensure_ascii=False))
        if error_fields is not None:
            updates.append("error_fields = ?")
            params.append(json.dumps(list(error_fields), ensure_ascii=False))
        if settings_schema is not None:
            updates.append("settings_schema = ?")
            params.append(json.dumps(list(settings_schema), ensure_ascii=False))
        if mapping_defaults is not None:
            updates.append("mapping_defaults = ?")
            params.append(json.dumps(mapping_defaults, ensure_ascii=False))
        if not updates:
            return current
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(slug)
        with conn:
            conn.execute(
                f"UPDATE device_types SET {', '.join(updates)} WHERE slug = ?",  # noqa: S608
                tuple(params),
            )
        updated = self.get_device_type(slug)
        if not updated:
            raise RuntimeError("Device type disappeared after update")
        return updated

    def delete_device_type(self, slug: str) -> bool:
        conn = self._get_conn()
        current = self.get_device_type(slug)
        if not current:
            return False
        if current.get("builtin"):
            raise ValueError("Builtin device types cannot be removed")
        in_use = conn.execute(
            "SELECT COUNT(1) AS total FROM devices WHERE device_type_slug = ?",
            (slug,),
        ).fetchone()
        if in_use and in_use["total"] > 0:
            raise ValueError("Cannot remove device type while devices reference it")
        with conn:
            cursor = conn.execute("DELETE FROM device_types WHERE slug = ?", (slug,))
        return cursor.rowcount > 0

    def _type_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "slug": row["slug"],
            "name": row["name"],
            "description": row["description"],
            "sensor_fields": self._safe_list_json(row["sensor_fields"]),
            "actuator_fields": self._safe_list_json(row["actuator_fields"]),
            "error_fields": self._safe_list_json(row["error_fields"]),
            "settings_schema": self._safe_list_json(row["settings_schema"]),
            "mapping_defaults": self._safe_load_json(row["mapping_defaults"]),
            "builtin": bool(row["builtin"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _safe_list_json(self, raw: Any) -> List[Any]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _validate_slug(slug: str) -> None:
        if not slug or not slug.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Slug must be alphanumeric with optional underscores/dashes")
