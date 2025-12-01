"""SQLite migration registry."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Callable, List


@dataclass(frozen=True)
class Migration:
    """Single migration step."""

    id: str
    description: str
    handler: Callable[[sqlite3.Connection], None]


def _migration_0001_templates(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _migration_0002_devices(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            port TEXT NOT NULL,
            baudrate INTEGER NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_devices_kind
        ON devices(kind)
        """
    )


def _migration_0003_devices_kind_peripheral(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE devices
        SET kind = 'peripheral'
        WHERE kind = 'esp'
        """
    )


def _migration_0004_notifications(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            source TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notifications_unread
        ON notifications(is_read)
        """
    )


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def _migration_0005_device_status_fields(conn: sqlite3.Connection) -> None:
    if not _column_exists(conn, "devices", "status"):
        conn.execute(
            "ALTER TABLE devices ADD COLUMN status TEXT NOT NULL DEFAULT 'unknown'"
        )
    if not _column_exists(conn, "devices", "status_message"):
        conn.execute("ALTER TABLE devices ADD COLUMN status_message TEXT")
    if not _column_exists(conn, "devices", "status_checked_at"):
        conn.execute("ALTER TABLE devices ADD COLUMN status_checked_at TEXT")


def _migration_0006_device_types(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS device_types (
            slug TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            sensor_fields TEXT NOT NULL DEFAULT '[]',
            actuator_fields TEXT NOT NULL DEFAULT '[]',
            error_fields TEXT NOT NULL DEFAULT '[]',
            settings_schema TEXT NOT NULL DEFAULT '[]',
            mapping_defaults TEXT NOT NULL DEFAULT '{}',
            builtin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    if not _column_exists(conn, "devices", "device_type_slug"):
        conn.execute(
            """
            ALTER TABLE devices
            ADD COLUMN device_type_slug TEXT NOT NULL DEFAULT 'generic_empty'
            """
        )
    if not _column_exists(conn, "devices", "mapping"):
        conn.execute(
            """
            ALTER TABLE devices
            ADD COLUMN mapping TEXT NOT NULL DEFAULT '{}'
            """
        )
    builtins = [
        {
            "slug": "generic_empty",
            "name": "Generic empty",
            "description": "Baseline type without fields",
            "sensor_fields": [],
            "actuator_fields": [],
            "error_fields": [],
            "settings_schema": [],
            "mapping_defaults": {},
        },
        {
            "slug": "generic_sensor",
            "name": "Generic сенсор",
            "description": "Temperature, humidity, CO2, pH, EC, TDS",
            "sensor_fields": [
                {"name": "temperature", "label": "Temperature", "unit": "C", "data_type": "float"},
                {"name": "humidity", "label": "Humidity", "unit": "%", "data_type": "float"},
                {"name": "co2", "label": "CO2", "unit": "ppm", "data_type": "float"},
                {"name": "ph", "label": "pH", "unit": "pH", "data_type": "float"},
                {"name": "ec", "label": "EC", "unit": "mS/cm", "data_type": "float"},
                {"name": "tds", "label": "TDS", "unit": "ppm", "data_type": "float"},
            ],
            "actuator_fields": [],
            "error_fields": [],
            "settings_schema": [],
            "mapping_defaults": {},
        },
        {
            "slug": "generic_actuator",
            "name": "Generic актуатор",
            "description": "Channels/actions for actuators",
            "sensor_fields": [],
            "actuator_fields": [
                {"name": f"channel{i}", "label": f"Channel {i}", "data_type": "bool"}
                for i in range(1, 9)
            ]
            + [
                {"name": f"action{i}", "label": f"Action {i}", "data_type": "string"}
                for i in range(1, 9)
            ],
            "error_fields": [],
            "settings_schema": [],
            "mapping_defaults": {},
        },
        {
            "slug": "generic_sensor_actuator",
            "name": "Generic сенсор + актуатор",
            "description": "Combined sensors and actuator channels",
            "sensor_fields": [
                {"name": "temperature", "label": "Temperature", "unit": "C", "data_type": "float"},
                {"name": "humidity", "label": "Humidity", "unit": "%", "data_type": "float"},
                {"name": "co2", "label": "CO2", "unit": "ppm", "data_type": "float"},
                {"name": "ph", "label": "pH", "unit": "pH", "data_type": "float"},
                {"name": "ec", "label": "EC", "unit": "mS/cm", "data_type": "float"},
                {"name": "tds", "label": "TDS", "unit": "ppm", "data_type": "float"},
            ],
            "actuator_fields": [
                {"name": f"channel{i}", "label": f"Channel {i}", "data_type": "bool"}
                for i in range(1, 9)
            ]
            + [
                {"name": f"action{i}", "label": f"Action {i}", "data_type": "string"}
                for i in range(1, 9)
            ],
            "error_fields": [],
            "settings_schema": [],
            "mapping_defaults": {},
        },
        {
            "slug": "htl_sensor",
            "name": "HTL climate",
            "description": "Temperature, humidity, light with diagnostics",
            "sensor_fields": [
                {"name": "temperature", "label": "Temperature", "unit": "C", "data_type": "float"},
                {"name": "humidity", "label": "Humidity", "unit": "%", "data_type": "float"},
                {"name": "light", "label": "Light", "unit": "lux", "data_type": "float"},
            ],
            "actuator_fields": [],
            "error_fields": [
                {"name": "sensor_init", "label": "Sensor init error"},
                {"name": "sensor_data", "label": "Sensor read error"},
                {"name": "comm", "label": "Communication error"},
            ],
            "settings_schema": [
                {"name": "address", "label": "Modbus address", "type": "number", "default": 3, "min": 1, "max": 247},
                {"name": "baudrate", "label": "Baudrate", "type": "number", "default": 9600},
                {
                    "name": "poll_interval_s",
                    "label": "Poll interval (s)",
                    "type": "number",
                    "default": 1.0,
                    "min": 0.1,
                    "max": 10.0,
                },
                {"name": "protocol", "label": "Protocol", "type": "select", "options": ["rtu", "ascii"], "default": "rtu"},
                {"name": "led_mode", "label": "LED mode", "type": "select", "options": ["auto", "on", "off"], "default": "auto"},
            ],
            "mapping_defaults": {
                "temperature": [{"op": "hex_to_int"}, {"op": "scale", "factor": 0.1}],
                "humidity": [{"op": "hex_to_int"}, {"op": "scale", "factor": 0.1}],
                "light": [{"op": "hex_to_int"}],
            },
        },
    ]
    for dtype in builtins:
        conn.execute(
            """
            INSERT OR IGNORE INTO device_types (
                slug, name, description, sensor_fields, actuator_fields, error_fields,
                settings_schema, mapping_defaults, builtin
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                dtype["slug"],
                dtype["name"],
                dtype.get("description"),
                json.dumps(dtype["sensor_fields"], ensure_ascii=False),
                json.dumps(dtype["actuator_fields"], ensure_ascii=False),
                json.dumps(dtype["error_fields"], ensure_ascii=False),
                json.dumps(dtype["settings_schema"], ensure_ascii=False),
                json.dumps(dtype["mapping_defaults"], ensure_ascii=False),
            ),
        )


def _migration_0007_module_configs(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS module_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            module_type TEXT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(slug, kind)
        )
        """
    )


def get_migrations() -> List[Migration]:
    """Return ordered migrations."""
    return [
        Migration(
            id="0001_create_templates",
            description="Create templates table",
            handler=_migration_0001_templates,
        ),
        Migration(
            id="0002_create_devices",
            description="Create serial device registry",
            handler=_migration_0002_devices,
        ),
        Migration(
            id="0003_devices_kind_peripheral",
            description="Rename ESP devices to peripheral controller kind",
            handler=_migration_0003_devices_kind_peripheral,
        ),
        Migration(
            id="0004_create_notifications",
            description="Create notifications table for persisted events",
            handler=_migration_0004_notifications,
        ),
        Migration(
            id="0005_devices_status_fields",
            description="Add persisted status columns for serial devices",
            handler=_migration_0005_device_status_fields,
        ),
        Migration(
            id="0006_device_types",
            description="Add device types and mapping columns",
            handler=_migration_0006_device_types,
        ),
        Migration(
            id="0007_module_configs",
            description="Store parsed module cfg definitions",
            handler=_migration_0007_module_configs,
        ),
    ]
