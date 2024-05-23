import bpy
from bpy.props import PointerProperty

from .ui.operators.old_modifier import old_modifier
from .properties import Mirror_Settings
from .ui.operators import mirror_vg as mirror_vg_py
#镜像顶点组
REG_MIRROR_VG_TAG=False
def reg_mirror_vg():

    global REG_MIRROR_VG_TAG
    if not REG_MIRROR_VG_TAG:
        bpy.types.Object.mirror_settings = PointerProperty(type=Mirror_Settings)
        mirror_vg_py.register()
        REG_MIRROR_VG_TAG=True
def unreg_mirror_vg():
    global REG_MIRROR_VG_TAG
    try:
        del bpy.types.Object.mirror_settings
        mirror_vg_py.unregister()
    except:pass
    REG_MIRROR_VG_TAG=False
#老版修改器
REG_OLD_MODIFIER_TAG=False
def reg_old_modifier():

    global REG_OLD_MODIFIER_TAG
    if not REG_OLD_MODIFIER_TAG:
        bpy.types.DATA_PT_modifiers.append(old_modifier)
        REG_OLD_MODIFIER_TAG=True
def unreg_old_modifier():
    global REG_OLD_MODIFIER_TAG
    try:
        bpy.types.DATA_PT_modifiers.remove(old_modifier)
    except:pass
    REG_OLD_MODIFIER_TAG=False

#波浪修改器
REG_WAVE_MODI_TAG=False
def reg_wave_modi():
    global REG_WAVE_MODI_TAG
    if not REG_WAVE_MODI_TAG:
        from .properties import ModifierProper
        bpy.types.Object.wave_modifiers_helper = PointerProperty(type=ModifierProper)
        REG_WAVE_MODI_TAG=True
def unreg_wave_modi():
    global REG_WAVE_MODI_TAG
    try:
        del bpy.types.Object.ModifierProper
    except:pass
    REG_WAVE_MODI_TAG=False
# 晶格
REG_LATTICE_MODI_TAG=False
def reg_lattice_modi():
    global REG_LATTICE_MODI_TAG
    if not REG_LATTICE_MODI_TAG:
        from .ui.npanels.lattice_helper import menu_register
        menu_register()
        REG_LATTICE_MODI_TAG=True
def unreg_lattice_modi():
    global REG_LATTICE_MODI_TAG
    try:
        from .ui.npanels.lattice_helper import menu_unregister
        menu_unregister()
    except:
        pass
    REG_LATTICE_MODI_TAG=False

# 简易型变
REG_SIMPLE_MODI_TAG=False
def reg_simple_modi():
    from .ui.npanels.simple_deform_helper import register as simple_ui_reg
    from .utils.simple_deform_helper import register as simple_utils_reg
    from .utils.simple_deform_helper_update import register as simple_utils_update_reg
    from .ui.sdh_gizmo.__init__ import register as simple_gizmo_reg
    from .utils.simple_deform_helper import GizmoUtils
    from .properties import SimpleDeformGizmoObjectPropertyGroup
    from .preferences import MACHIN4toolsPreferences
    global REG_SIMPLE_MODI_TAG
    if not REG_SIMPLE_MODI_TAG:
        simple_ui_reg()
        simple_utils_reg()
        simple_utils_update_reg()
        simple_gizmo_reg()
        GizmoUtils.pref_().sdh_display_bend_axis_switch_gizmo = False
        bpy.types.Object.SimpleDeformGizmo_PropertyGroup = PointerProperty(
            type=SimpleDeformGizmoObjectPropertyGroup,
            name='SimpleDeformGizmo_PropertyGroup')
        bpy.types.VIEW3D_MT_editor_menus.append(
            MACHIN4toolsPreferences.draw_header_tool_settings)
        REG_SIMPLE_MODI_TAG=True
def unreg_simple_modi():
    global REG_SIMPLE_MODI_TAG
    try:
        from .ui.npanels.simple_deform_helper import unregister as simple_ui_unreg
        simple_ui_unreg()
        from .utils.simple_deform_helper import unregister as simple_utils_unreg
        simple_utils_unreg()
        from .utils.simple_deform_helper_update import register as simple_utils_update_unreg
        simple_utils_update_unreg()
        from .ui.sdh_gizmo.__init__ import unregister as simple_gizmo_unreg
        simple_gizmo_unreg()
        # 删除属性
        from .preferences import MACHIN4toolsPreferences
        del bpy.types.Object.SimpleDeformGizmo_PropertyGroup
        bpy.types.VIEW3D_MT_editor_menus.remove(
            MACHIN4toolsPreferences.draw_header_tool_settings)
    except:
        pass

    REG_SIMPLE_MODI_TAG=False

#对齐助手
REG_ALIGN_HELPER_TAG=False
def reg_align_helper():
    global REG_ALIGN_HELPER_TAG
    if not REG_ALIGN_HELPER_TAG:
        from .icons.aliogn_helper.icon import register as ah_icon_reg
        ah_icon_reg()
        # from .ui.npanels.align_helper import register as ah_np_reg
        # ah_np_reg()
        REG_ALIGN_HELPER_TAG=True
def unreg_align_helper():
    global REG_ALIGN_HELPER_TAG
    try:
        from .icons.aliogn_helper.icon import unregister as ah_icon_unreg
        ah_icon_unreg()
        # from .ui.npanels.align_helper import unregister as ah_np_unreg
        # ah_np_unreg()
    except:pass
    REG_ALIGN_HELPER_TAG=False

def reg_and_update():
    from .utils.registration import get_prefs
    # 老版修改器
    if get_prefs().activate_old_modifier:
        reg_old_modifier()
    # 镜像顶点组
    if get_prefs().activate_mirror_vg:

        reg_mirror_vg()

    # 波浪
    if get_prefs().activate_wave_modifier:

        reg_wave_modi()

    # 晶格
    if get_prefs().activate_lattice_helper:

        reg_lattice_modi()

    # 简易形变
    if get_prefs().activate_simple_deform_helper:

        reg_simple_modi()

    if get_prefs().activate_align_helper_pie:

        reg_align_helper()
def unreg_and_update(unreg_addon=False):
    from .utils.registration import get_prefs
    # 老版修改器
    if not get_prefs().activate_old_modifier or unreg_addon:
        unreg_old_modifier()
    # 镜像权重
    if not get_prefs().activate_mirror_vg or unreg_addon:
        unreg_mirror_vg()

    if not get_prefs().activate_wave_modifier or unreg_addon:
        unreg_wave_modi()

    # 晶格
    if not get_prefs().activate_lattice_helper or unreg_addon:
        unreg_lattice_modi()

    # 简易型变
    if not get_prefs().activate_simple_deform_helper or unreg_addon:
        unreg_simple_modi()

    # align helper
    if not get_prefs().activate_align_helper_pie or unreg_addon:
        unreg_align_helper()