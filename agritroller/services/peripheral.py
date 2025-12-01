"""Peripheral controller UART/HID bridge service."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any, Dict, List

from agritroller.config import SerialConfig
from agritroller.services.base import BootstrapContext, Service
from agritroller.services.device_registry import DeviceRegistryService


class PeripheralControllerService(Service):
    """Handles UART commands and HID events for peripheral controllers."""

    def __init__(self, context: BootstrapContext, config: SerialConfig) -> None:
        super().__init__("peripheral_controller", context)
        self.config = config
        self._reader_tasks: Dict[int, asyncio.Task] = {}
        self._devices: List[Dict[str, Any]] = []

    async def _start(self) -> None:
        await self._load_devices()
        if not self._devices:
            self.logger.warning("No peripheral UART devices configured in database")
            return
        loop = asyncio.get_running_loop()
        for device in self._devices:
            if not device.get("enabled", True):
                self.logger.info(
                    "Peripheral controller #%s '%s' on %s is disabled",
                    device["id"],
                    device["name"],
                    device["port"],
                )
                continue
            self.logger.info(
                "Opening peripheral UART #%s '%s' on %s @ %s",
                device["id"],
                device["name"],
                device["port"],
                device["baudrate"],
            )
            task = loop.create_task(self._fake_serial_reader(device))
            self._reader_tasks[device["id"]] = task

    async def _stop(self) -> None:
        for task in self._reader_tasks.values():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._reader_tasks.clear()

    async def _load_devices(self) -> None:
        registry = self.context.state.get("device_registry")
        if not isinstance(registry, DeviceRegistryService):
            self.logger.warning("Device registry unavailable; peripheral devices not loaded")
            self._devices = []
            return
        self._devices = registry.list_devices(kind="peripheral")
        self.context.state["peripheral_devices"] = self._devices

    async def _fake_serial_reader(self, device: Dict[str, Any]) -> None:
        while True:
            await asyncio.sleep(1)
            self.logger.debug(
                "Peripheral heartbeat received from %s (%s)",
                device["name"],
                device["port"],
            )
