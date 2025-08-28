# ABOUTME: Utility functions for handling imports in both Blender addon and test contexts
# ABOUTME: Provides is_running_as_addon() to detect execution context for proper import paths

"""Import utilities for Blender addon compatibility."""


def is_running_as_addon():
    """Check if module is running as a Blender addon (vs standalone/tests).

    When running as Blender addon, __package__ is set to addon name.
    When running standalone or in tests, __package__ is None or empty.

    Returns:
        bool: True if running as Blender addon, False otherwise
    """
    import inspect

    frame = inspect.currentframe()
    if frame and frame.f_back:
        caller_globals = frame.f_back.f_globals
        package = caller_globals.get("__package__", "")
        name = caller_globals.get("__name__", "")

        # If package is set and contains addon name, we're in addon context
        if package and "cinemon_addon" in package:
            return True
        # If name contains dots and isn't __main__, we're likely in addon context
        if name != "__main__" and "." in name and "cinemon_addon" in name:
            return True

    return False
