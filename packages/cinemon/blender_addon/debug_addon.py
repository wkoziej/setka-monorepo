# ABOUTME: Debug script to catch Python errors in Blender addon  
# ABOUTME: Run this script in Blender Text Editor to see detailed Python errors

"""Debug script for testing Cinemon addon in Blender."""

import sys
import traceback

def test_addon_import():
    """Test importing addon modules and catch errors."""
    print("=== Testing Cinemon addon imports ===")
    
    try:
        print("1. Testing main addon import...")
        import cinemon_addon
        print("✓ Main addon imported successfully")
    except Exception as e:
        print(f"✗ Main addon import failed: {e}")
        traceback.print_exc()
    
    try:
        print("2. Testing operators import...")
        from cinemon_addon import operators
        print("✓ Operators imported successfully")
    except Exception as e:
        print(f"✗ Operators import failed: {e}")
        traceback.print_exc()
    
    try:
        print("3. Testing setka_common import...")
        from cinemon_addon.setka_common.config.yaml_config import YAMLConfigLoader
        print("✓ setka_common imported successfully")
    except Exception as e:
        print(f"✗ setka_common import failed: {e}")
        traceback.print_exc()

def test_preset_loading():
    """Test loading preset files."""
    print("\n=== Testing preset loading ===")
    
    try:
        import bpy
        from pathlib import Path
        
        # Get addon directory
        addon_dir = Path(__file__).parent
        preset_path = addon_dir / "example_presets" / "vintage.yaml"
        
        print(f"Loading preset: {preset_path}")
        
        # Simulate preset loading like in addon
        try:
            # Add vendor path
            vendor_path = addon_dir / "vendor"
            if str(vendor_path) not in sys.path:
                sys.path.insert(0, str(vendor_path))
            
            # Add addon path for setka_common
            if str(addon_dir) not in sys.path:
                sys.path.insert(0, str(addon_dir))
            
            import yaml
            with open(preset_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            print("✓ Preset loaded successfully")
            print(f"  - FPS: {config_data['project']['fps']}")
            print(f"  - Layout: {config_data['layout']['type']}")
            print(f"  - Animations: {len(config_data.get('strip_animations', {}))}")
            
        except Exception as e:
            print(f"✗ Preset loading failed: {e}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"✗ Preset test setup failed: {e}")
        traceback.print_exc()

def test_ui_errors():
    """Test UI panel drawing."""
    print("\n=== Testing UI panel ===")
    
    try:
        import bpy
        
        # Try to access scene properties
        scene = bpy.context.scene
        print(f"Scene: {scene}")
        
        # Test setting cinemon properties
        scene.cinemon_config_path = "test.yaml"
        scene['cinemon_fps'] = 30
        scene['cinemon_layout_type'] = "random"
        
        print("✓ Scene properties set successfully")
        
    except Exception as e:
        print(f"✗ UI test failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting Cinemon addon debug...")
    test_addon_import()
    test_preset_loading()
    test_ui_errors()
    print("\n=== Debug complete ===")