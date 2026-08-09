"""Domain data models for media metadata and playback status.

These models are framework-agnostic and use standard Python types only.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PlaybackStatus(Enum):
    """Enumeration of media playback statuses."""

    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TrackInfo:
    """Immutable metadata representation of a media track."""

    title: str
    artist: str
    album: str = ""
    album_art_bytes: Optional[bytes] = None
    app_id: str = "Unknown"
    duration_ms: int = 0
    position_ms: int = 0

    @classmethod
    def empty(cls) -> "TrackInfo":
        """Return a fallback TrackInfo object representing no active media."""
        return cls(
            title="No Media Playing",
            artist="Unknown Artist",
            album="",
            album_art_bytes=None,
            app_id="",
            duration_ms=0,
            position_ms=0,
        )


@dataclass(frozen=True)
class MediaSessionInfo:
    """Immutable representation of an active media session."""

    session_id: str
    app_id: str
    display_name: str
    is_current: bool = False
    is_selected: bool = False
