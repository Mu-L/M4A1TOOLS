import bpy
import os
from bpy.app.handlers import persistent
from time import time
from . utils.application import delay_execution
from . utils.asset import validate_assetbrowser_bookmarks
from . utils.draw import draw_axes_HUD, draw_focus_HUD, draw_surface_slide_HUD, draw_screen_cast_HUD, draw_group_poses_VIEW3D
from . utils.group import get_pose_batches, process_group_poses, select_group_children, set_group_pose, set_pose_uuid
from . utils.light import adjust_lights_for_rendering, get_area_light_poll
from . utils.math import compare_quat
from . utils.object import get_active_object, get_visible_objects
from . utils.registration import get_prefs, reload_msgbus, get_addon
from . utils.system import get_temp_dir
from . utils.view import sync_light_visibility

global_debug = False

axesHUD = None
prev_axes_objects = []

def manage_axes_HUD():
    global global_debug, axesHUD, prev_axes_objects

    debug = global_debug

    scene = getattr(bpy.context, 'scene', None)

    if scene:

        if debug:
            print("  axes HUD")

        if axesHUD and "RNA_HANDLE_REMOVED" in str(axesHUD):
            axesHUD = None

        axes_objects = [obj for obj in get_visible_objects(bpy.context) if obj.M4.draw_axes]

        active = get_active_object(bpy.context)

        if scene.M4.draw_active_axes and active and active not in axes_objects:
            axes_objects.append(active)

        if scene.M4.draw_cursor_axes:
            axes_objects.append('CURSOR')

        if axes_objects:
            if debug:
                print("   axes objects present:", [obj if obj == 'CURSOR' else obj.name for obj in axes_objects])

            if axes_objects != prev_axes_objects:
                if debug:
                    print("   axes objects changed")

                prev_axes_objects = axes_objects

                if axesHUD:
                    if debug:
                        print("   removing previous draw handler")

                    bpy.types.SpaceView3D.draw_handler_remove(axesHUD, 'WINDOW')

                if debug:
                    print("   adding new draw handler")
                axesHUD = bpy.types.SpaceView3D.draw_handler_add(draw_axes_HUD, (bpy.context, axes_objects), 'WINDOW', 'POST_VIEW')

        elif axesHUD:
            bpy.types.SpaceView3D.draw_handler_remove(axesHUD, 'WINDOW')

            if debug:
                print("   removing old draw handler")

            axesHUD = None
            prev_axes_objects = []

focusHUD = None

def manage_focus_HUD():
    global global_debug, focusHUD

    debug = global_debug

    scene = getattr(bpy.context, 'scene', None)

    if scene:

        if debug:
            print("  focus HUD")

        if focusHUD and "RNA_HANDLE_REMOVED" in str(focusHUD):
            focusHUD = None

        history = scene.M4.focus_history

        if history:
            if not focusHUD:
                if debug:
                    print("   adding new draw handler")

                focusHUD = bpy.types.SpaceView3D.draw_handler_add(draw_focus_HUD, (bpy.context, (1, 1, 1), 1, 2), 'WINDOW', 'POST_PIXEL')

        elif focusHUD:
            if debug:
                print("   removing old draw handler")

            bpy.types.SpaceView3D.draw_handler_remove(focusHUD, 'WINDOW')
            focusHUD = None

surfaceslideHUD = None

def manage_surface_slide_HUD():
    global global_debug, surfaceslideHUD

    debug = global_debug

    if debug:
        print("  surface slide HUD")

    if surfaceslideHUD and "RNA_HANDLE_REMOVED" in str(surfaceslideHUD):
        surfaceslideHUD = None

    active = get_active_object(bpy.context)

    if active:
        surfaceslide = [mod for mod in active.modifiers if mod.type == 'SHRINKWRAP' and 'SurfaceSlide' in mod.name]

        if surfaceslide and not surfaceslideHUD:
            if debug:
                print("   adding new draw handler")

            surfaceslideHUD = bpy.types.SpaceView3D.draw_handler_add(draw_surface_slide_HUD, (bpy.context, (0, 1, 0), 1, 2), 'WINDOW', 'POST_PIXEL')

        elif surfaceslideHUD and not surfaceslide:
            if debug:
                print("   removing old draw handler")

            bpy.types.SpaceView3D.draw_handler_remove(surfaceslideHUD, 'WINDOW')
            surfaceslideHUD = None

screencastHUD = None

def manage_screen_cast_HUD():
    global global_debug, screencastHUD

    debug = global_debug

    if debug:
        print("  screen cast HUD")

    wm = bpy.context.window_manager

    if screencastHUD and "RNA_HANDLE_REMOVED" in str(screencastHUD):
        screencastHUD = None

    if getattr(wm, 'M3_screen_cast', False):
        if not screencastHUD:
            if debug:
                print("   adding new draw handler")

            screencastHUD = bpy.types.SpaceView3D.draw_handler_add(draw_screen_cast_HUD, (bpy.context, ), 'WINDOW', 'POST_PIXEL')

    elif screencastHUD:
        if debug:
            print("   removing old draw handler")

        bpy.types.SpaceView3D.draw_handler_remove(screencastHUD, 'WINDOW')
        screencastHUD = None

def manage_group():
    global global_debug

    debug = global_debug

    if debug:
        print("  group management")

    C = bpy.context
    scene = getattr(C, 'scene', None)
    m3 = scene.M4

    if scene and C.mode == 'OBJECT':
        active = active if (active := get_active_object(C)) and active.M4.is_group_empty and active.select_get() else None

        if m3.group_select and active:
            if debug:
                print("   auto-selecting")

            select_group_children(C.view_layer, active, recursive=m3.group_recursive_select)

        if active:
            if debug:
                print("   storing user-set empty size")

            if round(active.empty_display_size, 4) != 0.0001 and active.empty_display_size != active.M4.group_size:
                active.M4.group_size = active.empty_display_size

        if (visible := get_visible_objects(C)):

            group_empties = [obj for obj in visible if obj.M4.is_group_empty]

            if m3.group_hide:
                if debug:
                    print("   hiding/unhiding") 

                selected = [obj for obj in group_empties if obj.select_get()]
                unselected = [obj for obj in group_empties if not obj.select_get()]

                if selected:
                    for group in selected:
                        if not group.show_name:
                            group.show_name = True

                        if group.empty_display_size != group.M4.group_size:
                            group.empty_display_size = group.M4.group_size

                if unselected:
                    for group in unselected:
                        if group.show_name:
                            group.show_name = False

                        if round(group.empty_display_size, 4) != 0.0001:
                            group.M4.group_size = group.empty_display_size
                            
                            group.empty_display_size = 0.0001

            for group in group_empties:
                if group == active:
                    if not group.empty_display_type == 'SPHERE':
                        if debug:
                            print("   setting active group display type to SPHERE")

                        group.empty_display_type = 'SPHERE'

                elif group.empty_display_type == 'SPHERE':
                    if debug:
                        print("   setting inactive group display type to CUBE")

                    group.empty_display_type = 'CUBE'

def manage_legacy_group_poses():
    global global_debug

    debug = global_debug

    if debug:
        print("  legacy group poses")

    legacy_group_empties = [obj for obj in bpy.data.objects if obj.type == 'EMPTY' and obj.M4.is_group_empty and not obj.M4.group_pose_COL]

    if legacy_group_empties:
        for empty in legacy_group_empties:

            if debug:
                print(f"   legacy group: {empty.name}")

            else:
                print(f"INFO: Updating group {empty.name}'s legacy rest pose to new multi-pose format")

            empty.M4.group_pose_IDX = 0

            pose = empty.M4.group_pose_COL.add()
            pose.index = 0

            legacy_mx = empty.matrix_parent_inverse @ empty.M4.group_rest_pose

            pose.mx = legacy_mx

            pose.avoid_update = True
            pose.name = _("Inception")

            set_pose_uuid(pose)

            if not compare_quat(legacy_mx.to_quaternion(), empty.matrix_local.to_quaternion(), precision=5):
                set_group_pose(empty, name=_('LegacyPose'))

    for empty in legacy_group_empties:
        if not empty.parent:
            process_group_poses(empty)

groupposesVIEW3D = None
olddrawn = None

def manage_group_poses_VIEW3D():
    global global_debug, groupposesVIEW3D, olddrawn

    debug = global_debug

    if debug:
        print("  group poses VIEW3D")

    scene = getattr(bpy.context, 'scene', None)

    if scene:
        if groupposesVIEW3D and "RNA_HANDLE_REMOVED" in str(groupposesVIEW3D):
            groupposesVIEW3D = None

        active = active if (active := get_active_object(bpy.context)) and active.select_get() and active.type == 'EMPTY' and active.M4.is_group_empty and active.M4.group_pose_COL else None
        pose = active.M4.group_pose_COL[active.M4.group_pose_IDX] if active else None

        if active and active.M4.draw_active_group_pose and pose:

            if not groupposesVIEW3D or (active, active.M4.group_pose_IDX, active.M4.group_pose_alpha, pose.uuid, pose.index, pose.batch, pose.batchlinked, pose.mx, pose.forced_preview_update) != olddrawn:
                if pose.forced_preview_update:
                    pose.forced_preview_update = False

                olddrawn = (active, active.M4.group_pose_IDX, active.M4.group_pose_alpha, pose.uuid, pose.index, pose.batch, pose.batchlinked, pose.mx.copy(), pose.forced_preview_update)

                if debug:
                    if not groupposesVIEW3D:
                        print("   adding VIEW3D handler")
                    else:
                        print("   re-creating VIEW3D handler because active, pose preview alpha, pose uuid, pose index, mx, batch of batchlinked props")

                if groupposesVIEW3D:
                    bpy.types.SpaceView3D.draw_handler_remove(groupposesVIEW3D, 'WINDOW')

                batches = []
                get_pose_batches(bpy.context, active, pose, batches, preview_batch_poses=True)

                groupposesVIEW3D = bpy.types.SpaceView3D.draw_handler_add(draw_group_poses_VIEW3D, (pose, batches, active.M4.group_pose_alpha, ), 'WINDOW', 'POST_VIEW')

        elif groupposesVIEW3D:
            if debug:
                print("   removing VIEW3D handler because there's no active, or drawing is disabled")

            bpy.types.SpaceView3D.draw_handler_remove(groupposesVIEW3D, 'WINDOW')
            groupposesVIEW3D = None

meshmachine = None
decalmachine = None
was_asset_drop_cleanup_executed = False

def manage_asset_drop_cleanup():
    global global_debug, was_asset_drop_cleanup_executed

    debug = global_debug

    if debug:
        print("  M3 asset drop cleanup")

    if was_asset_drop_cleanup_executed:
        if debug:
            print("   skipping second (duplicate) run")

        was_asset_drop_cleanup_executed = False
        return

    if debug:
        print("   checking for asset drop cleanup")

    global meshmachine, decalmachine

    if meshmachine is None:
        meshmachine = get_addon('MESHmachine')[0]

        if meshmachine:
            import MESHmachine

            if 'manage_asset_drop_cleanup' in dir(MESHmachine.handlers):
                meshmachine = False

                if debug:
                    print("    the installed MESHmachine already manages the asset drop itself, setting MM to False")

    if decalmachine is None:
        decalmachine = get_addon('DECALmachine')[0]

        if decalmachine:
            import DECALmachine

            if 'manage_asset_drop_cleanup' in dir(DECALmachine.handlers):
                decalmachine = False

                if debug:
                    print("    the installed DECALmachine already manages the asset drop itself, setting DM to False")

    if debug:
        print("    meshmachine:", meshmachine)
        print("    decalmachine:", decalmachine)

    C = bpy.context

    if C.mode == 'OBJECT' and (meshmachine or decalmachine):
        operators = C.window_manager.operators
        active = active if (active := get_active_object(C)) and active.type == 'EMPTY' and active.instance_collection and active.instance_type == 'COLLECTION' else None

        if active and operators:
            lastop = operators[-1]

            if lastop.bl_idname == 'OBJECT_OT_transform_to_mouse':
                if debug:
                    print()
                    print("    asset drop detected!")

                visible = get_visible_objects(C)

                for obj in visible:
                    if meshmachine and obj.MM.isstashobj:
                        if debug:
                            print("     stash object:", obj.name)

                        for col in obj.users_collection:
                            if debug:
                                print(f"      unlinking from {col.name}")

                            col.objects.unlink(obj)

                    if decalmachine and obj.DM.isbackup:
                        if debug:
                            print("     decal backup object:", obj.name)

                        for col in obj.users_collection:
                            if debug:
                                print(f"      unlinking from {col.name}")

                            col.objects.unlink(obj)

            was_asset_drop_cleanup_executed = True

def manage_lights_decrease_and_visibility_sync():
    global global_debug

    debug = global_debug

    if debug:
        print("  light descrease and visiblity sync")

    scene = getattr(bpy.context, 'scene', None)

    if scene:
        m3 = scene.M4
        p = get_prefs()

        if p.activate_render and p.activate_shading_pie and p.render_adjust_lights_on_render and get_area_light_poll() and m3.adjust_lights_on_render:
            if scene.render.engine == 'CYCLES':
                last = m3.adjust_lights_on_render_last
                divider = m3.adjust_lights_on_render_divider

                if last in ['NONE', 'INCREASE'] and divider > 1:
                    if debug:
                        print("   decreasing lights for cycles when starting render")

                    m3.adjust_lights_on_render_last = 'DECREASE'
                    m3.is_light_decreased_by_handler = True

                    adjust_lights_for_rendering(mode='DECREASE', debug=debug)

        if p.activate_render and p.render_sync_light_visibility:
            if debug:
                print("   light visibility syncing")

            sync_light_visibility(scene)

def manage_lights_increase():
    global global_debug
    
    debug = global_debug

    if debug:
        print("  light increase")

    scene = getattr(bpy.context, 'scene', None)

    if scene:
        m3 = scene.M4
        p = get_prefs()

        if p.activate_render and p.activate_shading_pie and p.render_adjust_lights_on_render and get_area_light_poll() and m3.adjust_lights_on_render:
            if scene.render.engine == 'CYCLES':
                last = m3.adjust_lights_on_render_last

                if last == 'DECREASE' and m3.is_light_decreased_by_handler:
                    if debug:
                        print("   increasing lights for cycles when finshing/aborting render")

                    m3.adjust_lights_on_render_last = 'INCREASE'
                    m3.is_light_decreased_by_handler = False

                    adjust_lights_for_rendering(mode='INCREASE', debug=debug)

def pre_undo_save():
    global global_debug

    debug = global_debug

    if debug:
        print("  undo save")

    scene = getattr(bpy.context, 'scene', None)

    if scene:
        m3 = scene.M4

        if m3.use_undo_save:
            global last_active_operator

            C = bpy.context
            bprefs =  bpy.context.preferences
            
            if debug:
                print("   active operator:", C.active_operator)

            first_redo = False

            if m3.use_redo_save and C.active_operator:
                if last_active_operator != C.active_operator:
                    last_active_operator = C.active_operator
                    first_redo = True

            if C.active_operator is None or first_redo:
                temp_dir = get_temp_dir(bpy.context)

                if temp_dir:
                    if debug:
                        if first_redo:
                            print("    saving before first redo")
                        else:
                            print("    saving before undoing")

                    filepath = bpy.data.filepath

                    if filepath:
                        filename = os.path.basename(filepath)
                    else:
                        filename = "startup.blend"

                    name, ext = os.path.splitext(filename)
                    filepath = os.path.join(temp_dir, name + '_undosave' + ext)

                    if debug: 
                        print("     to temp folder:", filepath)

                    if debug:
                        start = time()

                    bpy.ops.wm.save_as_mainfile(filepath=filepath, check_existing=True, copy=True, compress=True)

                    if debug:
                        print("     save time:", time() - start)

def manage_assetbrowser_bookmarks():
    global global_debug

    debug = global_debug

    if debug:
        print("  assetbrowser bookmarks")

    validate_assetbrowser_bookmarks()

def fix_empty_display_type():
    global global_debug

    debug = global_debug

    if debug:
        print("  fix emtpy display types")

        empty_display_type = [obj for obj in get_visible_objects(bpy.context) if not obj.display_type]

        for obj in empty_display_type:
            display_type = 'WIRE' if obj.hide_render or not obj.visible_camera else 'TEXTURED'
            obj.display_type = display_type
            print(f"INFO: Restored {obj.name}'s display type to {display_type}")

@persistent
def load_post(none):
    global global_debug

    if global_debug:
        print()
        print("M4A1tools load post handler:")
        print(" reloading msgbus")

    reload_msgbus()

    if global_debug:
        print(" managing legacy group poses")

    delay_execution(manage_legacy_group_poses)

    if global_debug:
        print(" managing assetbrowser bookmarks")

    delay_execution(manage_assetbrowser_bookmarks)

    if global_debug:
        print(" fix empty display_types")

    delay_execution(fix_empty_display_type)

last_active_operator = None

@persistent
def undo_pre(scene):
    global global_debug

    if global_debug:
        print()
        print("M4A1tools undo pre handler:")

    p = get_prefs()

    if p.activate_save_pie and p.save_pie_use_undo_save:
        if global_debug:
            print(" managing pre undo save")

        delay_execution(pre_undo_save)

@persistent
def render_start(scene):
    global global_debug

    if global_debug:
        print()
        print("M4A1tools render start handler:")

    p = get_prefs()

    # if p.activate_render and (p.render_adjust_lights_on_render or p.render_enforce_hide_render):
    #     if global_debug:
    #         print(" managing light decrease and light visibility sync")
    #
    #     delay_execution(manage_lights_decrease_and_visibility_sync)

@persistent
def render_end(scene):
    global global_debug

    if global_debug:
        print()
        print("M4A1tools render cancel or complete handler:")

    p = get_prefs()

    # if p.activate_render and p.render_adjust_lights_on_render:
    #     if global_debug:
    #         print(" managing light increase")
    #
    #     delay_execution(manage_lights_increase)

@persistent
def depsgraph_update_post(scene):
    global global_debug

    if global_debug:
        print()
        print("M4A1tools depsgraph update post handler:")

    p = get_prefs()

    if p.activate_shading_pie:
        if global_debug:
            print(" managing axes HUD")

        delay_execution(manage_axes_HUD)

    if p.activate_focus:
        if global_debug:
            print(" managing focus HUD")

        delay_execution(manage_focus_HUD)

    if p.activate_surface_slide:
        if global_debug:
            print(" managing surface slide HUD")

        delay_execution(manage_surface_slide_HUD)

    if p.activate_save_pie and p.show_screencast:
        if global_debug:
            print(" managing screen cast HUD")

        delay_execution(manage_screen_cast_HUD)

    if p.activate_group:
        if global_debug:
            print(" managing group")

        delay_execution(manage_group)

    if global_debug:
        print(" managing group poses VIEW3D")

    delay_execution(manage_group_poses_VIEW3D)

    if global_debug:
        print(" managing asset drop cleanup")

    delay_execution(manage_asset_drop_cleanup)
