import bpy
from bpy.props import StringProperty
from ... utils.registration import get_prefs
from ... utils.view import set_xray, reset_xray, update_local_view
from ... utils.object import parent
from ... utils.tools import get_active_tool, get_tools_from_context
from bpy.app.translations import pgettext as _
user_cavity = True

class EditMode(bpy.types.Operator):
    bl_idname = "m4a1.edit_mode"
    bl_label = "Edit Mode"
    bl_options = {'REGISTER', 'UNDO'}

    toggled_object = False

    @classmethod
    def poll(cls, context):
        if context.mode in ['OBJECT', 'EDIT_MESH']:
            active = context.active_object

            if active and active.override_library:
                if active.override_library:
                    cls.poll_message_set("You can't change modes on objects with a Library Override")

            return active and not active.override_library

    @classmethod
    def description(cls, context, properties):
        return _("Switch to {} Mode").format(_('Object') if context.mode == 'EDIT_MESH' else _('Edit'))

    def execute(self, context):
        global user_cavity

        shading = context.space_data.shading
        toggle_cavity = get_prefs().toggle_cavity
        toggle_xray = get_prefs().toggle_xray
        sync_tools = get_prefs().sync_tools

        if sync_tools:
            active_tool = get_active_tool(context).idname

        if context.mode == "OBJECT":
            if toggle_xray:
                set_xray(context)

            bpy.ops.object.mode_set(mode="EDIT")

            if toggle_cavity:
                user_cavity = shading.show_cavity
                shading.show_cavity = False

            if sync_tools and active_tool in get_tools_from_context(context):
                bpy.ops.wm.tool_set_by_id(name=active_tool)

            self.toggled_object = False

        elif context.mode == "EDIT_MESH":
            if toggle_xray:
                reset_xray(context)

            bpy.ops.object.mode_set(mode="OBJECT")

            if toggle_cavity and user_cavity:
                shading.show_cavity = True
                user_cavity = True

            if sync_tools and active_tool in get_tools_from_context(context):
                bpy.ops.wm.tool_set_by_id(name=active_tool)

            self.toggled_object = True

        return {'FINISHED'}

class MeshMode(bpy.types.Operator):
    bl_idname = "m4a1.mesh_mode"
    bl_label = "Mesh Mode"
    bl_options = {'REGISTER', 'UNDO'}

    mode: StringProperty()

    @classmethod
    def poll(cls, context):
        if context.mode in ['OBJECT', 'EDIT_MESH']:
            active = context.active_object

            if active and active.override_library:
                if active.override_library:
                    cls.poll_message_set("You can't change modes on objects with a Library Override")

            return active and not active.override_library

    @classmethod
    def description(cls, context, properties):
        mode = properties.mode

        isvert = tuple(context.scene.tool_settings.mesh_select_mode) == (True, False, False)
        isedge = tuple(context.scene.tool_settings.mesh_select_mode) == (False, True, False)
        isface = tuple(context.scene.tool_settings.mesh_select_mode) == (False, False, True)

        desc = _("{} Select").format(_(mode.capitalize()))

        if not (mode == 'VERT' and isvert or mode == 'EDGE' and isedge or mode == 'FACE' and isface):
            desc += _("\nSHIFT: Extend Selection")

        if isvert and mode != 'VERT' or isedge and mode != 'EDGE':
            desc += _('\n   or')

            if mode == 'VERT':
                desc += _("\nCTRL: Contract Selection")
            else:
                desc += _("\nCTRL: Expand Selection")

        elif isface and mode != 'FACE':
            desc += _('\n   or')
            desc += _("\nCTRL: Contract Selection")

        return desc

    def invoke(self, context, event):
        global user_cavity

        shading = context.space_data.shading
        toggle_cavity = get_prefs().toggle_cavity
        toggle_xray = get_prefs().toggle_xray

        if context.mode == "OBJECT":
            if toggle_xray:
                set_xray(context)

            active_tool = get_active_tool(context).idname if get_prefs().sync_tools else None

            bpy.ops.object.mode_set(mode="EDIT")

            if toggle_cavity:
                user_cavity = shading.show_cavity
                shading.show_cavity = False

            if active_tool and active_tool in get_tools_from_context(context):
                bpy.ops.wm.tool_set_by_id(name=active_tool)

        bpy.ops.mesh.select_mode(use_extend=event.shift, use_expand=event.ctrl, type=self.mode)
        return {'FINISHED'}

class ImageMode(bpy.types.Operator):
    bl_idname = "m4a1.image_mode"
    bl_label = "M4A1: Image Mode"
    bl_options = {'REGISTER'}

    mode: StringProperty()

    def execute(self, context):
        view = context.space_data
        active = context.active_object

        toolsettings = context.scene.tool_settings
        view.mode = self.mode

        if self.mode == "UV" and active:
            if active.mode == "OBJECT":
                uvs = active.data.uv_layers

                if not uvs:
                    uvs.new()

                bpy.ops.object.mode_set(mode="EDIT")

                if not toolsettings.use_uv_select_sync:
                    bpy.ops.mesh.select_all(action="SELECT")

        return {'FINISHED'}

class UVMode(bpy.types.Operator):
    bl_idname = "m4a1.uv_mode"
    bl_label = "M4A1: UV Mode"
    bl_options = {'REGISTER'}

    mode: StringProperty()

    def execute(self, context):
        toolsettings = context.scene.tool_settings
        view = context.space_data

        if view.mode != "UV":
            view.mode = "UV"

        if toolsettings.use_uv_select_sync:
            bpy.ops.mesh.select_mode(type=self.mode.replace("VERTEX", "VERT"))

        else:
            toolsettings.uv_select_mode = self.mode

        return {'FINISHED'}

class SurfaceDrawMode(bpy.types.Operator):
    bl_idname = "m4a1.surface_draw_mode"
    bl_label = "M4A1: Surface Draw Mode"
    bl_description = "Surface Draw, create parented, empty GreasePencil object and enter DRAW mode.\nSHIFT: Select the Line tool."
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        bpy.ops.object.mode_set(mode='OBJECT')

        scene = context.scene
        ts = scene.tool_settings
        mcol = context.collection
        view = context.space_data
        active = context.active_object

        existing_gps = [obj for obj in active.children if obj.type == "GPENCIL"]

        if existing_gps:
            gp = existing_gps[0]

        else:
            name = "%s_SurfaceDrawing" % (active.name)
            gp = bpy.data.objects.new(name, bpy.data.grease_pencils.new(name))

            mcol.objects.link(gp)

            gp.matrix_world = active.matrix_world
            parent(gp, active)

        update_local_view(view, [(gp, True)])

        layer = gp.data.layers.new(name="SurfaceLayer")
        layer.blend_mode = 'MULTIPLY'

        if not layer.frames:
            layer.frames.new(0)

        context.view_layer.objects.active = gp
        active.select_set(False)
        gp.select_set(True)

        gp.color = (0, 0, 0, 1)

        blacks = [mat for mat in bpy.data.materials if mat.name == 'Black' and mat.is_grease_pencil]
        mat = blacks[0] if blacks else bpy.data.materials.new(name='Black')

        bpy.data.materials.create_gpencil_data(mat)
        gp.data.materials.append(mat)

        bpy.ops.object.mode_set(mode='PAINT_GPENCIL')

        ts.gpencil_stroke_placement_view3d = 'SURFACE'

        gp.data.zdepth_offset = 0.01

        ts.gpencil_paint.brush.gpencil_settings.pen_strength = 1

        if not view.show_region_toolbar:
            view.show_region_toolbar = True

        opacity = gp.grease_pencil_modifiers.new(name="Opacity", type="GP_OPACITY")
        opacity.show_expanded = False
        thickness = gp.grease_pencil_modifiers.new(name="Thickness", type="GP_THICK")
        thickness.show_expanded = False

        if event.shift:
            bpy.ops.wm.tool_set_by_id(name="builtin.line")

        else:
            bpy.ops.wm.tool_set_by_id(name="builtin_brush.Draw")

        return {'FINISHED'}
