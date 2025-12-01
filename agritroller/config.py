"""Application configuration models.

The dataclasses declared here describe how each service can be configured.
In production these values should come from environment variables or JSON/YAML
files produced by the template constructor.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DATA_ROOT = Path(os.environ.get("AGRITROLLER_DATA_ROOT", Path.home() / ".agritroller"))


@dataclass
class SerialConfig:
    port: str = "/dev/ttyUSB0"
    baudrate: int = 115200
    timeout: float = 0.1


@dataclass
class RS485Config:
    port: str = "/dev/ttyUSB1"
    baudrate: int = 9600
    default_template_slug: str = "default"


@dataclass
class DatabaseConfig:
    path: Path = DATA_ROOT / "agritroller.db"
    echo: bool = False


@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    reload: bool = False


@dataclass
class SchedulerConfig:
    tick_seconds: int = 5


@dataclass
class FirmwareUpdateConfig:
    firmware_dir: Path = Path("firmware")
    ota_server: Optional[str] = None


@dataclass
class TemplateConfig:
    templates_dir: Path = Path("templates")
    seed_glob: str = "devices/*.json"


@dataclass
class ModuleConfigSettings:
    user_configs_dir: Path = DATA_ROOT / "configs"
    repo_configs_dir: Path = Path("configs")


@dataclass
class FrontendConfig:
    dist_dir: Path = Path("frontend/dist/spa")


@dataclass
class VersionConfig:
    version_file: Path = DATA_ROOT / "versions.json"
    backend_version: str = "0.1.0"
    frontend_version: str = "0.1.0"
    firmware_version: str = "0.1.0"


@dataclass
class WifiConfig:
    state_file: Path = DATA_ROOT / "wifi.json"
    scan_timeout: float = 10.0
    connect_timeout: float = 20.0


@dataclass
class AppConfig:
    environment: str = "development"
    serial: SerialConfig = field(default_factory=SerialConfig)
    rs485: RS485Config = field(default_factory=RS485Config)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    web: WebConfig = field(default_factory=WebConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    firmware: FirmwareUpdateConfig = field(default_factory=FirmwareUpdateConfig)
    templates: TemplateConfig = field(default_factory=TemplateConfig)
    module_configs: ModuleConfigSettings = field(default_factory=ModuleConfigSettings)
    frontend: FrontendConfig = field(default_factory=FrontendConfig)
    versions: VersionConfig = field(default_factory=VersionConfig)
    wifi: WifiConfig = field(default_factory=WifiConfig)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    return value in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value for {name}: {raw}") from exc


def load_app_config_from_env() -> AppConfig:
    """Create :class:`AppConfig` with environment overrides suitable for production."""

    cfg = AppConfig()
    cfg.environment = os.environ.get("AGRITROLLER_ENV", cfg.environment)

    cfg.serial.port = os.environ.get("AGRITROLLER_SERIAL_PORT", cfg.serial.port)
    cfg.serial.baudrate = _env_int("AGRITROLLER_SERIAL_BAUDRATE", cfg.serial.baudrate)
    cfg.serial.timeout = float(os.environ.get("AGRITROLLER_SERIAL_TIMEOUT", cfg.serial.timeout))

    cfg.rs485.port = os.environ.get("AGRITROLLER_RS485_PORT", cfg.rs485.port)
    cfg.rs485.baudrate = _env_int("AGRITROLLER_RS485_BAUDRATE", cfg.rs485.baudrate)
    cfg.rs485.default_template_slug = os.environ.get(
        "AGRITROLLER_RS485_DEFAULT_TEMPLATE", cfg.rs485.default_template_slug
    )

    cfg.database.path = Path(os.environ.get("AGRITROLLER_DB_PATH", cfg.database.path))
    cfg.database.echo = _env_bool("AGRITROLLER_DB_ECHO", cfg.database.echo)

    cfg.web.host = os.environ.get("AGRITROLLER_HOST", cfg.web.host)
    cfg.web.port = _env_int("AGRITROLLER_PORT", cfg.web.port)
    cfg.web.reload = _env_bool("AGRITROLLER_RELOAD", cfg.web.reload)

    cfg.scheduler.tick_seconds = _env_int("AGRITROLLER_SCHEDULER_TICK", cfg.scheduler.tick_seconds)

    cfg.firmware.firmware_dir = Path(os.environ.get("AGRITROLLER_FIRMWARE_DIR", cfg.firmware.firmware_dir))
    cfg.firmware.ota_server = os.environ.get("AGRITROLLER_OTA_SERVER", cfg.firmware.ota_server)

    cfg.templates.templates_dir = Path(os.environ.get("AGRITROLLER_TEMPLATES_DIR", cfg.templates.templates_dir))
    cfg.templates.seed_glob = os.environ.get("AGRITROLLER_TEMPLATES_GLOB", cfg.templates.seed_glob)

    cfg.module_configs.user_configs_dir = Path(
        os.environ.get("AGRITROLLER_USER_CONFIGS_DIR", cfg.module_configs.user_configs_dir)
    )
    cfg.module_configs.repo_configs_dir = Path(
        os.environ.get("AGRITROLLER_REPO_CONFIGS_DIR", cfg.module_configs.repo_configs_dir)
    )

    cfg.frontend.dist_dir = Path(os.environ.get("AGRITROLLER_FRONTEND_DIST", cfg.frontend.dist_dir))

    cfg.versions.version_file = Path(os.environ.get("AGRITROLLER_VERSION_FILE", cfg.versions.version_file))
    cfg.versions.backend_version = os.environ.get("AGRITROLLER_BACKEND_VERSION", cfg.versions.backend_version)
    cfg.versions.frontend_version = os.environ.get("AGRITROLLER_FRONTEND_VERSION", cfg.versions.frontend_version)
    cfg.versions.firmware_version = os.environ.get("AGRITROLLER_FIRMWARE_VERSION", cfg.versions.firmware_version)

    cfg.wifi.state_file = Path(os.environ.get("AGRITROLLER_WIFI_STATE", cfg.wifi.state_file))
    cfg.wifi.scan_timeout = float(os.environ.get("AGRITROLLER_WIFI_SCAN_TIMEOUT", cfg.wifi.scan_timeout))
    cfg.wifi.connect_timeout = float(os.environ.get("AGRITROLLER_WIFI_CONNECT_TIMEOUT", cfg.wifi.connect_timeout))

    return cfg
