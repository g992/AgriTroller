from pathlib import Path

import pytest

from agritroller.config import AppConfig, DatabaseConfig
from agritroller.services.base import BootstrapContext
from agritroller.services.database import DatabaseService
from agritroller.services.device_registry import DeviceRegistryService


@pytest.mark.asyncio
async def test_device_registry_crud(tmp_path: Path) -> None:
    db_path = tmp_path / "registry.db"
    config = AppConfig(database=DatabaseConfig(path=db_path))
    context = BootstrapContext(config=config)

    db_service = DatabaseService(context, config.database)
    registry_service = DeviceRegistryService(context, config.serial, config.rs485)

    await db_service.start()
    await registry_service.start()

    devices = registry_service.list_devices()
    assert devices, "default devices should be seeded"
    assert all("device_type_slug" in device for device in devices)

    new_device = registry_service.create_device(
        kind="peripheral",
        name="Peripheral Controller",
        port="/dev/ttyTEST0",
        baudrate=230400,
        metadata={"timeout": 0.2},
        device_type_slug="generic_actuator",
        mapping={"channel1": [{"op": "hex_to_int"}]},
        enabled=False,
    )
    assert new_device["name"] == "Peripheral Controller"
    assert new_device["metadata"]["timeout"] == 0.2
    assert new_device["device_type_slug"] == "generic_actuator"
    assert new_device["mapping"]["channel1"][0]["op"] == "hex_to_int"
    assert new_device["status"] == "unknown"

    updated = registry_service.update_device(
        new_device["id"],
        name="Peripheral Controller Updated",
        enabled=True,
        device_type_slug="generic_sensor_actuator",
        metadata={"timeout": 0.5},
    )
    assert updated["name"] == "Peripheral Controller Updated"
    assert updated["enabled"] is True
    assert updated["metadata"]["timeout"] == 0.5
    assert updated["device_type_slug"] == "generic_sensor_actuator"

    with pytest.raises(ValueError):
        registry_service.create_device(
            kind="rs485",
            name="Duplicate Port",
            port="/dev/ttyTEST0",
            baudrate=9600,
        )

    retyped = registry_service.update_device(updated["id"], kind="rs485")
    assert retyped["kind"] == "rs485"

    deleted = registry_service.delete_device(updated["id"])
    assert deleted is True
    assert registry_service.get_device(updated["id"]) is None

    await registry_service.stop()
    await db_service.stop()
