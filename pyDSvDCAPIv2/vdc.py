# pyDSvDCAPIv2/vdc.py
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from pyDSvDCAPIv2.connection import VDCConnection
from pyDSvDCAPIv2.device import Device
from pyDSvDCAPIv2.dsuid import DsUid
from pyDSvDCAPIv2.enums import EventType, VdcCapabilityFlag
from pyDSvDCAPIv2.exceptions import VDCConnectionError
from pyDSvDCAPIv2.heartbeat import HeartbeatTask
from pyDSvDCAPIv2.persistence import PropertyStore
from pyDSvDCAPIv2.ws_client import WebSocketClient

logger = logging.getLogger(__name__)

_RECONNECT_BASE = 2.0
_RECONNECT_MAX = 60.0


class VDC:
    """Top-level VDC entry point. Connects to dSS and manages device lifecycle."""

    def __init__(
        self,
        vdc_id: str,
        name: str,
        version: str,
        server_host: str,
        server_port: int = 62000,
        capabilities: list[VdcCapabilityFlag] | None = None,
        state_path: str = "state.yaml",
        heartbeat_interval: float = 30.0,
        ws_path: str | None = "/vdc/ws",
    ) -> None:
        self._seed = vdc_id
        self.vdc_id = vdc_id  # resolved to dSUID on start()
        self.name = name
        self.version = version
        self.server_host = server_host
        self.server_port = server_port
        self.capabilities: list[VdcCapabilityFlag] = capabilities or []
        self.heartbeat_interval = heartbeat_interval
        self.ws_path = ws_path
        self.heartbeat_metrics: dict[str, str] = {}

        self._devices: dict[str, Device] = {}
        self._store = PropertyStore(state_path)
        self._connection: VDCConnection | None = None
        self._heartbeat: HeartbeatTask | None = None
        self._ws: WebSocketClient | None = None
        self._running = False
        self._reconnect_delay = _RECONNECT_BASE
        self._session_options: dict[str, str] = {}

        # Callbacks
        self.on_scene_event: Callable[[Any], Awaitable[None]] | None = None

    def add_device(self, device: Device) -> None:
        """Register a device with this VDC."""
        device._vdc = self
        self._devices[device.device_id] = device

    async def remove_device(self, device_id: str) -> None:
        """Remove a device from dSS and deregister it."""
        if self._connection:
            await self._connection.send_device_removal(device_id)
        self._devices.pop(device_id, None)
        self._schedule_save()

    async def start(self) -> None:
        """Connect to dSS, run handshake, announce devices, start background tasks."""
        self._load_state()
        self._running = True
        await self._connect_with_retry()

    async def stop(self) -> None:
        """Gracefully stop all background tasks and close the connection."""
        self._running = False
        self._stop_background_tasks()
        if self._connection:
            await self._connection.close()
        self._store.flush()

    async def flush(self) -> None:
        """Force immediate YAML save."""
        self._store.flush()

    def _load_state(self) -> None:
        """Restore persisted state. Resolves vdc_id seed to stable dSUID."""
        data = self._store.load()
        vdc_data = data.get("vdc", {})

        # Resolve stable dSUID — reuse persisted one if present
        if vdc_data.get("vdc_id"):
            self.vdc_id = vdc_data["vdc_id"]
        else:
            self.vdc_id = DsUid.for_vdc(self._seed)

        # Restore device state and resolve dSUIDs
        persisted_devices: dict[str, dict] = {
            d["device_id"]: d for d in data.get("devices", []) if "device_id" in d
        }

        resolved: dict[str, Device] = {}
        for seed_id, device in self._devices.items():
            # Check if this device already has a persisted dSUID
            if seed_id in persisted_devices:
                # Already persisted with this ID
                device.state = dict(persisted_devices[seed_id].get("state", {}))
                resolved[seed_id] = device
            else:
                # Resolve to dSUID (seed may not be 34 chars)
                dsuid = DsUid.for_device(seed_id) if len(seed_id) != 34 else seed_id
                device.device_id = dsuid
                if dsuid in persisted_devices:
                    device.state = dict(persisted_devices[dsuid].get("state", {}))
                resolved[dsuid] = device

        self._devices = resolved

    def _build_state_dict(self) -> dict[str, Any]:
        return {
            "vdc": {
                "vdc_id": self.vdc_id,
                "name": self.name,
                "version": self.version,
                "server_host": self.server_host,
                "server_port": self.server_port,
                "capabilities": [int(c) for c in self.capabilities],
            },
            "devices": [d.to_dict() for d in self._devices.values()],
        }

    def _schedule_save(self) -> None:
        data = self._build_state_dict()
        # Stage data synchronously so flush() can always find it,
        # then schedule the debounced async write.
        self._store.stage(data)
        asyncio.create_task(self._store.schedule_save(data))

    async def _connect_with_retry(self) -> None:
        while self._running:
            try:
                self._connection = VDCConnection(self)
                await self._connection.connect()
                self._reconnect_delay = _RECONNECT_BASE
                await self._start_background_tasks()
                return
            except VDCConnectionError:
                raise
            except Exception as e:
                logger.warning(
                    "Connection failed: %s — retrying in %.0fs", e, self._reconnect_delay
                )
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, _RECONNECT_MAX)

    async def _start_background_tasks(self) -> None:
        await self._connection.start_dispatch()
        self._heartbeat = HeartbeatTask(self)
        self._heartbeat.start()
        upgrade = self._session_options.get("upgrade")
        if upgrade == "websocket" and self.ws_path:
            self._ws = WebSocketClient(self)
            url = f"ws://{self.server_host}:{self.server_port}{self.ws_path}"
            self._ws.start(url)

    def _stop_background_tasks(self) -> None:
        if self._heartbeat:
            self._heartbeat.stop()
        if self._ws:
            self._ws.stop()

    async def _on_disconnect(self) -> None:
        """Called by VDCConnection when the TCP connection drops."""
        if not self._running:
            return
        self._stop_background_tasks()
        logger.warning("Disconnected from dSS — reconnecting in %.0fs", self._reconnect_delay)
        await asyncio.sleep(self._reconnect_delay)
        self._reconnect_delay = min(self._reconnect_delay * 2, _RECONNECT_MAX)
        await self._connect_with_retry()

    async def _send_device_event(
        self, device: Device, event_type: EventType, attribute: str, value: str
    ) -> None:
        if self._connection:
            await self._connection.send_device_event(
                device.device_id, int(event_type), attribute, value
            )
