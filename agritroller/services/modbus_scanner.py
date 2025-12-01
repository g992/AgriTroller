"""Modbus RTU scanner for discovering devices on RS-485 with per-port queues."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import serial

from agritroller.services.base import BootstrapContext, Service


@dataclass
class ScanParams:
    port: str
    baudrate: int
    start_address: int
    end_address: int
    register: int
    function: int
    count: int
    timeout: float
    device_id: Optional[int] = None
    device_name: Optional[str] = None


class PortWorker:
    """Serial worker that executes queued Modbus jobs for a single port."""

    def __init__(self, port: str, service: "ModbusScannerService") -> None:
        self.port = port
        self.service = service
        self.queue: asyncio.Queue[Tuple[str, ScanParams]] = asyncio.Queue()
        self.task: Optional[asyncio.Task[None]] = None
        self.serial: Optional[serial.Serial] = None
        self.current_baudrate: Optional[int] = None
        self.running = False

    def start(self) -> None:
        if self.task:
            return
        self.running = True
        loop = asyncio.get_running_loop()
        self.task = loop.create_task(self._run())

    async def stop(self) -> None:
        self.running = False
        if self.task:
            self.task.cancel()
            with asyncio.exceptions.SuppressCancelledError():
                await self.task
        self._close_serial()
        self.task = None

    async def enqueue(self, job_id: str, params: ScanParams) -> None:
        await self.queue.put((job_id, params))

    async def _run(self) -> None:
        while self.running:
            try:
                job_id, params = await self.queue.get()
            except asyncio.CancelledError:
                break
            job = self.service.jobs.get(job_id)
            if not job:
                self.queue.task_done()
                continue
            job["status"] = "running"
            try:
                await asyncio.to_thread(self._ensure_serial, params)
                await asyncio.to_thread(self.service._scan_with_serial, self.serial, job, params)
                if job.get("status") != "error":
                    job["status"] = "completed"
            except Exception as exc:  # pragma: no cover - defensive
                job["status"] = "error"
                job["error"] = str(exc)
                self._close_serial()
            finally:
                self.queue.task_done()

    def _ensure_serial(self, params: ScanParams) -> None:
        reopen = False
        if self.serial is None or not self.serial.is_open:
            reopen = True
        elif self.current_baudrate != params.baudrate:
            self._close_serial()
            reopen = True
        if reopen:
            self.serial = serial.Serial(
                port=params.port,
                baudrate=params.baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=params.timeout,
            )
            self.current_baudrate = params.baudrate

    def _close_serial(self) -> None:
        if self.serial:
            try:
                self.serial.close()
            except Exception:
                pass
        self.serial = None
        self.current_baudrate = None


class ModbusScannerService(Service):
    """Queues Modbus scan jobs per port, keeping serial connections alive."""

    def __init__(self, context: BootstrapContext, default_timeout: float = 0.2) -> None:
        super().__init__("modbus_scanner", context)
        self.default_timeout = default_timeout
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.workers: Dict[str, PortWorker] = {}
        self._lock = asyncio.Lock()

    async def _start(self) -> None:
        self.context.state["modbus_scanner"] = self

    async def _stop(self) -> None:
        self.context.state.pop("modbus_scanner", None)
        workers = list(self.workers.values())
        self.workers.clear()
        for worker in workers:
            await worker.stop()
        self.jobs.clear()

    async def start_scan(
        self,
        *,
        port: str,
        baudrate: int,
        start_address: int,
        end_address: int,
        register: int,
        function: int = 3,
        count: int = 1,
        timeout: Optional[float] = None,
        device_id: Optional[int] = None,
        device_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = ScanParams(
            port=port,
            baudrate=baudrate,
            start_address=start_address,
            end_address=end_address,
            register=register,
            function=function,
            count=count,
            timeout=timeout or self.default_timeout,
            device_id=device_id,
            device_name=device_name,
        )
        job_id = uuid4().hex
        job = {
            "id": job_id,
            "status": "queued",
            "progress": 0,
            "total": max(0, end_address - start_address + 1),
            "results": [],
            "error": None,
            "started_at": time.time(),
            "device_id": device_id,
            "device_name": device_name,
            "port": port,
        }
        async with self._lock:
            self.jobs[job_id] = job
            worker = self._get_or_create_worker(port)
            await worker.enqueue(job_id, params)
        return self.serialize_job(job)

    def _get_or_create_worker(self, port: str) -> PortWorker:
        worker = self.workers.get(port)
        if not worker:
            worker = PortWorker(port, self)
            self.workers[port] = worker
            worker.start()
        return worker

    def _scan_with_serial(self, ser: Optional[serial.Serial], job: Dict[str, Any], params: ScanParams) -> None:
        if ser is None or not ser.is_open:
            raise RuntimeError("Serial connection unavailable")
        try:
            for address in range(params.start_address, params.end_address + 1):
                if job.get("cancelled"):
                    job["status"] = "cancelled"
                    break
                request = self._build_request(address, params.register, params.count, params.function)
                ser.reset_input_buffer()
                ser.write(request)
                expected_len = 5 + params.count * 2
                response = ser.read(expected_len)
                job["progress"] += 1
                if not self._valid_response(response, address, params.function, params.count):
                    continue
                value = self._parse_value(response, params.count)
                job["results"].append(
                    {
                        "address": address,
                        "register": params.register,
                        "function": params.function,
                        "raw": response.hex(),
                        "value": value,
                        "device_type_slug": job.get("device_type_slug"),
                    }
                )
        except Exception as exc:
            job["status"] = "error"
            job["error"] = str(exc)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

    def list_jobs(self) -> List[Dict[str, Any]]:
        return list(self.jobs.values())

    def serialize_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": job["id"],
            "status": job["status"],
            "progress": job.get("progress", 0),
            "total": job.get("total", 0),
            "results": job.get("results", []),
            "error": job.get("error"),
            "started_at": job.get("started_at"),
            "device_id": job.get("device_id"),
            "device_name": job.get("device_name"),
            "port": job.get("port"),
        }

    @staticmethod
    def _build_request(address: int, register: int, count: int, function: int) -> bytes:
        pdu = bytes(
            [
                address & 0xFF,
                function & 0xFF,
                (register >> 8) & 0xFF,
                register & 0xFF,
                (count >> 8) & 0xFF,
                count & 0xFF,
            ]
        )
        crc = ModbusScannerService._crc16(pdu)
        return pdu + crc.to_bytes(2, byteorder="little")

    @staticmethod
    def _valid_response(response: bytes, address: int, function: int, count: int) -> bool:
        if len(response) < 5:
            return False
        if response[0] != address or response[1] != function:
            return False
        data_len = response[2]
        expected_len = 3 + data_len + 2
        if data_len != count * 2 or len(response) < expected_len:
            return False
        body = response[: expected_len - 2]
        crc = int.from_bytes(response[expected_len - 2 : expected_len], byteorder="little")
        return crc == ModbusScannerService._crc16(body)

    @staticmethod
    def _parse_value(response: bytes, count: int) -> int:
        data_len = response[2]
        data = response[3 : 3 + data_len]
        if len(data) < 2:
            return 0
        value = int.from_bytes(data[:2], byteorder="big", signed=False)
        if count > 1 and len(data) >= count * 2:
            value = int.from_bytes(data[: count * 2], byteorder="big", signed=False)
        return value

    @staticmethod
    def _crc16(data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc & 0xFFFF
