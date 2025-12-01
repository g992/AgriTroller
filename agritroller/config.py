"""Application configuration models.

The dataclasses declared here describe how each service can be configured.
In production these values should come from environment variables or JSON/YAML
files produced by the template constructor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DATA_ROOT = Path.home() / ".agritroller"


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
    dist_dir: Path = Path("frontend/dist")


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
