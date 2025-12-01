from types import SimpleNamespace
from pathlib import Path

import pytest

from agritroller.config import AppConfig, WifiConfig
from agritroller.services.base import BootstrapContext
from agritroller.services.wifi import WifiService


@pytest.mark.asyncio
async def test_wifi_service_uses_fallback_networks(tmp_path: Path) -> None:
    app_config = AppConfig(wifi=WifiConfig(state_file=tmp_path / "wifi.json"))
    context = BootstrapContext(config=app_config)
    service = WifiService(context, app_config.wifi)
    service._nmcli_path = None  # ensure fallback is used
    service._airport_path = None

    await service.start()
    networks = await service.scan_networks()

    assert any(net["ssid"] == "agritroller-lab" for net in networks)
    assert all("signal" in net for net in networks)
    await service.stop()


@pytest.mark.asyncio
async def test_wifi_connect_persists_state_without_password(tmp_path: Path) -> None:
    app_config = AppConfig(wifi=WifiConfig(state_file=tmp_path / "wifi.json"))
    context = BootstrapContext(config=app_config)
    service = WifiService(context, app_config.wifi)
    service._nmcli_path = None
    service._airport_path = None

    await service.start()
    result = await service.connect("MyNet", "super-secret")

    assert result["status"] == "connected"
    status = service.get_status()
    assert status["ssid"] == "MyNet"
    assert "super-secret" not in (app_config.wifi.state_file.read_text())
    await service.stop()


@pytest.mark.asyncio
async def test_wifi_connect_records_error_on_failure(tmp_path: Path) -> None:
    app_config = AppConfig(wifi=WifiConfig(state_file=tmp_path / "wifi.json"))
    context = BootstrapContext(config=app_config)
    service = WifiService(context, app_config.wifi)

    await service.start()
    service._nmcli_path = "/usr/bin/nmcli"
    service._run_nmcli_connect = lambda *args, **kwargs: SimpleNamespace(  # type: ignore[assignment]
        returncode=10, stdout="", stderr="denied"
    )

    result = await service.connect("BrokenNet", "pw")

    assert result["status"] == "error"
    status = service.get_status()
    assert status["last_error"]
    await service.stop()
