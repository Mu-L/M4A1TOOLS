import bpy
from bpy.props import StringProperty
from bpy.app.translations import pgettext as _
class SetTransformPreset(bpy.types.Operator):
    bl_idname = "m4a1.set_transform_preset"
    bl_label = "M4A1: Set Transform Preset"
    bl_description = "Set Transform Pivot and Orientation at the same time."
    bl_options = {'REGISTER', 'UNDO'}

    pivot: StringProperty(name=_("Transform Pivot"))
    orientation: StringProperty(name=_("Transform Orientation"))

    def draw(self, context):
        layout = self.layout
        column = layout.column()

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'VIEW_3D'

    def execute(self, context):
        context.scene.tool_settings.transform_pivot_point = self.pivot
        context.scene.transform_orientation_slots[0].type = self.orientation

        return {'FINISHED'}
