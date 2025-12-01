"""
AgriTroller core package.

The package exposes the service container that wires together hardware
adapters (RS-485, peripheral UART), business logic, firmware/template managers,
and the HTTP API used by the Vue frontend.
"""

from .app import ServiceContainer
from .services import BootstrapContext

__all__ = ["BootstrapContext", "ServiceContainer"]
