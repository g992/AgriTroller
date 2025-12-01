"""Coarse scheduler orchestrating periodic tasks."""

from __future__ import annotations

import asyncio
import contextlib

from agritroller.config import SchedulerConfig
from agritroller.services.base import BootstrapContext, Service
from agritroller.services.logic import LogicService


class SchedulerService(Service):
    """Triggers routines based on template-driven rules."""

    def __init__(self, context: BootstrapContext, config: SchedulerConfig) -> None:
        super().__init__("scheduler", context)
        self.config = config
        self._task: asyncio.Task | None = None

    async def _start(self) -> None:
        self.logger.info("Scheduler tick = %ss", self.config.tick_seconds)
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._tick())

    async def _stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._task = None

    async def _tick(self) -> None:
        while True:
            await asyncio.sleep(self.config.tick_seconds)
            self.logger.debug(
                "Evaluating schedules with template %s",
                self.context.state.get("rs485_template"),
            )
            logic = self.context.state.get("logic_service")
            if isinstance(logic, LogicService):
                await logic.dispatch_cycle()
