"""Domain logic service."""

from __future__ import annotations

import asyncio

from agritroller.services.base import BootstrapContext, Service


class LogicService(Service):
    """Central decision maker that bridges scheduler output to hardware adapters."""

    def __init__(self, context: BootstrapContext) -> None:
        super().__init__("logic", context)

    async def _start(self) -> None:
        self.logger.info("Logic service ready")
        await asyncio.sleep(0)
        self.context.state["logic_service"] = self

    async def dispatch_cycle(self) -> None:
        """Placeholder method invoked by scheduler ticks."""
        rs485_template = self.context.state.get("rs485_template", {})
        self.logger.debug("Dispatch cycle with template: %s", rs485_template)
