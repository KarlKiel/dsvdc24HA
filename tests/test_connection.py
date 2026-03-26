import asyncio
import struct
import pytest
from pyDSvDCAPIv2.connection import frame_message, read_message


async def _mock_reader(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


def test_frame_message_prepends_4_byte_length():
    payload = b"hello"
    framed = frame_message(payload)
    assert len(framed) == 4 + len(payload)
    length = struct.unpack(">I", framed[:4])[0]
    assert length == len(payload)
    assert framed[4:] == payload


def test_frame_message_empty_payload():
    framed = frame_message(b"")
    assert framed == b"\x00\x00\x00\x00"


@pytest.mark.asyncio
async def test_read_message_extracts_payload():
    payload = b"test-payload"
    framed = frame_message(payload)
    reader = await _mock_reader(framed)
    result = await read_message(reader)
    assert result == payload


@pytest.mark.asyncio
async def test_read_message_handles_multiple_messages():
    payload1 = b"first"
    payload2 = b"second"
    reader = await _mock_reader(frame_message(payload1) + frame_message(payload2))
    assert await read_message(reader) == payload1
    assert await read_message(reader) == payload2
