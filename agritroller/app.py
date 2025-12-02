"""Application bootstrap utilities."""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Dict, List

from agritroller.config import AppConfig
from agritroller.services import (
    BootstrapContext,
    DatabaseService,
    DeviceRegistryService,
    EventBusService,
    FirmwareUpdateService,
    FrontendBridgeService,
    LogicService,
    ModbusScannerService,
    NotificationService,
    PortMonitorService,
    PeripheralControllerService,
    ModuleConfigService,
    RS485Service,
    SchedulerService,
    Service,
    TemplateService,
    VersioningService,
    WifiService,
    WebServerService,
)

logger = logging.getLogger("agritroller.app")


class ServiceContainer:
    """Registers and manages the lifecycle of services."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self.context = BootstrapContext(config=self.config)
        self.services: List[Service] = []

    def register_default_services(self) -> None:
        cfg = self.config
        self.services = [
            VersioningService(self.context, cfg.versions),
            DatabaseService(self.context, cfg.database),
            DeviceRegistryService(self.context, cfg.serial, cfg.rs485),
            TemplateService(self.context, cfg.templates),
            ModuleConfigService(self.context, cfg.module_configs),
            FirmwareUpdateService(self.context, cfg.firmware),
            EventBusService(self.context),
            NotificationService(self.context),
            WifiService(self.context, cfg.wifi),
            PortMonitorService(self.context, cfg.port_monitor),
            LogicService(self.context),
            ModbusScannerService(self.context),
            SchedulerService(self.context, cfg.scheduler),
            PeripheralControllerService(self.context, cfg.serial),
            RS485Service(self.context, cfg.rs485),
            FrontendBridgeService(self.context, cfg.frontend),
            WebServerService(self.context, cfg.web, cfg.frontend),
        ]

    async def start_all(self) -> None:
        if not self.services:
            self.register_default_services()
        for service in self.services:
            await service.start()

    async def stop_all(self) -> None:
        for service in reversed(self.services):
            await service.stop()

    async def run_forever(self) -> None:
        logger.info("AgriTroller stack started. Press Ctrl+C to stop.")
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        shutdown_signals = (signal.SIGINT, signal.SIGTERM)
        previous_handlers: Dict[int, signal.Handlers] = {}

        def request_shutdown() -> None:
            if not stop_event.is_set():
                logger.info("Shutdown signal received; stopping services...")
                stop_event.set()

        for sig in shutdown_signals:
            try:
                previous_handlers[sig] = signal.getsignal(sig)
                loop.add_signal_handler(sig, request_shutdown)
            except NotImplementedError:
                # Windows/limited event loops do not support add_signal_handler.
                previous_handlers[sig] = signal.signal(sig, lambda *_: request_shutdown())

        try:
            await stop_event.wait()
        finally:
            for sig in shutdown_signals:
                handler = previous_handlers.get(sig, signal.SIG_DFL)
                try:
                    loop.remove_signal_handler(sig)
                except NotImplementedError:
                    pass
                signal.signal(sig, handler)
