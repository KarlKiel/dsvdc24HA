# pyDSvDCAPIv2/heartbeat.py
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyDSvDCAPIv2.vdc import VDC

logger = logging.getLogger(__name__)


class HeartbeatTask:
    """Sends periodic Heartbeat messages to dSS."""

    def __init__(self, vdc: "VDC") -> None:
        self._vdc = vdc
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._vdc.heartbeat_interval)
                if self._vdc._connection:
                    await self._vdc._connection.send_heartbeat(
                        self._vdc.vdc_id,
                        self._vdc.heartbeat_metrics,
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Heartbeat error: %s", e)
