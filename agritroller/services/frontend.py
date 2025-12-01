"""Frontend orchestration service."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from agritroller.config import FrontendConfig
from agritroller.services.base import BootstrapContext, Service


class FrontendBridgeService(Service):
    """Provides metadata to the Vue application and watches build artifacts."""

    def __init__(self, context: BootstrapContext, config: FrontendConfig) -> None:
        super().__init__("frontend_bridge", context)
        self.config = config
        self._watch_task: asyncio.Task | None = None

    async def _start(self) -> None:
        self.logger.info("Serving static assets from %s", self.config.dist_dir)
        dist = Path(self.config.dist_dir)
        dist.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()
        self._watch_task = loop.create_task(self._fake_watch(dist))

    async def _stop(self) -> None:
        if self._watch_task:
            self._watch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._watch_task
        self._watch_task = None

    async def _fake_watch(self, dist: Path) -> None:
        while True:
            await asyncio.sleep(5)
            self.context.state["frontend_manifest"] = {
                "root": str(dist),
                "files": ["index.html"],
            }
