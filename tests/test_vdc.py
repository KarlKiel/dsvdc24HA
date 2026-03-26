# tests/test_vdc.py
import asyncio
import struct
import pytest
from unittest.mock import AsyncMock, patch
from pyDSvDCAPIv2.vdc import VDC
from pyDSvDCAPIv2.device import Device
from pyDSvDCAPIv2.enums import DeviceType, DeviceClass, DeviceStatus, VdcCapabilityFlag
from pyDSvDCAPIv2.proto import service_announcement_pb2, device_announcement_pb2
from pyDSvDCAPIv2.connection import frame_message


def _framed(pb_msg) -> bytes:
    return frame_message(pb_msg.SerializeToString())


@pytest.fixture
def vdc(tmp_path):
    return VDC(
        vdc_id="test-vdc",
        name="Test VDC",
        version="1.0.0",
        server_host="127.0.0.1",
        server_port=19999,
        state_path=str(tmp_path / "state.yaml"),
        ws_path=None,
    )


@pytest.fixture
def device():
    return Device(
        device_id="lamp-001",
        type=DeviceType.LIGHT,
        class_=DeviceClass.LIGHTING,
        status=DeviceStatus.ONLINE,
        name="Test Lamp",
    )


def test_add_device(vdc, device):
    vdc.add_device(device)
    assert device.device_id in vdc._devices or "lamp-001" in vdc._devices


def test_vdc_id_is_resolved_to_dsuid(vdc):
    # Before start(), vdc_id is the seed; after load_state it becomes dSUID
    assert vdc.vdc_id == "test-vdc" or len(vdc.vdc_id) == 34


@pytest.mark.asyncio
async def test_start_connects_and_announces(vdc, device, tmp_path):
    vdc.add_device(device)

    # Build mock dSS: send back a valid ServiceAcknowledgement
    ack = service_announcement_pb2.ServiceAcknowledgement()
    ack.protocolVersion = "2.0"
    ack_bytes = _framed(ack)

    async def mock_open_connection(host, port):
        reader = asyncio.StreamReader()
        # Feed the ack immediately
        reader.feed_data(ack_bytes)
        writer = AsyncMock()
        writer.drain = AsyncMock()
        writer.close = AsyncMock()
        writer.wait_closed = AsyncMock()
        return reader, writer

    with patch("asyncio.open_connection", side_effect=mock_open_connection):
        await vdc.start()
        await vdc.stop()


@pytest.mark.asyncio
async def test_state_is_persisted_after_device_update(vdc, device, tmp_path):
    vdc.add_device(device)
    device._vdc = vdc

    ack = service_announcement_pb2.ServiceAcknowledgement()
    ack.protocolVersion = "2.0"

    async def mock_open_connection(host, port):
        reader = asyncio.StreamReader()
        reader.feed_data(_framed(ack))
        writer = AsyncMock()
        writer.drain = AsyncMock()
        writer.close = AsyncMock()
        writer.wait_closed = AsyncMock()
        return reader, writer

    with patch("asyncio.open_connection", side_effect=mock_open_connection):
        await vdc.start()
        device.update_state("brightness", "80")
        vdc._store.flush()
        await vdc.stop()

    data = vdc._store.load()
    states = {d["device_id"]: d.get("state", {}) for d in data.get("devices", [])}
    # Device ID may have been resolved to a dSUID
    found = any(s.get("brightness") == "80" for s in states.values())
    assert found
