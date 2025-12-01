import asyncio
from pathlib import Path

import pytest

from agritroller.config import AppConfig, DatabaseConfig
from agritroller.services import (
    BootstrapContext,
    DatabaseService,
    EventBusService,
    NotificationService,
)


@pytest.mark.asyncio
async def test_notification_service_persists_events(tmp_path: Path) -> None:
    config = AppConfig(database=DatabaseConfig(path=tmp_path / "notifications.db"))
    context = BootstrapContext(config=config)

    database = DatabaseService(context, config.database)
    bus_service = EventBusService(context)
    notifications = NotificationService(context)

    await database.start()
    await bus_service.start()
    await notifications.start()

    bus = context.state["event_bus"]
    await bus.publish(
        {
            "type": "peripheral.error",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "payload": {"controller": "esp32"},
            "notify": True,
            "notification": {
                "severity": "error",
                "message": "Controller unavailable",
                "source": "peripheral_service",
                "created_at": "2024-01-01T00:00:00+00:00",
            },
        }
    )
    await bus.publish(
        {
            "type": "peripheral.heartbeat",
            "timestamp": "2024-01-01T00:01:00+00:00",
            "payload": {"alive": True},
            "notify": False,
        }
    )

    await asyncio.sleep(0.05)

    items = notifications.list_notifications()
    assert len(items) == 1
    entry = items[0]
    assert entry["event_type"] == "peripheral.error"
    assert entry["severity"] == "error"
    assert entry["source"] == "peripheral_service"
    assert entry["message"] == "Controller unavailable"
    assert entry["is_read"] is False

    assert notifications.mark_read(entry["id"]) is True
    updated_items = notifications.list_notifications()
    assert updated_items[0]["is_read"] is True

    notifications.mark_all_read()

    assert notifications.delete(entry["id"]) is True
    assert notifications.list_notifications() == []

    await bus.publish(
        {
            "type": "port.status",
            "timestamp": "2024-01-01T00:02:00+00:00",
            "payload": {"port": "/dev/ttyUSB0"},
            "notify": True,
            "notification": {
                "severity": "warning",
                "message": "Переподключение порта",
                "source": "port_monitor",
                "created_at": "2024-01-01T00:02:00+00:00",
            },
        }
    )
    await bus.publish(
        {
            "type": "port.status",
            "timestamp": "2024-01-01T00:03:00+00:00",
            "payload": {"port": "/dev/ttyUSB1"},
            "notify": True,
            "notification": {
                "severity": "ok",
                "message": "Порт восстановлен",
                "source": "port_monitor",
                "created_at": "2024-01-01T00:03:00+00:00",
            },
        }
    )

    await asyncio.sleep(0.05)

    assert len(notifications.list_notifications()) == 2
    assert notifications.delete_all() == 2
    assert notifications.list_notifications() == []

    await notifications.stop()
    await bus_service.stop()
    await database.stop()
