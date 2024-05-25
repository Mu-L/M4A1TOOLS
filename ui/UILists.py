import bpy
from .. utils.math import dynamic_format
from .. utils.ui import get_icon
from bpy.app.translations import pgettext as _
class AppendMatsUIList(bpy.types.UIList):
    bl_idname = "M4N1_UL_append_mats"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.split(factor=0.7)
        row.label(text=item.name)

class GroupPosesUIList(bpy.types.UIList):
    bl_idname = "M4N1_UL_group_poses"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        isactive = data.group_pose_IDX == index

        split = layout.split(factor=0.6)

        s = split.split(factor=0.15)
        s.prop(item, 'batchlinked', text='', icon='LINKED' if item.batchlinked else 'UNLINKED', emboss=False) if item.batch else s.separator()
        s.prop(item, "name", emboss=False, text="")

        row = split.row(align=True)

        if item.axis:
            row.label(text='', icon_value=get_icon(f"axis_{item.axis.lower()}"))
            row.label(text=f"{dynamic_format(item.angle, decimal_offset=1)}°")

        row = layout.row()

        row.alert = item.name == _('Inception')
        row.operator('m4n1.retrieve_group_pose', text='', icon='ARMATURE_DATA', emboss=False).index = index
        row.alert = False

        r = row.row(align=True)

        if isactive:
            op = r.operator('m4n1.sort_group_pose', text='', icon='TRIA_UP', emboss=False)
            op.direction = 'UP'
            op.index = index

            op = r.operator('m4n1.sort_group_pose', text='', icon='TRIA_DOWN', emboss=False)
            op.direction = 'DOWN'
            op.index = index

        else:
            r.label(text='', icon='BLANK1')
            r.label(text='', icon='BLANK1')

        layout.operator('m4n1.remove_group_pose', text='', icon='X', emboss=False).index = index
