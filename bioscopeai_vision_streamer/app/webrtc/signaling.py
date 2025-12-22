from aiortc.mediastreams import MediaStreamTrack
from fastapi import WebSocket

from .session import WebRTCSession
from .tracks import FakeVideoStreamTrack


class SignalingServer:
    """Signaling server for WebRTC connections."""

    @staticmethod
    def _track_factory() -> MediaStreamTrack:
        # For test cases, we use the fake video track.
        return FakeVideoStreamTrack()

    async def handle_websocket(self, websocket: WebSocket) -> None:
        """Handle a WebSocket connection for WebRTC signaling."""
        session = WebRTCSession(
            websocket=websocket,
            track_factory=self._track_factory,
        )
        await session.run()


signaling_server = SignalingServer()
