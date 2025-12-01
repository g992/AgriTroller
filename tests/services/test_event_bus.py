import pytest

from agritroller.services.event_bus import EventBus


@pytest.mark.asyncio
async def test_event_bus_subscribe_and_publish() -> None:
    bus = EventBus()
    subscription = await bus.subscribe()

    payload = {
        "type": "test.event",
        "timestamp": "2024-01-01T00:00:00+00:00",
        "payload": {"value": 42},
        "notify": False,
    }
    await bus.publish(payload)

    received = await subscription.get()
    assert received == payload

    await subscription.close()
