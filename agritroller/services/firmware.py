"""Firmware update orchestrator."""

from __future__ import annotations

import asyncio
from pathlib import Path

from agritroller.config import FirmwareUpdateConfig
from agritroller.services.base import BootstrapContext, Service


class FirmwareUpdateService(Service):
    """Tracks available firmware builds and schedules rollouts."""

    def __init__(self, context: BootstrapContext, config: FirmwareUpdateConfig) -> None:
        super().__init__("firmware_updater", context)
        self.config = config

    async def _start(self) -> None:
        firmware_dir = Path(self.config.firmware_dir)
        firmware_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info("Watching firmware bundles in %s", firmware_dir)
        await asyncio.sleep(0)
        self.context.state["firmware_dir"] = str(firmware_dir)
