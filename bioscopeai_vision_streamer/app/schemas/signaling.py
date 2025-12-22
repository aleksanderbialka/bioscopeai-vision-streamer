from pydantic import BaseModel


class OfferMessage(BaseModel):
    """WebRTC offer from client with SDP."""

    type: str = "offer"
    sdp: str


class AnswerMessage(BaseModel):
    """WebRTC answer from server to client with SDP."""

    type: str = "answer"
    sdp: str


class IceCandidateMessage(BaseModel):
    """ICE candidate for trickle ICE (candidate=None signals end-of-candidates)."""

    type: str = "ice-candidate"
    candidate: str | None = None
    sdp_mid: str | None = None
    sdp_m_line_index: int | None = None


class ByeMessage(BaseModel):
    """Client session termination signal."""

    type: str = "bye"


class PingMessage(BaseModel):
    """Heartbeat ping from client."""

    type: str = "ping"


class PongMessage(BaseModel):
    """Heartbeat pong response from server."""

    type: str = "pong"
