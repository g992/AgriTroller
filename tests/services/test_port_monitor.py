from pathlib import Path
from types import SimpleNamespace

import pytest

from agritroller.config import AppConfig, DatabaseConfig
from agritroller.services import (
    BootstrapContext,
    DatabaseService,
    DeviceRegistryService,
    EventBusService,
)
from agritroller.services.port_monitor import PortMonitorService


@pytest.mark.asyncio
async def test_port_monitor_refresh_device(monkeypatch, tmp_path: Path) -> None:
    config = AppConfig(database=DatabaseConfig(path=tmp_path / "ports.db"))
    context = BootstrapContext(config=config)

    database = DatabaseService(context, config.database)
    registry = DeviceRegistryService(context, config.serial, config.rs485)
    event_bus = EventBusService(context)
    monitor = PortMonitorService(context)

    await database.start()
    await registry.start()
    await event_bus.start()

    device = registry.create_device(
        kind="peripheral",
        name="Test Device",
        port="/dev/ttyTEST0",
        baudrate=57600,
    )

    class DummyPort:
        def __init__(self, device_name: str) -> None:
            self.device = device_name

    class DummySerial:
        def __init__(self, *args, **kwargs) -> None:
            self.closed = False

        def __enter__(self) -> "DummySerial":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            self.closed = True

    monkeypatch.setattr(
        "agritroller.services.port_monitor.list_ports",
        SimpleNamespace(comports=lambda: [DummyPort("/dev/ttyTEST0")]),
    )
    monkeypatch.setattr("agritroller.services.port_monitor.serial.Serial", DummySerial)

    await monitor.start()
    updated = await monitor.refresh_device(device["id"])

    assert updated["status"] == monitor.STATUS_AVAILABLE
    assert "Порт" in (updated["status_message"] or "")
    assert updated["status_checked_at"] is not None

    await monitor.stop()
    await event_bus.stop()
    await registry.stop()
    await database.stop()
