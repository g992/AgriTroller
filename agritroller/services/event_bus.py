"""Simple in-memory event bus."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, NotRequired, Set, TypedDict, Literal

from agritroller.services.base import BootstrapContext, Service


NotificationSeverity = Literal["ok", "warning", "error"]


class NotificationBody(TypedDict):
    """Payload describing user-facing notification details."""

    severity: NotificationSeverity
    message: str
    source: str
    created_at: str


class EventPayload(TypedDict):
    """Standardized event payload broadcasted across the stack."""

    type: str
    timestamp: str
    payload: Dict[str, Any]
    notify: bool
    notification: NotRequired[NotificationBody]


class NotificationEventPayload(EventPayload):
    """Specialized payload for events that must appear in notifications feed."""

    notify: Literal[True]
    notification: NotificationBody


@dataclass
class EventSubscription:
    """Handle returned by EventBus.subscribe()."""

    queue: asyncio.Queue[EventPayload]
    bus: "EventBus"

    async def get(self) -> EventPayload:
        return await self.queue.get()

    async def close(self) -> None:
        await self.bus._unsubscribe(self.queue)


class EventBus:
    """Fan-out publisher that broadcasts dict payloads to subscribers."""

    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue[EventPayload]] = set()
        self._lock = asyncio.Lock()

    async def publish(self, event: EventPayload) -> None:
        async with self._lock:
            subscribers: List[asyncio.Queue[EventPayload]] = list(self._subscribers)
        for queue in subscribers:
            queue.put_nowait(event)

    async def subscribe(self) -> EventSubscription:
        queue: asyncio.Queue[EventPayload] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        return EventSubscription(queue=queue, bus=self)

    async def _unsubscribe(self, queue: asyncio.Queue[EventPayload]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)


class EventBusService(Service):
    """Initializes the shared event bus and exposes it through the bootstrap context."""

    def __init__(self, context: BootstrapContext) -> None:
        super().__init__("event_bus", context)
        self.bus = EventBus()

    async def _start(self) -> None:
        self.context.state["event_bus"] = self.bus
        self.logger.info("Event bus ready")

    async def _stop(self) -> None:
        self.context.state.pop("event_bus", None)
