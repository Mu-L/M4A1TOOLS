import bpy
from bpy.types import Operator
from mathutils import Vector


class MoveProperty:

    def __init__(self):
        self.event = None

    @property
    def is_right_mouse(self):
        return self.event.type == 'RIGHTMOUSE'

    @property
    def is_release(self):
        return self.event.value == 'RELEASE'

    @property
    def is_exit(self):
        return self.is_release or self.is_right_mouse


def move(context, event):
    vector = None
    value = context.scene.M4.control_move_offset
    if event.type == 'UP_ARROW':
        vector = Vector((0, value, 0))
    elif event.type == 'DOWN_ARROW':
        vector = Vector((0, -value, 0))
    elif event.type == 'LEFT_ARROW':
        vector = Vector((-value, 0, 0))
    elif event.type == 'RIGHT_ARROW':
        vector = Vector((value, 0, 0))
    elif event.type == 'NUMPAD_PLUS':
        vector = Vector((0, 0, value))
    elif event.type == 'NUMPAD_MINUS':
        vector = Vector((0, 0, -value))

    obj = context.object
    if (vector is not None) and (context.object is not None):
        region_3d = context.space_data.region_3d
        view_matrix = region_3d.view_matrix.inverted()
        view_quat = view_matrix.to_quaternion().to_matrix().to_4x4()
        matrix = view_quat @ view_quat.Translation(vector)

        obj.matrix_world @= matrix
        obj.matrix_world @= view_quat.inverted()


class MoveOperator(Operator, MoveProperty):
    bl_idname = "m4a1.control_move"
    bl_description = "Move Control"
    bl_label = "Move Control"

    def __init__(self):
        super().__init__()
        self.timer = None
        self.event = None

    def invoke(self, context, event):
        wm = context.window_manager
        self.timer = wm.event_timer_add(1 / 60, window=context.window)
        wm.modal_handler_add(self)
        move(context, event)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.event = event

        if self.is_exit:
            context.window_manager.event_timer_remove(self.timer)
            return {'FINISHED', 'PASS_THROUGH'}
        move(context, event)
        return {'RUNNING_MODAL'}

