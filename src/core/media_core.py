"""MediaCore event coordinator bridging media providers to PySide6 Qt signals."""

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal

from src.core.models import TrackInfo, PlaybackStatus, VolumeState
from src.media.base_provider import BaseMediaProvider
from src.media.volume_provider import BaseVolumeProvider, WindowsVolumeProvider
from src.media.audio_capture import BaseAudioCapture, WASAPILoopbackCapture, AudioFrame
from src.media.audio_analyzer import AudioAnalyzer

logger = logging.getLogger(__name__)


class MediaCore(QObject):
    """Central event coordinator bridging framework-independent media providers to Qt signals."""

    track_changed = Signal(TrackInfo)
    playback_status_changed = Signal(PlaybackStatus)
    session_availability_changed = Signal(bool)
    sessions_changed = Signal(list)
    volume_changed = Signal(VolumeState)
    audio_visualizer_updated = Signal(list)

    def __init__(
        self,
        provider: BaseMediaProvider,
        volume_provider: Optional[BaseVolumeProvider] = None,
        audio_capture: Optional[BaseAudioCapture] = None,
        analyzer: Optional[AudioAnalyzer] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._provider = provider
        self._volume_provider = (
            volume_provider if volume_provider is not None else WindowsVolumeProvider()
        )
        self._audio_capture = (
            audio_capture if audio_capture is not None else WASAPILoopbackCapture()
        )
        self._analyzer = (
            analyzer if analyzer is not None else AudioAnalyzer(bar_count=5)
        )
        self._wire_provider_callbacks()

    def _wire_provider_callbacks(self) -> None:
        """Register internal callback handlers on underlying media, volume, and audio providers."""
        self._provider.set_on_track_changed(self._on_provider_track_changed)
        self._provider.set_on_status_changed(self._on_provider_status_changed)
        self._provider.set_on_session_availability_changed(
            self._on_provider_session_availability_changed
        )
        self._provider.set_on_sessions_changed(self._on_provider_sessions_changed)
        self._volume_provider.set_on_volume_changed(self._on_provider_volume_changed)
        if self._audio_capture:
            self._audio_capture.set_on_audio_frame(self._on_provider_audio_frame)

    # --- Public API & Lifecycle ---

    def start(self) -> None:
        """Start listening for media, volume, and audio events."""
        try:
            self._provider.start_listening()
            self._volume_provider.start_listening()
            if self._audio_capture:
                self._audio_capture.start()
        except Exception as e:
            logger.error("Failed to start media provider: %s", e)

    def stop(self) -> None:
        """Stop listening for media, volume, and audio events and clean up resources."""
        try:
            self._provider.stop_listening()
            self._volume_provider.stop_listening()
            if self._audio_capture:
                self._audio_capture.stop()
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

    def get_available_sessions(self) -> list:
        """Return list of active MediaSessionInfo objects from provider."""
        try:
            return self._provider.get_available_sessions()
        except Exception as e:
            logger.error("Error getting available sessions: %s", e)
            return []

    def get_active_session_info(self) -> Optional[MediaSessionInfo]:
        """Return currently active MediaSessionInfo or None."""
        try:
            sessions = self.get_available_sessions()
            return sessions[0] if sessions else None
        except Exception as e:
            logger.error("Error getting active session info: %s", e)
            return None

    def select_session(self, session_id: Optional[str]) -> bool:
        """Select a specific media session by ID. Pass None for automatic OS selection."""
        try:
            return self._provider.select_session(session_id)
        except Exception as e:
            logger.error("Error selecting session '%s': %s", session_id, e)
            return False

    def get_selected_session_id(self) -> Optional[str]:
        """Return ID of currently selected session, or None if automatic OS selection."""
        try:
            return self._provider.get_selected_session_id()
        except Exception as e:
            logger.error("Error getting selected session ID: %s", e)
            return None

    # --- Master Volume Controls ---

    def get_volume_state(self) -> VolumeState:
        """Return current VolumeState from volume provider."""
        try:
            return self._volume_provider.get_volume_state()
        except Exception as e:
            logger.error("Error getting volume state: %s", e)
            return VolumeState.unsupported()

    def set_volume(self, percent: int) -> bool:
        """Set master audio volume percentage (0–100)."""
        try:
            return self._volume_provider.set_volume(percent)
        except Exception as e:
            logger.error("Error setting volume percentage (%d%%): %s", percent, e)
            return False

    def set_mute(self, muted: bool) -> bool:
        """Set master audio mute state."""
        try:
            return self._volume_provider.set_mute(muted)
        except Exception as e:
            logger.error("Error setting mute state (%s): %s", muted, e)
            return False

    def toggle_mute(self) -> bool:
        """Toggle master audio mute state."""
        try:
            return self._volume_provider.toggle_mute()
        except Exception as e:
            logger.error("Error toggling mute state: %s", e)
            return False

    def is_volume_supported(self) -> bool:
        """Return True if system master volume control is supported."""
        return self.get_volume_state().is_supported

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

    def _on_provider_sessions_changed(self, sessions: list) -> None:
        """Handler for provider sessions change callbacks. Emits Qt signal safely."""
        try:
            self.sessions_changed.emit(sessions)
        except Exception as e:
            logger.error("Error emitting sessions_changed signal: %s", e)

    def _on_provider_volume_changed(self, state: VolumeState) -> None:
        """Handler for provider volume change callbacks. Emits Qt signal safely."""
        try:
            self.volume_changed.emit(state)
        except Exception as e:
            logger.error("Error emitting volume_changed signal: %s", e)

    def _on_provider_audio_frame(self, frame: AudioFrame) -> None:
        """Handler for provider audio frame callbacks. Analyzes frame and emits Qt signal safely."""
        try:
            if self._analyzer:
                bars = self._analyzer.process_frame(frame)
                self.audio_visualizer_updated.emit(bars)
        except Exception as e:
            logger.error("Error emitting audio_visualizer_updated signal: %s", e)
