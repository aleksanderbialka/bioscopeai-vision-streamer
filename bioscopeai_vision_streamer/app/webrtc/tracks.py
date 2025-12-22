import asyncio
import time

import cv2
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame


class FakeVideoStreamTrack(VideoStreamTrack):
    """Fake video track generating synthetic video frames."""

    kind = "video"

    def __init__(self, width: int = 640, height: int = 480, fps: int = 30) -> None:
        super().__init__()
        self.width = width
        self.height = height
        self.fps = fps
        self._start_time = time.time()

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()

        t = time.time() - self._start_time
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        cx = int((self.width / 2) + (self.width / 4) * np.sin(t))
        cy = int((self.height / 2) + (self.height / 4) * np.cos(t))
        radius = 40

        cv2.circle(frame, (cx, cy), radius, (0, 255, 0), thickness=-1)
        cv2.putText(
            frame,
            "BIOSCOPEAI WEBRTC",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        await asyncio.sleep(1 / self.fps)
        return video_frame
