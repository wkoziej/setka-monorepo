# ABOUTME: Blender Add-on for Cinemon - main initialization file
# ABOUTME: Provides UI panels and operators for VSE animation presets

"""Cinemon Blender Add-on for VSE animation preset management."""

bl_info = {
    "name": "Cinemon Animation",
    "author": "Setka Team",
    "version": (0, 1, 0),
    "blender": (4, 3, 0),
    "location": "Video Sequence Editor > N-Panel > Cinemon Animation",
    "description": "Manage and apply animation presets to VSE strips",
    "category": "Sequencer",
}

# Placeholder for addon registration
def register():
    """Register addon classes."""
    pass

def unregister():
    """Unregister addon classes."""
    pass

if __name__ == "__main__":
    register()