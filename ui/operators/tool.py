import bpy
from bpy.props import StringProperty, FloatProperty
from ... utils.draw import draw_fading_label
from ... utils.tools import get_tools_from_context, get_tool_options, get_active_tool
from ... utils.registration import get_addon_prefs, get_addon, get_prefs
from ... utils.tools import prettify_tool_name
from ... colors import white, green

boxcutter = None

class SetToolByName(bpy.types.Operator):
    bl_idname = "m4n1.set_tool_by_name"
    bl_label = "M4N1: Set Tool by Name"
    bl_description = "Set Tool by Name"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Tool name/ID")
    alpha: FloatProperty(name="Alpha", default=0.5, min=0.1, max=1)
    def draw(self, context):
        layout = self.layout
        column = layout.column()

        column.label(text=f"Tool: {self.name}")

    def execute(self, context):
        active_tool = get_active_tool(context).idname

        if active_tool == 'm4n1.tool_hyper_cursor_simple':
            context.space_data.overlay.show_cursor = True

        bpy.ops.wm.tool_set_by_id(name=self.name)

        if 'm4n1.tool_hyper_cursor' in self.name:
            context.scene.HC.show_gizmos = True
            size, color = 20, green
        else:
            size, color = 12, white

        draw_fading_label(context, text=prettify_tool_name(self.name), time=get_prefs().HUD_fade_tools_pie, size=size, color=color, move_y=10)

        return {'FINISHED'}

class SetBCPreset(bpy.types.Operator):
    bl_idname = "m4n1.set_boxcutter_preset"
    bl_label = "M4N1: Set BoxCutter Preset"
    bl_description = "Quickly enable/switch BC tool in/to various modes"
    bl_options = {'REGISTER', 'UNDO'}

    mode: StringProperty()
    shape_type: StringProperty()
    set_origin: StringProperty(default='MOUSE')
    @classmethod
    def poll(cls, context):
        global boxcutter

        if boxcutter is None:
            _, boxcutter, _, _ = get_addon("BoxCutter")

        return boxcutter in get_tools_from_context(context)

    def execute(self, context):
        global boxcutter

        if boxcutter is None:
            _, boxcutter, _, _ = get_addon("BoxCutter")

        tools = get_tools_from_context(context)
        bcprefs = get_addon_prefs('BoxCutter')

        if not tools[boxcutter]['active']:
            bpy.ops.wm.tool_set_by_id(name=boxcutter)

        options = get_tool_options(context, boxcutter, 'bc.shape_draw')

        if options:
            options.mode = self.mode
            options.shape_type = self.shape_type

            bcprefs.behavior.set_origin = self.set_origin
            bcprefs.snap.enable = True

        return {'FINISHED'}
