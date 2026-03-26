# pyDSvDCAPIv2/ws_client.py
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyDSvDCAPIv2.vdc import VDC

logger = logging.getLogger(__name__)

_RECONNECT_DELAY = 5.0


class WebSocketClient:
    """Optional WebSocket event channel to dSS.

    Activated when ServiceAcknowledgement.options['upgrade'] == 'websocket'
    and the VDC has ws_path configured.
    """

    def __init__(self, vdc: VDC) -> None:
        self._vdc = vdc
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self, url: str) -> None:
        self._url = url
        self._running = True
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        try:
            import websockets
        except ImportError:
            logger.error("websockets library not installed; WebSocket channel disabled")
            return

        while self._running:
            try:
                logger.info("WebSocket connecting to %s", self._url)
                async with websockets.connect(self._url) as ws:
                    logger.info("WebSocket connected")
                    async for message in ws:
                        if isinstance(message, bytes):
                            await self._vdc._connection._dispatch(message)
                        else:
                            logger.debug("Non-bytes WS message ignored")
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    logger.warning("WebSocket error: %s — reconnecting in %.0fs", e, _RECONNECT_DELAY)
                    await asyncio.sleep(_RECONNECT_DELAY)
