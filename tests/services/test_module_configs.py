from pathlib import Path

import pytest

from agritroller.config import AppConfig, DatabaseConfig, ModuleConfigSettings
from agritroller.services.base import BootstrapContext
from agritroller.services.database import DatabaseService
from agritroller.services.module_configs import ModuleConfigParser, ModuleConfigService


def _write_cfg(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_parser_merges_module_type(tmp_path: Path) -> None:
    base_cfg = tmp_path / "iarduino_base.cfg"
    module_cfg = tmp_path / "ac_switch.cfg"

    _write_cfg(
        base_cfg,
        """
        [module_type iarduino]
        name = Base IArduino
        register.ack.type = holding
        register.ack.addr = 0x0101
        register.ack.length = 2
        register.ack.description = "ack"
        """,
    )

    _write_cfg(
        module_cfg,
        """
        [module ac_switch]
        type = iarduino
        name = AC Switch
        register.local_reg.type = ai
        register.local_reg.addr = 0x0001
        register.local_reg.length = 2

        [actuator relay]
        module = ac_switch
        register.relay.type = coil
        register.relay.addr = 0x0001
        register.relay.length = 1
        register.relay.on_value = 1
        register.relay.off_value = 0
        register.relay.mode = binary

        [sensor vin]
        module = ac_switch
        register.vin.type = ai
        register.vin.addr = 0x0002
        register.vin.length = 2
        register.vin.data_type = uint16
        register.vin.transform = scale:0.1
        """,
    )

    parser = ModuleConfigParser()
    parsed = parser.parse_directory(tmp_path)

    assert len(parsed.modules) == 1
    module = parsed.modules[0]
    assert module.module_type == "iarduino"
    assert module.type_registers and module.type_registers[0]["register_type"] == "holding_register"
    assert module.registers[0]["address"] == 0x0001
    assert module.actuators[0]["registers"][0]["on_value"] == 1
    assert module.sensors[0]["registers"][0]["transform"] == "scale:0.1"


def test_parser_validates_missing_type(tmp_path: Path) -> None:
    module_cfg = tmp_path / "broken.cfg"
    _write_cfg(
        module_cfg,
        """
        [module unknown]
        type = missing_type

        [actuator only]
        module = unknown
        register.x.type = coil
        register.x.addr = 0x0001
        register.x.length = 1
        """,
    )

    parser = ModuleConfigParser()
    with pytest.raises(ValueError):
        parser.parse_directory(tmp_path)

@pytest.mark.asyncio
async def test_module_config_service_persists(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "cfgs"
    cfg_dir.mkdir()
    _write_cfg(
        cfg_dir / "base.cfg",
        """
        [module_type custom]
        register.base.type = holding
        register.base.addr = 0x0100
        register.base.length = 2
        """,
    )
    _write_cfg(
        cfg_dir / "mod.cfg",
        """
        [module mod1]
        type = custom
        register.reg1.type = ai
        register.reg1.addr = 0x0001
        register.reg1.length = 2

        [sensor temp]
        module = mod1
        register.t.type = ai
        register.t.addr = 0x0002
        register.t.length = 2
        register.t.data_type = int
        """,
    )

    app_config = AppConfig(
        database=DatabaseConfig(path=tmp_path / "db.sqlite"),
        module_configs=ModuleConfigSettings(user_configs_dir=cfg_dir, repo_configs_dir=cfg_dir),
    )
    context = BootstrapContext(config=app_config)
    db_service = DatabaseService(context, app_config.database)
    module_service = ModuleConfigService(context, app_config.module_configs)

    await db_service.start()
    await module_service.start()

    conn = context.state["db_conn"]
    rows = conn.execute(
        "SELECT slug, kind, module_type FROM module_configs ORDER BY kind, slug"
    ).fetchall()
    assert {row["kind"] for row in rows} == {"module", "module_type"}

    await module_service.stop()
    await db_service.stop()
