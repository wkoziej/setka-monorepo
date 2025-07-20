# ABOUTME: Blender addon UI components for layout controls and configuration
# ABOUTME: Provides panels and operators for layout type selection and parameter tuning

"""Layout UI controls for Cinemon Blender addon."""

import sys
from pathlib import Path

# Import Blender API
try:
    import bpy
    from bpy.types import Panel, Operator
    from bpy.props import StringProperty, FloatProperty, IntProperty, BoolProperty, EnumProperty
except ImportError:
    # For testing without Blender
    class Panel:
        pass
    
    class Operator:
        def report(self, level, message):
            """Mock report method for testing."""
            pass
    
    def StringProperty(**kwargs):
        return kwargs.get('default', '')
    
    def FloatProperty(**kwargs):
        return kwargs.get('default', 0.0)
    
    def IntProperty(**kwargs):
        return kwargs.get('default', 0)
    
    def BoolProperty(**kwargs):
        return kwargs.get('default', False)
    
    def EnumProperty(**kwargs):
        return kwargs.get('default', kwargs.get('items', [('default', 'Default', '')])[0][0])

# Import layout classes from VSE system
try:
    import sys
    from pathlib import Path
    
    # Add src/blender to path for real layouts
    blender_src_path = Path(__file__).parent.parent / "src" / "blender"
    if str(blender_src_path) not in sys.path:
        sys.path.insert(0, str(blender_src_path))
    
    from vse.layouts.random_layout import RandomLayout
    from vse.layouts.main_pip_layout import MainPipLayout as GridLayout  # Use MainPipLayout as Grid alternative
    
except ImportError:
    print("Warning: Could not import real layout classes, using mock implementations")
    # For testing - mock layout classes with basic functionality
    import random
    
    class RandomLayout:
        def __init__(self, margin=0.1, seed=42, overlap_allowed=False):
            self.margin = margin
            self.seed = seed
            self.overlap_allowed = overlap_allowed
        
        def generate_positions(self, num_strips=4):
            """Generate random positions for strips."""
            random.seed(self.seed)
            positions = []
            for i in range(num_strips):
                x = random.randint(-500, 500)  # Blender VSE coordinates
                y = random.randint(-300, 300)
                scale_x = random.uniform(0.5, 1.0)
                scale_y = random.uniform(0.5, 1.0)
                positions.append((x, y, scale_x, scale_y))
            return positions
    
    class GridLayout:
        def __init__(self, rows=2, columns=2, gap=0.05):
            self.rows = rows
            self.columns = columns
            self.gap = gap
        
        def generate_positions(self, num_strips=4):
            """Generate grid positions for strips."""
            positions = []
            for i in range(min(num_strips, self.rows * self.columns)):
                row = i // self.columns
                col = i % self.columns
                
                # Calculate position based on grid
                x = (col - self.columns/2) * 400  # Spread horizontally
                y = (row - self.rows/2) * 300     # Spread vertically
                scale_x = 0.8  # Slightly smaller for grid
                scale_y = 0.8
                positions.append((x, y, scale_x, scale_y))
            return positions


class CINEMON_PT_layout_panel(Panel):
    """Panel for layout configuration controls."""
    
    bl_label = "Layout Configuration"
    bl_idname = "CINEMON_PT_layout_panel"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Cinemon"
    bl_parent_id = "CINEMON_PT_main_panel"
    
    def draw(self, context):
        """Draw the layout configuration panel UI."""
        layout = self.layout
        scene = context.scene
        
        # Layout type selection
        layout.label(text="Layout Type:", icon='MOD_ARRAY')
        
        # Layout type dropdown
        layout_items = [
            ('random', 'Random', 'Random positioning with margin control'),
            ('grid', 'Grid', 'Grid-based positioning with rows/columns'),
        ]
        
        # Mock property for layout type
        layout_type = getattr(scene, 'cinemon_layout_type', 'random')
        
        # Create buttons for layout type selection
        row = layout.row(align=True)
        for item_id, label, description in layout_items:
            op = row.operator("cinemon.set_layout_type", text=label)
            op.layout_type = item_id
        
        layout.separator()
        
        # Show parameters based on selected layout type
        if layout_type == 'random':
            self.draw_random_params(layout, scene)
        elif layout_type == 'grid':
            self.draw_grid_params(layout, scene)
        
        # Preview button
        layout.separator()
        layout.operator("cinemon.preview_layout", text="Preview Layout", icon='RESTRICT_VIEW_OFF')
    
    def draw_random_params(self, layout, scene):
        """Draw random layout parameters."""
        box = layout.box()
        box.label(text="Random Layout Parameters:", icon='RNDCURVE')
        
        # Margin control
        margin = getattr(scene, 'cinemon_random_margin', 0.1)
        box.label(text=f"Margin: {margin:.2f}")
        
        # Seed control
        seed = getattr(scene, 'cinemon_random_seed', 42)
        box.label(text=f"Seed: {seed}")
        
        # Overlap control
        overlap = getattr(scene, 'cinemon_random_overlap', False)
        box.label(text=f"Allow Overlap: {overlap}")
        
        # Parameter adjustment operator
        op = box.operator("cinemon.set_random_params", text="Adjust Parameters")
    
    def draw_grid_params(self, layout, scene):
        """Draw grid layout parameters."""
        box = layout.box()
        box.label(text="Grid Layout Parameters:", icon='GRID')
        
        # Rows and columns
        rows = getattr(scene, 'cinemon_grid_rows', 2)
        columns = getattr(scene, 'cinemon_grid_columns', 2)
        gap = getattr(scene, 'cinemon_grid_gap', 0.05)
        
        box.label(text=f"Grid: {rows}x{columns}")
        box.label(text=f"Gap: {gap:.2f}")
        
        # Parameter adjustment operator
        op = box.operator("cinemon.set_grid_params", text="Adjust Parameters")
    


class CINEMON_OT_set_layout_type(Operator):
    """Set the layout type for video strips."""
    
    bl_idname = "cinemon.set_layout_type"
    bl_label = "Set Layout Type"
    bl_description = "Set the layout type for video strip positioning"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Layout type property
    try:
        layout_type: StringProperty(
            name="Layout Type",
            description="Type of layout to use",
            default="random"
        )
    except NameError:
        # For testing without bpy
        layout_type = "random"
    
    def execute(self, context):
        """Set the layout type in scene."""
        try:
            context.scene.cinemon_layout_type = self.layout_type
            self.report({'INFO'}, f"Layout type set to: {self.layout_type}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to set layout type: {e}")
            return {'CANCELLED'}


class CINEMON_OT_set_random_params(Operator):
    """Set random layout parameters."""
    
    bl_idname = "cinemon.set_random_params"
    bl_label = "Set Random Parameters"
    bl_description = "Configure random layout parameters"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Random layout properties
    try:
        margin: FloatProperty(
            name="Margin",
            description="Margin around strips",
            default=0.1,
            min=0.0,
            max=0.5
        )
        
        seed: IntProperty(
            name="Seed",
            description="Random seed for reproducible layouts",
            default=42,
            min=1,
            max=9999
        )
        
        overlap_allowed: BoolProperty(
            name="Allow Overlap",
            description="Allow strips to overlap",
            default=False
        )
    except NameError:
        # For testing without bpy
        margin = 0.1
        seed = 42
        overlap_allowed = False
    
    def execute(self, context):
        """Set random layout parameters in scene."""
        try:
            context.scene.cinemon_random_margin = self.margin
            context.scene.cinemon_random_seed = self.seed
            context.scene.cinemon_random_overlap = self.overlap_allowed
            
            self.report({'INFO'}, f"Random layout params set: margin={self.margin}, seed={self.seed}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to set random parameters: {e}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Open dialog for parameter adjustment."""
        # Get current values from scene
        self.margin = getattr(context.scene, 'cinemon_random_margin', 0.1)
        self.seed = getattr(context.scene, 'cinemon_random_seed', 42)
        self.overlap_allowed = getattr(context.scene, 'cinemon_random_overlap', False)
        
        return context.window_manager.invoke_props_dialog(self)


class CINEMON_OT_set_grid_params(Operator):
    """Set grid layout parameters."""
    
    bl_idname = "cinemon.set_grid_params"
    bl_label = "Set Grid Parameters"
    bl_description = "Configure grid layout parameters"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Grid layout properties
    try:
        rows: IntProperty(
            name="Rows",
            description="Number of rows in grid",
            default=2,
            min=1,
            max=4
        )
        
        columns: IntProperty(
            name="Columns",
            description="Number of columns in grid",
            default=2,
            min=1,
            max=4
        )
        
        gap: FloatProperty(
            name="Gap",
            description="Gap between grid cells",
            default=0.05,
            min=0.0,
            max=0.2
        )
    except NameError:
        # For testing without bpy
        rows = 2
        columns = 2
        gap = 0.05
    
    def execute(self, context):
        """Set grid layout parameters in scene."""
        try:
            context.scene.cinemon_grid_rows = self.rows
            context.scene.cinemon_grid_columns = self.columns
            context.scene.cinemon_grid_gap = self.gap
            
            self.report({'INFO'}, f"Grid layout set: {self.rows}x{self.columns}, gap={self.gap}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to set grid parameters: {e}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Open dialog for parameter adjustment."""
        # Get current values from scene
        self.rows = getattr(context.scene, 'cinemon_grid_rows', 2)
        self.columns = getattr(context.scene, 'cinemon_grid_columns', 2)
        self.gap = getattr(context.scene, 'cinemon_grid_gap', 0.05)
        
        return context.window_manager.invoke_props_dialog(self)


class CINEMON_OT_preview_layout(Operator):
    """Preview the current layout configuration."""
    
    bl_idname = "cinemon.preview_layout"
    bl_label = "Preview Layout"
    bl_description = "Preview the current layout configuration on existing strips"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """Apply layout preview to existing strips."""
        try:
            scene = context.scene
            layout_type = getattr(scene, 'cinemon_layout_type', 'random')
            
            # Get sequence editor
            if not scene.sequence_editor:
                self.report({'WARNING'}, "No sequence editor found")
                return {'CANCELLED'}
            
            sequences = scene.sequence_editor.sequences
            video_strips = [s for s in sequences if s.type == 'MOVIE']
            
            if not video_strips:
                self.report({'WARNING'}, "No video strips found to preview")
                return {'CANCELLED'}
            
            # Generate layout based on type
            if layout_type == 'random':
                layout = self.create_random_layout(scene)
            elif layout_type == 'grid':
                layout = self.create_grid_layout(scene)
            else:
                self.report({'WARNING'}, f"Layout type '{layout_type}' not implemented")
                return {'CANCELLED'}
            
            # Apply layout positions to strips
            positions = layout.generate_positions(len(video_strips))
            
            for strip, position in zip(video_strips, positions):
                # Apply position to strip transform
                if hasattr(strip, 'transform'):
                    # Position is typically (x, y, scale_x, scale_y) 
                    x, y, scale_x, scale_y = position[:4] if len(position) >= 4 else (position[0], position[1], 1.0, 1.0)
                    
                    # Set transform properties
                    strip.transform.offset_x = int(x)
                    strip.transform.offset_y = int(y) 
                    strip.transform.scale_x = scale_x
                    strip.transform.scale_y = scale_y
                    
                    print(f"Set strip '{strip.name}' to position ({x}, {y}) scale ({scale_x}, {scale_y})")
                else:
                    print(f"Warning: Strip '{strip.name}' has no transform property")
            
            self.report({'INFO'}, f"Applied {layout_type} layout preview to {len(video_strips)} strips")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to preview layout: {e}")
            return {'CANCELLED'}
    
    def create_random_layout(self, scene):
        """Create random layout from scene parameters."""
        margin = getattr(scene, 'cinemon_random_margin', 0.1)
        seed = getattr(scene, 'cinemon_random_seed', 42)
        overlap = getattr(scene, 'cinemon_random_overlap', False)
        
        return RandomLayout(margin=margin, seed=seed, overlap_allowed=overlap)
    
    def create_grid_layout(self, scene):
        """Create grid layout from scene parameters."""
        rows = getattr(scene, 'cinemon_grid_rows', 2)
        columns = getattr(scene, 'cinemon_grid_columns', 2)
        gap = getattr(scene, 'cinemon_grid_gap', 0.05)
        
        return GridLayout(rows=rows, columns=columns, gap=gap)


# All classes for registration
classes = [
    CINEMON_PT_layout_panel,
    CINEMON_OT_set_layout_type,
    CINEMON_OT_set_random_params,
    CINEMON_OT_set_grid_params,
    CINEMON_OT_preview_layout,
]


def register():
    """Register layout UI classes."""
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
        
        # Register scene properties for layout configuration
        bpy.types.Scene.cinemon_layout_type = StringProperty(
            name="Layout Type",
            description="Type of layout to use for video strips",
            default="random"
        )
        
        # Random layout properties
        bpy.types.Scene.cinemon_random_margin = FloatProperty(
            name="Random Margin",
            description="Margin around randomly positioned strips",
            default=0.1,
            min=0.0,
            max=0.5
        )
        
        bpy.types.Scene.cinemon_random_seed = IntProperty(
            name="Random Seed",
            description="Random seed for reproducible layouts",
            default=42,
            min=1,
            max=9999
        )
        
        bpy.types.Scene.cinemon_random_overlap = BoolProperty(
            name="Allow Overlap",
            description="Allow strips to overlap in random layout",
            default=False
        )
        
        # Grid layout properties
        bpy.types.Scene.cinemon_grid_rows = IntProperty(
            name="Grid Rows",
            description="Number of rows in grid layout",
            default=2,
            min=1,
            max=4
        )
        
        bpy.types.Scene.cinemon_grid_columns = IntProperty(
            name="Grid Columns",
            description="Number of columns in grid layout",
            default=2,
            min=1,
            max=4
        )
        
        bpy.types.Scene.cinemon_grid_gap = FloatProperty(
            name="Grid Gap",
            description="Gap between grid cells",
            default=0.05,
            min=0.0,
            max=0.2
        )
        
        print("Cinemon layout UI registered successfully")
    except (NameError, AttributeError):
        # bpy not available in test environment
        pass


def unregister():
    """Unregister layout UI classes."""
    try:
        # Clean up scene properties
        if hasattr(bpy.types.Scene, 'cinemon_layout_type'):
            delattr(bpy.types.Scene, 'cinemon_layout_type')
        if hasattr(bpy.types.Scene, 'cinemon_random_margin'):
            delattr(bpy.types.Scene, 'cinemon_random_margin')
        if hasattr(bpy.types.Scene, 'cinemon_random_seed'):
            delattr(bpy.types.Scene, 'cinemon_random_seed')
        if hasattr(bpy.types.Scene, 'cinemon_random_overlap'):
            delattr(bpy.types.Scene, 'cinemon_random_overlap')
        if hasattr(bpy.types.Scene, 'cinemon_grid_rows'):
            delattr(bpy.types.Scene, 'cinemon_grid_rows')
        if hasattr(bpy.types.Scene, 'cinemon_grid_columns'):
            delattr(bpy.types.Scene, 'cinemon_grid_columns')
        if hasattr(bpy.types.Scene, 'cinemon_grid_gap'):
            delattr(bpy.types.Scene, 'cinemon_grid_gap')
        
        # Unregister classes
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
        
        print("Cinemon layout UI unregistered")
    except (NameError, AttributeError):
        # bpy not available in test environment
        pass


if __name__ == "__main__":
    register()