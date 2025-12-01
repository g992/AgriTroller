"""Base classes for application services."""

from __future__ import annotations

import abc
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict

from agritroller.config import AppConfig


@dataclass
class BootstrapContext:
    """Shared runtime context for all services."""

    config: AppConfig
    state: Dict[str, Any] = field(default_factory=dict)


class Service(abc.ABC):
    """Simple async service life-cycle."""

    name: str

    def __init__(self, name: str, context: BootstrapContext) -> None:
        self.name = name
        self.context = context
        self.logger = logging.getLogger(f"agritroller.{name}")
        self._started = asyncio.Event()

    async def start(self) -> None:
        """Start the service (idempotent)."""
        if self._started.is_set():
            return
        self.logger.info("Starting service")
        await self._start()
        self._started.set()

    async def stop(self) -> None:
        """Stop the service gracefully."""
        if not self._started.is_set():
            return
        self.logger.info("Stopping service")
        await self._stop()
        self._started.clear()

    @abc.abstractmethod
    async def _start(self) -> None:
        ...

    async def _stop(self) -> None:
        """Optional hook for subclasses."""
        return
