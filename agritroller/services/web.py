"""Service wrapper for the HTTP API."""

from __future__ import annotations

from agritroller.config import FrontendConfig, WebConfig
from agritroller.services.base import BootstrapContext, Service
from agritroller.web import WebServer


class WebServerService(Service):
    """Bootstraps the HTTP server backing the Vue dashboard."""

    def __init__(
        self,
        context: BootstrapContext,
        config: WebConfig,
        frontend_config: FrontendConfig,
    ) -> None:
        super().__init__("web_server", context)
        self.config = config
        self._web_server = WebServer(context, config, frontend_config)

    async def _start(self) -> None:
        await self._web_server.start()

    async def _stop(self) -> None:
        await self._web_server.stop()
