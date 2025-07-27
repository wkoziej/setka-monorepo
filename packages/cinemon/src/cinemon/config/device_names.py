# ABOUTME: Device name constants for consistent strip targeting across presets
# ABOUTME: Centralizes device naming to avoid typos and enable easy refactoring

"""Constants for device names used in strip targeting."""


class DeviceNames:
    """Constants for common OBS device names in Polish setup."""

    # Main cameras (RPI devices)
    RPI_FRONT = "RPI_FRONT"
    RPI_RIGHT = "RPI_RIGHT"

    # V4L2 capture devices (USB cameras)
    V4L2_MAIN = "Urządzenie przechwytujące obraz (V4L2)"
    V4L2_DEVICE_2 = "Urządzenie przechwytujące obraz (V4L2) 2"
    V4L2_DEVICE_3 = "Urządzenie przechwytujące obraz (V4L2) 3"

    # Audio devices
    PULSEAUDIO_INPUT = "Przechwytywanie wejścia dźwięku (PulseAudio)"

    # Grouped constants for easier targeting
    MAIN_CAMERAS = [RPI_FRONT, RPI_RIGHT]
    PIP_CAMERAS = [V4L2_MAIN, V4L2_DEVICE_2, V4L2_DEVICE_3]
    ALL_VIDEO_DEVICES = MAIN_CAMERAS + PIP_CAMERAS
