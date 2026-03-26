from __future__ import annotations

import asyncio
import logging
import struct
import time
from typing import Any, TYPE_CHECKING

from pyDSvDCAPIv2.exceptions import VDCConnectionError
from pyDSvDCAPIv2.proto import (
    service_announcement_pb2,
    device_announcement_pb2,
    state_pb2,
    command_pb2,
    scene_pb2,
    event_pb2,
    firmware_pb2,
    heartbeat_pb2,
    error_pb2,
)

if TYPE_CHECKING:
    from pyDSvDCAPIv2.vdc import VDC

logger = logging.getLogger(__name__)

_RECONNECT_BASE = 2.0   # seconds
_RECONNECT_MAX = 60.0   # seconds


def frame_message(payload: bytes) -> bytes:
    """Prepend 4-byte big-endian length prefix to payload."""
    return struct.pack(">I", len(payload)) + payload


async def read_message(reader: asyncio.StreamReader) -> bytes:
    """Read one length-prefixed message from stream. Returns raw protobuf bytes."""
    header = await reader.readexactly(4)
    length = struct.unpack(">I", header)[0]
    return await reader.readexactly(length)


class VDCConnection:
    """Manages TCP connection to dSS, framing, handshake, dispatch, and reconnect."""

    def __init__(self, vdc: VDC) -> None:
        self._vdc = vdc
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._running = False
        self._dispatch_task: asyncio.Task | None = None

    async def connect(self) -> None:
        """Connect to dSS, handshake, and register all devices."""
        self._reader, self._writer = await asyncio.open_connection(
            self._vdc.server_host, self._vdc.server_port
        )
        logger.info("Connected to dSS at %s:%s", self._vdc.server_host, self._vdc.server_port)
        await self._handshake()
        await self._register_devices()

    async def _handshake(self) -> None:
        """Send ServiceAnnouncement, receive and validate ServiceAcknowledgement."""
        from pyDSvDCAPIv2.constants import ServiceConfig
        ann = service_announcement_pb2.ServiceAnnouncement()
        ann.vdcId = self._vdc.vdc_id
        ann.type = self._vdc.name
        ann.name = self._vdc.name
        ann.version = self._vdc.version
        for cap in self._vdc.capabilities:
            ann.caps.append(int(cap))
        if self._vdc.ws_path:
            ann.config[ServiceConfig.PROTO] = "protobuf"
            ann.config[ServiceConfig.WS] = "1"
            ann.config[ServiceConfig.WS_PATH] = self._vdc.ws_path

        await self._send(ann.SerializeToString())

        raw = await read_message(self._reader)
        ack = service_announcement_pb2.ServiceAcknowledgement()
        ack.ParseFromString(raw)

        if ack.error.code != 0:
            raise VDCConnectionError(
                f"dSS rejected handshake: [{ack.error.code}] {ack.error.message}"
            )
        self._vdc._session_options = dict(ack.options)
        logger.info("Handshake OK, protocol=%s", ack.protocolVersion)

    async def _register_devices(self) -> None:
        """Send DeviceAnnouncement for each registered device."""
        for device in self._vdc._devices.values():
            pb = self._device_to_proto(device)
            await self._send(pb.SerializeToString())
            logger.debug("Announced device %s (%s)", device.device_id, device.name)

    def _device_to_proto(self, device: Any) -> device_announcement_pb2.DeviceAnnouncement:
        pb = device_announcement_pb2.DeviceAnnouncement()
        pb.deviceId = device.device_id
        pb.type = int(device.type)
        # 'class' is a Python reserved keyword; use setattr to set the proto field
        setattr(pb, "class", int(device.class_))
        pb.name = device.name
        pb.status = int(device.status)
        for k, v in device.config.items():
            pb.config[k] = v
        for k, v in device.metadata.items():
            pb.metadata[k] = v
        for k, v in device.attributes.items():
            pb.attributes[k] = v
        # capabilities is repeated scalar enum — append integer values directly
        for cap in device.capabilities:
            pb.capabilities.append(int(cap.type))
        return pb

    async def _send(self, payload: bytes) -> None:
        """Send length-prefixed protobuf bytes to dSS."""
        self._writer.write(frame_message(payload))
        await self._writer.drain()

    async def send_raw(self, payload: bytes) -> None:
        """Public send interface used by VDC."""
        await self._send(payload)

    async def start_dispatch(self) -> None:
        """Start the background message dispatch loop."""
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())

    async def _dispatch_loop(self) -> None:
        """Read incoming messages from dSS and dispatch to device callbacks."""
        while self._running:
            try:
                raw = await read_message(self._reader)
                await self._dispatch(raw)
            except asyncio.IncompleteReadError:
                logger.warning("dSS connection closed")
                break
            except Exception as e:
                logger.error("Dispatch error: %s", e)
                break
        if self._running:
            await self._vdc._on_disconnect()

    async def _dispatch(self, raw: bytes) -> None:
        """Try to parse raw bytes as each known incoming message type and dispatch."""
        # Try SetStateRequest
        try:
            msg = state_pb2.SetStateRequest()
            msg.ParseFromString(raw)
            if msg.deviceId and msg.attribute:
                device = self._vdc._devices.get(msg.deviceId)
                if device and device.on_set_state:
                    resp = state_pb2.SetStateResponse()
                    resp.deviceId = msg.deviceId
                    try:
                        await device.on_set_state(msg.attribute, msg.value)
                        resp.status = 0  # CommandStatus.OK
                    except Exception as e:
                        logger.error("on_set_state error: %s", e)
                        resp.status = 1  # CommandStatus.FAILED
                    await self._send(resp.SerializeToString())
                return
        except Exception:
            pass

        # Try StateRequest (GetDeviceState)
        try:
            msg = state_pb2.StateRequest()
            msg.ParseFromString(raw)
            if msg.deviceId:
                device = self._vdc._devices.get(msg.deviceId)
                resp = state_pb2.StateResponse()
                resp.deviceId = msg.deviceId
                if device and device.on_get_state:
                    try:
                        val = await device.on_get_state(msg.attribute)
                        resp.values[msg.attribute] = val
                    except Exception as e:
                        logger.error("on_get_state error: %s", e)
                await self._send(resp.SerializeToString())
                return
        except Exception:
            pass

        # Try Command
        try:
            msg = command_pb2.Command()
            msg.ParseFromString(raw)
            if msg.deviceId and msg.command:
                device = self._vdc._devices.get(msg.deviceId)
                result = command_pb2.CommandResult()
                result.deviceId = msg.deviceId
                if device and device.on_command:
                    try:
                        out = await device.on_command(msg.command, dict(msg.params))
                        result.status = 0  # CMD_OK
                        for k, v in (out or {}).items():
                            result.result[k] = str(v)
                    except Exception as e:
                        logger.error("on_command error: %s", e)
                        result.status = 1  # CMD_FAILED
                await self._send(result.SerializeToString())
                return
        except Exception:
            pass

        # Try SceneActivation
        try:
            msg = scene_pb2.SceneActivation()
            msg.ParseFromString(raw)
            if msg.sceneId:
                if self._vdc.on_scene_event:
                    try:
                        await self._vdc.on_scene_event(msg)
                    except Exception as e:
                        logger.error("on_scene_event error: %s", e)
                return
        except Exception:
            pass

        # Try Heartbeat — echo back
        try:
            msg = heartbeat_pb2.Heartbeat()
            msg.ParseFromString(raw)
            if msg.vdcId:
                resp = heartbeat_pb2.Heartbeat()
                resp.vdcId = self._vdc.vdc_id
                resp.timestamp = int(time.time() * 1000)
                await self._send(resp.SerializeToString())
                return
        except Exception:
            pass

        logger.debug("Received unrecognized message (%d bytes), ignoring", len(raw))

    async def send_device_removal(self, device_id: str) -> None:
        pb = device_announcement_pb2.DeviceRemoval()
        pb.deviceId = device_id
        await self._send(pb.SerializeToString())

    async def send_device_event(
        self, device_id: str, event_type: int, attribute: str, value: str
    ) -> None:
        pb = event_pb2.DeviceEvent()
        pb.deviceId = device_id
        pb.type = event_type
        pb.attribute = attribute
        pb.value = value
        pb.timestamp = int(time.time() * 1000)
        await self._send(pb.SerializeToString())

    async def send_heartbeat(self, vdc_id: str, metrics: dict[str, str]) -> None:
        pb = heartbeat_pb2.Heartbeat()
        pb.vdcId = vdc_id
        pb.timestamp = int(time.time() * 1000)
        for k, v in metrics.items():
            pb.metrics[k] = v
        await self._send(pb.SerializeToString())

    async def close(self) -> None:
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
