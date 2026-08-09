"""Abstract base class for media detection providers."""

from abc import ABC, abstractmethod
from typing import Optional, Callable, List
from src.core.models import TrackInfo, PlaybackStatus, MediaSessionInfo

TrackCallback = Callable[[TrackInfo], None]
StatusCallback = Callable[[PlaybackStatus], None]
SessionAvailabilityCallback = Callable[[bool], None]
SessionsCallback = Callable[[List[MediaSessionInfo]], None]


class BaseMediaProvider(ABC):
    """Abstract interface defining the contract for all media detection providers."""

    @abstractmethod
    def get_current_track(self) -> TrackInfo:
        """Return the currently detected track or a fallback empty TrackInfo."""
        pass

    @abstractmethod
    def get_playback_status(self) -> PlaybackStatus:
        """Return the current playback status enum value."""
        pass

    @abstractmethod
    def start_listening(self) -> None:
        """Initialize provider connections and start monitoring for media events."""
        pass

    @abstractmethod
    def stop_listening(self) -> None:
        """Unregister event listeners and clean up provider resources."""
        pass

    @abstractmethod
    def set_on_track_changed(self, callback: Optional[TrackCallback]) -> None:
        """Register callback for track change events."""
        pass

    @abstractmethod
    def set_on_status_changed(self, callback: Optional[StatusCallback]) -> None:
        """Register callback for playback status change events."""
        pass

    @abstractmethod
    def set_on_session_availability_changed(
        self, callback: Optional[SessionAvailabilityCallback]
    ) -> None:
        """Register callback for session availability change events."""
        pass

    def set_on_sessions_changed(
        self, callback: Optional[SessionsCallback]
    ) -> None:
        """Register callback for session list change events."""
        pass

    def get_available_sessions(self) -> List[MediaSessionInfo]:
        """Return list of active media sessions."""
        return []

    def select_session(self, session_id: Optional[str]) -> bool:
        """Select a specific media session by ID. Pass None for automatic OS selection."""
        return False

    def get_selected_session_id(self) -> Optional[str]:
        """Return ID of currently selected session, or None if automatic OS selection."""
        return None


    # --- Transport Control Interface ---

    @abstractmethod
    def play(self) -> bool:
        """Request active media player to resume playback. Returns True if command was dispatched."""
        pass

    @abstractmethod
    def pause(self) -> bool:
        """Request active media player to pause playback. Returns True if command was dispatched."""
        pass

    @abstractmethod
    def toggle_play_pause(self) -> bool:
        """Toggle between play and pause state. Returns True if command was dispatched."""
        pass

    @abstractmethod
    def next_track(self) -> bool:
        """Request active media player to skip to the next track. Returns True if command was dispatched."""
        pass

    @abstractmethod
    def previous_track(self) -> bool:
        """Request active media player to skip to the previous track. Returns True if command was dispatched."""
        pass

    @abstractmethod
    def seek_to_position(self, position_ms: int) -> bool:
        """Request active media player to seek to a specific position in milliseconds. Returns True if command was dispatched."""
        pass
