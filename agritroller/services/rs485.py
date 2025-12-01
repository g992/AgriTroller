"""RS-485 bus adapter service."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from agritroller.config import RS485Config
from agritroller.services.base import BootstrapContext, Service
from agritroller.services.device_registry import DeviceRegistryService
from agritroller.services.templates import TemplateService


class RS485Service(Service):
    """Loads user templates and exchanges messages with RS-485 devices."""

    def __init__(self, context: BootstrapContext, config: RS485Config) -> None:
        super().__init__("rs485", context)
        self.config = config
        self._active_template: Optional[Dict[str, Any]] = None
        self._devices: List[Dict[str, Any]] = []

    async def _start(self) -> None:
        await self._load_devices()
        await self._load_template(self.config.default_template_slug)

    async def _stop(self) -> None:
        self.logger.info("Stopping RS-485 service")
        await asyncio.sleep(0)

    async def _load_template(self, slug: str) -> None:
        template_service: TemplateService | None = self.context.state.get("template_service")
        if not template_service:
            self.logger.warning("Template service is unavailable; cannot load template")
            return
        template = template_service.get_template(slug)
        if not template:
            self.logger.warning("Template '%s' not found in database", slug)
            return
        self._active_template = template["content"]
        self.context.state["rs485_template"] = self._active_template
        self.logger.info("Loaded RS-485 template '%s'", slug)

    async def _load_devices(self) -> None:
        registry = self.context.state.get("device_registry")
        if not isinstance(registry, DeviceRegistryService):
            self.logger.warning("Device registry unavailable; RS-485 devices not loaded")
            self._devices = []
            return
        self._devices = registry.list_devices(kind="rs485")
        self.context.state["rs485_devices"] = self._devices
        if not self._devices:
            self.logger.warning("No RS-485 devices configured in database")
            return
        for device in self._devices:
            if not device.get("enabled", True):
                self.logger.info(
                    "RS-485 device #%s '%s' on %s is disabled",
                    device["id"],
                    device["name"],
                    device["port"],
                )
                continue
            self.logger.info(
                "Initializing RS-485 device #%s '%s' on %s @ %s",
                device["id"],
                device["name"],
                device["port"],
                device["baudrate"],
            )
