"""FastAPI server exposing AgriTroller APIs."""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import contextlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, ConfigDict

from agritroller.config import FrontendConfig, WebConfig
from agritroller.services.base import BootstrapContext
from agritroller.services.device_registry import DeviceKind, DeviceRegistryService
from agritroller.services.event_bus import EventBus
from agritroller.services.module_configs import ModuleConfigService
from agritroller.services.modbus_scanner import ModbusScannerService
from agritroller.services.notifications import NotificationService
from agritroller.services.port_monitor import PortMonitorService
from agritroller.services.templates import TemplateService
from agritroller.services.wifi import WifiService
from agritroller.system import detect_serial_ports, gather_system_metrics


class DevicePayload(BaseModel):
    kind: str = Field(pattern="^(rs485|peripheral)$")
    name: str
    port: str
    baudrate: int
    metadata: Dict[str, Any] | None = None
    device_type_slug: Optional[str] = "generic_empty"
    mapping: Optional[Dict[str, Any]] = None
    enabled: bool = True


class DeviceUpdatePayload(BaseModel):
    kind: Optional[str] = Field(default=None, pattern="^(rs485|peripheral)$")
    name: Optional[str] = None
    port: Optional[str] = None
    baudrate: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    device_type_slug: Optional[str] = None
    mapping: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class WifiConnectPayload(BaseModel):
    ssid: str
    password: Optional[str] = None


class ModbusScanPayload(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    port: Optional[str] = None
    baudrate: Optional[int] = None
    device_id: Optional[int] = None
    start_address: int = Field(ge=1, le=247)
    end_address: int = Field(ge=1, le=247)
    register_address: int = Field(ge=0, le=65535, alias="register")
    function: int = Field(default=3, ge=1, le=4)
    count: int = Field(default=1, ge=1, le=4)
    timeout: float = Field(default=0.2, gt=0, lt=5)


class RegisterSpec(BaseModel):
    name: str
    register_type: str = Field(alias="type")
    address: int
    length: int = Field(default=1, ge=1)
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class FeatureSpec(BaseModel):
    slug: str
    registers: List[RegisterSpec]
    model_config = ConfigDict(extra="allow")


class ModuleTypeConfigPayload(BaseModel):
    slug: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    name: str
    description: Optional[str] = None
    registers: List[RegisterSpec] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")


class ModuleConfigPayload(BaseModel):
    slug: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    name: str
    module_type: Optional[str] = None
    description: Optional[str] = None
    registers: List[RegisterSpec] = Field(default_factory=list)
    actuators: List[FeatureSpec] = Field(default_factory=list)
    sensors: List[FeatureSpec] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")


class WebServer:
    """FastAPI/uvicorn host for HTTP API and static assets."""

    def __init__(
        self,
        context: BootstrapContext,
        config: WebConfig,
        frontend_config: Optional[FrontendConfig] = None,
    ) -> None:
        self.context = context
        self.config = config
        self.frontend_config = frontend_config
        self.logger = logging.getLogger("agritroller.web")
        self.app = FastAPI(title="AgriTroller API", version="0.1.0")
        self._configure_middlewares()
        self._configure_routes()
        self._mount_static()
        self._server: Optional[uvicorn.Server] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._task:
            return
        self.logger.info("Starting HTTP server on %s:%s", self.config.host, self.config.port)
        config_kwargs = {
            "app": self.app,
            "host": self.config.host,
            "port": self.config.port,
            "reload": self.config.reload,
            "loop": "asyncio",
            "log_config": None,
        }
        config_sig = inspect.signature(uvicorn.Config)  # older uvicorns lack install_signal_handlers
        if "install_signal_handlers" in config_sig.parameters:
            config_kwargs["install_signal_handlers"] = False
        config = uvicorn.Config(**config_kwargs)
        self._server = uvicorn.Server(config)
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._server.serve())

    async def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=3)
            except asyncio.TimeoutError:
                self.logger.warning("HTTP server shutdown timed out; cancelling task")
                self._task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task
        self._task = None
        self._server = None

    def _configure_middlewares(self) -> None:
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _configure_routes(self) -> None:
        @self.app.get("/api/health")
        async def health() -> Dict[str, str]:
            return {"status": "ok"}

        @self.app.get("/api/versions")
        async def versions() -> Dict[str, Any]:
            versions = self.context.state.get("versions")
            if not versions:
                raise HTTPException(status_code=503, detail="Version file not ready")
            return versions

        @self.app.get("/api/templates")
        async def list_templates() -> Any:
            service = self._get_template_service()
            return service.list_templates()

        @self.app.get("/api/module-configs/types")
        async def list_module_types() -> Any:
            service = self._get_module_config_service()
            return [self._serialize_module_type(record) for record in service.list_module_types()]

        @self.app.get("/api/module-configs/modules")
        async def list_modules() -> Any:
            service = self._get_module_config_service()
            return [self._serialize_module(record) for record in service.list_modules()]

        @self.app.post("/api/module-configs/types", status_code=201)
        async def create_module_type(payload: ModuleTypeConfigPayload) -> Any:
            service = self._get_module_config_service()
            try:
                created = service.save_module_type(payload.model_dump(exclude_none=True), overwrite=False)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return self._serialize_module_type(created.to_record())

        @self.app.put("/api/module-configs/types/{slug}")
        async def update_module_type(slug: str, payload: ModuleTypeConfigPayload) -> Any:
            service = self._get_module_config_service()
            updated_payload = payload.model_dump(exclude_none=True)
            updated_payload["slug"] = slug
            try:
                updated = service.save_module_type(updated_payload, overwrite=True)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return self._serialize_module_type(updated.to_record())

        @self.app.delete("/api/module-configs/types/{slug}", status_code=204)
        async def delete_module_type(slug: str) -> Response:
            service = self._get_module_config_service()
            deleted = service.delete_config(slug, kind="module_type")
            if not deleted:
                raise HTTPException(status_code=404, detail="Module type not found")
            return Response(status_code=204)

        @self.app.post("/api/module-configs/modules", status_code=201)
        async def create_module(payload: ModuleConfigPayload) -> Any:
            service = self._get_module_config_service()
            try:
                created = service.save_module(payload.model_dump(exclude_none=True), overwrite=False)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return self._serialize_module(created.to_record())

        @self.app.put("/api/module-configs/modules/{slug}")
        async def update_module(slug: str, payload: ModuleConfigPayload) -> Any:
            service = self._get_module_config_service()
            updated_payload = payload.model_dump(exclude_none=True)
            updated_payload["slug"] = slug
            try:
                updated = service.save_module(updated_payload, overwrite=True)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return self._serialize_module(updated.to_record())

        @self.app.delete("/api/module-configs/modules/{slug}", status_code=204)
        async def delete_module(slug: str) -> Response:
            service = self._get_module_config_service()
            deleted = service.delete_config(slug, kind="module")
            if not deleted:
                raise HTTPException(status_code=404, detail="Module not found")
            return Response(status_code=204)

        @self.app.get("/api/device-types")
        async def list_device_types() -> Any:
            raise HTTPException(status_code=404, detail="Device type API disabled")

        @self.app.get("/api/templates/{slug}")
        async def get_template(slug: str) -> Any:
            service = self._get_template_service()
            template = service.get_template(slug)
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            return template

        @self.app.get("/api/system/metrics")
        async def system_metrics() -> Dict[str, Any]:
            db_path = self.context.state.get("db_path")
            metrics = gather_system_metrics(db_path)
            return metrics

        @self.app.post("/api/system/restart")
        async def restart_system() -> Dict[str, str]:
            await self._schedule_restart()
            return {"status": "restarting"}

        @self.app.get("/api/wifi/networks")
        async def list_wifi_networks() -> Dict[str, Any]:
            wifi = self._get_wifi_service()
            networks = await wifi.scan_networks()
            return {"networks": networks}

        @self.app.get("/api/wifi/status")
        async def wifi_status() -> Dict[str, Any]:
            wifi = self._get_wifi_service()
            return wifi.get_status()

        @self.app.post("/api/wifi/connect")
        async def wifi_connect(payload: WifiConnectPayload) -> Dict[str, Any]:
            wifi = self._get_wifi_service()
            try:
                return await wifi.connect(payload.ssid, payload.password)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        @self.app.get("/api/devices/ports")
        async def list_serial_ports() -> Dict[str, List[str]]:
            ports = await asyncio.to_thread(detect_serial_ports)
            return {"ports": ports}

        @self.app.get("/api/devices")
        async def list_devices(kind: Optional[str] = None) -> Any:
            registry = self._get_device_registry()
            normalized_kind = kind
            if normalized_kind == "esp":
                normalized_kind = "peripheral"
            if normalized_kind not in (None, "rs485", "peripheral"):
                raise HTTPException(status_code=400, detail="Unsupported device type")
            return (
                registry.list_devices(kind=normalized_kind) if normalized_kind else registry.list_devices()
            )

        @self.app.post("/api/devices", status_code=201)
        async def create_device(payload: DevicePayload) -> Any:
            registry = self._get_device_registry()
            try:
                device = registry.create_device(
                    kind=payload.kind,  # type: ignore[arg-type]
                    name=payload.name,
                    port=payload.port,
                    baudrate=payload.baudrate,
                    metadata=payload.metadata,
                    device_type_slug=payload.device_type_slug or "generic_empty",
                    mapping=payload.mapping,
                    enabled=payload.enabled,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            monitor = self._get_port_monitor(optional=True)
            if monitor:
                try:
                    device = await monitor.refresh_device(device["id"])
                except Exception:  # pragma: no cover - best effort
                    self.logger.exception("Failed to refresh device port status")
            return device

        @self.app.get("/api/devices/{device_id}")
        async def get_device(device_id: int) -> Any:
            registry = self._get_device_registry()
            device = registry.get_device(device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")
            return device

        @self.app.put("/api/devices/{device_id}")
        async def update_device(device_id: int, payload: DeviceUpdatePayload) -> Any:
            registry = self._get_device_registry()
            try:
                device = registry.update_device(
                    device_id,
                    kind=cast(Optional[DeviceKind], payload.kind),
                    name=payload.name,
                    port=payload.port,
                    baudrate=payload.baudrate,
                    metadata=payload.metadata,
                    device_type_slug=payload.device_type_slug,
                    mapping=payload.mapping,
                    enabled=payload.enabled,
                )
            except LookupError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            if payload.port is not None or payload.baudrate is not None:
                monitor = self._get_port_monitor(optional=True)
                if monitor:
                    try:
                        device = await monitor.refresh_device(device_id)
                    except Exception:  # pragma: no cover - best effort
                        self.logger.exception("Failed to refresh device port status")
            return device

        @self.app.delete("/api/devices/{device_id}", status_code=204)
        async def delete_device(device_id: int) -> Response:
            registry = self._get_device_registry()
            deleted = registry.delete_device(device_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Device not found")
            return Response(status_code=204)

        @self.app.post("/api/devices/{device_id}/refresh-port")
        async def refresh_device_port(device_id: int) -> Any:
            monitor = self._get_port_monitor()
            try:
                return await monitor.refresh_device(device_id)
            except LookupError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

        @self.app.post("/api/rs485/scan", status_code=201)
        async def start_modbus_scan(payload: ModbusScanPayload) -> Any:
            scanner = self._get_modbus_scanner()
            registry = self._get_device_registry()
            if payload.start_address > payload.end_address:
                raise HTTPException(status_code=400, detail="start_address must be <= end_address")
            port = payload.port
            baudrate = payload.baudrate
            device_name: Optional[str] = None
            device_id: Optional[int] = payload.device_id
            if device_id is not None:
                device = registry.get_device(device_id)
                if not device or device.get("kind") != "rs485":
                    raise HTTPException(status_code=404, detail="RS-485 device not found")
                port = device["port"]
                baudrate = device["baudrate"]
                device_name = device["name"]
            if not port:
                raise HTTPException(status_code=400, detail="Port is required")
            if baudrate is None:
                raise HTTPException(status_code=400, detail="Baudrate is required")
            job = await scanner.start_scan(
                port=port,
                baudrate=baudrate,
                start_address=payload.start_address,
                end_address=payload.end_address,
                register=payload.register_address,
                function=payload.function,
                count=payload.count,
                timeout=payload.timeout,
                device_id=device_id,
                device_name=device_name,
            )
            return scanner.serialize_job(job)

        @self.app.get("/api/rs485/scan")
        async def list_modbus_scans() -> Any:
            scanner = self._get_modbus_scanner()
            return [scanner.serialize_job(job) for job in scanner.list_jobs()]

        @self.app.get("/api/rs485/scan/{job_id}")
        async def get_modbus_scan(job_id: str) -> Any:
            scanner = self._get_modbus_scanner()
            job = scanner.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Scan job not found")
            return scanner.serialize_job(job)

        @self.app.get("/api/notifications")
        async def list_notifications(
            limit: int = Query(20, ge=1, le=200),
            include_read: bool = True,
        ) -> Any:
            notification_service = self._get_notification_service()
            return notification_service.list_notifications(limit=limit, include_read=include_read)

        @self.app.delete("/api/notifications/{notification_id}", status_code=204)
        async def delete_notification(notification_id: int) -> Response:
            notification_service = self._get_notification_service()
            deleted = notification_service.delete(notification_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Notification not found")
            return Response(status_code=204)

        @self.app.delete("/api/notifications", status_code=204)
        async def delete_all_notifications() -> Response:
            notification_service = self._get_notification_service()
            notification_service.delete_all()
            return Response(status_code=204)

        @self.app.post("/api/notifications/{notification_id}/read", status_code=204)
        async def mark_notification_read(notification_id: int) -> Response:
            notification_service = self._get_notification_service()
            updated = notification_service.mark_read(notification_id)
            if not updated:
                raise HTTPException(status_code=404, detail="Notification not found")
            return Response(status_code=204)

        @self.app.post("/api/notifications/read-all", status_code=204)
        async def mark_all_notifications_read() -> Response:
            notification_service = self._get_notification_service()
            notification_service.mark_all_read()
            return Response(status_code=204)

        @self.app.websocket("/api/ws/events")
        async def events_socket(websocket: WebSocket) -> None:
            await websocket.accept()
            bus = self._get_event_bus()
            subscription = await bus.subscribe()
            await websocket.send_json(
                {
                    "type": "event_bus.connected",
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    "payload": {"message": "Event bus connected"},
                    "notify": False,
                }
            )
            try:
                while True:
                    event = await subscription.get()
                    await websocket.send_json(event)
            except WebSocketDisconnect:
                self.logger.info("Event websocket disconnected")
            finally:
                await subscription.close()

    def _mount_static(self) -> None:
        if not self.frontend_config:
            return
        dist_dir = Path(self.frontend_config.dist_dir)
        if dist_dir.exists():
            self.logger.info("Serving frontend assets from %s", dist_dir)
            # Mount after API routes so /api/* continues to work.
            self.app.mount(
                "/",
                StaticFiles(directory=str(dist_dir), html=True),
                name="frontend",
            )

    def _get_template_service(self) -> TemplateService:
        template_service = self.context.state.get("template_service")
        if not isinstance(template_service, TemplateService):
            raise HTTPException(status_code=503, detail="Template service unavailable")
        return template_service

    def _get_module_config_service(self) -> ModuleConfigService:
        service = self.context.state.get("module_config_service")
        if not isinstance(service, ModuleConfigService):
            raise HTTPException(status_code=503, detail="Module config service unavailable")
        return service

    def _get_device_registry(self) -> DeviceRegistryService:
        registry = self.context.state.get("device_registry")
        if not isinstance(registry, DeviceRegistryService):
            raise HTTPException(status_code=503, detail="Device registry unavailable")
        return registry

    def _get_event_bus(self) -> EventBus:
        bus = self.context.state.get("event_bus")
        if not isinstance(bus, EventBus):
            raise HTTPException(status_code=503, detail="Event bus unavailable")
        return bus

    def _get_notification_service(self) -> NotificationService:
        service = self.context.state.get("notification_service")
        if not isinstance(service, NotificationService):
            raise HTTPException(status_code=503, detail="Notification service unavailable")
        return service

    def _get_modbus_scanner(self) -> ModbusScannerService:
        service = self.context.state.get("modbus_scanner")
        if not isinstance(service, ModbusScannerService):
            raise HTTPException(status_code=503, detail="Modbus scanner unavailable")
        return service

    def _get_port_monitor(self, optional: bool = False) -> Optional[PortMonitorService]:
        service = self.context.state.get("port_monitor")
        if not isinstance(service, PortMonitorService):
            if optional:
                return None
            raise HTTPException(status_code=503, detail="Port monitor unavailable")
        return service

    def _get_wifi_service(self) -> WifiService:
        service = self.context.state.get("wifi_service")
        if not isinstance(service, WifiService):
            raise HTTPException(status_code=503, detail="Wi-Fi service unavailable")
        return service

    def _serialize_module_type(self, record: Dict[str, Any]) -> Dict[str, Any]:
        content = record.get("content", {}) if isinstance(record, dict) else {}
        meta = content.get("meta", {}) if isinstance(content, dict) else {}
        return {
            "slug": content.get("slug") or record.get("slug"),
            "name": content.get("name") or record.get("name"),
            "description": meta.get("description"),
            "registers": content.get("registers", []),
            "meta": meta,
            "kind": record.get("kind", "module_type"),
        }

    def _serialize_module(self, record: Dict[str, Any]) -> Dict[str, Any]:
        content = record.get("content", {}) if isinstance(record, dict) else {}
        meta = content.get("meta", {}) if isinstance(content, dict) else {}
        return {
            "slug": content.get("slug") or record.get("slug"),
            "name": content.get("name") or record.get("name"),
            "module_type": content.get("module_type") or record.get("module_type"),
            "registers": content.get("registers", []),
            "type_registers": content.get("type_registers", []),
            "actuators": content.get("actuators", []),
            "sensors": content.get("sensors", []),
            "meta": meta,
            "kind": record.get("kind", "module"),
        }

    async def _schedule_restart(self) -> None:
        loop = asyncio.get_running_loop()
        loop.call_later(0.5, self._terminate_process)

    def _terminate_process(self) -> None:
        self.logger.warning("Restart requested via API; terminating process")
        os._exit(0)
