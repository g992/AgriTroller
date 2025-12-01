"""Version registry service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from agritroller.config import VersionConfig
from agritroller.services.base import BootstrapContext, Service


class VersioningService(Service):
    """Keeps the versions.json file in sync."""

    def __init__(self, context: BootstrapContext, config: VersionConfig) -> None:
        super().__init__("versioning", context)
        self.config = config
        self._versions: Dict[str, str] = {}

    async def _start(self) -> None:
        version_file = self.config.version_file
        version_file.parent.mkdir(parents=True, exist_ok=True)
        self._versions = self._ensure_version_file(version_file)
        self.context.state["versions"] = self._versions
        self.context.state["version_file"] = str(version_file)
        self.logger.info("Version registry ready: %s", version_file)

    def _ensure_version_file(self, version_file: Path) -> Dict[str, str]:
        defaults = {
            "backend": self.config.backend_version,
            "frontend": self.config.frontend_version,
            "firmware": self.config.firmware_version,
        }
        data = defaults.copy()
        if version_file.exists():
            try:
                stored = json.loads(version_file.read_text(encoding="utf-8"))
                data.update({k: str(v) for k, v in stored.items() if isinstance(v, (str, int, float))})
            except (OSError, json.JSONDecodeError) as exc:
                self.logger.warning("Failed to parse version file %s: %s", version_file, exc)
        version_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def update_versions(self, **kwargs: str) -> Dict[str, str]:
        version_file = self.config.version_file
        self._versions.update(kwargs)
        version_file.write_text(json.dumps(self._versions, ensure_ascii=False, indent=2), encoding="utf-8")
        self.context.state["versions"] = self._versions
        return self._versions
