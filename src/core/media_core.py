"""MediaCore event coordinator bridging media providers to PySide6 Qt signals."""

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal

from src.core.models import TrackInfo, PlaybackStatus
from src.media.base_provider import BaseMediaProvider

logger = logging.getLogger(__name__)


class MediaCore(QObject):
    """Central event coordinator bridging framework-independent media providers to Qt signals."""

    track_changed = Signal(TrackInfo)
    playback_status_changed = Signal(PlaybackStatus)
    session_availability_changed = Signal(bool)

    def __init__(
        self,
        provider: BaseMediaProvider,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._provider = provider
        self._wire_provider_callbacks()

    def _wire_provider_callbacks(self) -> None:
        """Register internal callback handlers on the underlying provider."""
        self._provider.set_on_track_changed(self._on_provider_track_changed)
        self._provider.set_on_status_changed(self._on_provider_status_changed)
        self._provider.set_on_session_availability_changed(
            self._on_provider_session_availability_changed
        )

    # --- Public API & Lifecycle ---

    def start(self) -> None:
        """Start listening for media events on the underlying provider."""
        try:
            self._provider.start_listening()
        except Exception as e:
            logger.error("Failed to start media provider: %s", e)

    def stop(self) -> None:
        """Stop listening for media events and clean up provider resources."""
        try:
            self._provider.stop_listening()
        except Exception as e:
            logger.error("Failed to stop media provider cleanly: %s", e)

    def get_current_track(self) -> TrackInfo:
        """Return the current TrackInfo object from the provider."""
        return self._provider.get_current_track()

    def get_playback_status(self) -> PlaybackStatus:
        """Return the current PlaybackStatus enum from the provider."""
        return self._provider.get_playback_status()

    def is_session_available(self) -> bool:
        """Return True if an active media session exists on the provider."""
        if hasattr(self._provider, "is_session_available"):
            return self._provider.is_session_available()
        return self.get_playback_status() != PlaybackStatus.CLOSED

    # --- Transport Controls ---

    def play(self) -> bool:
        """Request active media player to resume playback. Returns True if command was scheduled."""
        try:
            return self._provider.play()
        except Exception as e:
            logger.error("Error delegating play command: %s", e)
            return False

    def pause(self) -> bool:
        """Request active media player to pause playback. Returns True if command was scheduled."""
        try:
            return self._provider.pause()
        except Exception as e:
            logger.error("Error delegating pause command: %s", e)
            return False

    def toggle_play_pause(self) -> bool:
        """Request active media player to toggle play/pause state. Returns True if command was scheduled."""
        try:
            return self._provider.toggle_play_pause()
        except Exception as e:
            logger.error("Error delegating toggle_play_pause command: %s", e)
            return False

    def next_track(self) -> bool:
        """Request active media player to skip to the next track. Returns True if command was scheduled."""
        try:
            return self._provider.next_track()
        except Exception as e:
            logger.error("Error delegating next_track command: %s", e)
            return False

    def previous_track(self) -> bool:
        """Request active media player to skip to the previous track. Returns True if command was scheduled."""
        try:
            return self._provider.previous_track()
        except Exception as e:
            logger.error("Error delegating previous_track command: %s", e)
            return False

    def seek_to_position(self, position_ms: int) -> bool:
        """Request active media player to seek to position_ms. Returns True if command was scheduled."""
        try:
            return self._provider.seek_to_position(position_ms)
        except Exception as e:
            logger.error("Error delegating seek_to_position command: %s", e)
            return False


    # --- Internal Callback Handlers (Cross-Thread Signal Emitters) ---

    def _on_provider_track_changed(self, track: TrackInfo) -> None:
        """Handler for provider track change callbacks. Emits Qt signal safely."""
        try:
            self.track_changed.emit(track)
        except Exception as e:
            logger.error("Error emitting track_changed signal: %s", e)

    def _on_provider_status_changed(self, status: PlaybackStatus) -> None:
        """Handler for provider playback status callbacks. Emits Qt signal safely."""
        try:
            self.playback_status_changed.emit(status)
        except Exception as e:
            logger.error("Error emitting playback_status_changed signal: %s", e)

    def _on_provider_session_availability_changed(self, available: bool) -> None:
        """Handler for provider session availability callbacks. Emits Qt signal safely."""
        try:
            self.session_availability_changed.emit(available)
        except Exception as e:
            logger.error("Error emitting session_availability_changed signal: %s", e)
