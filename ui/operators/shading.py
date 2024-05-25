import bpy
from bpy.props import IntProperty, StringProperty, BoolProperty, FloatProperty
from math import degrees, radians
from bpy.types import GPENCIL_MT_layer_active
from mathutils import Matrix
from ... utils.registration import get_prefs
from ... utils.light import adjust_lights_for_rendering, get_area_light_poll
from ... utils.view import sync_light_visibility
from ... utils.material import adjust_bevel_shader
from bpy.app.translations import pgettext as _
render_visibility = []
matcap1_color_type = None

class SwitchShading(bpy.types.Operator):
    bl_idname = "m4a1.switch_shading"
    bl_label = "M4A1: Switch Shading"
    bl_options = {'REGISTER', 'UNDO'}

    shading_type: StringProperty(name=_("Shading Type"), default='SOLID')
    toggled_overlays = False

    @classmethod
    def description(cls, context, properties):
        shading = context.space_data.shading
        overlay = context.space_data.overlay
        shading_type = properties.shading_type

        if shading.type == shading_type:
            return _("{} Overlays for {} Shading").format(_('Disable') if overlay.show_overlays else _('Enable'),shading_type.capitalize())
        else:
            return _("Switch to {} shading, and restore previously set Overlay Visibility").format(shading_type.capitalize())

    def execute(self, context):
        scene = context.scene

        shading = context.space_data.shading
        overlay = context.space_data.overlay

        self.initiate_overlay_settings(context, shading, overlay)

        if shading.type == self.shading_type:
            self.prefs[self.shading_type] = not self.prefs[self.shading_type]
            self.toggled_overlays = 'Enable' if self.prefs[self.shading_type] else 'Disable'

        else:
            shading.type = self.shading_type
            self.toggled_overlays = False

            if get_prefs().activate_render and get_prefs().activate_shading_pie and get_prefs().render_adjust_lights_on_render and get_area_light_poll() and scene.M4.adjust_lights_on_render:
                self.adjust_lights(scene, shading.type, debug=False)

            if shading.type == 'RENDERED' and scene.render.engine == 'CYCLES':

                if get_prefs().activate_render and get_prefs().render_sync_light_visibility:
                    sync_light_visibility(scene)

                if get_prefs().activate_render and get_prefs().activate_shading_pie and get_prefs().render_use_bevel_shader and scene.M4.use_bevel_shader:
                    adjust_bevel_shader(context)

            if get_prefs().activate_render and get_prefs().activate_shading_pie and get_prefs().render_enforce_hide_render and scene.M4.enforce_hide_render:
                self.enforce_render_visibility(context, shading.type, debug=True)

        overlay.show_overlays = self.prefs[self.shading_type]
        return {'FINISHED'}

    def initiate_overlay_settings(self, context, shading, overlay, debug=False):
        if not context.scene.M4.get('show_overlay_prefs', False):
            if debug:
                print("initiating overlays prefs on scene object")

            context.scene.M4['show_overlay_prefs'] = {'SOLID': True,
                                                      'MATERIAL': False,
                                                      'RENDERED': False,
                                                      'WIREFRAME': True}

        self.prefs = context.scene.M4['show_overlay_prefs']

        if overlay.show_overlays != self.prefs[shading.type]:
            self.prefs[shading.type] = overlay.show_overlays
            print("INFO: Corrected out-of-sync Overlay Visibility setting!")

    def adjust_lights(self, scene, new_shading_type, debug=False):
        m3 = scene.M4

        last = m3.adjust_lights_on_render_last

        if last in ['NONE', 'INCREASE'] and new_shading_type == 'RENDERED' and scene.render.engine == 'CYCLES':
            m3.adjust_lights_on_render_last = 'DECREASE'

            if debug:
                print("decreasing on switch to cycies rendering")

            adjust_lights_for_rendering(mode='DECREASE')

        elif last == 'DECREASE' and new_shading_type == 'MATERIAL':
            m3.adjust_lights_on_render_last = 'INCREASE'

            if debug:
                print("increasing on switch to material shading")

            adjust_lights_for_rendering(mode='INCREASE')

    def enforce_render_visibility(self, context, new_shading_type, debug=False):
        global render_visibility

        if new_shading_type == 'RENDERED':
            render_visibility = [(obj, obj.name) for obj in context.visible_objects if obj.hide_render == True and obj.visible_get()]

            for obj, name in render_visibility:
                obj.hide_set(True)
        else:

            for obj, name in render_visibility:
                obj = bpy.data.objects.get(name)

                if obj:
                    obj.hide_set(False)
                else:
                    print(_("WARNING: Object {} could no longer be found".format(name)))

            render_visibility = []

class ToggleOutline(bpy.types.Operator):
    bl_idname = "m4a1.toggle_outline"
    bl_label = "Toggle Outline"
    bl_description = "Toggle Object Outlines"
    bl_options = {'REGISTER'}

    def execute(self, context):
        shading = context.space_data.shading

        shading.show_object_outline = not shading.show_object_outline

        return {'FINISHED'}

class ToggleCavity(bpy.types.Operator):
    bl_idname = "m4a1.toggle_cavity"
    bl_label = "Toggle Cavity"
    bl_description = "Toggle Cavity (Screen Space Ambient Occlusion)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene

        scene.M4.show_cavity = not scene.M4.show_cavity

        return {'FINISHED'}

class ToggleCurvature(bpy.types.Operator):
    bl_idname = "m4a1.toggle_curvature"
    bl_label = "Toggle Curvature"
    bl_description = "Toggle Curvature (Edge Highlighting)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene

        scene.M4.show_curvature = not scene.M4.show_curvature

        return {'FINISHED'}

class MatcapSwitch(bpy.types.Operator):
    bl_idname = "m4a1.matcap_switch"
    bl_label = "Matcap Switch"
    bl_description = "Quickly Switch between two Matcaps"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if context.space_data.type == 'VIEW_3D':
            shading = context.space_data.shading
            return shading.type == "SOLID" and shading.light == "MATCAP"

    def execute(self, context):
        view = context.space_data
        shading = view.shading

        matcap1 = get_prefs().switchmatcap1
        matcap2 = get_prefs().switchmatcap2

        switch_background = get_prefs().matcap_switch_background

        force_single = get_prefs().matcap2_force_single
        global matcap1_color_type

        disable_overlays = get_prefs().matcap2_disable_overlays

        if matcap1 and matcap2 and "NOT FOUND" not in [matcap1, matcap2]:
            if shading.studio_light == matcap1:
                shading.studio_light = matcap2

                if switch_background:
                    shading.background_type = get_prefs().matcap2_switch_background_type

                    if get_prefs().matcap2_switch_background_type == 'VIEWPORT':
                        shading.background_color = get_prefs().matcap2_switch_background_viewport_color

                if force_single and shading.color_type != 'SINGLE':
                    matcap1_color_type = shading.color_type
                    shading.color_type = 'SINGLE'

                if disable_overlays and view.overlay.show_overlays:
                    view.overlay.show_overlays = False

            elif shading.studio_light == matcap2:
                shading.studio_light = matcap1

                if switch_background:
                    shading.background_type = get_prefs().matcap1_switch_background_type

                    if get_prefs().matcap1_switch_background_type == 'VIEWPORT':
                        shading.background_color = get_prefs().matcap1_switch_background_viewport_color

                if force_single and matcap1_color_type:
                    shading.color_type = matcap1_color_type
                    matcap1_color_type = None

                if disable_overlays and not view.overlay.show_overlays:
                    view.overlay.show_overlays = True

            else:
                shading.studio_light = matcap1

        return {'FINISHED'}

class RotateStudioLight(bpy.types.Operator):
    bl_idname = "m4a1.rotate_studiolight"
    bl_label = "M4A1: Rotate Studiolight"
    bl_options = {'REGISTER', 'UNDO'}

    angle: IntProperty(name="Angle")

    @classmethod
    def description(cls, context, properties):
        return _("Rotate Studio Light by {} degrees\nALT: Rotate visible lights too").format(int(properties.angle))

    def invoke(self, context, event):
        current = degrees(context.space_data.shading.studiolight_rotate_z)
        new = (current + self.angle)

        if new > 360:
            new = new % 360

        if new > 180:
            new = -180 + (new - 180)

        context.space_data.shading.studiolight_rotate_z = radians(new)

        if event.alt:
            rmx = Matrix.Rotation(radians(self.angle), 4, 'Z')
            lights = [obj for obj in context.visible_objects if obj.type == 'LIGHT']

            for light in lights:
                light.matrix_world = rmx @ light.matrix_world

        return {'FINISHED'}

class AddWorld(bpy.types.Operator):
    bl_idname = "m4a1.add_world"
    bl_label = "M4A1: Add World"
    bl_description = "M4A1: Add World"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.scene:
            return not context.scene.world

    def execute(self, context):

        if bpy.data.worlds:
            context.scene.world = bpy.data.worlds[0]

        else:
            world = bpy.data.worlds.new(name="World")
            world.use_nodes = True
            context.scene.world = world

        return {'FINISHED'}

class AdjustBevelShaderRadius(bpy.types.Operator):
    bl_idname = "m4a1.adjust_bevel_shader_radius"
    bl_label = "M4A1: Adjust Bevel Radius"
    bl_options = {'REGISTER', 'UNDO'}

    global_radius: BoolProperty(name=_("Adjust Global Bevel Radius"), default=True)
    decrease: BoolProperty(name=_("Decrease Radius"), default=True)
    factor: FloatProperty()

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return True

    @classmethod
    def description(cls, context, properties):
        desc = _("\n{} {} Bevel Radius").format('Halve' if properties.decrease else 'Double','Global' if properties.global_radius else '''Active Objects's''')
        desc += _("\nSHIFT: {} {} Bevel Radius").format('-25%' if properties.decrease else '+33%','Global' if properties.global_radius else '''Active Objects's''')
        return desc

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

    def invoke(self, context, event):
        active = context.active_object

        if not self.global_radius and not active: 
            return {'CANCELLED'}

        if event.shift:
            self.factor = 3 / 4 if self.decrease else 4 / 3

        else:
            self.factor = 1 / 2 if self.decrease else 2

        return self.execute(context)

    def execute(self, context):
        active = context.active_object

        if self.global_radius:
            context.scene.M4.bevel_shader_radius *= self.factor

        else:
            active.M4.bevel_shader_radius_mod *= self.factor

        return {'FINISHED'}
