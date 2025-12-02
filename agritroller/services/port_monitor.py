"""Monitors UART/RS-485 port availability and broadcasts status events."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import serial
from serial.serialutil import SerialException
from serial.tools import list_ports

from agritroller.config import PortMonitorConfig
from agritroller.services.base import BootstrapContext, Service
from agritroller.services.device_registry import DeviceRegistryService
from agritroller.services.event_bus import EventBus


class PortMonitorService(Service):
    """Validates configured devices against actual serial ports."""

    STATUS_AVAILABLE = "available"
    STATUS_BUSY = "busy"
    STATUS_MISSING = "missing"
    STATUS_UNKNOWN = "unknown"

    def __init__(self, context: BootstrapContext, config: PortMonitorConfig) -> None:
        super().__init__("port_monitor", context)
        self.config = config
        self._task: Optional[asyncio.Task[None]] = None

    async def _start(self) -> None:
        self.context.state["port_monitor"] = self
        await self.refresh_all_ports()
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._watch_ports())
        self.logger.info(
            "Port monitor initialized (interval=%.1fs)",
            max(0.1, self.config.poll_interval),
        )

    async def _stop(self) -> None:
        self.context.state.pop("port_monitor", None)
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._task = None

    async def refresh_all_ports(
        self,
        *,
        notify_on_change_only: bool = False,
        skip_unchanged: bool = False,
    ) -> List[Dict[str, Any]]:
        registry = self._get_registry()
        devices = registry.list_devices()
        results: List[Dict[str, Any]] = []
        for device in devices:
            try:
                updated = await self.refresh_device(
                    device["id"],
                    notify_on_change_only=notify_on_change_only,
                    skip_if_unchanged=skip_unchanged,
                )
                results.append(updated)
            except LookupError:
                continue
        return results

    async def refresh_device(
        self,
        device_id: int,
        *,
        notify_on_change_only: bool = False,
        skip_if_unchanged: bool = False,
    ) -> Dict[str, Any]:
        registry = self._get_registry()
        device = registry.get_device(device_id)
        if not device:
            raise LookupError(f"Device {device_id} not found")
        status, message = await asyncio.to_thread(self._probe_port, device)
        changed = status != device.get("status") or (message or "") != (device.get("status_message") or "")
        if skip_if_unchanged and not changed:
            return device
        updated = registry.update_device_status(
            device_id,
            status=status,
            status_message=message,
        )
        if not notify_on_change_only or changed:
            await self._broadcast_status(updated)
        return updated

    def _probe_port(self, device: Dict[str, Any]) -> Tuple[str, str]:
        port_path = device["port"]
        baudrate = device["baudrate"]
        available_ports = {port.device for port in list_ports.comports() if port.device}
        if port_path not in available_ports and not Path(port_path).exists():
            return self.STATUS_MISSING, "Порт недоступен в системе"
        try:
            with serial.Serial(port=port_path, baudrate=baudrate, timeout=1):
                return self.STATUS_AVAILABLE, "Порт готов к работе"
        except (SerialException, OSError) as exc:
            return self.STATUS_BUSY, str(exc)

    async def _broadcast_status(self, device: Dict[str, Any]) -> None:
        bus = self._get_event_bus()
        status = device.get("status", self.STATUS_UNKNOWN)
        severity = self._severity_for_status(status)
        message = device.get("status_message") or "Статус порта не определён"
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        event = {
            "type": "device.port_status",
            "timestamp": timestamp,
            "payload": {
                "device_id": device["id"],
                "name": device["name"],
                "port": device["port"],
                "status": status,
                "message": message,
                "checked_at": device.get("status_checked_at") or timestamp,
            },
            "notify": True,
            "notification": {
                "severity": severity,
                "message": f"{device['name']}: {message}",
                "source": "port_monitor",
                "created_at": timestamp,
            },
        }
        await bus.publish(event)

    async def _watch_ports(self) -> None:
        interval = max(0.1, self.config.poll_interval)
        while True:
            await asyncio.sleep(interval)
            try:
                await self.refresh_all_ports(notify_on_change_only=True, skip_unchanged=True)
            except asyncio.CancelledError:
                raise
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception("Port monitor poll failed")

    def _severity_for_status(self, status: str) -> str:
        if status == self.STATUS_AVAILABLE:
            return "ok"
        if status == self.STATUS_BUSY:
            return "warning"
        if status == self.STATUS_MISSING:
            return "error"
        return "warning"

    def _get_registry(self) -> DeviceRegistryService:
        registry = self.context.state.get("device_registry")
        if not isinstance(registry, DeviceRegistryService):
            raise RuntimeError("Device registry unavailable for port monitor")
        return registry

    def _get_event_bus(self) -> EventBus:
        bus = self.context.state.get("event_bus")
        if not isinstance(bus, EventBus):
            raise RuntimeError("Event bus unavailable for port monitor")
        return bus
