"""Windows GSMTC (Global System Media Transport Controls) media provider implementation."""

import asyncio
import logging
import threading
from typing import Optional, Callable, Set

try:
    import winrt.windows.media.control as media_control
    import winrt.windows.storage.streams as streams
    WINRT_AVAILABLE = True
except ImportError:  # pragma: no cover
    WINRT_AVAILABLE = False
    media_control = None  # type: ignore[assignment]
    streams = None  # type: ignore[assignment]

from src.core.models import TrackInfo, PlaybackStatus
from src.media.base_provider import BaseMediaProvider

logger = logging.getLogger(__name__)

TrackCallback = Callable[[TrackInfo], None]
StatusCallback = Callable[[PlaybackStatus], None]
SessionAvailabilityCallback = Callable[[bool], None]


class GSMTCProvider(BaseMediaProvider):
    """Media provider for Windows GSMTC using PyWinRT 3.x."""

    def __init__(
        self,
        on_track_changed: Optional[TrackCallback] = None,
        on_status_changed: Optional[StatusCallback] = None,
        on_session_availability_changed: Optional[SessionAvailabilityCallback] = None,
    ) -> None:
        self._on_track_changed_cb = on_track_changed
        self._on_status_changed_cb = on_status_changed
        self._on_session_availability_changed_cb = on_session_availability_changed

        self._lock = threading.RLock()
        self._is_listening = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_ready = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._pending_tasks: Set[asyncio.Task] = set()

        self._manager = None
        self._current_session = None

        self._manager_token = None
        self._sessions_token = None
        self._props_token = None
        self._playback_token = None

        self._current_track: TrackInfo = TrackInfo.empty()
        self._playback_status: PlaybackStatus = PlaybackStatus.CLOSED
        self._is_session_available: bool = False

    # --- Public BaseMediaProvider Interface ---

    def start_listening(self) -> None:
        """Start the background event loop and register WinRT session listeners."""
        with self._lock:
            if self._is_listening:
                return

            if not WINRT_AVAILABLE:
                logger.warning("WinRT libraries not available. GSMTCProvider cannot start.")
                return

            self._is_listening = True
            self._loop_ready.clear()

            # Create background worker thread
            self._thread = threading.Thread(
                target=self._run_event_loop,
                name="GSMTCProviderWorker",
                daemon=True,
            )
            self._thread.start()

        # Wait for worker thread to initialize event loop
        if not self._loop_ready.wait(timeout=3.0):
            logger.error("GSMTCProvider worker thread failed to initialize event loop.")
            self.stop_listening()
            return

        # Submit startup coroutine to background loop
        try:
            future = self._run_coroutine_on_loop(self._async_start())
            if future:
                future.result(timeout=5.0)
        except Exception as e:
            logger.error("Startup failed for GSMTCProvider: %s", e)
            self.stop_listening()

    def stop_listening(self) -> None:
        """Cleanly unregister listeners, cancel pending tasks, and shutdown event loop."""
        with self._lock:
            if not self._is_listening:
                return
            self._is_listening = False

            loop = self._loop
            thread = self._thread

        if loop and loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(self._async_stop(), loop)
                future.result(timeout=5.0)
            except Exception as e:
                logger.warning("Error during _async_stop execution: %s", e)

            # Schedule loop stop on background thread
            loop.call_soon_threadsafe(loop.stop)

        if thread and thread.is_alive():
            thread.join(timeout=3.0)

        with self._lock:
            self._loop = None
            self._thread = None
            self._loop_ready.clear()
            self._manager = None
            self._current_session = None
            self._current_track = TrackInfo.empty()
            self._playback_status = PlaybackStatus.CLOSED
            self._is_session_available = False

    def get_current_track(self) -> TrackInfo:
        """Return the current cached TrackInfo object."""
        with self._lock:
            return self._current_track

    def get_playback_status(self) -> PlaybackStatus:
        """Return the current cached PlaybackStatus enum."""
        with self._lock:
            return self._playback_status

    def is_session_available(self) -> bool:
        """Return True if an active media session exists."""
        with self._lock:
            return self._is_session_available

    # --- Transport Control Interface Stubs (Full winrt implementation in Step 2) ---

    def play(self) -> bool:
        """Request active media player to resume playback."""
        return False

    def pause(self) -> bool:
        """Request active media player to pause playback."""
        return False

    def toggle_play_pause(self) -> bool:
        """Toggle between play and pause state."""
        return False

    def next_track(self) -> bool:
        """Request active media player to skip to the next track."""
        return False

    def previous_track(self) -> bool:
        """Request active media player to skip to the previous track."""
        return False

    def seek_to_position(self, position_ms: int) -> bool:
        """Request active media player to seek to a specific position in milliseconds."""
        return False


    # --- Callback Registration Setters ---

    def set_on_track_changed(self, callback: Optional[TrackCallback]) -> None:
        with self._lock:
            self._on_track_changed_cb = callback

    def set_on_status_changed(self, callback: Optional[StatusCallback]) -> None:
        with self._lock:
            self._on_status_changed_cb = callback

    def set_on_session_availability_changed(
        self, callback: Optional[SessionAvailabilityCallback]
    ) -> None:
        with self._lock:
            self._on_session_availability_changed_cb = callback

    # --- Background Loop Management ---

    def _run_event_loop(self) -> None:
        """Background thread target that runs the asyncio event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with self._lock:
            self._loop = loop

        # Signal main thread that loop is initialized and running
        self._loop_ready.set()

        try:
            loop.run_forever()
        finally:
            try:
                # Cancel remaining tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as e:
                logger.warning("Error closing event loop: %s", e)
            finally:
                loop.close()

    def _run_coroutine_on_loop(self, coro):
        """Submit a coroutine to the background loop and track its task."""
        with self._lock:
            if self._loop and self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(coro, self._loop)
                return future
        return None

    # --- Async Lifecycle & WinRT Integration ---

    async def _async_start(self) -> None:
        """Request session manager and initialize initial session bindings."""
        if not WINRT_AVAILABLE:
            return

        try:
            self._manager = await media_control.GlobalSystemMediaTransportControlsSessionManager.request_async()
            if not self._manager:
                logger.warning("GSMTC SessionManager returned None.")
                return

            self._manager_token = self._manager.add_current_session_changed(
                self._on_current_session_changed_winrt
            )
            self._sessions_token = self._manager.add_sessions_changed(
                self._on_sessions_changed_winrt
            )

            await self._evaluate_current_session()
        except Exception as e:
            logger.error("Error in _async_start: %s", e)
            raise

    async def _async_stop(self) -> None:
        """Unbind WinRT listeners, cancel pending tasks, and clear references."""
        self._unbind_current_session()

        if self._manager:
            try:
                if self._manager_token is not None:
                    self._manager.remove_current_session_changed(self._manager_token)
                if self._sessions_token is not None:
                    self._manager.remove_sessions_changed(self._sessions_token)
            except Exception as e:
                logger.warning("Error removing manager listeners: %s", e)

        # Cancel pending tasks
        with self._lock:
            tasks = list(self._pending_tasks)
            self._pending_tasks.clear()

        for task in tasks:
            if not task.done():
                task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # --- Session Evaluation & Event Binding ---

    async def _evaluate_current_session(self) -> None:
        """Query get_current_session() and bind to the active media session."""
        with self._lock:
            if not self._is_listening or not self._manager:
                return

        try:
            new_session = self._manager.get_current_session()
        except Exception as e:
            logger.warning("Error getting current session: %s", e)
            new_session = None

        with self._lock:
            old_session = self._current_session

        if self._is_same_session(old_session, new_session):
            return

        self._unbind_current_session()

        if new_session is None:
            self._update_session_availability(False)
            self._update_track_info(TrackInfo.empty())
            self._update_playback_status(PlaybackStatus.CLOSED)
            return

        with self._lock:
            self._current_session = new_session

        try:
            self._props_token = new_session.add_media_properties_changed(
                self._on_media_properties_changed_winrt
            )
            self._playback_token = new_session.add_playback_info_changed(
                self._on_playback_info_changed_winrt
            )
        except Exception as e:
            logger.warning("Error adding session event listeners: %s", e)

        self._update_session_availability(True)
        await self._fetch_session_data(new_session)

    def _unbind_current_session(self) -> None:
        """Unregister event tokens from current session."""
        with self._lock:
            session = self._current_session
            props_token = self._props_token
            playback_token = self._playback_token

            self._current_session = None
            self._props_token = None
            self._playback_token = None

        if session:
            try:
                if props_token is not None:
                    session.remove_media_properties_changed(props_token)
                if playback_token is not None:
                    session.remove_playback_info_changed(playback_token)
            except Exception as e:
                logger.warning("Error removing session listeners: %s", e)

    def _is_same_session(self, session_a, session_b) -> bool:
        """Compare session identities via app ID or reference equality."""
        if session_a is session_b:
            return True
        if session_a is None or session_b is None:
            return False

        try:
            app_a = getattr(session_a, "source_app_user_model_id", None)
            app_b = getattr(session_b, "source_app_user_model_id", None)
            if app_a and app_b:
                return app_a == app_b
        except Exception:
            pass

        return session_a == session_b

    # --- Metadata & Playback Extraction ---

    async def _fetch_session_data(self, session) -> None:
        """Fetch media properties, timeline, and playback status for a session."""
        await self._fetch_media_properties(session)
        self._fetch_playback_status(session)

    async def _fetch_media_properties(self, session) -> None:
        """Fetch track properties and album art asynchronously."""
        if not session:
            return

        try:
            props = await session.try_get_media_properties_async()
        except Exception as e:
            logger.warning("Error fetching media properties: %s", e)
            return

        if not props:
            self._update_track_info(TrackInfo.empty())
            return

        title = getattr(props, "title", "") or "Unknown Title"
        artist = getattr(props, "artist", "") or "Unknown Artist"
        album = getattr(props, "album_title", "") or ""
        app_id = getattr(session, "source_app_user_model_id", "") or "Unknown"

        duration_ms = 0
        position_ms = 0
        try:
            timeline = session.get_timeline_properties()
            if timeline:
                if hasattr(timeline, "end_time") and timeline.end_time:
                    duration_ms = int(timeline.end_time.total_seconds() * 1000)
                if hasattr(timeline, "position") and timeline.position:
                    position_ms = int(timeline.position.total_seconds() * 1000)
        except Exception as e:
            logger.debug("Could not read timeline properties: %s", e)

        album_art_bytes = None
        thumbnail_ref = getattr(props, "thumbnail", None)
        if thumbnail_ref:
            album_art_bytes = await self._extract_thumbnail_bytes(thumbnail_ref)

        track = TrackInfo(
            title=title,
            artist=artist,
            album=album,
            album_art_bytes=album_art_bytes,
            app_id=app_id,
            duration_ms=duration_ms,
            position_ms=position_ms,
        )

        self._update_track_info(track)

    def _fetch_playback_status(self, session) -> None:
        """Fetch current playback status synchronously."""
        if not session:
            self._update_playback_status(PlaybackStatus.CLOSED)
            return

        try:
            info = session.get_playback_info()
            if not info:
                self._update_playback_status(PlaybackStatus.UNKNOWN)
                return

            status_val = getattr(info, "playback_status", None)
            mapped_status = self._map_playback_status(status_val)
            self._update_playback_status(mapped_status)
        except Exception as e:
            logger.warning("Error fetching playback info: %s", e)
            self._update_playback_status(PlaybackStatus.UNKNOWN)

    async def _extract_thumbnail_bytes(self, thumbnail_ref) -> Optional[bytes]:
        """Read bytes from thumbnail stream reference."""
        if not thumbnail_ref:
            return None

        try:
            stream = await thumbnail_ref.open_read_async()
            if not stream or stream.size == 0:
                return None

            reader = streams.DataReader(stream)
            await reader.load_async(stream.size)
            buffer = reader.read_buffer(stream.size)
            return bytes(buffer)
        except Exception as e:
            logger.debug("Error extracting thumbnail bytes: %s", e)
            return None

    def _map_playback_status(self, status_enum_value) -> PlaybackStatus:
        """Map WinRT PlaybackStatus enum value to domain PlaybackStatus."""
        if status_enum_value is None:
            return PlaybackStatus.UNKNOWN

        # 1. Direct PyWinRT Enum comparison if available
        if WINRT_AVAILABLE and media_control:
            try:
                enum_cls = media_control.GlobalSystemMediaTransportControlsSessionPlaybackStatus
                if status_enum_value == enum_cls.PLAYING:
                    return PlaybackStatus.PLAYING
                if status_enum_value == enum_cls.PAUSED:
                    return PlaybackStatus.PAUSED
                if status_enum_value == enum_cls.STOPPED:
                    return PlaybackStatus.STOPPED
                if status_enum_value == enum_cls.CLOSED:
                    return PlaybackStatus.CLOSED
            except Exception:
                pass

        # 2. Check enum name property (e.g., 'PLAYING', 'PAUSED')
        name = getattr(status_enum_value, "name", "")
        if not name:
            name = str(status_enum_value)
        name_upper = str(name).upper()

        if "PLAYING" in name_upper:
            return PlaybackStatus.PLAYING
        elif "PAUSED" in name_upper:
            return PlaybackStatus.PAUSED
        elif "STOPPED" in name_upper:
            return PlaybackStatus.STOPPED
        elif "CLOSED" in name_upper:
            return PlaybackStatus.CLOSED

        # 3. Integer value fallbacks (WinRT spec: 4=PLAYING, 5=PAUSED, 3=STOPPED, 1=CLOSED)
        val = getattr(status_enum_value, "value", status_enum_value)
        if val == 4:
            return PlaybackStatus.PLAYING
        elif val == 5:
            return PlaybackStatus.PAUSED
        elif val == 3:
            return PlaybackStatus.STOPPED
        elif val == 1:
            return PlaybackStatus.CLOSED

        return PlaybackStatus.UNKNOWN

    # --- State Updating & Duplicate Suppression ---

    def _update_track_info(self, new_track: TrackInfo) -> None:
        """Update cached track info and emit callback if changed."""
        with self._lock:
            old_track = self._current_track
            if self._is_track_equal(old_track, new_track):
                return
            self._current_track = new_track
            callback = self._on_track_changed_cb

        if callback:
            try:
                callback(new_track)
            except Exception as e:
                logger.error("Error in on_track_changed callback: %s", e)

    def _update_playback_status(self, new_status: PlaybackStatus) -> None:
        """Update cached playback status and emit callback if changed."""
        with self._lock:
            if self._playback_status == new_status:
                return
            self._playback_status = new_status
            callback = self._on_status_changed_cb

        if callback:
            try:
                callback(new_status)
            except Exception as e:
                logger.error("Error in on_status_changed callback: %s", e)

    def _update_session_availability(self, available: bool) -> None:
        """Update cached session availability and emit callback if changed."""
        with self._lock:
            if self._is_session_available == available:
                return
            self._is_session_available = available
            callback = self._on_session_availability_changed_cb

        if callback:
            try:
                callback(available)
            except Exception as e:
                logger.error("Error in on_session_availability_changed callback: %s", e)

    def _is_track_equal(self, t1: TrackInfo, t2: TrackInfo) -> bool:
        """Compare TrackInfo fields ignoring position_ms to prevent callback spam."""
        return (
            t1.title == t2.title
            and t1.artist == t2.artist
            and t1.album == t2.album
            and t1.album_art_bytes == t2.album_art_bytes
            and t1.app_id == t2.app_id
            and t1.duration_ms == t2.duration_ms
        )

    # --- WinRT Event Handler Wrappers ---

    def _on_current_session_changed_winrt(self, sender, args) -> None:
        """Handler for WinRT CurrentSessionChanged event."""
        self._schedule_coroutine(self._evaluate_current_session())

    def _on_sessions_changed_winrt(self, sender, args) -> None:
        """Handler for WinRT SessionsChanged event."""
        self._schedule_coroutine(self._evaluate_current_session())

    def _on_media_properties_changed_winrt(self, sender, args) -> None:
        """Handler for WinRT MediaPropertiesChanged event."""
        with self._lock:
            session = self._current_session
        if session:
            self._schedule_coroutine(self._fetch_media_properties(session))

    def _on_playback_info_changed_winrt(self, sender, args) -> None:
        """Handler for WinRT PlaybackInfoChanged event."""
        with self._lock:
            session = self._current_session
        if session:
            self._fetch_playback_status(session)

    def _schedule_coroutine(self, coro) -> None:
        """Schedule a coroutine on the background event loop and track its task."""
        with self._lock:
            if not self._is_listening or not self._loop or not self._loop.is_running():
                return
            try:
                task = self._loop.create_task(coro)
                self._pending_tasks.add(task)
                task.add_done_callback(self._pending_tasks.discard)
            except Exception as e:
                logger.warning("Error scheduling coroutine: %s", e)
