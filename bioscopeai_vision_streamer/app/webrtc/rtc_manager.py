import asyncio

from aiortc import RTCPeerConnection
from loguru import logger


class RTCManager:
    """Manager for active RTCPeerConnections."""

    def __init__(self) -> None:
        self._pcs: set[RTCPeerConnection] = set()

    @property
    def pcs(self) -> set[RTCPeerConnection]:
        return self._pcs

    def register(self, pc: RTCPeerConnection) -> None:
        self._pcs.add(pc)
        logger.info("Registered PeerConnection. Active connections: %s", len(self._pcs))

    async def unregister(self, pc: RTCPeerConnection) -> None:
        if pc in self._pcs:
            await pc.close()
            self._pcs.discard(pc)
            logger.info(
                "Unregistered PeerConnection. Active connections: %s",
                len(self._pcs),
            )

    async def close_all(self) -> None:
        logger.info("Closing all PeerConnections (%s)", len(self._pcs))
        coros = [pc.close() for pc in self._pcs]
        await asyncio.gather(*coros, return_exceptions=True)
        self._pcs.clear()


rtc_manager = RTCManager()
