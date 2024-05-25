import bpy
from .. utils.registration import get_prefs
from .. utils.group import get_group_base_name, get_group_polls
from .. utils.ui import get_icon
from .. import bl_info


def get_active_object():
    return bpy.context.object

def get_active_wave_modifier(obj):
    if obj and obj.modifiers.active and obj.modifiers.active.type == 'WAVE':
        return obj.modifiers.active
    return None

def is_wave_modifier_out(obj):
    return obj.wave_modifiers_helper.direction == 'out'

def get_wave_properties(obj):
    return obj.wave_modifiers_helper

def calculate_frame_info(mod, prop, is_out):
    stop_frame = mod.time_offset + mod.damping_time + mod.lifetime
    sum_frame = int((mod.lifetime + mod.damping_time) - mod.time_offset)
    frame_start = prop.frame_start if is_out else prop.frame_zero
    frame_end = prop.frame_end if is_out else prop.frame_stop

    if not is_out:
        sum_frame = prop.frame_stop

    return sum_frame, stop_frame, frame_start, frame_end


class PanelM4N1tools(bpy.types.Panel):
    bl_idname = "M4N1_PT_m4n1_tools"
    bl_label = "M4N1tools %s" % ('.'.join([str(v) for v in bl_info['version']]))
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "M4N1"
    bl_order = 20

    @classmethod
    def poll(cls, context):
        p = get_prefs()

        if p.show_sidebar_panel:
            if context.mode == 'OBJECT':
                return p.activate_smart_drive or p.activate_unity or p.activate_group or p.activate_assetbrowser_tools
            elif context.mode == 'EDIT_MESH':
                return p.activate_extrude

    def draw(self, context):
        layout = self.layout

        m3 = context.scene.M4
        p = get_prefs()

        if context.mode == 'OBJECT':

            if p.activate_smart_drive:
                box = layout.box()
                box.prop(m3, "show_smart_drive", text="Smart Drive", icon='TRIA_DOWN' if m3.show_smart_drive else 'TRIA_RIGHT', emboss=False)

                if m3.show_smart_drive:
                    self.draw_smart_drive(m3, box)

            # if p.activate_unity:
            #     box = layout.box()
            #
            #     box.prop(m3, "show_unity", text="Unity", icon='TRIA_DOWN' if m3.show_unity else 'TRIA_RIGHT', emboss=False)
            #
            #     if m3.show_unity:
            #         self.draw_unity(context, m3, box)

            if p.activate_group:
                box = layout.box()

                box.prop(m3, "show_group", text="Group", icon='TRIA_DOWN' if m3.show_group else 'TRIA_RIGHT', emboss=False)

                if m3.show_group:
                    self.draw_group(context, m3, box)

            # if p.activate_assetbrowser_tools:
            #     box = layout.box()
            #
            #     box.prop(m3, "show_assetbrowser_tools", text="Assetbrowser Tools", icon='TRIA_DOWN' if m3.show_assetbrowser_tools else 'TRIA_RIGHT', emboss=False)
            #
            #     if m3.show_assetbrowser_tools:
            #         self.draw_assetbrowser_tools(context, box)
            # #网格形变助手
            # if p.activate_meshdeform_helper:
            #     box = layout.box()
            #
            #     box.prop(m3, "show_meshdeform_helper", text="Meshdeform Helper", icon='TRIA_DOWN' if m3.show_meshdeform_helper else 'TRIA_RIGHT', emboss=False)
            #
            #     if m3.show_meshdeform_helper:
            #         b = box.box()
            #         column=b.column(align=True)
            #         column.operator('m4n1.convex_meshdeform', text="Create convex hull")
            #         column.operator("m4n1.bind_meshdeform")
            #         column.operator("m4n1.apply_meshdeform")
            #对齐助手
            if p.activate_align_helper_pie:
                box = layout.box()

                box.prop(m3, "show_align_helper", text="Align Helper", icon='TRIA_DOWN' if m3.show_align_helper else 'TRIA_RIGHT', emboss=False)

                if m3.show_align_helper:
                    b = box.box()
                    sp = b.split(factor=0.4, align=True)
                    a = sp.row(align=True)
                    b = sp.row(align=True)

                    b.scale_y = a.scale_x = a.scale_y = 1.5
                    from .npanels.align_helper import draw_left,draw_right
                    pref = get_prefs()
                    if not pref.ah_show_text:
                        b.scale_x = 2
                    if getattr(context.space_data, 'region_3d', False):
                        draw_left(a, context)
                        draw_right(b, context)
            #波浪修改器
            if bpy.context.object.type=='MESH':
                mod = bpy.context.object.modifiers.active
                if p.activate_wave_modifier and mod and (mod.type == 'WAVE'):
                    box = layout.box()
                    box.prop(m3, "show_wave_modifier", text="Wave Modifier", icon='TRIA_DOWN' if m3.show_wave_modifier else 'TRIA_RIGHT', emboss=False)
                    if m3.show_wave_modifier :
                        column = box.column(align=True)
                        b = column.box()
                        b.label(text="Wave Modifier")
                        b.use_property_split = True

                        prop = bpy.context.object.wave_modifiers_helper

                        col = b.column()

                        row = col.row(align=True, heading='Motion')
                        row.prop(mod, 'use_x', expand=True, toggle=1)
                        row.prop(mod, 'use_y', expand=True, toggle=1)

                        col.prop(mod, 'use_cyclic')

                        row = col.row(align=False, heading='Along Normals')
                        row.prop(mod, 'use_normal', text='')

                        row.prop(mod, 'use_normal_x', expand=True, toggle=1, text='X')
                        row.prop(mod, 'use_normal_y', expand=True, toggle=1, text='Y')
                        row.prop(mod, 'use_normal_z', expand=True, toggle=1, text='Z')

                        col.prop(mod, 'falloff_radius', text='Falloff')
                        col.prop(mod, 'height')

                        row = col.row(align=True)
                        row.prop(prop, 'width')
                        row.prop(prop, 'width_use_high_precision',
                                 icon='PREFERENCES',
                                 icon_only=True)

                        col.prop(prop, 'space')

                        row = col.row()
                        row.prop(prop, 'direction', expand=True)

                        col.separator()

                        col.prop_search(mod,
                                        "vertex_group",
                                        context.object,
                                        "vertex_groups",
                                        text="Vertex Groups")
                        b2 = column.box()
                        b2.label(text="Animation")
                        # def draw_wave_animation(context):
                        # layout = bpy.context.area.regions.type('UI').layout
                        b2.use_property_split = True

                        obj = get_active_object()
                        mod = get_active_wave_modifier(obj)
                        prop = get_wave_properties(obj)

                        # if mod and prop:
                        is_out = is_wave_modifier_out(obj)
                        sum_frame, stop_frame, frame_start, frame_end = calculate_frame_info(mod, prop, is_out)

                        row = b2.row(align=True)
                        row.prop(prop, 'frequency')
                        row.prop(prop, 'cycle', icon='FILE_REFRESH', icon_only=True)

                        if prop.cycle:
                            b2.prop(prop, 'offset')
                            b2.separator()
                            col = b2
                        else:
                            b2.separator()
                            col = b2.column(align=True)
                            if is_out:
                                col.prop(prop, 'frame_start')
                                col.prop(prop, 'frame_end')
                            else:
                                col.prop(prop, 'frame_zero')
                                col.prop(prop, 'frame_stop')
                            col.prop(mod, 'damping_time', text='Damping')
                            col.separator()

                        scene = bpy.context.scene
                        if prop.cycle:
                            col.label(text=f'Total frame count for looping: {scene.frame_end - scene.frame_start}')
                        else:
                            col.label(text=f'Total frame count for motion: {round(sum_frame, 2)}')
                            col.label(text=f'{"Frame Start" if is_out else "Frame Zero"}: {frame_start}')
                            col.label(text=f'{"Frame End" if is_out else "Frame Stop"}: {frame_end}')
                            col.label(text=f'Full stop frame: {round(stop_frame, 2)}')



        elif context.mode == 'EDIT_MESH':

            if p.activate_extrude:
                box = layout.box()

                box.prop(m3, "show_extrude", text="Extrude", icon='TRIA_DOWN' if m3.show_extrude else 'TRIA_RIGHT', emboss=False)

                if m3.show_extrude:
                    self.draw_extrude(context, m3, box)

    def draw_smart_drive(self, m3, layout):
        column = layout.column()

        b = column.box()
        b.label(text="Driver")

        col = b.column(align=True)

        row = col.split(factor=0.25, align=True)
        row.label(text="Values")
        r = row.row(align=True)
        op = r.operator("m4n1.set_driver_value", text='', icon='SORT_ASC')
        op.mode = 'DRIVER'
        op.value = 'START'
        r.prop(m3, 'driver_start', text='')
        r.operator("m4n1.switch_driver_values", text='', icon='ARROW_LEFTRIGHT').mode = 'DRIVER'
        r.prop(m3, 'driver_end', text='')
        op = r.operator("m4n1.set_driver_value", text='', icon='SORT_ASC')
        op.mode = 'DRIVER'
        op.value = 'END'

        row = col.split(factor=0.25, align=True)
        row.label(text="Transform")
        r = row.row(align=True)
        r.prop(m3, 'driver_transform', expand=True)

        row = col.split(factor=0.25, align=True)
        row.scale_y = 0.9
        row.label(text="Axis")
        r = row.row(align=True)
        r.prop(m3, 'driver_axis', expand=True)

        row = col.split(factor=0.25, align=True)
        row.label(text="Space")
        r = row.row(align=True)
        r.prop(m3, 'driver_space', expand=True)

        b = column.box()
        b.label(text="Driven")

        col = b.column(align=True)

        row = col.split(factor=0.25, align=True)
        row.label(text="Values")
        r = row.row(align=True)
        op = r.operator("m4n1.set_driver_value", text='', icon='SORT_ASC')
        op.mode = 'DRIVEN'
        op.value = 'START'
        r.prop(m3, 'driven_start', text='')
        r.operator("m4n1.switch_driver_values", text='', icon='ARROW_LEFTRIGHT').mode = 'DRIVEN'
        r.prop(m3, 'driven_end', text='')
        op = r.operator("m4n1.set_driver_value", text='', icon='SORT_ASC')
        op.mode = 'DRIVEN'
        op.value = 'END'

        row = col.split(factor=0.25, align=True)
        row.label(text="Transform")
        r = row.row(align=True)
        r.prop(m3, 'driven_transform', expand=True)

        row = col.split(factor=0.25, align=True)
        row.scale_y = 0.9
        row.label(text="Axis")
        r = row.row(align=True)
        r.prop(m3, 'driven_axis', expand=True)

        row = col.split(factor=0.25, align=True)
        row.label(text="Limit")
        r = row.row(align=True)
        r.prop(m3, 'driven_limit', expand=True)

        r = column.row()
        r.scale_y = 1.2
        r.operator("m4n1.smart_drive", text='Drive it!', icon='AUTO')

    def draw_unity(self, context, m3, layout):
        all_prepared = True if context.selected_objects and all([obj.M4.unity_exported for obj in context.selected_objects]) else False

        column = layout.column(align=True)

        row = column.split(factor=0.3)
        row.label(text="Export")
        row.prop(m3, 'unity_export', text='True' if m3.unity_export else 'False', toggle=True)

        row = column.split(factor=0.3)
        row.label(text="Triangulate")
        row.prop(m3, 'unity_triangulate', text='True' if m3.unity_triangulate else 'False', toggle=True)

        column.separator()

        if m3.unity_export:
            column.prop(m3, 'unity_export_path', text='')

            if all_prepared:
                row = column.row(align=True)
                row.scale_y = 1.5

                if m3.unity_export_path:
                    row.operator_context = 'EXEC_DEFAULT'

                op = row.operator("export_scene.fbx", text='Export')
                op.use_selection = True
                op.apply_scale_options = 'FBX_SCALE_ALL'

                if m3.unity_export_path:
                    op.filepath = m3.unity_export_path

        if not m3.unity_export or not all_prepared:
            row = column.row(align=True)
            row.scale_y = 1.5
            row.operator("m4n1.prepare_unity_export", text="Prepare + Export %s" % ('Selected' if context.selected_objects else 'Visible') if m3.unity_export else "Prepare %s" % ('Selected' if context.selected_objects else 'Visible')).prepare_only = False

        row = column.row(align=True)
        row.scale_y = 1.2
        row.operator("m4n1.restore_unity_export", text="Restore Transformations")

    def draw_group(self, context, m3, layout):
        p = get_prefs()

        active_group, active_child, group_empties, groupable, ungroupable, addable, removable, selectable, duplicatable, groupifyable, batchposable = get_group_polls(context)

        box = layout.box()

        if group_empties:

            b = box.box()
            b.label(text='Group Gizmos')

            split = b.split(factor=0.5, align=True)

            split.prop(m3, 'show_group_gizmos', text="Global Group Gizmos", toggle=True, icon='HIDE_OFF' if m3.show_group_gizmos else 'HIDE_ON')

            row = split.row(align=True)
            row.prop(m3, 'group_gizmo_size', text='Size')

            r = row.row(align=True)
            r.active = m3.group_gizmo_size != 1
            op = r.operator('wm.context_set_float', text='', icon='LOOP_BACK')
            op.data_path = 'scene.M4.group_gizmo_size'
            op.value = 1
            r.operator('m4n1.bake_group_gizmo_size', text='', icon='SORT_ASC')

            if active_group:
                empty = context.active_object

                prefix, basename, suffix = get_group_base_name(empty.name)

                b = box.box()
                b.label(text='Active Group')

                row = b.row(align=True)
                row.alignment = 'LEFT'
                row.label(text='', icon='SPHERE')

                if prefix:
                    r = row.row(align=True)
                    r.alignment = 'LEFT'
                    r.active = False
                    r.label(text=prefix)

                r = row.row(align=True)
                r.alignment = 'LEFT'
                r.active = True
                r.label(text=basename)

                if suffix:
                    r = row.row(align=True)
                    r.alignment = 'LEFT'
                    r.active = False
                    r.label(text=suffix)

                row = b.row()
                row.scale_y = 1.25

                if m3.affect_only_group_origin:
                    row.prop(m3, "affect_only_group_origin", text="Disable, when done!", toggle=True, icon_value=get_icon('error'))
                else:
                    row.prop(m3, "affect_only_group_origin", text="Adjust Group Origin", toggle=True, icon='OBJECT_ORIGIN')

                if m3.show_group_gizmos:
                    column = b.column(align=True)
                    split = column.split(factor=0.5, align=True)

                    split.prop(empty.M4, 'show_group_gizmo', text="Group Gizmos", toggle=True, icon='HIDE_OFF' if empty.M4.show_group_gizmo else 'HIDE_ON')

                    row = split.row(align=True)
                    row.prop(empty.M4, 'group_gizmo_size', text='Size')

                    r = row.row(align=True)
                    r.active = empty.M4.group_gizmo_size != 1
                    op = r.operator('wm.context_set_float', text='', icon='LOOP_BACK')
                    op.data_path = 'active_object.M4.group_gizmo_size'
                    op.value = 1

                    row = column.row(align=True)
                    row.active = empty.M4.show_group_gizmo
                    row.prop(empty.M4, 'show_group_x_rotation', text="X", toggle=True)
                    row.prop(empty.M4, 'show_group_y_rotation', text="Y", toggle=True)
                    row.prop(empty.M4, 'show_group_z_rotation', text="Z", toggle=True)

                row = b.row()

                split = row.split(factor=0.3)
                split.label(text="Poses")

                if empty.M4.group_pose_COL and empty.M4.group_pose_IDX >= 0:
                    row = split.row(align=True)
                    row.prop(empty.M4, 'draw_active_group_pose', text='Preview', icon='HIDE_OFF' if empty.M4.draw_active_group_pose else 'HIDE_ON')

                    r = row.row(align=True)
                    r.enabled = empty.M4.draw_active_group_pose
                    r.prop(empty.M4, 'group_pose_alpha', text='Alpha.')

                column = b.column()

                if empty.M4.group_pose_COL:
                    column.template_list("M4N1_UL_group_poses", "", empty.M4, "group_pose_COL", empty.M4, "group_pose_IDX", rows=max(len(empty.M4.group_pose_COL), 1))

                else:
                    column.active = False
                    column.label(text=" None")

                split = b.split(factor=0.3, align=True)
                split.scale_y = 1.25
                split.operator('m4n1.set_group_pose', text='Set Pose', icon='ARMATURE_DATA').batch = False

                s = split.split(factor=0.6, align=True)
                row = s.row(align=True)
                row.enabled = batchposable
                row.operator('m4n1.set_group_pose', text='Set Batch Pose', icon='LINKED').batch = True

                s.operator('m4n1.update_group_pose', text='Update', icon='FILE_REFRESH')

        b = box.box()
        b.label(text='Settings')

        column = b.column(align=True)

        row = column.split(factor=0.3, align=True)
        row.label(text="Auto Select")
        r = row.row(align=True)

        if not p.use_group_sub_menu:
            r.prop(m3, 'show_group_select', text='', icon='HIDE_OFF' if m3.show_group_select else 'HIDE_ON')

        r.prop(m3, 'group_select', text='True' if m3.group_select else 'False', toggle=True)

        row = column.split(factor=0.3, align=True)
        row.label(text="Recursive")
        r = row.row(align=True)

        if not p.use_group_sub_menu:
            r.prop(m3, 'show_group_recursive_select', text='', icon='HIDE_OFF' if m3.show_group_recursive_select else 'HIDE_ON')

        r.prop(m3, 'group_recursive_select', text='True' if m3.group_recursive_select else 'False', toggle=True)

        row = column.split(factor=0.3, align=True)
        row.label(text="Hide Empties")
        r = row.row(align=True)

        if not p.use_group_sub_menu:
            r.prop(m3, 'show_group_hide', text='', icon='HIDE_OFF' if m3.show_group_hide else 'HIDE_ON')

        r.prop(m3, 'group_hide', text='True' if m3.group_hide else 'False', toggle=True)

        b = box.box()
        b.label(text='Tools')

        column = b.column(align=True)

        row = column.row(align=True)
        row.scale_y = 1.2
        r = row.row(align=True)
        r.active = groupable
        r.operator("m4n1.group", text="Group.")
        r = row.row(align=True)
        r.active = ungroupable
        r.operator("m4n1.ungroup", text="Un-Group")
        r = row.row(align=True)

        row = column.row(align=True)
        row.scale_y = 1
        r.active = groupifyable
        row.operator("m4n1.groupify", text="Groupify")

        column.separator()
        column = column.column(align=True)

        row = column.row(align=True)
        row.scale_y = 1.2
        r = row.row(align=True)
        r.active = selectable
        r.operator("m4n1.select_group", text="Select Group")
        r = row.row(align=True)
        r.active = duplicatable
        r.operator("m4n1.duplicate_group", text="Duplicate Group")

        column = column.column(align=True)

        row = column.row(align=True)
        row.scale_y = 1.2
        r = row.row(align=True)
        r.active = addable and (active_group or active_child)
        r.operator("m4n1.add_to_group", text="Add to Group")
        r = row.row(align=True)
        r.active = removable
        r.operator("m4n1.remove_from_group", text="Remove from Group")

    def draw_extrude(self, context, m3, layout):
        column = layout.column(align=True)

        row = column.row(align=True)
        row.scale_y = 1.2
        row.operator("m4n1.cursor_spin", text='Cursor Spin')
        row.operator("m4n1.punch_it", text='Punch It', icon_value=get_icon('fist'))

    def draw_assetbrowser_tools(self, context, layout):
        column = layout.column(align=True)
        column.scale_y = 1.2

        column.operator("m4n1.create_assembly_asset", text='Create Assembly Asset', icon='ASSET_MANAGER')
        column.operator("m4n1.assemble_instance_collection", text='Assemble Instance Collection', icon='NETWORK_DRIVE')
