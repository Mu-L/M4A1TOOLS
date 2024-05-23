from sys import dont_write_bytecode
import bpy
from bpy.props import IntProperty, StringProperty, BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty
import os
import shutil
from . import bl_info
from . utils.ui import get_icon, draw_keymap_items, get_keymap_item
from . utils.registration import activate, get_path, get_name, get_addon
from . utils.draw import draw_split_row
from . utils.simple_deform_helper import GizmoUtils
from . utils.system import get_bl_info_from_file, remove_folder, get_update_files
from . items import preferences_tabs, matcap_background_type_items

decalmachine = None
meshmachine = None
punchit = None
curvemachine = None
hypercursor = None

has_sidebar = ['OT_smart_drive',
               'OT_group',
               'OT_create_assembly_asset',
               'OT_prepare_unity_export']

has_hud = ['OT_material_picker',
           'OT_surface_slide',
           'OT_clean_up',
           'OT_clipping_toggle',
           'OT_group',
           'OT_transform_edge_constrained',
           'OT_focus',
           'OT_select_hierarchy',
           'MT_tools_pie',
           'OT_mirror']

is_fading = ['OT_clean_up',
             'OT_clipping_toggle',
             'OT_group',
             'OT_select_hierarchy',
             'MT_tools_pie']

has_settings = has_sidebar + has_hud + ['OT_smart_vert',
                                        'OT_clean_up',
                                        'OT_punch_it',
                                        'OT_transform_edge_constrained',
                                        'OT_focus',
                                        'OT_group',
                                        'OT_render',
                                        'OT_create_assembly_asset',
                                        'OT_clipping_toggle',
                                        'OT_surface_slide',
                                        'OT_material_picker',
                                        'OT_clipping_toggle',
                                        'OT_customize',
                                 
                                        'MT_modes_pie',
                                        'MT_save_pie',
                                        'MT_shading_pie',
                                        'MT_cursor_pie',
                                        'MT_snapping_pie',
                                        'MT_viewport_pie',
                                        'MT_tools_pie']

has_skribe = None
has_screencast_keys = None

class MACHIN4toolsPreferences(bpy.types.AddonPreferences, GizmoUtils):
    path = get_path()
    bl_idname = get_name()

    def update_update_path(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.update_path:
            if os.path.exists(self.update_path):
                filename = os.path.basename(self.update_path)

                if filename.endswith('.zip'):
                    split = filename.split('_')

                    if len(split) == 2:
                        addon_name, tail = split

                        if addon_name == bl_info['name']:
                            split = tail.split('.')

                            if len(split) >= 3:
                                dst = os.path.join(self.path, '_update')

                                from zipfile import ZipFile

                                with ZipFile(self.update_path, mode="r") as z:
                                    print(f"INFO: extracting {addon_name} update to {dst}")
                                    z.extractall(path=dst)

                                blinfo = get_bl_info_from_file(os.path.join(dst, addon_name, '__init__.py'))

                                if blinfo:
                                    self.update_msg = f"{blinfo['name']} {'.'.join(str(v) for v in blinfo['version'])} is ready to be installed."

                                else:
                                    remove_folder(dst)

            self.avoid_update = True
            self.update_path = ''

    update_path: StringProperty(name="Update File Path", subtype="FILE_PATH", update=update_update_path)
    update_msg: StringProperty(name="Update Message")

    registration_debug: BoolProperty(name="Addon Terminal Registration Output", default=True)

    def update_switchmatcap1(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        matcaps = [mc.name for mc in context.preferences.studio_lights if os.path.basename(os.path.dirname(mc.path)) == "matcap"]
        if self.switchmatcap1 not in matcaps:
            self.avoid_update = True
            self.switchmatcap1 = "NOT FOUND"

    def update_switchmatcap2(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        matcaps = [mc.name for mc in context.preferences.studio_lights if os.path.basename(os.path.dirname(mc.path)) == "matcap"]
        if self.switchmatcap2 not in matcaps:
            self.avoid_update = True
            self.switchmatcap2 = "NOT FOUND"

    def update_custom_preferences_keymap(self, context):
        if self.custom_preferences_keymap:
            kc = context.window_manager.keyconfigs.user

            for km in kc.keymaps:
                if km.is_user_modified:
                    self.custom_preferences_keymap = False
                    self.dirty_keymaps = True
                    return

            self.dirty_keymaps = False

    def update_auto_smooth_angle_presets(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        try:
            angles = [int(a) for a in self.auto_smooth_angle_presets.split(',')]
        except:
            self.avoid_update = True
            self.auto_smooth_angle_presets = "10, 15, 20, 30, 60, 180"

    def update_activate_smart_vert(self, context):
        activate(self, register=self.activate_smart_vert, tool="smart_vert")

    def update_activate_smart_edge(self, context):
        activate(self, register=self.activate_smart_edge, tool="smart_edge")

    def update_activate_smart_face(self, context):
        activate(self, register=self.activate_smart_face, tool="smart_face")
    def update_activate_old_modifier(self, context):
        from .aigodlike_tool_reg import reg_old_modifier,unreg_old_modifier
        if self.activate_old_modifier:
            reg_old_modifier()
        else:
            unreg_old_modifier()
    def update_activate_mirror_vg(self, context):
        activate(self, register=self.activate_mirror_vg, tool="mirror_vg")

    # def update_activate_meshdeform_helper(self, context):
    #     activate(self, register=self.activate_meshdeform_helper, tool="meshdeform_helper")
    def update_activate_simple_deform_helper(self, context):
        activate(self, register=self.activate_simple_deform_helper, tool="simple_deform_helper")
    def update_activate_lattice_helper(self, context):
        activate(self, register=self.activate_lattice_helper, tool="lattice_helper")
    def update_activate_wave_modifier(self, context):
        from .aigodlike_tool_reg import reg_wave_modi,unreg_wave_modi
        if self.activate_wave_modifier:
            reg_wave_modi()
        else:
            unreg_wave_modi()
        # activate(self, register=self.activate_wave_modifier, tool="wave_modifier")
    def update_activate_clean_up(self, context):
        activate(self, register=self.activate_clean_up, tool="clean_up")

    def update_activate_edge_constraint(self, context):
        activate(self, register=self.activate_edge_constraint, tool="edge_constraint")

    def update_activate_extrude(self, context):
        activate(self, register=self.activate_extrude, tool="extrude")

    def update_activate_focus(self, context):
        activate(self, register=self.activate_focus, tool="focus")

    def update_activate_mirror(self, context):
        activate(self, register=self.activate_mirror, tool="mirror")

    def update_activate_align(self, context):
        activate(self, register=self.activate_align, tool="align")

    def update_activate_group(self, context):
        activate(self, register=self.activate_group, tool="group")

    def update_activate_smart_drive(self, context):
        activate(self, register=self.activate_smart_drive, tool="smart_drive")

    def update_activate_assetbrowser_tools(self, context):
        activate(self, register=self.activate_assetbrowser_tools, tool="assetbrowser")

    def update_activate_filebrowser_tools(self, context):
        activate(self, register=self.activate_filebrowser_tools, tool="filebrowser")

    def update_activate_render(self, context):
        activate(self, register=self.activate_render, tool="render")

    def update_activate_smooth(self, context):
        activate(self, register=self.activate_smooth, tool="smooth")

    def update_activate_clipping_toggle(self, context):
        activate(self, register=self.activate_clipping_toggle, tool="clipping_toggle")

    def update_activate_surface_slide(self, context):
        activate(self, register=self.activate_surface_slide, tool="surface_slide")

    def update_activate_material_picker(self, context):
        activate(self, register=self.activate_material_picker, tool="material_picker")

    def update_activate_apply(self, context):
        activate(self, register=self.activate_apply, tool="apply")

    def update_activate_select(self, context):
        activate(self, register=self.activate_select, tool="select")

    def update_activate_mesh_cut(self, context):
        activate(self, register=self.activate_mesh_cut, tool="mesh_cut")

    def update_activate_region(self, context):
        activate(self, register=self.activate_region, tool="region")

    def update_activate_thread(self, context):
        activate(self, register=self.activate_thread, tool="thread")

    def update_activate_unity(self, context):
        activate(self, register=self.activate_unity, tool="unity")

    def update_activate_customize(self, context):
        activate(self, register=self.activate_customize, tool="customize")

    def update_activate_modes_pie(self, context):
        activate(self, register=self.activate_modes_pie, tool="modes_pie")

    def update_activate_save_pie(self, context):
        activate(self, register=self.activate_save_pie, tool="save_pie")

    def update_activate_shading_pie(self, context):
        activate(self, register=self.activate_shading_pie, tool="shading_pie")

    def update_activate_views_pie(self, context):
        activate(self, register=self.activate_views_pie, tool="views_pie")

    def update_activate_align_pie(self, context):
        activate(self, register=self.activate_align_pie, tool="align_pie")

    def update_activate_align_helper_pie(self, context):
        activate(self, register=self.activate_align_helper_pie, tool="align_helper_pie")

    def update_activate_cursor_pie(self, context):
        activate(self, register=self.activate_cursor_pie, tool="cursor_pie")

    def update_activate_transform_pie(self, context):
        activate(self, register=self.activate_transform_pie, tool="transform_pie")

    def update_activate_snapping_pie(self, context):
        activate(self, register=self.activate_snapping_pie, tool="snapping_pie")

    def update_activate_collections_pie(self, context):
        activate(self, register=self.activate_collections_pie, tool="collections_pie")

    def update_activate_workspace_pie(self, context):
        activate(self, register=self.activate_workspace_pie, tool="workspace_pie")

    def update_activate_tools_pie(self, context):
        activate(self, register=self.activate_tools_pie, tool="tools_pie")

    focus_show: BoolProperty(name="Show Focus Preferences", default=False)
    focus_view_transition: BoolProperty(name="Viewport Tweening", default=True)
    focus_lights: BoolProperty(name="Ignore Lights (keep them always visible)", default=False)

    #lattice helper
    lh_show: BoolProperty(name="Show lattice helper Preferences", default=False)
    lh_def_res: bpy.props.IntVectorProperty(name="Default lattice resolution", default=[2, 2, 2], min=2, max=64)
    lh_items = [('KEY_LINEAR', 'Linear', ''),
             ('KEY_CARDINAL', 'Cardinal', ''),
             ('KEY_CATMULL_ROM', 'Catmull-Rom', ''),
             ('KEY_BSPLINE', 'BSpline', '')]
    lh_lerp: bpy.props.EnumProperty(name="Interpolation", items=lh_items, default='KEY_LINEAR')
    #simple deform helper
    sdh_show: BoolProperty(name="Show simple deform helper Preferences", default=False)
    sdh_deform_wireframe_color: FloatVectorProperty(
        name='Deform Wireframe',
        description='Draw Deform Wireframe Color',
        default=(1, 1, 1, 0.3),
        soft_max=1,
        soft_min=0,
        size=4, subtype='COLOR')
    sdh_bound_box_color: FloatVectorProperty(
        name='Bound Box',
        description='Draw Bound Box Color',
        default=(1, 0, 0, 0.5),
        soft_max=1,
        soft_min=0,
        size=4,
        subtype='COLOR')
    sdh_limits_bound_box_color: FloatVectorProperty(
        name='Upper and lower limit Bound Box Color',
        description='Draw Upper and lower limit Bound Box Color',
        default=(0.3, 1, 0.2, 0.5),
        soft_max=1,
        soft_min=0,
        size=4,
        subtype='COLOR')
    sdh_modifiers_limits_tolerance: FloatProperty(
        name='Upper and lower limit tolerance',
        description='Minimum value between upper and lower limits',
        default=0.05,
        max=1,
        min=0.0001
    )
    sdh_display_bend_axis_switch_gizmo: BoolProperty(
        name='Show Toggle Bend Axis Gizmo',
        default=False,
        options={'SKIP_SAVE'})
    sdh_update_deform_wireframe: BoolProperty(
        name='Show Deform Wireframe',
        default=False)
    sdh_show_set_axis_button: BoolProperty(
        name='Show Set Axis Button',
        default=False)
    sdh_show_gizmo_property_location: EnumProperty(
        name='Gizmo Property Show Location',
        items=[('ToolSettings', 'Tool Settings', ''),
               ('ToolOptions', 'Tool Options', ''),
               ],
        default='ToolSettings'
    )

    #align helper
    ah_show_text: BoolProperty(name='Show Button Text', default=True)

    group_show: BoolProperty(name="Show Group Preferences", default=False)
    group_auto_name: BoolProperty(name="Auto Name Groups", description="Automatically add a Prefix and/or Suffix to any user-set Group Name", default=True)
    group_basename: StringProperty(name="Group Basename", default="GROUP")
    group_prefix: StringProperty(name="Prefix to add to Group Names", default="_")
    group_suffix: StringProperty(name="Suffix to add to Group Names", default="_grp")
    group_size: FloatProperty(name="Group Empty Draw Size", description="Default Group Size", default=0.2)
    group_fade_sizes: BoolProperty(name="Fade Group Empty Sizes", description="Make Sub Group's Emtpies smaller than their Parents", default=True)
    group_fade_factor: FloatProperty(name="Fade Group Size Factor", description="Factor by which to decrease each Group Empty's Size", default=0.8, min=0.1, max=0.9)
    group_remove_empty: BoolProperty(name="Remove Empty Groups", description="Automatically remove Empty Groups in each Cleanup Pass", default=True)

    # assetbrowser_show: BoolProperty(name="Show Asset Browser Tools Preferences", default=False)
    preferred_default_catalog: StringProperty(name="Preferred Default Catalog", default="Model")
    preferred_assetbrowser_workspace_name: StringProperty(name="Preferred Workspace for Assembly Asset Creation", default="General.alt")
    show_assembly_asset_creation_in_save_pie: BoolProperty(name="Show Assembly Asset Creation in Save Pie", default=True)
    show_instance_collection_assembly_in_modes_pie: BoolProperty(name="Show Collection Instance Assembly in Modes Pie", default=True)
    hide_wire_objects_when_creating_assembly_asset: BoolProperty(name="Hide Wire Objects when creating Assembly Asset", default=True)
    hide_wire_objects_when_assembling_instance_collection: BoolProperty(name="Hide Wire Objects when assembling Collection Instance", default=True)

    # region_show: BoolProperty(name="Show Region Preferences", default=False)
    # region_prefer_left_right: BoolProperty(name="Prefer Left/Right over Bottom/Top", default=True)
    # region_close_range: FloatProperty(name="Close Range", subtype='PERCENTAGE', default=30, min=1, max=50)
    # region_toggle_assetshelf: BoolProperty(name="Toggle the Asset Shelf, instead of the Browser", default=False)
    # region_toggle_assetbrowser_top: BoolProperty(name="Toggle the Asset Browser at the Top", default=True)
    # region_toggle_assetbrowser_bottom: BoolProperty(name="Toggle the Asset Browser at the Bottom", default=True)
    # region_warp_mouse_to_asset_border: BoolProperty(name="Warp Mouse to Asset Browser Border", default=False)

    # render_show: BoolProperty(name="Show Render Preferences", default=False)
    # render_folder_name: StringProperty(name="Render Folder Name", description="Folder used to stored rended images relative to the Location of the .blend file", default='out')
    # render_seed_count: IntProperty(name="Seed Render Count", description="Set the Amount of Seed Renderings used to remove Fireflies", default=3, min=2, max=9)
    # render_keep_seed_renderings: BoolProperty(name="Keep Individual Renderings", description="Keep the individual Seed Renderings, after they've been combined into a single Image", default=False)
    # render_use_clownmatte_naming: BoolProperty(name="Use Clownmatte Name", description="""It's a better name than "Cryptomatte", believe me""", default=True)
    # render_show_buttons_in_light_properties: BoolProperty(name="Show Render Buttons in Light Properties Panel", description="Show Render Buttons in Light Properties Panel", default=True)
    # render_sync_light_visibility: BoolProperty(name="Sync Light visibility/renderability", description="Sync Light hide_render props based on hide_viewport props", default=True)
    # render_adjust_lights_on_render: BoolProperty(name="Ajust Area Lights when Rendering in Cycles", description="Adjust Area Lights when Rendering, to better match Eevee and Cycles", default=True)
    # render_enforce_hide_render: BoolProperty(name="Enforce hide_render setting when Viewport Rendering", description="Hide Objects based on their hide_render props, when Viewport Rendering with Cyclces", default=True)
    # render_use_bevel_shader: BoolProperty(name="Automatically set up Bevel Shader when Cycles Rendering", description="Set up Bevel Shader on all visible Materials when Cycles Renderings", default=True)

    # matpick_show: BoolProperty(name="Show Material Picker Preferences", default=False)
    # matpick_workspace_names: StringProperty(name="Workspaces the Material Picker should appear on", default="Shading, Material")
    # matpick_shading_type_material: BoolProperty(name="Show Material Picker in all Material Shading Viewports", default=True)
    # matpick_shading_type_render: BoolProperty(name="Show Material Picker in all Render Shading Viewports", default=False)
    # matpick_spacing_obj: FloatProperty(name="Object Mode Spacing", min=0, default=20)
    # matpick_spacing_edit: FloatProperty(name="Edit Mode Spacing", min=0, default=5)

    customize_show: BoolProperty(name="Show Customize Preferences", default=False)
    custom_startup: BoolProperty(name="Startup Scene", default=False)
    custom_theme: BoolProperty(name="Theme", default=True)
    custom_matcaps: BoolProperty(name="Matcaps", default=True)
    custom_shading: BoolProperty(name="Shading", default=False)
    custom_overlays: BoolProperty(name="Overlays", default=False)
    custom_outliner: BoolProperty(name="Outliner", default=False)
    custom_preferences_interface: BoolProperty(name="Preferences: Interface", default=False)
    custom_preferences_viewport: BoolProperty(name="Preferences: Viewport", default=False)
    custom_preferences_input_navigation: BoolProperty(name="Preferences: Input & Navigation", default=False)
    custom_preferences_keymap: BoolProperty(name="Preferences: Keymap", default=False, update=update_custom_preferences_keymap)
    custom_preferences_system: BoolProperty(name="Preferences: System", default=False)
    custom_preferences_save: BoolProperty(name="Preferences: Save & Load", default=False)

    modes_pie_show: BoolProperty(name="Show Modes Pie Preferences", default=False)
    toggle_cavity: BoolProperty(name="Toggle Cavity/Curvature OFF in Edit Mode, ON in Object Mode", default=True)
    toggle_xray: BoolProperty(name="Toggle X-Ray ON in Edit Mode, OFF in Object Mode, if Pass Through or Wireframe was enabled in Edit Mode", default=True)
    sync_tools: BoolProperty(name="Sync Tool if possible, when switching Modes", default=True)

    save_pie_show: BoolProperty(name="Show Save Pie", default=False)
    save_pie_show_obj_export: BoolProperty(name="Show .obj Export", default=True)
    save_pie_show_plasticity_export: BoolProperty(name="Show Plasticity Export", default=True)
    save_pie_show_fbx_export: BoolProperty(name="Show .fbx Export", default=True)
    save_pie_show_usd_export: BoolProperty(name="Show .usd Export", default=True)
    save_pie_show_stl_export: BoolProperty(name="Show .stl Export", default=False)
    fbx_export_apply_scale_all: BoolProperty(name="Use 'Fbx All' for Applying Scale", description="This is useful for Unity, but bad for Unreal Engine", default=False)
    show_screencast: BoolProperty(name="Show Screencast in Save Pie", description="Show Screencast in Save Pie", default=True)
    screencast_operator_count: IntProperty(name="Operator Count", description="Maximum number of Operators displayed when Screen Casting", default=12, min=1, max=100)
    screencast_fontsize: IntProperty(name="Font Size", default=12, min=2)
    screencast_highlight_m4n1: BoolProperty(name="Highlight M4N1 operators", description="Highlight Operators from M4N1 addons", default=True)
    screencast_show_addon: BoolProperty(name="Display Operator's Addons", description="Display Operator's Addon", default=True)
    screencast_show_idname: BoolProperty(name="Display Operator's idnames", description="Display Operator's bl_idname", default=False)
    screencast_use_skribe: BoolProperty(name="Use SKRIBE (dedicated, preferred)", default=True)
    screencast_use_screencast_keys: BoolProperty(name="Use Screencast Keys (addon)", default=True)
    save_pie_use_undo_save: BoolProperty(name="Make Pre-Undo Saving available in the Pie", default=False)

    shading_pie_show: BoolProperty(name="Show Shading Pie", default=False)
    align_helper_pie_show: BoolProperty(name="Align Helper Pie", default=False)
    overlay_solid: BoolProperty(name="Show Overlays in Solid Shading by default", description="For a newly created scene, or a .blend file where where it wasn't set before, show Overlays for Solid shaded 3D views", default=True)
    overlay_material: BoolProperty(name="Show Overlays in Material Shading by default", description="For a newly created scene, or a .blend file where where it wasn't set before, show Overlays for Material shaded 3D views", default=False)
    overlay_rendered: BoolProperty(name="Show Overlays in Rendered Shading by default", description="For a newly created scene, or a .blend file where where it wasn't set before, show Overlays for Rendered shaded 3D views", default=False)
    overlay_wire: BoolProperty(name="Show Overlays in Wire Shading by default", description="For a newly created scene, or a .blend file where where it wasn't set before, show Overlays for Wire shaded 3D views", default=True)
    switchmatcap1: StringProperty(name="Matcap 1", update=update_switchmatcap1)
    switchmatcap2: StringProperty(name="Matcap 2", update=update_switchmatcap2)
    matcap2_force_single: BoolProperty(name="Force Single Color Shading for Matcap 2", default=True)
    matcap2_disable_overlays: BoolProperty(name="Disable Overlays for Matcap 2", default=True)
    matcap_switch_background: BoolProperty(name="Switch Background too", default=False)
    matcap1_switch_background_type: EnumProperty(name="Matcap 1 Background Type", items=matcap_background_type_items, default="THEME")
    matcap1_switch_background_viewport_color: FloatVectorProperty(name="Matcap 1 Background Color", subtype='COLOR', default=[0.05, 0.05, 0.05], size=3, min=0, max=1)
    matcap2_switch_background_type: EnumProperty(name="Matcap 2 Background Type", items=matcap_background_type_items, default="THEME")
    matcap2_switch_background_viewport_color: FloatVectorProperty(name="Matcap 2 Background Color", subtype='COLOR', default=[0.05, 0.05, 0.05], size=3, min=0, max=1)
    auto_smooth_angle_presets: StringProperty(name="Autosmooth Angle Preset", default="10, 15, 20, 30, 60, 180", update=update_auto_smooth_angle_presets)

    views_pie_show: BoolProperty(name="Show Views Pie Preferences", default=False)
    obj_mode_rotate_around_active: BoolProperty(name="Rotate Around Selection, but only in Object Mode", default=False)
    custom_views_use_trackball: BoolProperty(name="Force Trackball Navigation when using Custom Views", default=True)
    custom_views_set_transform_preset: BoolProperty(name="Set Transform Preset when using Custom Views", default=False)
    show_orbit_selection: BoolProperty(name="Show Orbit around Active", default=True)
    show_orbit_method: BoolProperty(name="Show Orbit Method Selection", default=True)

    cursor_pie_show: BoolProperty(name="Show Cursor and Origin Pie Preferences", default=False)
    cursor_show_to_grid: BoolProperty(name="Show Cursor and Selected to Grid", default=False)
    cursor_set_transform_preset: BoolProperty(name="Set Transform Preset when Setting Cursor", default=False)

    snapping_pie_show: BoolProperty(name="Show Snapping Pie Preferences", default=False)
    snap_show_absolute_grid: BoolProperty(name="Show Absolute Grid Snapping", default=False)
    snap_show_volume: BoolProperty(name="Show Volume Snapping", default=False)

    workspace_pie_show: BoolProperty(name="Show Workspace Pie Preferences", default=False)
    pie_workspace_left_name: StringProperty(name="Left Workspace Name", default="Layout")
    pie_workspace_left_text: StringProperty(name="Left Workspace Custom Label", default="M4N1")
    pie_workspace_left_icon: StringProperty(name="Left Workspace Icon", default="VIEW3D")
    pie_workspace_top_left_name: StringProperty(name="Top-Left Workspace Name", default="UV Editing")
    pie_workspace_top_left_text: StringProperty(name="Top-Left Workspace Custom Label", default="UVs")
    pie_workspace_top_left_icon: StringProperty(name="Top-Left Workspace Icon", default="GROUP_UVS")
    pie_workspace_top_name: StringProperty(name="Top Workspace Name", default="Shading")
    pie_workspace_top_text: StringProperty(name="Top Workspace Custom Label", default="Materials")
    pie_workspace_top_icon: StringProperty(name="Top Workspace Icon", default="MATERIAL_DATA")
    pie_workspace_top_right_name: StringProperty(name="Top-Right Workspace Name", default="")
    pie_workspace_top_right_text: StringProperty(name="Top-Right Workspace Custom Label", default="")
    pie_workspace_top_right_icon: StringProperty(name="Top-Right Workspace Icon", default="")
    pie_workspace_right_name: StringProperty(name="Right Workspace Name", default="Rendering")
    pie_workspace_right_text: StringProperty(name="Right Workspace Custom Label", default="")
    pie_workspace_right_icon: StringProperty(name="Right Workspace Icon", default="")
    pie_workspace_bottom_right_name: StringProperty(name="Bottom-Right Workspace Name", default="")
    pie_workspace_bottom_right_text: StringProperty(name="Bottom-Right Workspace Custom Label", default="")
    pie_workspace_bottom_right_icon: StringProperty(name="Bottom-Right Workspace Icon", default="")
    pie_workspace_bottom_name: StringProperty(name="Bottom Workspace Name", default="Scripting")
    pie_workspace_bottom_text: StringProperty(name="Bottom Workspace Custom Label", default="")
    pie_workspace_bottom_icon: StringProperty(name="Bottom Workspace Icon", default="CONSOLE")
    pie_workspace_bottom_left_name: StringProperty(name="Bottom-Left Workspace Name", default="")
    pie_workspace_bottom_left_text: StringProperty(name="Bottom-Left Workspace Custom Label", default="")
    pie_workspace_bottom_left_icon: StringProperty(name="Bottom-Left Workspace Icon", default="")

    tools_pie_show: BoolProperty(name="Show Tools Pie Preferences", default=False)
    tools_show_boxcutter_presets: BoolProperty(name="Show BoxCutter Presets", default=True)
    tools_show_hardops_menu: BoolProperty(name="Show Hard Ops Menu", default=True)
    tools_show_quick_favorites: BoolProperty(name="Show Quick Favorites", default=False)
    tools_show_tool_bar: BoolProperty(name="Show Tool Bar", default=False)

    activate_smart_vert: BoolProperty(name="Smart Vert", default=True, update=update_activate_smart_vert)
    activate_smart_edge: BoolProperty(name="Smart Edge", default=True, update=update_activate_smart_edge)
    activate_smart_face: BoolProperty(name="Smart Face", default=True, update=update_activate_smart_face)
    activate_old_modifier: BoolProperty(name="Old Modifier", default=True, update=update_activate_old_modifier)
    activate_mirror_vg: BoolProperty(name="Mirror Vg", default=True, update=update_activate_mirror_vg)
    # activate_meshdeform_helper: BoolProperty(name="Meshdeform Helper", default=True, update=update_activate_meshdeform_helper)
    activate_simple_deform_helper: BoolProperty(name="Simple Deform Helper", default=True, update=update_activate_simple_deform_helper)
    activate_wave_modifier: BoolProperty(name="Wave Modifier", default=True, update=update_activate_wave_modifier)
    activate_lattice_helper: BoolProperty(name="Lattice Helper", default=True, update=update_activate_lattice_helper)
    activate_clean_up: BoolProperty(name="Clean Up", default=True, update=update_activate_clean_up)
    activate_edge_constraint: BoolProperty(name="Edge Constraint", default=True, update=update_activate_edge_constraint)
    activate_extrude: BoolProperty(name="Extrude", default=True, update=update_activate_extrude)
    activate_focus: BoolProperty(name="Focus", default=True, update=update_activate_focus)
    activate_mirror: BoolProperty(name="Mirror", default=True, update=update_activate_mirror)
    activate_align: BoolProperty(name="Align", default=True, update=update_activate_align)
    activate_group: BoolProperty(name="Group", default=True, update=update_activate_group)
    activate_smart_drive: BoolProperty(name="Smart Drive", default=True, update=update_activate_smart_drive)
    activate_filebrowser_tools: BoolProperty(name="File Browser Tools", default=True, update=update_activate_filebrowser_tools)
    activate_assetbrowser_tools: BoolProperty(name="Asset Browser Tools", default=True, update=update_activate_assetbrowser_tools)
    activate_region: BoolProperty(name="Toggle Region", default=True, update=update_activate_region)
    activate_render: BoolProperty(name="Render", default=True, update=update_activate_render)
    activate_smooth: BoolProperty(name="Smooth", default=True, update=update_activate_smooth)
    activate_clipping_toggle: BoolProperty(name="Clipping Toggle", default=True, update=update_activate_clipping_toggle)
    activate_surface_slide: BoolProperty(name="Surface Slide", default=True, update=update_activate_surface_slide)
    activate_material_picker: BoolProperty(name="Material Picker", default=True, update=update_activate_material_picker)
    activate_apply: BoolProperty(name="Apply", default=True, update=update_activate_apply)
    activate_select: BoolProperty(name="Select", default=True, update=update_activate_select)
    activate_mesh_cut: BoolProperty(name="Mesh Cut", default=True, update=update_activate_mesh_cut)
    activate_thread: BoolProperty(name="Thread", default=True, update=update_activate_thread)
    activate_unity: BoolProperty(name="Unity", default=True, update=update_activate_unity)
    activate_customize: BoolProperty(name="Customize", default=True, update=update_activate_customize)

    activate_modes_pie: BoolProperty(name="Modes Pie", default=True, update=update_activate_modes_pie)
    activate_save_pie: BoolProperty(name="Save Pie", default=True, update=update_activate_save_pie)
    activate_shading_pie: BoolProperty(name="Shading Pie", default=True, update=update_activate_shading_pie)
    activate_views_pie: BoolProperty(name="Views Pie", default=True, update=update_activate_views_pie)
    activate_align_pie: BoolProperty(name="Align Pies", default=True, update=update_activate_align_pie)
    activate_align_helper_pie: BoolProperty(name="Align Helper Pies", default=True, update=update_activate_align_helper_pie)
    activate_cursor_pie: BoolProperty(name="Cursor and Origin Pie", default=True, update=update_activate_cursor_pie)
    activate_transform_pie: BoolProperty(name="Transform Pie", default=True, update=update_activate_transform_pie)
    activate_snapping_pie: BoolProperty(name="Snapping Pie", default=True, update=update_activate_snapping_pie)
    activate_collections_pie: BoolProperty(name="Collections Pie", default=True, update=update_activate_collections_pie)
    activate_workspace_pie: BoolProperty(name="Workspace Pie", default=True, update=update_activate_workspace_pie)
    activate_tools_pie: BoolProperty(name="Tools Pie", default=True, update=update_activate_tools_pie)

    use_group_sub_menu: BoolProperty(name="Use Group Sub-Menu", default=False)
    use_group_outliner_toggles: BoolProperty(name="Show Group Outliner Toggles", default=True)

    show_sidebar_panel: BoolProperty(name="Show Sidebar Panel", description="Show M4N1tools Panel in 3D View's Sidebar", default=True)

    modal_hud_scale: FloatProperty(name="HUD Scale", description="Scale of HUD elements", default=1, min=0.1)
    modal_hud_timeout: FloatProperty(name="HUD timeout", description="Global Timeout Modulation (not exposed in M4N1tools)", default=1, min=0.1)
    HUD_fade_clean_up: FloatProperty(name="Clean Up HUD Fade Time (seconds)", default=1, min=0.1)
    HUD_fade_select_hierarchy: FloatProperty(name="Select Hierarchy HUD Fade Time (seconds)", default=1.5, min=0.1)
    HUD_fade_clipping_toggle: FloatProperty(name="Clipping Toggle HUD Fade Time (seconds)", default=1, min=0.1)
    HUD_fade_group: FloatProperty(name="Group HUD Fade Time (seconds)", default=1, min=0.1)
    HUD_fade_tools_pie: FloatProperty(name="Tools Pie HUD Fade Time (seconds)", default=0.75, min=0.1)
    mirror_flick_distance: IntProperty(name="Flick Distance", default=75, min=20, max=1000)

    update_available: BoolProperty(name="Update is available", default=False)

    def update_show_update(self, context):
        if self.show_update:
            get_update_files(force=True)

    tabs: EnumProperty(name="Tabs", items=preferences_tabs, default="GENERAL")
    show_update: BoolProperty(default=False, update=update_show_update)
    avoid_update: BoolProperty(default=False)
    dirty_keymaps: BoolProperty(default=False)

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        # self.draw_update(column)

        # self.draw_support(column)

        column = layout.column(align=True)

        row = column.row()
        row.prop(self, "tabs", expand=True)

        box = column.box()

        if self.tabs == "GENERAL":
            self.draw_general(box)

        elif self.tabs == "KEYMAPS":
            self.draw_keymaps(box)

        elif self.tabs == "ABOUT":
            pass
            box.label(text="This plugin integrates some of the Pepperoni Joe's plugins and is developed based on MACHIN3TOOLS.", icon='INFO')
            # self.draw_about(box)

    def draw_update(self, layout):
        row = layout.row()
        row.scale_y = 1.25
        row.prop(self, 'show_update', text="Install M4N1tools Update", icon='TRIA_DOWN' if self.show_update else 'TRIA_RIGHT')

        if self.show_update:
            update_files = get_update_files()

            box = layout.box()
            box.separator()

            if self.update_msg:
                row = box.row()
                row.scale_y = 1.5

                split = row.split(factor=0.4, align=True)
                split.label(text=self.update_msg, icon_value=get_icon('refresh_green'))

                s = split.split(factor=0.3, align=True)
                s.operator('m4n1.remove_m4n1tools_update', text='Remove Update', icon='CANCEL')
                s.operator('wm.quit_blender', text='Quit Blender + Install Update', icon='FILE_REFRESH')

            else:

                if update_files:

                    b = box.box()
                    col = b.column(align=True)

                    row = col.row()
                    row.alignment = 'LEFT'
                    row.label(text="Found the following Updates in your home and/or Downloads folder: ")
                    row.operator('m4n1.rescan_m4n1tools_updates', text="Re-Scan", icon='FILE_REFRESH')

                    col.separator()

                    for path, tail, _ in update_files:
                        row = col.row()
                        row.alignment = 'LEFT'

                        r = row.row()
                        r.active = False

                        r.alignment = 'LEFT'
                        r.label(text="found")

                        op = row.operator('m4n1.use_m4n1tools_update', text=f"M4N1tools {tail}")
                        op.path = path
                        op.tail = tail

                        r = row.row()
                        r.active = False
                        r.alignment = 'LEFT'
                        r.label(text=path)

                row = box.row()

                split = row.split(factor=0.4, align=True)
                split.prop(self, 'update_path', text='')

                text = "Select M4N1tools_x.x.x.zip file"

                if update_files:
                    if len(update_files) > 1:
                        text += " or pick one from above"

                    else:
                        text += " or pick the one above"

                split.label(text=text)

            box.separator()
    
    def draw_support(self, layout):
        layout.separator()

        box = layout.box()
        box.label(text="Support")

        column = box.column()
        row = column.row()
        row.scale_y = 1.5
        row.operator('m4n1.get_m4n1tools_support', text='Get Support', icon='GREASEPENCIL')

    def draw_general(self, layout):
        global has_skribe, has_screencast_keys

        if has_skribe is None:
            has_skribe = bool(shutil.which('skribe'))

        if has_screencast_keys is None:
            has_screencast_keys = bool(get_addon('Screencast Keys')[1])

        split = layout.split()

        b = split.box()
        b.label(text="Activate")

        bb = b.box()
        bb.label(text="Tools")

        column = bb.column(align=True)

        draw_split_row(self, column, prop='activate_smart_vert', text='Smart Vert', label='Smart Vertex Merging, Connecting and Sliding', factor=0.25)
        draw_split_row(self, column, prop='activate_smart_edge', text='Smart Edge', label='Smart Edge Creation, Manipulation, Projection and Selection Conversion', factor=0.25)
        draw_split_row(self, column, prop='activate_smart_face', text='Smart Face', label='Smart Face Creation and Object-from-Face Creation', factor=0.25)
        draw_split_row(self, column, prop='activate_old_modifier', text='Old Modifier', label='Enable Old Modifier', factor=0.25)
        draw_split_row(self, column, prop='activate_mirror_vg', text='Mirror Vg', label="Mirror Vertex Group", factor=0.25)
        draw_split_row(self, column, prop='activate_wave_modifier', text='Wave Modifier', label="Improve Parameter Display for Wave Modifier", factor=0.25)
        # draw_split_row(self, column, prop='activate_meshdeform_helper', text='Meshdeform Helper', label="Quick Setup Mesh Deformation", factor=0.25)
        draw_split_row(self, column, prop='activate_simple_deform_helper', text='Simple Deform Helper', label="User-friendly Visual 3D Components", factor=0.25)
        draw_split_row(self, column, prop='activate_lattice_helper', text='Lattice Helper', label="Convenient and Quick Grid Creation", factor=0.25)

        draw_split_row(self, column, prop='activate_clean_up', text='Clean Up', label='Quick Geometry Clean-up', factor=0.25)
        draw_split_row(self, column, prop='activate_edge_constraint', text='Edge Constraint', label='Edge Constrained Rotation and Scaling', factor=0.25)
        draw_split_row(self, column, prop='activate_extrude', text='Extrude', label="PunchIt Manifold Extrusion and Cursor Spin", factor=0.25)
        draw_split_row(self, column, prop='activate_focus', text='Focus', label='Object Focus and Multi-Level Isolation', factor=0.25)
        draw_split_row(self, column, prop='activate_mirror', text='Mirror', label='Flick Object Mirroring and Un-Mirroring', factor=0.25)
        # draw_split_row(self, column, prop='activate_align', text='Align', label='Object per-axis Location, Rotation and Scale Alignment, as well as Object-Inbetween-Alignment', factor=0.25)
        draw_split_row(self, column, prop='activate_group', text='Group', label='Group Objects using Empties as Parents', factor=0.25)
        draw_split_row(self, column, prop='activate_smart_drive', text='Smart Drive', label='Use one Object to drive another', factor=0.25)
        # draw_split_row(self, column, prop='activate_assetbrowser_tools', text='Assetbrowser Tools', label='Easy Assemly Asset Creation and Import via the Asset Browser', factor=0.25)
        draw_split_row(self, column, prop='activate_filebrowser_tools', text='Filebrowser Tools', label='Additional Tools/Shortcuts for the Filebrowser (and Assetbrowser)', factor=0.25)
        # draw_split_row(self, column, prop='activate_region', text='Toggle Region', label='Toggle 3D View Toolbar, Sidebar and Asset Browsers using a single T keymap, depending on mouse position', factor=0.25)
        # draw_split_row(self, column, prop='activate_render', text='Render', label='Tools for efficient, iterative rendering', factor=0.25)
        # draw_split_row(self, column, prop='activate_smooth', text='Smooth', label='Toggle Smoothing in Korean Bevel and SubD workflows', factor=0.25)
        draw_split_row(self, column, prop='activate_clipping_toggle', text='Clipping Toggle', label='Viewport Clipping Plane Toggle', factor=0.25)
        # draw_split_row(self, column, prop='activate_surface_slide', text='Surface Slide', label='Easily modify Mesh Topology, while maintaining Form', factor=0.25)
        # draw_split_row(self, column, prop='activate_material_picker', text='Material Picker', label="Pick Materials from the Material Workspace's 3D View", factor=0.25)
        # draw_split_row(self, column, prop='activate_apply', text='Apply', label='Apply Transformations while keeping the Bevel Width as well as the Child Transformations unchanged', factor=0.25)
        draw_split_row(self, column, prop='activate_select', text='Select', label='Select Center Objects, Select/Hide Wire Objects, Select Hierarchy', factor=0.25)
        draw_split_row(self, column, prop='activate_mesh_cut', text='Mesh Cut', label='Knife Intersect a Mesh-Object, using another one', factor=0.25)
        draw_split_row(self, column, prop='activate_thread', text='Thread', label='Easily turn Cylinder Faces into Thread', factor=0.25)
        # draw_split_row(self, column, prop='activate_unity', text='Unity', label='Unity related Tools', factor=0.25)

        column.separator()

        draw_split_row(self, column, prop='activate_customize', text='Customize', label='Customize various Blender preferences, settings and keymaps', factor=0.25)

        bb = b.box()
        bb.label(text="Pie Menus")

        column = bb.column(align=True)

        draw_split_row(self, column, prop='activate_modes_pie', text='Modes Pie', label='Quick mode changing', factor=0.25)
        draw_split_row(self, column, prop='activate_save_pie', text='Save Pie', label='Save, Open, Append and Link. Load Recent, Previous and Next. Purge and Clean Out. ScreenCast and Versioned Startup file', factor=0.25)
        draw_split_row(self, column, prop='activate_shading_pie', text='Shading Pie', label='Control shading, overlays, eevee and some object properties', factor=0.25)
        draw_split_row(self, column, prop='activate_views_pie', text='Views Pie', label='Control views. Create and manage cameras', factor=0.25)
        draw_split_row(self, column, prop='activate_align_pie', text='Alignments Pie', label='Edit mesh and UV alignments', factor=0.25)
        draw_split_row(self, column, prop='activate_align_helper_pie', text='Align Helper Pie', label='Object Alignment Assistant',factor=0.25)
        draw_split_row(self, column, prop='activate_cursor_pie', text='Cursor and Origin Pie', label='Cursor and Origin manipulation', factor=0.25)
        # draw_split_row(self, column, prop='activate_transform_pie', text='Transform Pie', label='Transform Orientations and Pivots', factor=0.25)
        # draw_split_row(self, column, prop='activate_snapping_pie', text='Snapping Pie', label='Snapping', factor=0.25)
        draw_split_row(self, column, prop='activate_collections_pie', text='Collections Pie', label='Collection management', factor=0.25)
        # draw_split_row(self, column, prop='activate_workspace_pie', text='Workspace Pie', label='Switch Workplaces. If enabled, customize it in ui/pies.py', factor=0.25)

        column.separator()

        draw_split_row(self, column, prop='activate_tools_pie', text='Tools Pie', label='Switch Tools, useful with BoxCutter/HardOps and HyperCursor', factor=0.25)

        b = split.box()
        b.label(text="Settings")

        bb = b.box()
        bb.label(text="Addon")

        column = bb.column()
        draw_split_row(self, column, prop='registration_debug', label='Print Addon Registration Output in System Console')

        if any([getattr(bpy.types, f'M4N1_{name}', False) for name in has_sidebar]):
            bb = b.box()
            bb.label(text="View 3D")

            if any([getattr(bpy.types, f'M4N1_{name}', False) for name in has_sidebar]):
                column = bb.column()
                draw_split_row(self, column, prop='show_sidebar_panel', label='Show Sidebar Panel')

        if any([getattr(bpy.types, f'M4N1_{name}', False) for name in has_hud]):
            bb = b.box()
            bb.label(text="HUD")

            column = bb.column(align=True)
            factor = 0.4 if getattr(bpy.types, 'M4N1_OT_mirror', False) else 0.2

            row = draw_split_row(self, column, prop='modal_hud_scale', label='HUD Scale', factor=factor)

            if getattr(bpy.types, "M4N1_OT_mirror", False):
                draw_split_row(self, row, prop='mirror_flick_distance', label='Mirror Flick Distance', factor=factor)

            if any([getattr(bpy.types, f'M4N1_{name}', False) for name in is_fading]):
                column = bb.column()
                column.label(text="Fade time")

                column = bb.column()
                row = column.row(align=True)

                if getattr(bpy.types, "M4N1_OT_clean_up", False):
                    row.prop(self, "HUD_fade_clean_up", text="Clean Up")

                if getattr(bpy.types, "M4N1_OT_clipping_toggle", False):
                    row.prop(self, "HUD_fade_clipping_toggle", text="Clipping Toggle")

                if getattr(bpy.types, "M4N1_OT_group", False):
                    row.prop(self, "HUD_fade_group", text="Group")

                if getattr(bpy.types, "M4N1_OT_group", False):
                    row.prop(self, "HUD_fade_select_hierarchy", text="Select Hierarchy")

                if getattr(bpy.types, "M4N1_MT_tools_pie", False):
                    row.prop(self, "HUD_fade_tools_pie", text="Tools Pie")

        if getattr(bpy.types, "M4N1_OT_focus", False):
            bb = b.box()
            bb.prop(self, 'focus_show', text="Focus", icon='TRIA_DOWN' if self.focus_show else 'TRIA_RIGHT', emboss=False)

            if self.focus_show:
                column = bb.column(align=True)

                draw_split_row(self, column, prop='focus_view_transition', label='Viewport Tweening')
                draw_split_row(self, column, prop='focus_lights', label='Ignore Lights (keep them always visible)')
        if getattr(bpy.types, "M4N1_OT_lattice_operator", False):
            bb = b.box()
            bb.prop(self, 'lh_show', text="Lattice Helper", icon='TRIA_DOWN' if self.lh_show else 'TRIA_RIGHT', emboss=False)

            if self.lh_show:
                column = bb.column(align=True)
                column.prop(self,"lh_def_res")
                column.prop(self,"lh_lerp")
                # draw_split_row(self, column, prop='lh_def_res', label='Default lattice resolution')
                # draw_split_row(self, column, prop='lh_lerp', label='Interpolation)')
        #simple deform helper
        if getattr(bpy.types, "M4N1_OT_simple_deform_gizmo_axis", False):
            bb = b.box()
            bb.prop(self, 'sdh_show', text="Simple Deform Helper", icon='TRIA_DOWN' if self.sdh_show else 'TRIA_RIGHT', emboss=False)

            if self.sdh_show:
                col = bb.column(align=True)
                box = col.box()
                for text in ("You can press the following shortcut keys when dragging values",
                             "    Wheel:   Switch Origin Ctrl Mode",
                             "    X,Y,Z:  Switch Modifier Deform Axis",
                             "    W:       Switch Deform Wireframe Show",
                             "    A:       Switch To Select Bend Axis Mode(deform_method=='BEND')",):
                    box.label(text=self.translate_text(text))

                col.prop(self, 'sdh_deform_wireframe_color')
                col.prop(self, 'sdh_bound_box_color')
                col.prop(self, 'sdh_limits_bound_box_color')

                col.label(text='Gizmo Property Show Location')
                col.prop(self, 'sdh_show_gizmo_property_location', expand=True)
        if getattr(bpy.types, "M4N1_OT_group", False):
            bb = b.box()
            bb.prop(self, 'group_show', text="Group", icon='TRIA_DOWN' if self.group_show else 'TRIA_RIGHT', emboss=False)

            if self.group_show:
                column = bb.column(align=True)

                draw_split_row(self, column, prop='use_group_sub_menu', text='Sub Menu', label='Use Group Sub Menu in Object Context Menu')
                draw_split_row(self, column, prop='use_group_outliner_toggles', text='Outliner Toggles', label='Show Group Toggles in Outliner Header')
                draw_split_row(self, column, prop='group_remove_empty', text='Remove Empty', label='Automatically remove Empty Groups in each Cleanup Pass')

                column.separator()
                column.separator()
                column.separator()

                row = column.row()
                r = row.split(factor=0.2)
                r.label(text="Basename")
                r.prop(self, "group_basename", text="")

                row = column.row()
                r = row.split(factor=0.2)
                r.prop(self, "group_auto_name", text='Auto Name', toggle=True)

                rr = r.row()
                rr.active = self.group_auto_name
                rr.prop(self, "group_prefix", text="Prefix")
                rr.prop(self, "group_suffix", text="Suffix")

                column.separator()

                r = draw_split_row(self, column, prop='group_size', label='Default Empty Draw Size', factor=0.4)
                draw_split_row(self, r, prop='group_fade_sizes', label='Fade Sub Group Sizes', factor=0.4)

                rr = r.row()
                rr.active = self.group_fade_sizes
                rr.prop(self, "group_fade_factor", text='Factor')

        # if getattr(bpy.types, "M4N1_OT_assemble_instance_collection", False):
        #     bb = b.box()
        #     bb.prop(self, 'assetbrowser_show', text="Assetbrowser Tools", icon='TRIA_DOWN' if self.assetbrowser_show else 'TRIA_RIGHT', emboss=False)
        #
        #     if self.assetbrowser_show:
        #         column = bb.column(align=True)
        #
        #         draw_split_row(self, column, prop='preferred_default_catalog', label='Preferred Default Catalog (must exist already)')
        #         draw_split_row(self, column, prop='preferred_assetbrowser_workspace_name', label='Preferred Workspace for Assembly Asset Creation')
        #         draw_split_row(self, column, prop='hide_wire_objects_when_creating_assembly_asset', label='Hide Wire Objects when creatinng Assembly Asset')
        #         draw_split_row(self, column, prop='hide_wire_objects_when_assembling_instance_collection', label='Hide Wire Objects when assemgling Instance Collection')
        #
        #         if getattr(bpy.types, "M4N1_MT_modes_pie", False):
        #             draw_split_row(self, column, prop='show_instance_collection_assembly_in_modes_pie', label='Show Instance Collection Assembly in Modes Pie')
        #
        #         if getattr(bpy.types, "M4N1_MT_save_pie", False):
        #             draw_split_row(self, column, prop='show_assembly_asset_creation_in_save_pie', label='Show Assembly Asset Creation in Save Pie')

        # if getattr(bpy.types, "M4N1_OT_toggle_view3d_region", False):
        #     bb = b.box()
        #     bb.prop(self, 'region_show', text="Toggle Region", icon='TRIA_DOWN' if self.region_show else 'TRIA_RIGHT', emboss=False)
        #
        #     if self.region_show:
        #         column = bb.column(align=True)
        #
        #         draw_split_row(self, column, prop='region_prefer_left_right', label='Prefer Left/Right toggle, over Bottom/Top, before Close Range is used to determine whether the other pair is toggled')
        #         draw_split_row(self, column, prop='region_close_range', label='Close Range - Proximity to Boundary as Percetange of the Area Width/Height')
        #
        #         if bpy.app.version >= (4, 0, 0):
        #             column.separator()
        #
        #             draw_split_row(self, column, prop='region_toggle_assetshelf', label='If available toggle the Asset Shelf instead of the Browser', info='This is still extremely limited in Blender 4.0, and practically unusable')
        #
        #         column.separator()
        #
        #         draw_split_row(self, column, prop='region_toggle_assetbrowser_top', label='Toggle Asset Browser at Top of 3D View')
        #         draw_split_row(self, column, prop='region_toggle_assetbrowser_bottom', label='Toggle Asset Browser at Bottom of 3D View')
        #
        #         if any([self.region_toggle_assetbrowser_top, self.region_toggle_assetbrowser_bottom]):
        #             draw_split_row(self, column, prop='region_warp_mouse_to_asset_border', label='Warp Mouse to Asset Browser Border')

        # if getattr(bpy.types, "M4N1_OT_render", False):
        #     bb = b.box()
        #     bb.prop(self, 'render_show', text="Render", icon='TRIA_DOWN' if self.render_show else 'TRIA_RIGHT', emboss=False)
        #
        #     if self.render_show:
        #         column = bb.column(align=True)
        #
        #         draw_split_row(self, column, prop='render_folder_name', label='Folder Name (relative to the .blend file)')
        #         draw_split_row(self, column, prop='render_seed_count', label='Seed Render Count')
        #         draw_split_row(self, column, prop='render_keep_seed_renderings', label='Keep Individual Seed Renderings')
        #         draw_split_row(self, column, prop='render_use_clownmatte_naming', label='Use Clownmatte Naming')
        #         draw_split_row(self, column, prop='render_show_buttons_in_light_properties', label='Show Render Buttons in Light Properties Panel')
        #         draw_split_row(self, column, prop='render_sync_light_visibility', label='Sync Light visibility/renderability')
        #
        #         column.separator()
        #         column.separator()
        #         column.separator()
        #
        #         if self.activate_shading_pie:
        #             column.label(text="NOTE: The following are all controlled from the Shading Pie", icon='INFO')
        #             column.separator()
        #
        #             draw_split_row(self, column, prop='render_adjust_lights_on_render', label='Adjust Area Lights when Rendering in Cycles')
        #             draw_split_row(self, column, prop='render_enforce_hide_render', label='Enforce hide_render settign when Viewport Rendering')
        #             draw_split_row(self, column, prop='render_use_bevel_shader', label='Automatically Set Up Bevel Shader')
        #
        #         else:
        #             column.label(text="Enable the Shading Pie for additional options", icon='INFO')

        # if getattr(bpy.types, "M4N1_OT_material_picker", False):
        #     bb = b.box()
        #     bb.prop(self, 'matpick_show', text="Material Picker", icon='TRIA_DOWN' if self.matpick_show else 'TRIA_RIGHT', emboss=False)
        #
        #     if self.matpick_show:
        #         column = bb.column(align=True)
        #
        #         draw_split_row(self, column, prop='matpick_workspace_names', label='Show Material Picker in these Workspaces')
        #         draw_split_row(self, column, prop='matpick_shading_type_material', label='Show Material Picker in Views set to Material Shading')
        #         draw_split_row(self, column, prop='matpick_shading_type_render', label='Show Material Picker in Views set to Rendered Shading')
        #         draw_split_row(self, column, prop='matpick_spacing_obj', label='Object Mode Header Spacing')
        #         draw_split_row(self, column, prop='matpick_spacing_edit', label='Edit Mode Header Spacing')

        if getattr(bpy.types, "M4N1_OT_customize", False):
            bb = b.box()
            bb.prop(self, 'customize_show', text="Customize", icon='TRIA_DOWN' if self.customize_show else 'TRIA_RIGHT', emboss=False)

            if self.customize_show:

                bb.label(text='General')

                column = bb.column(align=True)

                row = draw_split_row(self, column, prop='custom_theme', label='Theme', factor=0.4)
                row = draw_split_row(self, row, prop='custom_matcaps', label='Matcaps', factor=0.4)
                draw_split_row(self, row, prop='custom_shading', label='Shading', factor=0.4)

                row = draw_split_row(self, column, prop='custom_overlays', label='Overlays', factor=0.4)
                row = draw_split_row(self, row, prop='custom_outliner', label='Outliner', factor=0.4)
                draw_split_row(self, row, prop='custom_startup', label='Startup', factor=0.4)

                bb.separator()
                bb.label(text='Preferences')

                column = bb.column(align=True)

                row = draw_split_row(self, column, prop='custom_preferences_interface', label='Interface', factor=0.4)
                draw_split_row(self, row, prop='custom_preferences_keymap', label='Keymaps', factor=0.4)
                draw_split_row(self, row, prop='custom_preferences_viewport', label='Viewport', factor=0.4)

                row = draw_split_row(self, column, prop='custom_preferences_system', label='System', factor=0.4)
                draw_split_row(self, row, prop='custom_preferences_input_navigation', label='Input & Navigation', factor=0.4)
                draw_split_row(self, row, prop='custom_preferences_save', label='Save', factor=0.4)

                if self.dirty_keymaps:
                    column.separator()

                    row = column.row()
                    row.label(text="Keymaps have been modified, restore them first.", icon="ERROR")
                    row.operator("m4n1.restore_keymaps", text="Restore now")
                    row.label()

                bb.separator()

                column = bb.column()
                row = column.row()
                row.label()
                row.operator("m4n1.customize", text="Customize")
                row.label()

        b.separator()

        if getattr(bpy.types, "M4N1_MT_modes_pie", False):
            bb = b.box()
            bb.prop(self, 'modes_pie_show', text="Modes Pie", icon='TRIA_DOWN' if self.modes_pie_show else 'TRIA_RIGHT', emboss=False)

            if self.modes_pie_show:
                column = bb.column(align=True)

                draw_split_row(self, column, prop='toggle_cavity', label='Toggle Cavity/Curvature OFF in Edit Mode, ON in Object Mode')
                draw_split_row(self, column, prop='toggle_xray', label='Toggle X-Ray ON in Edit Mode, OFF in Object Mode, if Pass Through or Wireframe was enabled in Edit Mode')
                draw_split_row(self, column, prop='sync_tools', label='Sync Tool if possible, when switching Modes')

        if getattr(bpy.types, "M4N1_MT_save_pie", False):

            bb = b.box()
            bb.prop(self, 'save_pie_show', text="Save Pie", icon='TRIA_DOWN' if self.save_pie_show else 'TRIA_RIGHT', emboss=False)

            if self.save_pie_show:

                bb.label(text='Import / Export')

                column = bb.column(align=True)

                row = column.row(align=True)
                split = row.split(factor=0.5, align=True)

                r = split.split(factor=0.42, align=True)
                r.prop(self, "save_pie_show_obj_export", text=str(self.save_pie_show_obj_export), toggle=True)
                r.label(text="Show .obj Import/Export")

                split.separator()

                row = column.row(align=True)
                split = row.split(factor=0.5, align=True)

                r = split.split(factor=0.42, align=True)
                r.prop(self, "save_pie_show_plasticity_export", text=str(self.save_pie_show_plasticity_export), toggle=True)
                r.label(text="Show Plasticity Import/Export")

                if self.save_pie_show_plasticity_export:
                    split.label(text=".obj import/export with Axes set up already", icon='INFO')

                else:
                    split.separator()

                row = column.row(align=True)
                split = row.split(factor=0.5, align=True)

                r = split.split(factor=0.42, align=True)
                r.prop(self, "save_pie_show_fbx_export", text=str(self.save_pie_show_fbx_export), toggle=True)
                r.label(text="Show .fbx Import/Export")

                if self.save_pie_show_fbx_export:
                    r = split.split(factor=0.42, align=True)
                    r.prop(self, "fbx_export_apply_scale_all", text=str(self.fbx_export_apply_scale_all), toggle=True)
                    r.label(text="Use 'Fbx All' for Applying Scale")

                else:
                    split.separator()

                row = column.row(align=True)
                split = row.split(factor=0.5, align=True)

                r = split.split(factor=0.42, align=True)
                r.prop(self, "save_pie_show_usd_export", text=str(self.save_pie_show_usd_export), toggle=True)
                r.label(text="Show .usd Import/Export")

                split.separator()

                row = column.row(align=True)
                split = row.split(factor=0.5, align=True)

                r = split.split(factor=0.42, align=True)
                r.prop(self, "save_pie_show_stl_export", text=str(self.save_pie_show_stl_export), toggle=True)
                r.label(text="Show .stl Import/Export")

                split.separator()

                bb.separator()
                bb.label(text='Screen Cast')

                column = bb.column(align=True)

                draw_split_row(self, column, prop='show_screencast', label='Show Screencast in Save Pie')

                if self.show_screencast:
                    split = bb.split(factor=0.5)
                    col = split.column(align=True)

                    draw_split_row(self, col, prop='screencast_operator_count', label='Operator Count', factor=0.4)
                    draw_split_row(self, col, prop='screencast_fontsize', label='Font Size', factor=0.4)

                    col = split.column(align=True)

                    draw_split_row(self, col, prop='screencast_highlight_m4n1', label='Highlight Operators from M4N1 addons', factor=0.3)
                    draw_split_row(self, col, prop='screencast_show_addon', label="Display Operator's Addon", factor=0.3)
                    draw_split_row(self, col, prop='screencast_show_idname', label="Display Operator's bl_idname", factor=0.3)

                    if has_skribe or has_screencast_keys:
                        col.separator()

                        if has_skribe:
                            draw_split_row(self, col, prop='screencast_use_skribe', label='Use SKRIBE (dedicated, preferred)', factor=0.3)

                        if has_screencast_keys:
                            draw_split_row(self, col, prop='screencast_use_screencast_keys', label='Use Screencast Keys (addon)', factor=0.3)

                bb.separator()
                bb.label(text='Pre-Undo Save')

                column = bb.column(align=True)
                draw_split_row(self, column, prop='save_pie_use_undo_save', label='Make Pre-Undo Saving available in the Pie', info='Useful if you notice Undo causing crashes')

                kmi = get_keymap_item('Window', 'm4n1.save_versioned_startup_file')

                if kmi:
                    bb.separator()
                    bb.label(text='Versioned Startup File')

                    column = bb.column(align=True)
                    draw_split_row(kmi, column, prop='active', text='Enabled' if kmi.active else 'Disabled', label='Use CTRL + U keymap override')
        if getattr(bpy.types, "M4N1_MT_pie_popoti_align_helper", False):

            bb = b.box()
            bb.prop(self, 'align_helper_pie_show', text="Align Helper Pie",
                    icon='TRIA_DOWN' if self.align_helper_pie_show else 'TRIA_RIGHT', emboss=False)

            if self.align_helper_pie_show:
                bb.label(text='npanel text')
                column = bb.column(align=True)
                column.prop(self, 'ah_show_text')
        if getattr(bpy.types, "M4N1_MT_shading_pie", False):

            bb = b.box()
            bb.prop(self, 'shading_pie_show', text="Shading Pie", icon='TRIA_DOWN' if self.shading_pie_show else 'TRIA_RIGHT', emboss=False)

            if self.shading_pie_show:

                bb.label(text='Overlay Visibility (per-shading type)')
                column = bb.column(align=True)

                row = draw_split_row(self, column, prop='overlay_solid', label='Solid Shading', factor=0.5)
                draw_split_row(self, row, prop='overlay_material', label='Material Shading', factor=0.5)
                draw_split_row(self, row, prop='overlay_rendered', label='Rendered Shading', factor=0.5)
                draw_split_row(self, row, prop='overlay_wire', label='Wire Shading', factor=0.5)

                bb.separator()
                bb.label(text='Autosmooth')

                column = bb.column(align=True)

                draw_split_row(self, column, prop='auto_smooth_angle_presets', label='Auto Smooth Angle Presets shown in the Shading Pie as buttons', factor=0.25)

                bb.separator()
                bb.label(text='Matcap Switch')

                column = bb.column()

                row = column.row()
                row.prop(self, "switchmatcap1")
                row.prop(self, "switchmatcap2")

                split = column.split(factor=0.5)

                draw_split_row(self, split, prop='matcap_switch_background', label='Switch Background too', factor=0.25)

                col = split.column(align=True)

                draw_split_row(self, col, prop='matcap2_force_single', label='Force Single Color Shading for Matcap 2', factor=0.25)
                draw_split_row(self, col, prop='matcap2_disable_overlays', label='Disable Overlays for Matcap 2', factor=0.25)

                if self.matcap_switch_background:
                    row = column.row()
                    row.prop(self, "matcap1_switch_background_type", expand=True)
                    row.prop(self, "matcap2_switch_background_type", expand=True)

                    if any([bg == 'VIEWPORT' for bg in [self.matcap1_switch_background_type, self.matcap2_switch_background_type]]):
                        row = column.split(factor=0.5)

                        if self.matcap1_switch_background_type == 'VIEWPORT':
                            row.prop(self, "matcap1_switch_background_viewport_color", text='')

                        else:
                            row.separator()

                        if self.matcap2_switch_background_type == 'VIEWPORT':
                            row.prop(self, "matcap2_switch_background_viewport_color", text='')

                        else:
                            row.separator()

        if getattr(bpy.types, "M4N1_MT_viewport_pie", False):
            bb = b.box()
            bb.prop(self, 'views_pie_show', text="Views Pie", icon='TRIA_DOWN' if self.views_pie_show else 'TRIA_RIGHT', emboss=False)

            if self.views_pie_show:

                column = bb.column(align=True)

                draw_split_row(self, column, prop='custom_views_use_trackball', label='Force Trackball Navigation when using Custom Views')

                if self.activate_transform_pie:
                    draw_split_row(self, column, prop='custom_views_set_transform_preset', label='Set Transform Preset when using Custom Views')

                draw_split_row(self, column, prop='show_orbit_selection', label='Show Orbit around Active')
                draw_split_row(self, column, prop='show_orbit_method', label='Show Turntable/Trackball Orbit Method Selection')

        if getattr(bpy.types, "M4N1_MT_cursor_pie", False):
            bb = b.box()
            bb.prop(self, 'cursor_pie_show', text="Cursor and Origin Pie", icon='TRIA_DOWN' if self.cursor_pie_show else 'TRIA_RIGHT', emboss=False)

            if self.cursor_pie_show:
                column = bb.column(align=True)

                draw_split_row(self, column, prop='cursor_show_to_grid', label='Show Cursor and Selected to Grid')

                if self.activate_transform_pie or self.activate_shading_pie:
                        if self.activate_transform_pie:
                            draw_split_row(self, column, prop='cursor_set_transform_preset', label='Set Transform Preset when Setting Cursor')

        # if getattr(bpy.types, "M4N1_MT_snapping_pie", False):
        #     bb = b.box()
        #     bb.prop(self, 'snapping_pie_show', text="Snapping Pie", icon='TRIA_DOWN' if self.snapping_pie_show else 'TRIA_RIGHT', emboss=False)
        #
        #     if self.snapping_pie_show:
        #         column = bb.column(align=True)
        #
        #         draw_split_row(self, column, prop='snap_show_absolute_grid', label='Show Absolute Grid Snapping')
        #         draw_split_row(self, column, prop='snap_show_volume', label='Show Volume Snapping')

        # if getattr(bpy.types, "M4N1_MT_workspace_pie", False):
        #     bb = b.box()
        #     bb.prop(self, 'workspace_pie_show', text="Workspace Pie", icon='TRIA_DOWN' if self.workspace_pie_show else 'TRIA_RIGHT', emboss=False)
        #
        #     if self.workspace_pie_show:
        #
        #         column = bb.column()
        #         column.label(text="It's your responsibility to pick workspace- and icon names that actually exist!", icon='ERROR')
        #
        #         first = column.split(factor=0.2)
        #         first.separator()
        #
        #         second = first.split(factor=0.25)
        #         second.separator()
        #
        #         third = second.split(factor=0.33)
        #
        #         col = third.column()
        #         col.label(text="Top")
        #
        #         col.prop(self, 'pie_workspace_top_name', text="", icon='WORKSPACE')
        #         col.prop(self, 'pie_workspace_top_text', text="", icon='SMALL_CAPS')
        #         col.prop(self, 'pie_workspace_top_icon', text="", icon='IMAGE_DATA')
        #
        #         fourth = third.split(factor=0.5)
        #         fourth.separator()
        #
        #         fifth = fourth
        #         fifth.separator()
        #
        #         first = column.split(factor=0.2)
        #         first.separator()
        #
        #         second = first.split(factor=0.25)
        #
        #         col = second.column()
        #         col.label(text="Top-Left")
        #
        #         col.prop(self, 'pie_workspace_top_left_name', text="", icon='WORKSPACE')
        #         col.prop(self, 'pie_workspace_top_left_text', text="", icon='SMALL_CAPS')
        #         col.prop(self, 'pie_workspace_top_left_icon', text="", icon='IMAGE_DATA')
        #
        #         third = second.split(factor=0.33)
        #         third.separator()
        #
        #         fourth = third.split(factor=0.5)
        #
        #         col = fourth.column()
        #         col.label(text="Top-Right")
        #
        #         col.prop(self, 'pie_workspace_top_right_name', text="", icon='WORKSPACE')
        #         col.prop(self, 'pie_workspace_top_right_text', text="", icon='SMALL_CAPS')
        #         col.prop(self, 'pie_workspace_top_right_icon', text="", icon='IMAGE_DATA')
        #
        #         fifth = fourth
        #         fifth.separator()
        #
        #         first = column.split(factor=0.2)
        #
        #         col = first.column()
        #         col.label(text="Left")
        #
        #         col.prop(self, 'pie_workspace_left_name', text="", icon='WORKSPACE')
        #         col.prop(self, 'pie_workspace_left_text', text="", icon='SMALL_CAPS')
        #         col.prop(self, 'pie_workspace_left_icon', text="", icon='IMAGE_DATA')
        #
        #         second = first.split(factor=0.25)
        #         second.separator()
        #
        #         third = second.split(factor=0.33)
        #
        #         col = third.column()
        #         col.label(text="")
        #         col.label(text="")
        #         col.operator('m4n1.get_icon_name_help', text="Icon Names?", icon='INFO')
        #
        #         fourth = third.split(factor=0.5)
        #         fourth.separator()
        #
        #         fifth = fourth
        #
        #         col = fifth.column()
        #         col.label(text="Right")
        #
        #         col.prop(self, 'pie_workspace_right_name', text="", icon='WORKSPACE')
        #         col.prop(self, 'pie_workspace_right_text', text="", icon='SMALL_CAPS')
        #         col.prop(self, 'pie_workspace_right_icon', text="", icon='IMAGE_DATA')
        #
        #         first = column.split(factor=0.2)
        #         first.separator()
        #
        #         second = first.split(factor=0.25)
        #
        #         col = second.column()
        #         col.label(text="Bottom-Left")
        #
        #         col.prop(self, 'pie_workspace_bottom_left_name', text="", icon='WORKSPACE')
        #         col.prop(self, 'pie_workspace_bottom_left_text', text="", icon='SMALL_CAPS')
        #         col.prop(self, 'pie_workspace_bottom_left_icon', text="", icon='IMAGE_DATA')
        #
        #         third = second.split(factor=0.33)
        #         third.separator()
        #
        #         fourth = third.split(factor=0.5)
        #
        #         col = fourth.column()
        #         col.label(text="Bottom-Right")
        #
        #         col.prop(self, 'pie_workspace_bottom_right_name', text="", icon='WORKSPACE')
        #         col.prop(self, 'pie_workspace_bottom_right_text', text="", icon='SMALL_CAPS')
        #         col.prop(self, 'pie_workspace_bottom_right_icon', text="", icon='IMAGE_DATA')
        #
        #         fifth = fourth
        #         fifth.separator()
        #
        #         first = column.split(factor=0.2)
        #         first.separator()
        #
        #         second = first.split(factor=0.25)
        #         second.separator()
        #
        #         third = second.split(factor=0.33)
        #
        #         col = third.column()
        #         col.label(text="Bottom")
        #
        #         col.prop(self, 'pie_workspace_bottom_name', text="", icon='WORKSPACE')
        #         col.prop(self, 'pie_workspace_bottom_text', text="", icon='SMALL_CAPS')
        #         col.prop(self, 'pie_workspace_bottom_icon', text="", icon='IMAGE_DATA')
        #
        #         fourth = third.split(factor=0.5)
        #         fourth.separator()
        #
        #         fifth = fourth
        #         fifth.separator()

        if getattr(bpy.types, "M4N1_MT_tools_pie", False):
            bb = b.box()
            bb.prop(self, 'tools_pie_show', text="Tools Pie", icon='TRIA_DOWN' if self.tools_pie_show else 'TRIA_RIGHT', emboss=False)

            if self.tools_pie_show:
                split = bb.split(factor=0.5)

                col = split.column(align=True)

                draw_split_row(self, col, prop='tools_show_boxcutter_presets', label='Show BoxCutter Presets', factor=0.4)
                draw_split_row(self, col, prop='tools_show_hardops_menu', label='Show Hard Ops Menu', factor=0.4)

                col = split.column(align=True)

                draw_split_row(self, col, prop='tools_show_quick_favorites', label='Show Quick Favorites', factor=0.4)
                draw_split_row(self, col, prop='tools_show_tool_bar', label='Show Tool Bar', factor=0.4)

        if not any([getattr(bpy.types, f'M4N1_{name}', False) for name in has_settings]):
            b.label(text="No tools or pie menus with settings have been activated.", icon='ERROR')

    def draw_keymaps(self, layout):
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.user

        from . registration import keys

        split = layout.split()

        b = split.box()
        b.label(text="Tools")

        if not self.draw_tool_keymaps(kc, keys, b):
            b.label(text="No keymappings available, because none of the tools have been activated.", icon='ERROR')

        b = split.box()
        b.label(text="Pie Menus")

        if not self.draw_pie_keymaps(kc, keys, b):
            b.label(text="No keymappings created, because none of the pies have been activated.", icon='ERROR')

    def draw_about(self, layout):
        global decalmachine, meshmachine, punchit, curvemachine, hypercursor

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        if punchit is None:
            punchit = get_addon('PUNCHit')[0]

        if curvemachine is None:
            curvemachine = get_addon('CURVEmachine')[0]

        if hypercursor is None:
            hypercursor = get_addon('HyperCursor')[0]

        column = layout.column(align=True)

        row = column.row(align=True)

        row.scale_y = 1.5
        row.operator("wm.url_open", text='M4N1tools', icon='INFO').url = 'https://m4n1.io/M4N1tools/'
        row.operator("wm.url_open", text='MACHINƎ.io', icon='WORLD').url = 'https://m4n1.io'
        row.operator("wm.url_open", text='blenderartists', icon_value=get_icon('blenderartists')).url = 'https://blenderartists.org/t/m4n1tools/1135716/'

        row = column.row(align=True)
        row.scale_y = 1.5
        row.operator("wm.url_open", text='Patreon', icon_value=get_icon('patreon')).url = 'https://patreon.com/m4n1'
        row.operator("wm.url_open", text='Twitter', icon_value=get_icon('twitter')).url = 'https://twitter.com/m4n1io'
        row.operator("wm.url_open", text='Youtube', icon_value=get_icon('youtube')).url = 'https://www.youtube.com/c/M4N1/'
        row.operator("wm.url_open", text='Artstation', icon_value=get_icon('artstation')).url = 'https://www.artstation.com/m4n1'

        column.separator()

        row = column.row(align=True)
        row.scale_y = 1.5
        row.operator("wm.url_open", text='DECALmachine', icon_value=get_icon('save' if decalmachine else 'cancel_grey')).url = 'https://decal.m4n1.io'
        row.operator("wm.url_open", text='MESHmachine', icon_value=get_icon('save' if meshmachine else 'cancel_grey')).url = 'https://mesh.m4n1.io'
        row.operator("wm.url_open", text='PUNCHit', icon_value=get_icon('save' if punchit else 'cancel_grey')).url = 'https://m4n1.io/PUNCHit'
        row.operator("wm.url_open", text='CURVEmachine', icon_value=get_icon('save' if curvemachine else 'cancel_grey')).url = 'https://m4n1.io/CURVEmachine'
        row.operator("wm.url_open", text='HyperCursor', icon_value=get_icon('save' if hypercursor else 'cancel_grey')).url = 'https://www.youtube.com/playlist?list=PLcEiZ9GDvSdWs1w4ZrkbMvCT2R4F3O9yD'

    def draw_tool_keymaps(self, kc, keysdict, layout):
        drawn = False

        for name in keysdict:
            if "PIE" not in name:
                keylist = keysdict.get(name)

                if draw_keymap_items(kc, name, keylist, layout) and not drawn:
                    drawn = True

        return drawn

    def draw_pie_keymaps(self, kc, keysdict, layout):
        drawn = False

        for name in keysdict:
            if "PIE" in name:
                keylist = keysdict.get(name)

                if draw_keymap_items(kc, name, keylist, layout):
                    drawn = True

        return drawn

    def draw_header_tool_settings(self, context):
        if GizmoUtils.poll_simple_deform_public(context):
            row = self.layout.row()
            obj = context.object
            mod = obj.modifiers.active

            row.separator(factor=0.2)
            row.prop(mod,
                     'deform_method',
                     expand=True)
            row.prop(mod,
                     'deform_axis',
                     expand=True)

            show_type = 'angle' if mod.deform_method in ('BEND', 'TWIST') else 'factor'
            row.prop(mod, show_type)