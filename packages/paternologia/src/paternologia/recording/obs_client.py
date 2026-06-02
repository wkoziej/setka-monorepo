# ABOUTME: obs-websocket v5 client wrapping obsws-python for record start/stop.
# ABOUTME: Idempotent commands, RecordStateChanged events, reconnect-friendly.

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


def _default_req_factory(host: str, port: int, password: str):
    from obsws_python import ReqClient

    return ReqClient(host=host, port=port, password=password, timeout=3)


def _default_event_factory(host: str, port: int, password: str):
    from obsws_python import EventClient

    return EventClient(host=host, port=port, password=password)


class ObsClient:
    """Thin wrapper around obsws-python for recording control.

    The OBS clients are created via injectable factories so the wrapper logic
    (idempotency, event mapping, reconnect state) can be tested without OBS.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 4455,
        password: str = "",
        *,
        on_record_state: Callable[[object], None] | None = None,
        req_factory: Callable[[str, int, str], object] = _default_req_factory,
        event_factory: Callable[[str, int, str], object] = _default_event_factory,
    ):
        self._host = host
        self._port = port
        self._password = password
        self._on_record_state = on_record_state
        self._req_factory = req_factory
        self._event_factory = event_factory
        self._req = None
        self._event = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Connect (or reconnect) the request + event clients. Idempotent."""
        if self._connected:
            return True
        try:
            self._req = self._req_factory(self._host, self._port, self._password)
            self._event = self._event_factory(self._host, self._port, self._password)
            self._event.callback.register(self._on_record_state_changed)
            self._connected = True
            logger.info("OBS connected at %s:%d", self._host, self._port)
        except Exception as e:
            logger.warning("OBS connect failed (%s:%d): %s", self._host, self._port, e)
            self._req = None
            self._event = None
            self._connected = False
        return self._connected

    def disconnect(self) -> None:
        for client in (self._event, self._req):
            try:
                if client is not None:
                    client.disconnect()
            except Exception as e:
                logger.debug("OBS disconnect error: %s", e)
        self._req = None
        self._event = None
        self._connected = False

    def is_recording(self) -> bool:
        """True if OBS is currently recording (output_active)."""
        if self._req is None:
            return False
        return bool(self._req.get_record_status().output_active)

    def start_record(self) -> bool:
        """Start recording if not already active. Returns True if it issued start."""
        if self._req is None:
            logger.warning("start_record ignored — OBS not connected")
            return False
        if self.is_recording():
            logger.info("start_record is a no-op — OBS already recording")
            return False
        self._req.start_record()
        logger.info("OBS StartRecord sent")
        return True

    def stop_record(self) -> str | None:
        """Stop recording if active. Returns the output path, or None."""
        if self._req is None:
            logger.warning("stop_record ignored — OBS not connected")
            return None
        if not self.is_recording():
            logger.info("stop_record is a no-op — OBS not recording")
            return None
        response = self._req.stop_record()
        output_path = getattr(response, "output_path", None)
        logger.info("OBS StopRecord sent (output_path=%s)", output_path)
        return output_path

    def _on_record_state_changed(self, data) -> None:
        """obsws EventClient callback (event thread). Marshals to the consumer.

        Hands the raw event to on_record_state; the OBS plan-002 hook stamps t0
        and writes the timeline. This plan only relays start/stop state.
        """
        if self._on_record_state is not None:
            self._on_record_state(data)
