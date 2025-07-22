# ABOUTME: Apply system coordination for Cinemon addon
# ABOUTME: Main entry point that delegates to specialized modules

"""Apply system coordination for Cinemon addon."""

try:
    from .vse_operators import (
        regenerate_animations_for_strips, 
        CINEMON_OT_discard_changes,
        ApplyUIManager,
        register as register_vse_operators,
        unregister as unregister_vse_operators
    )
    from .animation_applicators import apply_animation_to_strip, clear_strip_animations
except ImportError:
    # For direct module execution/testing
    from vse_operators import (
        regenerate_animations_for_strips,
        CINEMON_OT_discard_changes,
        ApplyUIManager,
        register as register_vse_operators,
        unregister as unregister_vse_operators
    )
    from animation_applicators import apply_animation_to_strip, clear_strip_animations


# Export all classes and functions for backward compatibility
classes = [
    CINEMON_OT_discard_changes
]


def register():
    """Register apply system (delegates to vse_operators)."""
    try:
        register_vse_operators()
        print("Apply system registered successfully")
    except Exception as e:
        print(f"Apply system registration error: {e}")


def unregister():
    """Unregister apply system (delegates to vse_operators)."""
    try:
        unregister_vse_operators()
        print("Apply system unregistered")
    except Exception as e:
        print(f"Apply system unregistration error: {e}")


if __name__ == "__main__":
    register()