import bpy
from mathutils import Matrix
from math import radians
from .. utils.registration import get_prefs

class GizmoGroupGroupTransform(bpy.types.GizmoGroup):
    bl_idname = "M4N1_GGT_group_transform"
    bl_label = "Group Transform Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'SCALE', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        if get_prefs().activate_group:
            if context.mode == 'OBJECT':
                if context.scene.M4.show_group_gizmos:
                    return [obj for obj in context.visible_objects if obj.M4.is_group_empty and obj.M4.show_group_gizmo]

    def setup(self, context):
        self.group_gizmos = self.create_group_empty_gizmos(context)

    def refresh(self, context):

        if not self.is_modal():
            self.gizmos.clear()
            self.group_gizmos = self.create_group_empty_gizmos(context)

    def draw_prepare(self, context):

        if self.is_modal():
            for gzm in self.gizmos:

                if gzm.is_modal:
                    gzm.line_width = 1
                    gzm.arc_inner_factor = 0.4
                    gzm.draw_options = {'ANGLE_VALUE'}

                else:
                    gzm.hide = True

        else:
            for name, axes in self.group_gizmos.items():
                for gzm in axes.values():
                    gzm.draw_options = {'CLIP' if len(axes.values()) > 1 else 'ANGLE_START_Y'}

    def is_modal(self):
        return any(gzm.is_modal for gzm in self.gizmos)

    def create_group_empty_gizmos(self, context):
        group_gizmos = {}

        group_empties = [obj for obj in context.visible_objects if obj.M4.is_group_empty and obj.M4.show_group_gizmo]

        for empty in group_empties:
            gizmos = {}

            for axis in self.get_group_axes(empty):
                gzm = self.create_rotation_gizmo(context, empty, axis=axis, scale=5, line_width=2, alpha=0.25, alpha_highlight=1, hover=False)

                gizmos[axis] = gzm

            group_gizmos[empty.name] = gizmos

        return group_gizmos

    def get_group_axes(self, group_empty):
        axes = []

        if group_empty.M4.show_group_x_rotation:
            axes.append('X')

        if group_empty.M4.show_group_y_rotation:
            axes.append('Y')

        if group_empty.M4.show_group_z_rotation:
            axes.append('Z')

        return axes

    def create_rotation_gizmo(self, context, empty, axis='Z', scale=5, line_width=2, alpha=0.5, alpha_highlight=1, hover=False):
        gzm = self.gizmos.new("GIZMO_GT_dial_3d")

        op = gzm.target_set_operator("m4n1.transform_group")
        op.name = empty.name
        op.axis = axis

        gzm.matrix_basis = empty.matrix_world @ self.get_gizmo_rotation_matrix(axis)

        gzm.draw_options = {'ANGLE_START_Y'}
        gzm.use_draw_value = True
        gzm.use_draw_hover = hover

        gzm.line_width = line_width

        gzm.scale_basis = context.scene.M4.group_gizmo_size * empty.M4.group_size * empty.M4.group_gizmo_size * scale

        gzm.color = (1, 0.3, 0.3) if axis == 'X' else (0.3, 1, 0.3) if axis == 'Y' else (0.3, 0.3, 1)
        gzm.alpha = alpha
        gzm.color_highlight = (1, 0.5, 0.5) if axis == 'X' else (0.5, 1, 0.5) if axis == 'Y' else (0.5, 0.5, 1)
        gzm.alpha_highlight = alpha_highlight

        return gzm

    def get_gizmo_rotation_matrix(self, axis):
        if axis == 'X':
            return Matrix.Rotation(radians(90), 4, 'Y')

        if axis == 'Y':
            return Matrix.Rotation(radians(-90), 4, 'X')

        elif axis == 'Z':
            return Matrix()
