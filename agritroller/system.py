"""System metrics helpers for AgriTroller."""

from __future__ import annotations

import glob
import platform
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
from serial.tools import list_ports


def gather_system_metrics(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Collect CPU, memory, storage, and database file usage statistics."""

    cpu_info = {
        "percent": psutil.cpu_percent(interval=None),
        "load_average": list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else None,
        "cores": psutil.cpu_count(logical=True) or 0,
    }

    virtual_mem = psutil.virtual_memory()
    memory_info = {
        "total_bytes": virtual_mem.total,
        "used_bytes": virtual_mem.used,
        "available_bytes": virtual_mem.available,
        "percent": virtual_mem.percent,
    }

    storage_path = Path(db_path).parent if db_path else Path.home()
    disk_usage = psutil.disk_usage(str(storage_path))
    storage_info = {
        "mount": str(storage_path),
        "total_bytes": disk_usage.total,
        "used_bytes": disk_usage.used,
        "free_bytes": disk_usage.free,
        "percent": disk_usage.percent,
    }

    database_info = {
        "path": str(db_path) if db_path else None,
        "size_bytes": _safe_file_size(db_path) if db_path else 0,
    }

    return {
        "cpu": cpu_info,
        "memory": memory_info,
        "storage": storage_info,
        "database": database_info,
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _safe_file_size(path: Optional[Path]) -> int:
    if not path:
        return 0
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0


def detect_serial_ports() -> List[str]:
    """Return a best-effort list of available serial/UART ports."""

    devices: List[str] = []
    try:
        devices = [port.device for port in list_ports.comports() if port.device]
    except Exception:
        devices = []

    if devices:
        # remove duplicates while preserving order
        seen: Dict[str, None] = {}
        for dev in devices:
            if dev not in seen:
                seen[dev] = None
        return list(seen.keys())

    return _fallback_serial_ports()


def _fallback_serial_ports() -> List[str]:
    system = platform.system().lower()
    patterns: List[str] = []
    if "linux" in system:
        patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/ttyS*"]
    elif "darwin" in system or "mac" in system:
        patterns = ["/dev/tty.*", "/dev/cu.*"]
    elif "win" in system:
        # COM paths are not globbable reliably; return a preset
        return [f"COM{idx}" for idx in range(1, 9)]

    matches: List[str] = []
    for pattern in patterns:
        matches.extend(glob.glob(pattern))

    if matches:
        matches = sorted(set(matches))
        return matches

    return ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "COM3", "COM4"]
