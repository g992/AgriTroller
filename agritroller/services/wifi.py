"""Wi-Fi scanning and connection helpers."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agritroller.config import WifiConfig
from agritroller.services.base import BootstrapContext, Service
from agritroller.services.event_bus import EventBus


class WifiService(Service):
    """Expose a best-effort Wi-Fi control surface via nmcli or fallbacks."""

    def __init__(self, context: BootstrapContext, config: WifiConfig) -> None:
        super().__init__("wifi", context)
        self.config = config
        self._state: Dict[str, Any] = {
            "ssid": None,
            "status": "disconnected",
            "last_connected_at": None,
            "last_error": None,
        }
        self._nmcli_path = shutil.which("nmcli")
        self._airport_path = self._detect_airport()

    async def _start(self) -> None:
        self._state = self._load_state()
        self.context.state["wifi_service"] = self
        self.logger.info(
            "Wi-Fi service ready (nmcli=%s, state=%s)", bool(self._nmcli_path), self.config.state_file
        )
        await self._broadcast_status(self.get_status(), notify=False)

    async def _stop(self) -> None:
        self.context.state.pop("wifi_service", None)

    async def scan_networks(self) -> List[Dict[str, Any]]:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._scan_networks_sync),
                timeout=self.config.scan_timeout + 2,
            )
        except asyncio.TimeoutError:
            self.logger.warning("Wi-Fi scan timed out after %.1fs", self.config.scan_timeout)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self.logger.warning("Wi-Fi scan failed: %s", exc)
        return self._fallback_networks()

    async def connect(self, ssid: str, password: Optional[str] = None) -> Dict[str, Any]:
        cleaned_ssid = ssid.strip()
        if not cleaned_ssid:
            raise ValueError("SSID is required")

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._connect_sync, cleaned_ssid, password or ""),
                timeout=self.config.connect_timeout + 2,
            )
            await self._broadcast_status(result)
            return result
        except asyncio.TimeoutError:
            message = f"Wi-Fi connect timed out after {self.config.connect_timeout:.1f}s"
            self.logger.warning(message)
            self._update_state(cleaned_ssid, "error", message)
            result = {
                "ssid": cleaned_ssid,
                "status": "error",
                "message": message,
                **self.get_status(),
            }
            await self._broadcast_status(result)
            return result

    def get_status(self) -> Dict[str, Any]:
        return {
            "ssid": self._state.get("ssid"),
            "status": self._state.get("status", "disconnected"),
            "last_connected_at": self._state.get("last_connected_at"),
            "last_error": self._state.get("last_error"),
        }

    def _scan_networks_sync(self) -> List[Dict[str, Any]]:
        if self._nmcli_path:
            raw_output = self._run_nmcli_scan()
            parsed = self._parse_nmcli_output(raw_output)
            if parsed:
                return parsed
        if self._airport_path:
            raw_output = self._run_airport_scan()
            parsed = self._parse_airport_output(raw_output)
            if parsed:
                return parsed
        return self._fallback_networks()

    def _run_nmcli_scan(self) -> str:
        command = [
            self._nmcli_path,
            "-t",
            "-f",
            "ACTIVE,SSID,SIGNAL,SECURITY",
            "device",
            "wifi",
            "list",
        ]
        proc = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=self.config.scan_timeout,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.strip() or proc.stdout.strip()
            if "not authorized" in stderr.lower():
                raise RuntimeError("nmcli not authorized; grant NetworkManager control via polkit or sudo.")
            raise RuntimeError(stderr or "nmcli scan failed")
        return proc.stdout

    def _parse_nmcli_output(self, raw: str) -> List[Dict[str, Any]]:
        networks: List[Dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(":")
            if len(parts) < 4:
                continue
            active_flag = parts[0].lower() in {"yes", "y", "true", "on", "*", "1"}
            signal_raw = parts[-2] or "0"
            security = parts[-1] or "open"
            ssid = ":".join(parts[1:-2]).strip() or "(hidden)"
            try:
                signal = int(signal_raw)
            except ValueError:
                signal = 0
            networks.append(
                {
                    "ssid": ssid,
                    "signal": max(0, min(100, signal)),
                    "security": security,
                    "active": active_flag or self._state.get("ssid") == ssid,
                }
            )
        return networks

    def _run_airport_scan(self) -> str:
        command = [self._airport_path or "airport", "-s"]
        proc = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=self.config.scan_timeout,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.strip() or proc.stdout.strip()
            raise RuntimeError(stderr or "airport scan failed")
        return proc.stdout

    def _parse_airport_output(self, raw: str) -> List[Dict[str, Any]]:
        networks: List[Dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.lower().startswith("ssid "):
                continue
            # airport aligns columns; BSSID is a reliable delimiter
            parts = line.split()
            if len(parts) < 5:
                continue
            bssid_index = next((idx for idx, token in enumerate(parts) if ":" in token and len(token) == 17), None)
            if bssid_index is None or bssid_index == 0:
                continue
            ssid = " ".join(parts[:bssid_index]).strip() or "(hidden)"
            try:
                signal = abs(int(parts[bssid_index + 1])) if len(parts) > bssid_index + 1 else 0
                signal = max(0, min(100, 100 - signal))  # rough mapping from RSSI to quality
            except ValueError:
                signal = 0
            security = " ".join(parts[bssid_index + 4 :]) if len(parts) > bssid_index + 4 else "open"
            networks.append(
                {
                    "ssid": ssid,
                    "signal": signal,
                    "security": security or "open",
                    "active": self._state.get("ssid") == ssid,
                }
            )
        return networks

    def _connect_sync(self, ssid: str, password: str) -> Dict[str, Any]:
        if not self._nmcli_path:
            self.logger.info("nmcli not available; storing Wi-Fi selection for %s", ssid)
            self._update_state(ssid, "connected", None)
            return {
                "ssid": ssid,
                "status": "connected",
                "message": "Сеть сохранена локально (nmcli недоступен)",
                "last_connected_at": self._state.get("last_connected_at"),
                "last_error": None,
            }

        try:
            proc = self._run_nmcli_connect(ssid, password)
            success = proc.returncode == 0
            message = proc.stdout.strip() or proc.stderr.strip() or "nmcli завершился без вывода"
        except Exception as exc:  # pragma: no cover - rare path
            success = False
            message = str(exc)

        status = "connected" if success else "error"
        error_text = None if success else message
        self._update_state(ssid, status, error_text)
        return {
            "ssid": ssid,
            "status": status,
            "message": message,
            "last_connected_at": self._state.get("last_connected_at"),
            "last_error": self._state.get("last_error"),
        }

    def _run_nmcli_connect(self, ssid: str, password: str) -> subprocess.CompletedProcess[str]:
        command = [self._nmcli_path or "nmcli", "device", "wifi", "connect", ssid]
        if password:
            command.extend(["password", password])
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=self.config.connect_timeout,
        )

    def _update_state(self, ssid: str, status: str, error: Optional[str]) -> None:
        if status == "connected":
            self._state["last_connected_at"] = datetime.now(tz=timezone.utc).isoformat()
            self._state["last_error"] = None
        else:
            self._state["last_error"] = error
        self._state["ssid"] = ssid
        self._state["status"] = status
        self._save_state()

    async def _broadcast_status(self, status: Dict[str, Any], notify: bool = True) -> None:
        bus = self._get_event_bus()
        if not bus:
            return
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        status_value = status.get("status") or "unknown"
        ssid = status.get("ssid") or "—"
        message = status.get("message") or status.get("last_error") or ""
        severity = "ok" if status_value == "connected" else "error"
        if status_value == "connected":
            notif_message = f"Wi‑Fi подключен: {ssid}"
        elif status_value == "disconnected":
            notif_message = message or "Wi‑Fi отключен"
        else:
            notif_message = message or "Wi‑Fi статус обновлён"
        event = {
            "type": "wifi_status",
            "timestamp": timestamp,
            "payload": {
                "status": status_value,
                "ssid": ssid,
                "message": message,
                "last_error": status.get("last_error"),
                "last_connected_at": status.get("last_connected_at"),
            },
            "notify": notify,
        }
        if notify:
            event["notification"] = {
                "severity": severity,
                "message": notif_message,
                "source": "wifi",
                "created_at": timestamp,
            }
        await bus.publish(event)  # type: ignore[arg-type]

    def _get_event_bus(self) -> Optional[EventBus]:
        bus = self.context.state.get("event_bus")
        return bus if isinstance(bus, EventBus) else None

    def _detect_airport(self) -> Optional[str]:
        path = shutil.which("airport")
        if path:
            return path
        mac_path = (
            "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        )
        return mac_path if Path(mac_path).exists() else None

    def _load_state(self) -> Dict[str, Any]:
        state_file = self.config.state_file
        state_file.parent.mkdir(parents=True, exist_ok=True)
        if not state_file.exists():
            return dict(self._state)
        try:
            loaded = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                merged = {**self._state, **loaded}
                return merged
        except (OSError, json.JSONDecodeError) as exc:
            self.logger.warning("Failed to read Wi-Fi state %s: %s", state_file, exc)
        return dict(self._state)

    def _save_state(self) -> None:
        state_file = self.config.state_file
        try:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:  # pragma: no cover - best effort
            self.logger.warning("Failed to persist Wi-Fi state: %s", exc)

    def _fallback_networks(self) -> List[Dict[str, Any]]:
        preferred_ssid = self._state.get("ssid")
        return [
            {
                "ssid": "agritroller-lab",
                "signal": 72,
                "security": "WPA2",
                "active": preferred_ssid == "agritroller-lab",
            },
            {
                "ssid": "field-gateway",
                "signal": 58,
                "security": "WPA2/WPA3",
                "active": preferred_ssid == "field-gateway",
            },
            {
                "ssid": "setup",
                "signal": 34,
                "security": "open",
                "active": preferred_ssid == "setup",
            },
        ]
