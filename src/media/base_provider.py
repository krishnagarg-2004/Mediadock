"""Abstract base class for media detection providers."""

from abc import ABC, abstractmethod
from typing import Optional, Callable
from src.core.models import TrackInfo, PlaybackStatus

TrackCallback = Callable[[TrackInfo], None]
StatusCallback = Callable[[PlaybackStatus], None]
SessionAvailabilityCallback = Callable[[bool], None]


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
