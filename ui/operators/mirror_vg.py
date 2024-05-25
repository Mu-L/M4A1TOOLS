import bpy
from bpy.props import PointerProperty
preview_collections = {}


def is_interface():
    return bpy.context.preferences.view.use_translate_interface


def is_cn():
    return bpy.context.preferences.view.language in ('zh_CN', 'zh_HANS') and is_interface()


def select_icon():
    # from . import preview_collections

    if is_cn():
        return preview_collections['main']['xuan_icon'].icon_id
    else:
        return preview_collections['main']['selected_icon'].icon_id


def multiple_icon():
    # from . import preview_collections

    if is_cn():
        return preview_collections['main']['duo_icon'].icon_id
    else:
        return preview_collections['main']['multiple_icon'].icon_id


def sna_add_to_data_pt_vertex_groups(self, context):
    layout = self.layout
    column = layout.column(heading='', align=False)

    obj_prop = context.object.mirror_settings
    row = layout.row(align=True)
    left_right = row.row(align=True)
    left_right.enabled = obj_prop.is_center or obj_prop.is_multiple
    left_right.prop(obj_prop, 'left_right', expand=True, text='')

    button = row.row(align=True)

    button.prop(obj_prop, 'is_center', text='', toggle=True, icon_value=446)
    button.operator('m4a1.vg_mirror_weight', text='Mirror weights', icon_value=0)

    button.prop(obj_prop, 'is_multiple', text='', icon_value=multiple_icon())
    select = row.row(align=True)
    select.prop(obj_prop, 'is_selected', text='', icon_value=select_icon())
    select.enabled = obj_prop.is_multiple
    row.row(align=True).prop(obj_prop, 'mirror_method', text='', icon_value=30)

    split = column.split(align=True)
    split.operator('m4a1.vg_clear_unused', text='Clear unused')
    split.operator('m4a1.vg_remove_zero', text='Clear zero')
# 脚本目录
import os
script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
# 图标目录
icons_dir = os.path.join(script_dir, "icons")


def load_icon(icon_name, icon_path, pcoll):
    """ 加载并注册一个图标 """
    pcoll.load(icon_name, icon_path, 'IMAGE')

def register():


    bpy.types.DATA_PT_vertex_groups.append(sna_add_to_data_pt_vertex_groups)
    # icon
    global preview_collections
    pcoll = bpy.utils.previews.new()
    # 加载多个图标
    load_icon("duo_icon", os.path.join(icons_dir, "duo.png"), pcoll)
    load_icon("xuan_icon", os.path.join(icons_dir, "xuan.png"), pcoll)
    load_icon("multiple_icon", os.path.join(icons_dir, "multiple.png"), pcoll)
    load_icon("selected_icon", os.path.join(icons_dir, "selected.png"), pcoll)
    preview_collections["main"] = pcoll


def unregister():
    bpy.types.DATA_PT_vertex_groups.remove(sna_add_to_data_pt_vertex_groups)
    for pcoll in preview_collections.values():
        # print('镜像顶点组',pcoll)
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
