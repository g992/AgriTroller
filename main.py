"""AgriTroller application entrypoint."""

from __future__ import annotations

import asyncio
import logging
import os

from agritroller import ServiceContainer
from agritroller.config import load_app_config_from_env


def configure_logging() -> None:
    level = os.environ.get("AGRITROLLER_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


async def run() -> None:
    configure_logging()
    config = load_app_config_from_env()
    container = ServiceContainer(config)
    await container.start_all()
    try:
        await container.run_forever()
    finally:
        await container.stop_all()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.getLogger("agritroller").info("Shutdown requested via keyboard interrupt")
