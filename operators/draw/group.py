import bpy
from bpy.props import FloatProperty, FloatVectorProperty, BoolProperty
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d
from ... utils.draw import draw_circle
from ... utils.ui import get_zoom_factor, init_timer_modal, set_countdown, get_timer_progress
from ... utils.registration import get_prefs
from ... colors import white, blue
from bpy.app.translations import pgettext as _
class DrawGroupRestPose(bpy.types.Operator):
    bl_idname = "m4n1.draw_group_rest_pose"
    bl_label = "M4N1: Draw Group Rest Pose"
    bl_options = {'INTERNAL'}

    location: FloatVectorProperty(name="Location", subtype='TRANSLATION', default=Vector((0, 0, 0)))
    size: FloatProperty(name="Size", default=1)
    time: FloatProperty(name=_("Time (s)"), default=1)
    alpha: FloatProperty(name="Alpha", default=0.3, min=0.1, max=1)
    reverse: BoolProperty(name=_("Reverse the Motion"), default=False)
    def draw_HUD(self, context):
        alpha = get_timer_progress(self) * self.alpha * (5 if self.reverse else 1)
        scale = get_timer_progress(self) * 5

        if self.reverse:
            scale = 2 / scale

        location2d, zoom_factor = self.get_location2d_and_zoom_factor(context, self.location)
        draw_circle(location2d, radius=scale * (self.size / zoom_factor), width=5, color = blue if self.reverse else white, alpha=alpha)

    def modal(self, context, event):
        context.area.tag_redraw()

        if self.countdown < 0:
            self.finish(context)
            return {'FINISHED'}

        if event.type == 'TIMER':
            set_countdown(self)

        return {'PASS_THROUGH'}

    def finish(self, context):
        context.window_manager.event_timer_remove(self.TIMER)
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

    def execute(self, context):
        self.time = get_prefs().HUD_fade_group / 3
        init_timer_modal(self)

        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.TIMER = context.window_manager.event_timer_add(0.01, window=context.window)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def get_location2d_and_zoom_factor(self, context, location):
        location2d = location_3d_to_region_2d(context.region, context.region_data, coord=location)
        zoom_factor = get_zoom_factor(context, location, scale=10)
        return location2d, zoom_factor
