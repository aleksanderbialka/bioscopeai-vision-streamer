import asyncio
import contextlib
import json
import os
from collections.abc import Callable
from typing import Any

from aiortc import (
    MediaStreamTrack,
    RTCConfiguration,
    RTCIceCandidate,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)
from fastapi import WebSocket
from loguru import logger

from bioscopeai_vision_streamer.app.schemas.signaling import (
    AnswerMessage,
    ByeMessage,
    IceCandidateMessage,
    OfferMessage,
    PingMessage,
    PongMessage,
)
from bioscopeai_vision_streamer.app.webrtc import rtc_manager


class WebRTCSession:
    """Manages a single WebRTC session with signaling and peer connection lifecycle."""

    ICE_GATHERING_TIMEOUT = 5.0
    MESSAGE_PREVIEW_LENGTH = 100
    MIN_CANDIDATE_PARTS = 8
    _ice_servers_cache: list[RTCIceServer] | None = None

    @staticmethod
    def build_ice_servers() -> list[RTCIceServer]:
        """Build ICE server configuration based on environment mode (cached)."""
        if WebRTCSession._ice_servers_cache is not None:
            return WebRTCSession._ice_servers_cache

        mode = os.getenv("WEBRTC_ICE_MODE", "prod")

        if mode == "dev":
            logger.info("Using DEV ICE configuration (TURN only, forced relay)")
            WebRTCSession._ice_servers_cache = [
                RTCIceServer(
                    urls=["turn:turn:3478?transport=tcp"],
                    username="dev",
                    credential="devpass",
                )
            ]
            return WebRTCSession._ice_servers_cache

        logger.info("Using PROD ICE configuration")
        servers = [RTCIceServer(urls=["stun:stun.l.google.com:19302"])]

        turn_urls = os.getenv("TURN_URLS", "").split(",")
        turn_user = os.getenv("TURN_USERNAME")
        turn_pass = os.getenv("TURN_CREDENTIAL")

        if turn_urls and turn_user and turn_pass:
            servers.append(
                RTCIceServer(urls=turn_urls, username=turn_user, credential=turn_pass)
            )
        else:
            logger.warning("No TURN server configured for production")

        WebRTCSession._ice_servers_cache = servers
        return servers

    def __init__(
        self,
        websocket: WebSocket,
        track_factory: Callable[[], MediaStreamTrack],
    ) -> None:
        self.websocket = websocket
        self.track_factory = track_factory
        self.pc: RTCPeerConnection | None = None
        self._closed = False
        self._cleanup_done = False
        self._ice_gathering_complete = asyncio.Event()
        self._message_handlers = {
            "offer": self._handle_offer,
            "ice-candidate": self._handle_ice_candidate,
            "bye": self._handle_bye,
            "ping": self._handle_ping,
        }

    async def run(self) -> None:
        """
        Main session loop: accepts WebSocket, creates peer connection,
        and processes messages.
        """
        await self.websocket.accept()
        logger.info("WebSocket accepted for WebRTC session")

        ice_servers = self.build_ice_servers()
        config = RTCConfiguration(iceServers=ice_servers)
        self.pc = RTCPeerConnection(configuration=config)
        rtc_manager.register(self.pc)  # type: ignore[attr-defined]

        self._attach_pc_event_handlers(self.pc)
        self.pc.addTrack(self.track_factory())

        try:
            while not self._closed:
                message_text = await self.websocket.receive_text()
                await self._handle_message(message_text)
        except (OSError, ValueError) as exc:
            logger.exception(f"Error in WebRTCSession.run: {exc}")
        finally:
            await self._cleanup()

    def _attach_pc_event_handlers(self, pc: RTCPeerConnection) -> None:
        """Attach diagnostic event handlers to peer connection."""

        @pc.on("iceconnectionstatechange")
        def on_iceconnectionstatechange() -> None:
            logger.info(
                f"ICE connection state: {pc.iceConnectionState} | "
                f"ICE gathering: {pc.iceGatheringState}"
            )
            if pc.iceConnectionState == "failed":
                logger.error(
                    "ICE connection failed, check STUN/TURN servers and network"
                )
            elif pc.iceConnectionState == "disconnected":
                logger.warning("ICE connection disconnected")
            elif pc.iceConnectionState == "connected":
                logger.info("ICE connection established")

        @pc.on("connectionstatechange")
        def on_connectionstatechange() -> None:
            logger.info(
                f"Connection state: {pc.connectionState} | Signaling: {pc.signalingState}"
            )
            if pc.connectionState == "failed":
                logger.error("Peer connection failed")
            elif pc.connectionState == "connected":
                logger.info("Peer connection established")

        @pc.on("icegatheringstatechange")
        def on_icegatheringstatechange() -> None:
            if pc.iceGatheringState == "complete":
                logger.info("ICE gathering complete")
                self._ice_gathering_complete.set()

        @pc.on("icecandidate")
        async def on_icecandidate(event) -> None:  # type: ignore[no-untyped-def]
            """Send ICE candidate to client via trickle ICE."""
            if event.candidate:
                candidate_msg = IceCandidateMessage(
                    candidate=event.candidate.candidate,
                    sdp_mid=event.candidate.sdpMid,
                    sdp_m_line_index=event.candidate.sdpMLineIndex,
                )
                await self._send_json(candidate_msg.model_dump())
                logger.info(
                    f"Sent ICE candidate to client | Type: {event.candidate.type} | "
                    f"IP: {event.candidate.ip}"
                )

    async def _handle_message(self, raw: str) -> None:
        """Dispatch incoming message based on type field."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON message: {raw}")
            return

        msg_type = data.get("type")
        handler = self._message_handlers.get(msg_type)

        if handler:
            await handler(data)
        else:
            logger.warning(f"Unsupported signaling message type: {msg_type}")

    async def _handle_offer(self, data: dict[str, Any]) -> None:
        """Process WebRTC offer and send answer back to client."""
        if not self.pc:
            logger.error("No PeerConnection in session when handling offer")
            return

        offer = OfferMessage(**data)

        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer.sdp, type=offer.type)
        )

        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        await self._wait_for_ice_gathering()

        answer_msg = AnswerMessage(type="answer", sdp=self.pc.localDescription.sdp)
        await self._send_json(answer_msg.model_dump())
        logger.info("WebRTC answer sent to client")

    async def _wait_for_ice_gathering(self, timeout: float | None = None) -> None:
        """Wait for ICE gathering to complete with timeout (supports no-trickle ICE)."""
        if not self.pc:
            return

        if self.pc.iceGatheringState == "complete":
            return

        timeout = timeout or self.ICE_GATHERING_TIMEOUT
        try:
            await asyncio.wait_for(self._ice_gathering_complete.wait(), timeout=timeout)
        except TimeoutError:
            logger.warning(
                f"ICE gathering timeout after {timeout}s (state: {self.pc.iceGatheringState})"
            )

    def _parse_ice_candidate(
        self, candidate_str: str, sdp_mid: str | None, sdp_m_line_index: int | None
    ) -> RTCIceCandidate | None:
        """Parse ICE candidate string into RTCIceCandidate object."""
        parts = candidate_str.split()
        if len(parts) < self.MIN_CANDIDATE_PARTS:
            logger.error(f"Invalid candidate format: {candidate_str}")
            return None

        try:
            return RTCIceCandidate(
                foundation=parts[0].split(":")[1],
                component=int(parts[1]),
                protocol=parts[2],
                priority=int(parts[3]),
                ip=parts[4],
                port=int(parts[5]),
                type=parts[7],
                sdpMid=sdp_mid,
                sdpMLineIndex=sdp_m_line_index,
            )
        except (ValueError, IndexError) as e:
            logger.error(
                f"Failed to parse ICE candidate: {e} | candidate: {candidate_str}"
            )
            return None

    async def _handle_ice_candidate(self, data: dict[str, Any]) -> None:
        """Process ICE candidate from client."""
        if not self.pc:
            logger.error("No PeerConnection when handling ICE candidate")
            return

        if self.pc.iceConnectionState in {"closed", "failed", "disconnected"}:
            logger.warning(
                f"Ignoring ICE candidate, PeerConnection is {self.pc.iceConnectionState}"
            )
            return

        ice_msg = IceCandidateMessage(**data)

        if ice_msg.candidate is None:
            logger.debug("Received end-of-candidates signal")
            try:
                await self.pc.addIceCandidate(None)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Failed to process end-of-candidates: {e}")
            return

        sdp_mid = ice_msg.sdp_mid or data.get("sdpMid") or data.get("sdp_mid")
        sdp_m_line_index = (
            ice_msg.sdp_m_line_index
            or data.get("sdpMLineIndex")
            or data.get("sdp_m_line_index")
        )

        candidate = self._parse_ice_candidate(
            ice_msg.candidate, sdp_mid, sdp_m_line_index
        )
        if not candidate:
            return

        try:
            await self.pc.addIceCandidate(candidate)
            logger.info(
                f"Added ICE candidate from client | Type: {candidate.type} | IP: {candidate.ip} | "
                f"Protocol: {candidate.protocol} | Port: {candidate.port}"
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to add ICE candidate: {e}")

    async def _handle_bye(self, data: dict[str, Any]) -> None:
        """Close session when client sends bye message."""
        _ = ByeMessage(**data)
        logger.info("Received 'bye' from client, closing session")
        self._closed = True

    async def _handle_ping(self, data: dict[str, Any]) -> None:
        """Respond to ping with pong (heartbeat mechanism)."""
        _ = PingMessage(**data)
        pong = PongMessage()
        await self._send_json(pong.model_dump())

    async def _send_json(self, payload: dict[str, Any]) -> None:
        """Send JSON message over WebSocket."""
        try:
            await self.websocket.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to send message over WebSocket: {exc}")
            self._closed = True

    async def _cleanup(self) -> None:
        """Clean up peer connection and WebSocket resources."""
        if self._cleanup_done:
            return
        self._cleanup_done = True

        logger.info("Cleaning up WebRTC session")

        if self.pc:
            if self.pc.connectionState not in {"closed", "failed"}:
                try:
                    await self.pc.close()
                except OSError as e:
                    logger.warning(f"Error closing PeerConnection: {e}")

            try:
                rtc_manager.unregister(self.pc)  # type: ignore[attr-defined]
            except OSError as e:
                logger.error(f"Error during unregister: {e}")

        with contextlib.suppress(OSError):
            await self.websocket.close()
