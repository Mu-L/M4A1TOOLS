import bpy
from bpy.types import Menu
import os
import importlib
from .. utils.registration import get_prefs, get_addon
from .. utils.ui import get_icon
from .. utils.collection import get_scene_collections
from .. utils.system import abspath, get_temp_dir
from .. utils.tools import get_tools_from_context, get_active_tool
from .. utils.light import get_area_light_poll
from .. utils.modifier import get_auto_smooth
from bpy.app.translations import pgettext as _p
wavefront_addon = None

batchops = None
boxcutter = None
hardops = None

decalmachine = None
hypercursor = None
hypercursor_version = None
hypercursorlast = None

class PieModes(Menu):
    bl_idname = "M4A1_MT_modes_pie"
    bl_label = "Modes"

    def draw(self, context):
        layout = self.layout
        toolsettings = context.tool_settings

        active = context.active_object

        global hypercursor, hypercursor_version

        if hypercursor is None or hypercursor_version is None:
            hypercursor, _, hypercursor_version, _ = get_addon("HyperCursor")

        pie = layout.menu_pie()

        if active:
            if context.mode in ['OBJECT', 'EDIT_MESH', 'EDIT_ARMATURE', 'POSE', 'EDIT_CURVE', 'EDIT_TEXT', 'EDIT_SURFACE', 'EDIT_METABALL', 'EDIT_LATTICE', 'EDIT_GPENCIL', 'PAINT_GPENCIL', 'SCULPT_GPENCIL', 'WEIGHT_GPENCIL', 'SCULPT_CURVES']:
                if active.type == 'MESH':
                    if context.area.type == "VIEW_3D":

                        if active.library:
                            blendpath = abspath(active.library.filepath)
                            library = active.library.name

                            op = pie.operator("m4a1.open_library_blend", text="Open %s" % (os.path.basename(blendpath)))
                            op.blendpath = blendpath
                            op.library = library

                        else:
                            depress = active.mode == 'EDIT' and context.scene.tool_settings.mesh_select_mode[0]
                            pie.operator("m4a1.mesh_mode", text="Vertex", depress=depress, icon_value=get_icon('vertex')).mode = 'VERT'

                            depress = active.mode == 'EDIT' and context.scene.tool_settings.mesh_select_mode[2]
                            pie.operator("m4a1.mesh_mode", text="Face", depress=depress, icon_value=get_icon('face')).mode = 'FACE'

                            depress = active.mode == 'EDIT' and context.scene.tool_settings.mesh_select_mode[1]
                            pie.operator("m4a1.mesh_mode", text="Edge", depress=depress, icon_value=get_icon('edge')).mode = 'EDGE'

                            text, icon = (_p("Edit"), get_icon('edit_mesh')) if active.mode == "OBJECT" else ("Object", get_icon('object'))
                            pie.operator("m4a1.edit_mode", text=text, icon_value=icon)

                            self.draw_mesh_modes(context, pie)

                            if context.mode == 'EDIT_MESH' and hypercursor:
                                box = pie.split()
                                column = box.column()

                                row = column.row(align=True)
                                row.scale_y = 1.2

                                row.label(text="Gizmos")

                                depress = active.HC.show_geometry_gizmo_previews if hypercursor_version < (0, 9, 16) else active.HC.geometry_gizmos_show_previews
                                row.operator("m4a1.toggle_gizmo_data_layer_preview", text="Preview", depress=depress)

                                if tuple(bpy.context.scene.tool_settings.mesh_select_mode) in [(False, True, False), (False, False, True)]:
                                    row.operator("m4a1.toggle_gizmo", text="Toggle")

                            else:
                                pie.separator()

                            if get_prefs().activate_surface_slide:
                                hassurfaceslide = [mod for mod in active.modifiers if mod.type == 'SHRINKWRAP' and 'SurfaceSlide' in mod.name]

                                if context.mode == 'EDIT_MESH':
                                    box = pie.split()
                                    column = box.column(align=True)

                                    row = column.row(align=True)
                                    row.scale_y = 1.2

                                    if hassurfaceslide:
                                        row.operator("m4a1.finish_surface_slide", text='Finish Surface Slide', icon='OUTLINER_DATA_SURFACE')
                                    else:
                                        row.operator("m4a1.surface_slide", text='Surface Slide', icon='OUTLINER_DATA_SURFACE')

                                elif hassurfaceslide:
                                    box = pie.split()
                                    column = box.column(align=True)

                                    row = column.row(align=True)
                                    row.scale_y = 1.2
                                    row.operator("m4a1.finish_surface_slide", text='Finish Surface Slide', icon='OUTLINER_DATA_SURFACE')

                                else:
                                    pie.separator()

                            else:
                                pie.separator()

                            if context.mode == "EDIT_MESH":
                                box = pie.split()
                                column = box.column()

                                row = column.row()
                                row.scale_y = 1.2
                                row.prop(context.scene.M4, "pass_through", text="Pass Through" if context.scene.M4.pass_through else "Occlude", icon="XRAY")

                                column.prop(toolsettings, "use_mesh_automerge", text="Auto Merge")

                            else:
                                pie.separator()

                    if context.area.type == "IMAGE_EDITOR":
                        toolsettings = context.scene.tool_settings

                        if context.mode == "OBJECT":
                            pie.operator("m4a1.image_mode", text="UV Edit", icon="GROUP_UVS").mode = "UV"

                            pie.operator("m4a1.image_mode", text="Paint", icon="TPAINT_HLT").mode = "PAINT"

                            pie.operator("m4a1.image_mode", text="Mask", icon="MOD_MASK").mode = "MASK"

                            pie.operator("m4a1.image_mode", text="View", icon="FILE_IMAGE").mode = "VIEW"

                        elif context.mode == "EDIT_MESH":
                            pie.operator("m4a1.uv_mode", text="Vertex", icon_value=get_icon('vertex')).mode = "VERTEX"

                            pie.operator("m4a1.uv_mode", text="Face", icon_value=get_icon('face')).mode = "FACE"

                            pie.operator("m4a1.uv_mode", text="Edge", icon_value=get_icon('edge')).mode = "EDGE"

                            pie.operator("object.mode_set", text="Object", icon_value=get_icon('object')).mode = "OBJECT"

                            pie.prop(context.scene.M4, "uv_sync_select", text="Sync Selection", icon="UV_SYNC_SELECT")

                            if toolsettings.use_uv_select_sync:
                                pie.separator()
                            else:
                                pie.operator("m4a1.uv_mode", text="Island", icon_value=get_icon('island')).mode = "ISLAND"

                            pie.separator()

                            pie.separator()

                elif active.type == 'ARMATURE':
                    pie.operator("object.mode_set", text=_p("Edit Mode"), icon='EDITMODE_HLT').mode = "EDIT"

                    pie.operator("object.mode_set", text="Pose", icon='POSE_HLT').mode = "POSE"

                    pie.separator()

                    text, icon = ("Edit", "EDITMODE_HLT") if active.mode == "OBJECT" else ("Object", "OBJECT_DATAMODE")
                    if active.mode == "POSE":
                        pie.operator("object.posemode_toggle", text=text, icon=icon)
                    else:
                        pie.operator("object.editmode_toggle", text=text, icon=icon)

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    pie.separator()

                elif active.type in ['CURVE', 'FONT', 'SURFACE', 'META', 'LATTICE']:
                    pie.operator("object.mode_set", text="Edit Mode", icon='EDITMODE_HLT').mode = "EDIT"

                    pie.separator()

                    pie.separator()

                    text, icon = ("Edit", "EDITMODE_HLT") if active.mode == "OBJECT" else ("Object", "OBJECT_DATAMODE")
                    pie.operator("object.editmode_toggle", text=text, icon=icon)

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    if bpy.context.mode in ['EDIT_SURFACE', 'EDIT_METABALL']:
                        box = pie.split()
                        column = box.column()

                        row = column.row()
                        row.scale_y = 1.2
                        row.prop(context.scene.M4, "pass_through", text="Pass Through" if context.scene.M4.pass_through else "Occlude", icon="XRAY")
                    else:
                        pie.separator()

                elif active.type == 'CURVES':

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    self.draw_hair_modes(context, pie)

                    if context.mode == 'SCULPT_CURVES':
                        box = pie.split()
                        column = box.column()
                        column.scale_y = 1.5
                        column.scale_x = 1.5

                        row = column.row(align=True)

                        domain = active.data.selection_domain

                        if domain == 'POINT':
                            row.prop(active.data, "use_sculpt_selection", text="", icon='CURVE_BEZCIRCLE')
                        else:
                            row.operator("curves.set_selection_domain", text="", icon='CURVE_BEZCIRCLE').domain = 'POINT'

                        if domain == 'CURVE':
                            row.prop(active.data, "use_sculpt_selection", text="", icon='CURVE_PATH')
                        else:
                            row.operator("curves.set_selection_domain", text="", icon='CURVE_PATH').domain = 'CURVE'

                    else:
                        pie.separator()

                    pie.separator()

                    pie.separator()

                elif active.type == 'GPENCIL':
                    gpd = context.gpencil_data

                    pie.operator("object.mode_set", text="Edit Mode", icon='EDITMODE_HLT').mode = "EDIT_GPENCIL"

                    pie.operator("object.mode_set", text="Sculpt", icon='SCULPTMODE_HLT').mode = "SCULPT_GPENCIL"

                    pie.operator("object.mode_set", text="Draw", icon='GREASEPENCIL').mode = "PAINT_GPENCIL"

                    text, icon = ("Draw", "GREASEPENCIL") if active.mode == "OBJECT" else ("Object", "OBJECT_DATAMODE")

                    if active.mode == "WEIGHT_GPENCIL":
                        pie.operator("gpencil.weightmode_toggle", text=text, icon=icon)
                    elif active.mode == "EDIT_GPENCIL":
                        pie.operator("gpencil.editmode_toggle", text=text, icon=icon)
                    elif active.mode == "SCULPT_GPENCIL":
                        pie.operator("gpencil.sculptmode_toggle", text=text, icon=icon)
                    else:
                        pie.operator("gpencil.paintmode_toggle", text=text, icon=icon)

                    self.draw_gp_modes(context, pie)

                    self.draw_gp_extra(active, pie)

                    box = pie.split()
                    column = box.column()
                    column.scale_y = 1.2
                    column.scale_x = 1.2

                    if context.mode == "PAINT_GPENCIL":
                        row = column.row(align=True)
                        row.prop(toolsettings, "use_gpencil_draw_onback", text="", icon="MOD_OPACITY")
                        row.prop(toolsettings, "use_gpencil_weight_data_add", text="", icon="WPAINT_HLT")
                        row.prop(toolsettings, "use_gpencil_draw_additive", text="", icon="FREEZE")

                    elif context.mode == "EDIT_GPENCIL":
                        row = column.row(align=True)
                        row.prop(toolsettings, "gpencil_selectmode_edit", text="", expand=True)
                        row.prop(active.data, "use_curve_edit", text="", icon='IPO_BEZIER')

                    box = pie.split()
                    column = box.column(align=True)

                    if context.mode == "EDIT_GPENCIL":
                        row = column.row(align=True)
                        row.prop(gpd, "use_multiedit", text="", icon='GP_MULTIFRAME_EDITING')

                        r = row.row(align=True)
                        r.active = gpd.use_multiedit
                        r.popover(panel="VIEW3D_PT_gpencil_multi_frame", text="Multiframe")

                        row = column.row(align=True)
                        row.popover(panel="VIEW3D_PT_tools_grease_pencil_interpolate", text="Interpolate")

                    elif context.mode == "SCULPT_GPENCIL":
                        row = column.row(align=True)
                        row.prop(toolsettings, "use_gpencil_select_mask_point", text="")
                        row.prop(toolsettings, "use_gpencil_select_mask_stroke", text="")
                        row.prop(toolsettings, "use_gpencil_select_mask_segment", text="")

                        row.separator()
                        row.prop(gpd, "use_multiedit", text="", icon='GP_MULTIFRAME_EDITING')

                        r = row.row(align=True)
                        r.active = gpd.use_multiedit
                        r.popover(panel="VIEW3D_PT_gpencil_multi_frame", text="Multiframe")

                elif active.type == 'EMPTY':

                    if get_prefs().activate_assetbrowser_tools and get_prefs().show_instance_collection_assembly_in_modes_pie:

                        if active.instance_collection and active.instance_type == 'COLLECTION':
                            pie.operator("m4a1.assemble_instance_collection", text="Assemble Instance Collection")

                        else:
                            pie.separator()

                        if active.instance_collection and active.instance_type == 'COLLECTION' and active.instance_collection.library:
                            blendpath = abspath(active.instance_collection.library.filepath)
                            library = active.instance_collection.library.name

                            op = pie.operator("m4a1.open_library_blend", text=f"Open {os.path.basename(blendpath)} Library")
                            op.blendpath = blendpath
                            op.library = library

                        else:
                            pie.separator()

                    else:

                        if active.instance_collection and active.instance_type == 'COLLECTION' and active.instance_collection.library:
                            blendpath = abspath(active.instance_collection.library.filepath)
                            library = active.instance_collection.library.name

                            op = pie.operator("m4a1.open_library_blend", text=f"Open {os.path.basename(blendpath)} Library")
                            op.blendpath = blendpath
                            op.library = library

                        else:
                            pie.separator()

                        pie.separator()

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    pie.separator()

            elif context.mode == "SCULPT":
                    pie.separator()

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    self.draw_mesh_modes(context, pie)

                    pie.separator()

                    pie.separator()

                    pie.separator()

            elif context.mode == "PAINT_TEXTURE":
                    pie.separator()

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    self.draw_mesh_modes(context, pie)

                    box = pie.split()
                    column = box.column()
                    column.scale_y = 1.5
                    column.scale_x = 1.5

                    row = column.row(align=True)
                    row.prop(active.data, "use_paint_mask", text="", icon="FACESEL")

                    pie.separator()

                    pie.separator()

            elif context.mode == "PAINT_WEIGHT":
                    pie.separator()

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    self.draw_mesh_modes(context, pie)

                    box = pie.split()
                    column = box.column()
                    column.scale_y = 1.5
                    column.scale_x = 1.5

                    row = column.row(align=True)
                    row.prop(active.data, "use_paint_mask", text="", icon="FACESEL")
                    row.prop(active.data, "use_paint_mask_vertex", text="", icon="VERTEXSEL")

                    pie.separator()

                    pie.separator()

            elif context.mode == "PAINT_VERTEX":
                    pie.separator()

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    self.draw_mesh_modes(context, pie)

                    box = pie.split()
                    column = box.column()
                    column.scale_y = 1.5
                    column.scale_x = 1.5

                    row = column.row(align=True)
                    row.prop(active.data, "use_paint_mask", text="", icon="FACESEL")
                    row.prop(active.data, "use_paint_mask_vertex", text="", icon="VERTEXSEL")

                    pie.separator()

                    pie.separator()

            elif context.mode == "PARTICLE":
                    pie.separator()

                    pie.separator()

                    pie.separator()

                    pie.separator()

                    self.draw_mesh_modes(context, pie)

                    box = pie.split()
                    column = box.column()
                    column.scale_y = 1.5
                    column.scale_x = 1.5

                    row = column.row(align=True)
                    row.prop(toolsettings.particle_edit, "select_mode", text="", expand=True)

                    pie.separator()

                    pie.separator()

        else:
            pie.separator()

            pie.separator()

            pie.separator()

            pie.separator()

            pie.separator()

            pie.separator()

            pie.separator()

            pie.separator()

    def draw_gp_modes(self, context, pie):
        box = pie.split()
        column = box.column()
        column.scale_y = 1.5
        column.scale_x = 1.5

        row = column.row(align=True)
        r = row.row(align=True)
        r.active = False if context.mode == "WEIGHT_GPENCIL" else True
        r.operator("object.mode_set", text="", icon="WPAINT_HLT").mode = 'WEIGHT_GPENCIL'
        r = row.row(align=True)
        r.active = False if context.mode == "PAINT_GPENCIL" else True
        r.operator("object.mode_set", text="", icon="GREASEPENCIL").mode = 'PAINT_GPENCIL'
        r = row.row(align=True)
        r.active = False if context.mode == "SCULPT_GPENCIL" else True
        r.operator("object.mode_set", text="", icon="SCULPTMODE_HLT").mode = 'SCULPT_GPENCIL'
        r = row.row(align=True)
        r.active = False if context.mode == "OBJECT" else True
        r.operator("object.mode_set", text="", icon="OBJECT_DATA").mode = 'OBJECT'
        r = row.row(align=True)
        r.active = False if context.mode == 'EDIT_GPENCIL' else True
        r.operator("object.mode_set", text="", icon="EDITMODE_HLT").mode = 'EDIT_GPENCIL'

    def draw_gp_extra(self, active, pie):
        box = pie.split()
        column = box.column(align=True)

        row = column.row(align=True)
        row.scale_y = 1.5

        row.operator('m4a1.shrinkwrap_grease_pencil', text='Shrinkwrap')
        row.prop(active.data, 'zdepth_offset', text='')

        opacity = [mod for mod in active.grease_pencil_modifiers if mod.type == 'GP_OPACITY']
        thickness = [mod for mod in active.grease_pencil_modifiers if mod.type == 'GP_THICK']

        if opacity:
            row = column.row(align=True)
            row.prop(opacity[0], 'factor', text='Opacity')

        if thickness:
            row = column.row(align=True)
            row.prop(thickness[0], 'thickness_factor', text='Thickness')

    def draw_mesh_modes(self, context, pie):
        box = pie.split()
        column = box.column()
        column.scale_y = 1.5
        column.scale_x = 1.5

        row = column.row(align=True)

        r = row.row(align=True)
        r.active = False if context.mode == 'PAINT_GPENCIL' else True
        r.operator("m4a1.surface_draw_mode", text="", icon="GREASEPENCIL")

        if context.active_object.particle_systems:
            r = row.row(align=True)
            r.active = False if context.mode == 'TEXTURE_PAINT' else True
            r.operator("object.mode_set", text="", icon="PARTICLEMODE").mode = 'PARTICLE_EDIT'

        r = row.row(align=True)
        r.active = False if context.mode == 'TEXTURE_PAINT' else True
        r.operator("object.mode_set", text="", icon="TPAINT_HLT").mode = 'TEXTURE_PAINT'

        r = row.row(align=True)
        r.active = False if context.mode == 'WEIGHT_PAINT' else True
        r.operator("object.mode_set", text="", icon="WPAINT_HLT").mode = 'WEIGHT_PAINT'

        r = row.row(align=True)
        r.active = False if context.mode == 'VERTEX_PAINT' else True
        r.operator("object.mode_set", text="", icon="VPAINT_HLT").mode = 'VERTEX_PAINT'

        r = row.row(align=True)
        r.active = False if context.mode == 'SCULPT' else True
        r.operator("object.mode_set", text="", icon="SCULPTMODE_HLT").mode = 'SCULPT'

        r = row.row(align=True)
        r.active = False if context.mode == 'OBJECT' else True
        r.operator("object.mode_set", text="", icon="OBJECT_DATA").mode = 'OBJECT'

        r = row.row(align=True)
        r.active = False if context.mode == 'EDIT_MESH' else True
        r.operator("object.mode_set", text="", icon="EDITMODE_HLT").mode = 'EDIT'

    def draw_hair_modes(self, context, pie):
        box = pie.split()
        column = box.column()
        column.scale_y = 1.5
        column.scale_x = 1.5

        row = column.row(align=True)

        r = row.row(align=True)
        r.active = False if context.mode == 'SCULPT_CURVES' else True
        r.operator("object.mode_set", text="", icon="SCULPTMODE_HLT").mode = 'SCULPT_CURVES'

        r = row.row(align=True)
        r.active = False if context.mode == 'OBJECT' else True
        r.operator("object.mode_set", text="", icon="OBJECT_DATA").mode = 'OBJECT'

class PieSave(Menu):
    bl_idname = "M4A1_MT_save_pie"
    bl_label = "Save, Open, Append"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        scene = context.scene
        wm = context.window_manager

        is_in_temp_dir = bpy.data.filepath and get_temp_dir(context) == os.path.dirname(bpy.data.filepath)

        pie.operator("wm.open_mainfile", text="Open...", icon_value=get_icon('open'))

        pie.operator("m4a1.save", text="Save", icon_value=get_icon('save'))

        pie.operator("m4a1.save_as", text="Save As..", icon_value=get_icon('save_as'))

        box = pie.split()

        b = box.box()
        self.draw_left_column(wm, scene, b)

        column = box.column()
        b = column.box()
        self.draw_center_column_top(context, b)

        if bpy.data.filepath:
            b = column.box()
            self.draw_center_column_bottom(b, is_in_temp_dir=is_in_temp_dir)

        b = box.box()
        self.draw_right_column(b)

        pie.separator()

        pie.separator()

        pie.operator("m4a1.new", text="New", icon_value=get_icon('new'))

        pie.operator("m4a1.save_incremental", text="Incremental Save", icon_value=get_icon('save_incremental'))

    def draw_left_column(self, wm, scene, layout):
        column = layout.column(align=True)
        column.scale_x = 1.1

        row = column.row(align=True)
        row.scale_y = 1.2
        row.operator("m4a1.load_most_recent", text="(R) Most Recent", icon_value=get_icon('open_recent'))
        row.operator("wm.call_menu", text="All Recent", icon_value=get_icon('open_recent')).name = "TOPBAR_MT_file_open_recent"

        column.separator()

        if get_prefs().save_pie_use_undo_save:
            row = column.row(align=True)
            row.prop(scene.M4, "use_undo_save", text="Undo Save", icon='LOOP_BACK')

            r = row.row(align=True)
            r.active = scene.M4.use_undo_save
            r.prop(scene.M4, "use_redo_save", text="Redo Save", icon='FILE_REFRESH')

        row = column.row(align=True)
        row.scale_y = 1.2
        row.operator("m4a1.open_temp_dir", text="Open Temp Dir", icon_value=get_icon('recover_auto_save'))

        column.operator("wm.revert_mainfile", text="Revert", icon_value=get_icon('revert'))

        # if get_prefs().show_screencast:
        #     column.separator()
        #
        #     screencast = getattr(wm, 'M3_screen_cast', False)
        #     text, icon = ('Disable', 'PAUSE') if screencast else ('Enable', 'PLAY')
        #
        #     column.operator('m4a1.screen_cast', text=f"{text} Screen Cast", depress=screencast, icon=icon)

    def draw_center_column_top(self, context, layout):
        global wavefront_addon

        if bpy.app.version <= (4, 0, 0) and wavefront_addon is None:
            wavefront_addon = get_addon('Wavefront OBJ format')[0]

        column = layout.column(align=True)

        if get_prefs().save_pie_show_obj_export:
            row = column.split(factor=0.25, align=True)
            row.label(text="OBJ")
            r = row.row(align=True)

            if wavefront_addon:
                r.operator("import_scene.obj", text="Import", icon_value=get_icon('import'))
                r.operator("export_scene.obj", text="Export", icon_value=get_icon('export')).use_selection = True if context.selected_objects else False
            else:
                r.operator("wm.obj_import", text="Import", icon_value=get_icon('import'))
                r.operator("wm.obj_export", text="Export", icon_value=get_icon('export')).export_selected_objects = True if context.selected_objects else False

        if get_prefs().save_pie_show_plasticity_export:
            row = column.split(factor=0.25, align=True)
            row.label(text="Plasticity")
            r = row.row(align=True)

            if wavefront_addon:
                op = r.operator("import_scene.obj", text="Import", icon_value=get_icon('import'))
                op.up_axis = 'Z'
                op.forward_axis = 'Y'

                op = r.operator("export_scene.obj", text="Export", icon_value=get_icon('export')).use_selection = True if context.selected_objects else False
                op.use_selection = True if context.selected_objects else False
                op.up_axis = 'Z'
                op.forward_axis = 'Y'

            else:
                op = r.operator("wm.obj_import", text="Import", icon_value=get_icon('import'))
                op.up_axis = 'Z'
                op.forward_axis = 'Y'

                op = r.operator("wm.obj_export", text="Export", icon_value=get_icon('export'))
                op.export_selected_objects = True if context.selected_objects else False
                op.up_axis = 'Z'
                op.forward_axis = 'Y'

        if get_prefs().save_pie_show_fbx_export:
            row = column.split(factor=0.25, align=True)
            row.label(text="FBX")
            r = row.row(align=True)
            r.operator("import_scene.fbx", text="Import", icon_value=get_icon('import'))

            op = r.operator("export_scene.fbx", text="Export", icon_value=get_icon('export'))
            op.use_selection = True if context.selected_objects else False

            if get_prefs().fbx_export_apply_scale_all:
                op.apply_scale_options='FBX_SCALE_ALL'

        if get_prefs().save_pie_show_usd_export:
            row = column.split(factor=0.25, align=True)
            row.label(text="USD")
            r = row.row(align=True)
            r.operator("wm.usd_import", text="Import", icon_value=get_icon('import'))

            op = r.operator("wm.usd_export", text="Export", icon_value=get_icon('export'))
            op.selected_objects_only = True if context.selected_objects else False

        if get_prefs().save_pie_show_stl_export:
            row = column.split(factor=0.25, align=True)
            row.label(text="STL")
            r = row.row(align=True)
            r.operator("import_mesh.stl", text="Import", icon_value=get_icon('import'))

            op = r.operator("export_mesh.stl", text="Export", icon_value=get_icon('export'))
            op.use_selection = True if context.selected_objects else False

    def draw_center_column_bottom(self, layout, is_in_temp_dir=False):
        column = layout.column(align=True)

        row = column.split(factor=0.5, align=True)
        row.scale_y = 1.2
        row.operator("m4a1.load_previous", text="Previous", icon_value=get_icon('open_previous'))
        row.operator("m4a1.load_next", text="Next", icon_value=get_icon('open_next'))

        if is_in_temp_dir:
            column = layout.column(align=True)
            column.label(text="You are currently in the Temp Folder", icon_value=get_icon('warning'))
            column.label(text="If you want to save, do it elsewhere!", icon='BLANK1')

    def draw_right_column(self, layout):
        column = layout.column(align=True)

        row = column.row(align=True)
        r = row.row(align=True)
        r.operator("wm.append", text="Append", icon_value=get_icon('append'))
        r.operator("wm.link", text="Link", icon_value=get_icon('link'))

        row.separator()

        r = row.row(align=True)
        r.operator("wm.call_menu", text='', icon_value=get_icon('external_data')).name = "TOPBAR_MT_file_external_data"
        r.operator("m4a1.purge_orphans", text="Purge")

        if get_prefs().activate_assetbrowser_tools and get_prefs().show_assembly_asset_creation_in_save_pie:
            column.separator()
            row = column.row()
            row.scale_y = 1.2
            row.operator("m4a1.create_assembly_asset", text="Create Assembly Asset", icon='ASSET_MANAGER')

        column.separator()
        column.operator("m4a1.clean_out_blend_file", text="Clean out .blend", icon_value=get_icon('error'))

class PieShading(Menu):
    bl_idname = "M4A1_MT_shading_pie"
    bl_label = "Shading and Overlays"

    def draw(self, context):
        global decalmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        layout = self.layout

        view = context.space_data
        active = context.active_object

        overlay = view.overlay
        shading = view.shading

        pie = layout.menu_pie()

        m3 = context.scene.M4

        text, icon = self.get_text_icon(context, "SOLID")
        pie.operator("m4a1.switch_shading", text=text, icon=icon, depress=shading.type == 'SOLID' and overlay.show_overlays).shading_type = 'SOLID'

        text, icon = self.get_text_icon(context, "MATERIAL")
        pie.operator("m4a1.switch_shading", text=text, icon=icon, depress=shading.type == 'MATERIAL' and overlay.show_overlays).shading_type = 'MATERIAL'

        pie.separator()

        box = pie.split()

        if (active and active.select_get()) or context.mode == 'EDIT_MESH':
            b = box.box()
            self.draw_object_box(context, active, view, b)

        if overlay.show_overlays and shading.type == 'SOLID':
            column = box.column()
            b = column.box()
            self.draw_overlay_box(context, active, view, b)

            b = column.box()
            self.draw_solid_box(context, view, b)

        elif overlay.show_overlays:
            b = box.box()
            self.draw_overlay_box(context, active, view, b)

        elif shading.type == 'SOLID':
            b = box.box()
            self.draw_solid_box(context, view, b)

        b = box.box()
        self.draw_shade_box(context, view, b)

        if view.shading.type in ["MATERIAL", 'RENDERED']:
            b = box.box()

            if view.shading.type == 'MATERIAL' or view.shading.type == 'RENDERED' and context.scene.render.engine == 'BLENDER_EEVEE':
                self.draw_eevee_box(context, view, b)

            elif view.shading.type == 'RENDERED' and context.scene.render.engine == 'CYCLES':
                self.draw_cycles_box(context, view, b, decalmachine)

            if get_prefs().activate_render and get_prefs().render_adjust_lights_on_render and get_area_light_poll():
                self.draw_light_adjust_box(context, m3, b)

        pie.separator()

        pie.separator()

        text, icon = self.get_text_icon(context, "WIREFRAME")
        pie.operator("m4a1.switch_shading", text=text, icon=icon, depress=shading.type == 'WIREFRAME' and overlay.show_overlays).shading_type = 'WIREFRAME'

        text, icon = self.get_text_icon(context, "RENDERED")
        pie.operator("m4a1.switch_shading", text=text, icon=icon, depress=shading.type == 'RENDERED' and overlay.show_overlays).shading_type = 'RENDERED'

    def draw_overlay_box(self, context, active, view, layout):
        m3 = context.scene.M4

        overlay = context.space_data.overlay
        perspective_type = view.region_3d.view_perspective
        is_sel_wire = any(obj.show_wire for obj in context.selected_objects)

        column = layout.column(align=True)
        row = column.row(align=True)

        row.prop(view.overlay, "show_stats", text="Stats")
        row.prop(view.overlay, "show_cursor", text="Cursor")
        row.prop(view.overlay, "show_object_origins", text="Origins")

        r = row.row(align=True)
        r.active = view.overlay.show_object_origins
        r.prop(view.overlay, "show_object_origins_all", text="All")

        if view.shading.type == 'SOLID' and view.overlay.show_overlays:
            row = column.split(factor=0.5, align=True)
            row.prop(view.shading, "show_backface_culling")
            row.prop(view.overlay, "show_relationship_lines")

        elif view.shading.type == 'SOLID':
            row = column.row(align=True)
            row.prop(view.shading, "show_backface_culling")

        elif view.overlay.show_overlays:
            row = column.row(align=True)
            row.prop(view.overlay, "show_relationship_lines")

        if view.overlay.show_overlays:
            if context.mode == 'EDIT_MESH':
                row = column.split(factor=0.5, align=True)
                row.prop(view.overlay, "show_face_orientation")
                row.prop(view.overlay, "show_extra_indices")

            elif context.mode == 'OBJECT' and get_prefs().activate_group:
                row = column.split(factor=0.5, align=True)
                row.prop(view.overlay, "show_face_orientation")
                row.prop(m3, "show_group_gizmos", toggle=True)

            else:
                row = column.row(align=True)
                row.prop(view.overlay, "show_face_orientation")

        column.separator()

        row = column.split(factor=0.4, align=True)
        row.operator("m4a1.toggle_grid", text="Grid", icon="GRID", depress=overlay.show_ortho_grid if perspective_type == 'ORTHO' and view.region_3d.is_orthographic_side_view else overlay.show_floor)
        r = row.row(align=True)
        r.active = view.overlay.show_floor
        r.prop(view.overlay, "show_axis_x", text="X", toggle=True)
        r.prop(view.overlay, "show_axis_y", text="Y", toggle=True)
        r.prop(view.overlay, "show_axis_z", text="Z", toggle=True)

        if context.mode in ['OBJECT', 'EDIT_MESH']:
            row = column.split(factor=0.4, align=True)
            icon = 'wireframe_xray' if m3.show_edit_mesh_wire else 'wireframe'

            if context.mode == 'OBJECT':
                depress = overlay.show_wireframes or is_sel_wire
                text = 'Wireframe (all + selection)' if overlay.show_wireframes and is_sel_wire else 'Wireframe (all)' if overlay.show_wireframes else 'Wireframe (selection)' if is_sel_wire else 'Wireframe'

            elif context.mode == 'EDIT_MESH':
                depress = m3.show_edit_mesh_wire
                text = 'Wireframe (xray)' if m3.show_edit_mesh_wire else 'Wireframe'

            row.operator("m4a1.toggle_wireframe", text=text, icon_value=get_icon(icon), depress=depress)

            r = row.row(align=True)

            if context.mode == "OBJECT":
                r.active = True if view.overlay.show_wireframes or (active and active.show_wire) else False
                r.prop(view.overlay, "wireframe_opacity", text="Opacity")

            elif context.mode == "EDIT_MESH":
                r.active = view.shading.show_xray
                r.prop(view.shading, "xray_alpha", text="X-Ray")

        hasaxes = m3.draw_cursor_axes or m3.draw_active_axes or any([obj.M4.draw_axes for obj in context.visible_objects])

        row = column.split(factor=0.4, align=True)
        rs = row.split(factor=0.5, align=True)
        rs.prop(m3, "draw_active_axes", text="Active", icon='EMPTY_AXIS')
        rs.prop(m3, "draw_cursor_axes", text="Cursor", icon='PIVOT_CURSOR')

        r = row.row(align=True)
        r.active = hasaxes
        r.prop(m3, "draw_axes_screenspace", text="", icon='WORKSPACE')
        r.prop(m3, "draw_axes_size", text="")
        r.prop(m3, "draw_axes_alpha", text="")

    def draw_solid_box(self, context, view, layout):
        shading = context.space_data.shading

        column = layout.column(align=True)

        row = column.split(factor=0.4, align=True)
        row.operator("m4a1.toggle_outline", text=_p("(Q) Outline"), depress=shading.show_object_outline)
        row.prop(view.shading, "object_outline_color", text="")

        hascavity = view.shading.show_cavity and view.shading.cavity_type in ['WORLD', 'BOTH']

        row = column.split(factor=0.4, align=True)
        row.operator("m4a1.toggle_cavity", text=_p("Cavity"), depress=hascavity)
        r = row.row(align=True)
        r.active = hascavity
        r.prop(view.shading, "cavity_valley_factor", text="")
        r.prop(context.scene.display, "matcap_ssao_distance", text="")

        hascurvature = view.shading.show_cavity and view.shading.cavity_type in ['SCREEN', 'BOTH']

        row = column.split(factor=0.4, align=True)
        row.operator("m4a1.toggle_curvature", text=_p("(V) Curvature"), depress=hascurvature)
        r = row.row(align=True)
        r.active = hascurvature
        r.prop(view.shading, "curvature_ridge_factor", text="")
        r.prop(view.shading, "curvature_valley_factor", text="")

    def draw_object_box(self, context, active, view, layout):
        overlay = view.overlay
        shading = view.shading

        column = layout.column(align=True)

        row = column.row()
        row = column.split(factor=0.5)
        row.prop(active, "name", text="")

        if active.type == 'ARMATURE':
            row.prop(active.data, "display_type", text="")
        else:
            row.prop(active, "display_type", text="")

        if overlay.show_overlays and shading.type in ['SOLID', 'WIREFRAME']:
            row = column.split(factor=0.5)
            r = row.row(align=True)
            r.prop(active, "show_name", text="Name")

            if active.type == 'ARMATURE':
                r.prop(active.data, "show_axes", text="Axes")
            else:
                r.prop(active.M4, "draw_axes", text="Axes")

            r = row.row(align=True)
            r.prop(active, "show_in_front", text="In Front")

            if shading.color_type == 'OBJECT':
                r.prop(active, "color", text="")

        elif overlay.show_overlays:
            row = column.split(factor=0.5)

            r = row.row(align=True)
            r.prop(active, "show_name", text="Name")

            if active.type == 'ARMATURE':
                r.prop(active.data, "show_axes", text="Axes")
            else:
                r.prop(active.M4, "draw_axes", text="Axes")

            row.separator()

        elif shading.type in ['SOLID', 'WIREFRAME']:
            if shading.color_type == 'OBJECT':
                row = column.split(factor=0.5, align=True)
                row.prop(active, "show_in_front", text="In Front")
                row.prop(active, "color", text="")

            else:
                row = column.row()
                row.prop(active, "show_in_front", text="In Front")

        if active.type == "MESH":
            mesh = active.data
            angles = [int(a) for a in get_prefs().auto_smooth_angle_presets.split(',')]

            column.separator()

            row = column.split(factor=0.55, align=True)
            r = row.row(align=True)
            r.operator("m4a1.shade", text="Smooth", icon_value=get_icon('smooth')).shade_type = 'SMOOTH'
            r.operator("m4a1.shade", text="Flat", icon_value=get_icon('flat')).shade_type = 'FLAT'

            is_auto_smooth = bool(mod := get_auto_smooth(active)) if bpy.app.version >= (4, 1, 0) else mesh.use_auto_smooth
            icon = "CHECKBOX_HLT" if is_auto_smooth else "CHECKBOX_DEHLT"

            r = row.row(align=True)
            r.operator("m4a1.toggle_auto_smooth", text="Auto Smooth", icon=icon).angle = 0

            if bpy.app.version >= (4, 1, 0) and is_auto_smooth:
                r.prop(mod, '["Socket_1"]', text="", icon='IPO_LINEAR', invert_checkbox=True)

            row = column.split(factor=0.55, align=True)
            r = row.row(align=True)
            r.active = not mesh.has_custom_normals

            for angle in angles:
                r.operator("m4a1.toggle_auto_smooth", text=str(angle)).angle = angle

            r = row.row(align=True)
            r.active = not mesh.has_custom_normals and is_auto_smooth

            if bpy.app.version >= (4, 1, 0):

                if r.active:
                    r.prop(mod, '["Input_1"]', text=_p("Auto Smooth Angle"))  # see https://blender.stackexchange.com/questions/222535/how-to-draw-inputs-from-geometry-nodes-modifier-in-a-panel and the following comment below as well
                else:
                    r.label(text=_p("Auto Smooth Angle: None"))

            else:
                r.prop(mesh, "auto_smooth_angle")

            if bpy.app.version >= (4, 1, 0) or is_auto_smooth:
                if mesh.has_custom_normals:
                    column.operator("mesh.customdata_custom_splitnormals_clear", text=_p("(N) Clear Custom Normals"))

            if active.mode == 'EDIT' and view.overlay.show_overlays:
                column.separator()

                row = column.split(factor=0.2, align=True)
                row.label(text='Normals')
                row.prop(view.overlay, "show_vertex_normals", text="", icon='NORMALS_VERTEX')
                row.prop(view.overlay, "show_split_normals", text="", icon='NORMALS_VERTEX_FACE')
                row.prop(view.overlay, "show_face_normals", text="", icon='NORMALS_FACE')

                r = row.row(align=True)
                r.active = any([view.overlay.show_vertex_normals, view.overlay.show_face_normals, view.overlay.show_split_normals])
                r.prop(view.overlay, "normals_length", text="Size")

                row = column.split(factor=0.2, align=True)
                row.label(text='Edges')
                row.prop(view.overlay, "show_edge_sharp", text="Sharp", toggle=True)
                row.prop(view.overlay, "show_edge_bevel_weight", text="Bevel", toggle=True)
                row.prop(view.overlay, "show_edge_crease", text="Creases", toggle=True)
                row.prop(view.overlay, "show_edge_seams", text="Seams", toggle=True)

        elif active.type == "CURVE" and context.mode == 'OBJECT':
            curve = active.data

            column.separator()

            row = column.split(factor=0.2, align=True)
            row.label(text='Curve')

            r = row.split(factor=0.4, align=True)
            r.prop(curve, "bevel_depth", text="Depth")
            r.prop(curve, "resolution_u")

            row = column.split(factor=0.2, align=True)
            row.label(text='Fill')

            r = row.split(factor=0.4, align=True)
            r.active = curve.bevel_depth > 0
            r.prop(curve, "fill_mode", text="")
            r.prop(curve, "bevel_resolution", text="Resolution")

            if active.mode == 'EDIT' and view.overlay.show_overlays:
                column.separator()

                splines = curve.splines
                if splines:
                    spline = curve.splines[0]
                    if spline.type == 'BEZIER':
                        row = column.split(factor=0.2, align=True)
                        row.label(text='Handles')
                        row.prop(view.overlay, "display_handle", text="")

                row = column.split(factor=0.2, align=True)
                row.label(text='Normals')

                r = row.split(factor=0.2, align=True)
                r.prop(view.overlay, "show_curve_normals", text="", icon='CURVE_PATH')
                rr = r.row(align=True)
                rr.active = view.overlay.show_curve_normals
                rr.prop(view.overlay, "normals_length", text="Length")

            column.separator()

            if bpy.app.version >= (4, 1, 0):
                row = column.split(factor=0.55, align=True)
                r = row.row(align=True)
                r.operator("m4a1.shade", text="Smooth", icon_value=get_icon('smooth')).shade_type = 'SMOOTH'
                r.operator("m4a1.shade", text="Flat", icon_value=get_icon('flat')).shade_type = 'FLAT'

            else:
                row = column.split(factor=0.5, align=True)
                row.operator("m4a1.shade", text="Smooth", icon_value=get_icon('smooth')).shade_type = 'SMOOTH'
                row.operator("m4a1.shade", text="Flat", icon_value=get_icon('flat')).shade_type = 'FLAT'

            if bpy.app.version >= (4, 1, 0):
                angles = [int(a) for a in get_prefs().auto_smooth_angle_presets.split(',')]

                is_auto_smooth = bool(mod := get_auto_smooth(active))
                icon = "CHECKBOX_HLT" if is_auto_smooth else "CHECKBOX_DEHLT"

                row.operator("m4a1.toggle_auto_smooth", text="Auto Smooth", icon=icon).angle = 0

                row = column.split(factor=0.55, align=True)
                r = row.row(align=True)

                for angle in angles:
                    r.operator("m4a1.toggle_auto_smooth", text=str(angle)).angle = angle

                r = row.row(align=True)
                r.active = is_auto_smooth

                if is_auto_smooth:
                    r.prop(mod, '["Input_1"]', text="Auto Smooth Angle")
                else:
                    r.label(text="Auto Smooth Angle: None")

        elif active.type == "SURFACE" and context.mode == 'OBJECT':
            row = column.split(factor=0.5, align=True)
            row.operator("m4a1.shade", text="Smooth", icon_value=get_icon('smooth')).shade_type = 'SMOOTH'
            row.operator("m4a1.shade", text="Flat", icon_value=get_icon('flat')).shade_type = 'FLAT'

    def draw_shade_box(self, context, view, layout):
        scene = context.scene
        m3 = scene.M4

        column = layout.column(align=True) 

        if view.shading.type == "SOLID":

            row = column.row(align=True)
            row.prop(m3, "shading_light", expand=True)

            if view.shading.light in ["STUDIO", "MATCAP"]:
                row = column.row()
                row.template_icon_view(view.shading, "studio_light", show_labels=True, scale=4, scale_popup=3)

            if view.shading.light == "STUDIO":
                row = column.split(factor=0.3, align=True)
                row.prop(view.shading, "use_world_space_lighting", text='World Space', icon='WORLD')
                r = row.row(align=True)
                r.active = view.shading.use_world_space_lighting
                r.prop(view.shading, "studiolight_rotate_z", text="Rotation")

            elif view.shading.light == "MATCAP":
                row = column.row(align=True)
                row.operator("m4a1.matcap_switch", text="(X) Matcap Switch")
                row.operator('view3d.toggle_matcap_flip', text="Matcap Flip", icon='ARROW_LEFTRIGHT')

            elif view.shading.light == "FLAT":

                if m3.use_flat_shadows:
                    row = column.split(factor=0.6, align=True)

                    col = row.column(align=True)
                    r = col.row(align=True)
                    r.scale_y = 1.25
                    r.prop(m3, "use_flat_shadows")

                    c = col.column(align=True)
                    c.active = m3.use_flat_shadows
                    c.prop(scene.display, "shadow_shift")
                    c.prop(scene.display, "shadow_focus")

                    r = row.row(align=True)
                    r.prop(scene.display, "light_direction", text="")

                else:
                    row = column.row(align=True)
                    row.scale_y = 1.25
                    row.prop(m3, "use_flat_shadows")

            row = column.row(align=True)
            row.prop(view.shading, "color_type", expand=True)

            if view.shading.color_type == 'SINGLE':
                column.prop(view.shading, "single_color", text="")

            elif view.shading.color_type == 'MATERIAL':
                column.operator("m4a1.colorize_materials", text=_p('Colorize Materials'), icon='MATERIAL')

            elif view.shading.color_type == 'OBJECT':
                r = column.split(factor=0.12, align=True)
                r.label(text="from")
                r.operator("m4a1.colorize_objects_from_active", text='Active', icon='OBJECT_DATA')
                r.operator("m4a1.colorize_objects_from_materials", text='Material', icon='MATERIAL')
                r.operator("m4a1.colorize_objects_from_collections", text='Collection', icon='OUTLINER_OB_GROUP_INSTANCE')
                r.operator("m4a1.colorize_objects_from_groups", text='Group', icon='GROUP_VERTEX')

        elif view.shading.type == "WIREFRAME":
            row = column.row()
            row.prop(view.shading, "show_xray_wireframe", text="")
            row.prop(view.shading, "xray_alpha_wireframe", text="X-Ray")

            row = column.row(align=True)
            row.prop(view.shading, "wireframe_color_type", expand=True)

        elif view.shading.type in ['MATERIAL', 'RENDERED']:

            if view.shading.type == 'RENDERED':
                row = column.split(factor=0.3, align=True)
                row.scale_y = 1.2
                row.label(text='Engine')
                row.prop(m3, 'render_engine', expand=True)
                column.separator()

            studio_worlds = [w for w in context.preferences.studio_lights if os.path.basename(os.path.dirname(w.path)) == "world"]

            if any([bpy.data.lights, studio_worlds]):
                row = column.row(align=True)

                if bpy.data.lights:
                    if view.shading.type == 'MATERIAL':
                        row.prop(view.shading, "use_scene_lights")

                    elif view.shading.type == 'RENDERED':
                        row.prop(view.shading, "use_scene_lights_render")

                if studio_worlds:
                    if view.shading.type == 'MATERIAL':
                        row.prop(view.shading, "use_scene_world")

                    elif view.shading.type == 'RENDERED':
                        row.prop(view.shading, "use_scene_world_render")

                    if scene.world:
                        row.prop(scene, 'world', text='')

                    else:
                        row.operator("m4a1.add_world", text=f"{'Set' if bpy.data.worlds else 'New'} World", icon='ADD')

                    if (view.shading.type == 'MATERIAL' and not view.shading.use_scene_world) or (view.shading.type == 'RENDERED' and not view.shading.use_scene_world_render):
                        row = column.row(align=True)
                        row.template_icon_view(view.shading, "studio_light", scale=4, scale_popup=4)

                        if (view.shading.type == 'MATERIAL' or (view.shading.type == 'RENDERED' and scene.render.engine == 'BLENDER_EEVEE')) and view.shading.studiolight_background_alpha:
                            row = column.split(factor=0.55, align=True)
                            r = row.row(align=True)
                            r.operator("m4a1.rotate_studiolight", text='+180').angle = 180
                            r.prop(view.shading, "studiolight_rotate_z", text="Rotation")
                            row.prop(view.shading, "studiolight_background_blur")
                        else:
                            row = column.split(factor=0.15, align=True)
                            row.operator("m4a1.rotate_studiolight", text='+180').angle = 180
                            row.prop(view.shading, "studiolight_rotate_z", text="Rotation")

                        row = column.split(factor=0.5, align=True)
                        row.prop(view.shading, "studiolight_intensity")
                        row.prop(view.shading, "studiolight_background_alpha")

            if not studio_worlds or (view.shading.type == 'MATERIAL' and view.shading.use_scene_world) or (view.shading.type == 'RENDERED' and view.shading.use_scene_world_render):
                world = scene.world
                if world:
                    if world.use_nodes:
                        tree = scene.world.node_tree
                        output = tree.nodes.get("World Output")

                        if output:
                            input_surf = output.inputs.get("Surface")

                            if input_surf:
                                if input_surf.links:
                                    node = input_surf.links[0].from_node

                                    if node.type == "BACKGROUND":
                                        color = node.inputs['Color']
                                        strength = node.inputs['Strength']

                                        if color.links:
                                            column.prop(strength, "default_value", text="Background Strength")
                                        else:
                                            row = column.split(factor=0.7, align=True)
                                            row.prop(strength, "default_value", text="Background Strength")
                                            row.prop(color, "default_value", text="")
            if view.shading.type == 'RENDERED':
                enforce_hide_render = get_prefs().activate_render and get_prefs().render_enforce_hide_render

                if enforce_hide_render:
                    row = column.split(factor=0.5, align=True)
                else:
                    row = column.row(align=True)

                row.prop(scene.render, 'film_transparent')

                if enforce_hide_render:
                    row.prop(m3, 'enforce_hide_render', text="Enforce hide_render")

    def draw_eevee_box(self, context, view, layout):
        column = layout.column(align=True)

        split = column.split(factor=0.3, align=True)

        row = split.row(align=True)
        row.label(text='Presets')
        row.prop(context.scene.M4, "eevee_preset_set_use_scene_lights", text='', icon='LIGHT_SUN')
        row.prop(context.scene.M4, "eevee_preset_set_use_scene_world", text='', icon='WORLD')

        row = split.row(align=True)
        row.prop(context.scene.M4, "eevee_preset", expand=True)

        row = column.split(factor=0.3, align=True)
        row.label(text='Passes')
        row.prop(view.shading, "render_pass", text='')

        if bpy.app.version >= (3, 5, 0):

            row = column.split(factor=0.3, align=True)
            row.label(text='Compositor')

            row.prop(context.scene.M4, "use_compositor", expand=True)

        col = column.column(align=True)

        icon = "TRIA_DOWN" if context.scene.eevee.use_ssr else "TRIA_RIGHT"
        col.prop(context.scene.eevee, "use_ssr", icon=icon)
        if context.scene.eevee.use_ssr:
            row = col.row(align=True)
            row.prop(context.scene.eevee, "ssr_thickness")
            row.prop(context.scene.eevee, "use_ssr_halfres")

            row = col.row(align=True)
            row.prop(context.scene.eevee, "use_ssr_refraction")

        col = column.column(align=True)

        icon = "TRIA_DOWN" if context.scene.eevee.use_gtao else "TRIA_RIGHT"
        col.prop(context.scene.eevee, "use_gtao", icon=icon)
        if context.scene.eevee.use_gtao:
            row = col.row(align=True)
            row.prop(context.scene.eevee, "gtao_distance")
            row.prop(context.scene.M4, "eevee_gtao_factor")

        col = column.column(align=True)

        icon = "TRIA_DOWN" if context.scene.eevee.use_bloom else "TRIA_RIGHT"
        col.prop(context.scene.eevee, "use_bloom", icon=icon)
        if context.scene.eevee.use_bloom:
            row = col.row(align=True)
            row.prop(context.scene.eevee, "bloom_threshold")
            row.prop(context.scene.eevee, "bloom_radius")
            row = col.row(align=True)
            row.prop(context.scene.M4, "eevee_bloom_intensity")

        col = column.column(align=True)

        icon = "TRIA_DOWN" if context.scene.eevee.use_volumetric_lights else "TRIA_RIGHT"
        col.prop(context.scene.eevee, "use_volumetric_lights", icon=icon)
        if context.scene.eevee.use_volumetric_lights:
            row = col.row(align=True)
            row.prop(context.scene.eevee, "volumetric_start")
            row.prop(context.scene.eevee, "volumetric_end")

            row = col.split(factor=0.4, align=True)
            row.prop(context.scene.eevee, "volumetric_tile_size", text='')
            row.prop(context.scene.eevee, "volumetric_samples")

            if context.scene.eevee.use_volumetric_shadows:
                row = col.split(factor=0.4, align=True)
            else:
                row = col.row(align=True)

            row.prop(context.scene.eevee, "use_volumetric_shadows", text='Shadows')
            if context.scene.eevee.use_volumetric_shadows:
                row.prop(context.scene.eevee, "volumetric_shadow_samples", text='Samples')

    def draw_cycles_box(self, context, view, layout, decalmachine):
        cycles = context.scene.cycles
        column = layout.column(align=True)

        active = active if (active := context.active_object) and active.select_get() else None

        row = column.split(factor=0.3, align=True)
        row.label(text='Cycles Settings')
        row.prop(context.scene.M4, 'cycles_device', expand=True)

        row = column.split(factor=0.297, align=True)
        row.label(text='Passes')
        row.prop(view.shading.cycles, "render_pass", text='')

        if bpy.app.version >= (3, 5, 0):

            row = column.split(factor=0.31, align=True)
            row.label(text='Compositor')
            row.prop(context.scene.M4, "use_compositor", expand=True)

        row = column.split(factor=0.33, align=True)
        row.prop(cycles, 'use_preview_denoising', text='Denoise')
        row.prop(cycles, 'use_adaptive_sampling', text='Adaptive')
        row.prop(cycles, 'seed')

        row = column.split(factor=0.5, align=True)
        row.prop(cycles, 'preview_samples', text='Viewport')
        row.prop(cycles, 'samples', text='Render')

        row = column.split(factor=0.33, align=True)
        row.prop(cycles, 'use_fast_gi', text='Fast GI')
        row.prop(cycles, 'ao_bounces', text="Viewport")
        row.prop(cycles, 'ao_bounces_render', text="Render")

        if active:
            column = layout.column(align=True)
            row = column.split(factor=0.5, align=True)
            row.prop(active, 'is_shadow_catcher')
            row.prop(active, 'is_holdout')

        use_bevel_shader = get_prefs().activate_render and get_prefs().render_use_bevel_shader

        if use_bevel_shader:
            m3 = context.scene.M4

            column = layout.column(align=True)

            split = column.split(factor=0.35, align=True)
            split.prop(m3, 'use_bevel_shader')

            row = split.row(align=True)
            row.active = m3.use_bevel_shader
            row.prop(m3, 'bevel_shader_use_dimensions', text="", icon='FULLSCREEN_ENTER')
            row.prop(m3, 'bevel_shader_samples')
            row.prop(m3, 'bevel_shader_radius', text='Width')
            op = row.operator('m4a1.adjust_bevel_shader_radius', text='', icon='TRIA_DOWN')
            op.global_radius = True
            op.decrease = True
            op = row.operator('m4a1.adjust_bevel_shader_radius', text='', icon='TRIA_UP')
            op.global_radius = True
            op.decrease = False

            if active:
                row = column.row(align=True)

                if decalmachine and active.DM.isdecal:
                    if active.parent:
                        if active.DM.decaltype == 'PANEL':
                            row.label(text="Bevel Radius of Panel Decals is modulated via the parent object!", icon='INFO')
                        else:
                            row.label(text="Bevel Shader on non-panel decals is not (yet?) supported!", icon='INFO')

                            row = column.row(align=True)
                            row.label(text='', icon='BLANK1')
                            row.label(text="Do you really need this? Email me, if so: decal@m4a1.io")

                    else:
                        row.label(text="Bevel Shader on decals without parent objects is not supported.", icon='INFO')

                else:
                    row = column.row(align=True)

                    row.active = m3.use_bevel_shader
                    row.prop(active.M4, 'bevel_shader_toggle', text="Active Object Toggle")

                    r = row.row(align=True)
                    r.active = m3.use_bevel_shader and active.M4.bevel_shader_toggle
                    r.prop(active.M4, 'bevel_shader_radius_mod', text="Active Object Factor")
                    op = r.operator('m4a1.adjust_bevel_shader_radius', text='', icon='TRIA_DOWN')
                    op.global_radius = False
                    op.decrease = True
                    op = r.operator('m4a1.adjust_bevel_shader_radius', text='', icon='TRIA_UP')
                    op.global_radius = False
                    op.decrease = False

    def draw_light_adjust_box(self, context, m3, layout):
        column = layout.column(align=True)

        row = column.row(align=True)
        row.prop(m3, 'adjust_lights_on_render', text='Adjust Lights when Rendering')
        r = row.row(align=True)
        r.active = m3.adjust_lights_on_render
        r.prop(m3, 'adjust_lights_on_render_divider', text='')

    def get_text_icon(self, context, shading):
        if context.space_data.shading.type == shading:
            text = _p("Overlays")
            icon = "OVERLAY"
        else:
            if shading == "SOLID":
                text = _p("(L) Solid")
                icon = "SHADING_SOLID"
            elif shading == "MATERIAL":
                text = _p("Material")
                icon = "SHADING_TEXTURE"
            elif shading == "RENDERED":
                text = _p("Rendered")
                icon = "SHADING_RENDERED"
            elif shading == "WIREFRAME":
                text = "Wireframe"
                icon = "SHADING_WIRE"

        return text, icon

class PieViewport(Menu):
    bl_idname = "M4A1_MT_viewport_pie"
    bl_label = "Viewport and Cameras"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        scene = context.scene
        view = context.space_data
        r3d = view.region_3d

        op = pie.operator("m4a1.view_axis", text="Front")
        op.axis='FRONT'

        op = pie.operator("m4a1.view_axis", text="Right")
        op.axis='RIGHT'

        op = pie.operator("m4a1.view_axis", text="Top")
        op.axis='TOP'

        box = pie.split()

        b = box.box()
        self.draw_camera_box(scene, view, b)

        column = box.column()
        b = column.box()
        self.draw_other_views_box(b)

        b = column.box()
        self.draw_custom_views_box(scene, b)

        b = box.box()
        self.draw_view_properties_box(context, view, r3d, b)

        pie.separator()

        pie.separator()

        if get_prefs().show_orbit_selection:
            box = pie.split()
            box.scale_y = 1.2
            box.operator("m4a1.toggle_orbit_selection", text=_p("Orbit Selection"), depress=context.preferences.inputs.use_rotate_around_active)
        else:
            pie.separator()

        if get_prefs().show_orbit_method:
            box = pie.split()
            box.scale_y = 1.2
            box.operator("m4a1.toggle_orbit_method", text=context.preferences.inputs.view_rotate_method.title())
        else:
            pie.separator()

    def draw_camera_box(self, scene, view, layout):
        column = layout.column(align=True)

        column.scale_x = 2

        row = column.row()
        row.scale_y = 1.5
        row.operator("m4a1.smart_view_cam", text="Smart View Cam", icon='HIDE_OFF')

        if view.region_3d.view_perspective == 'CAMERA':
            cams = [obj for obj in scene.objects if obj.type == "CAMERA"]

            if len(cams) > 1:
                row = column.row(align=True)
                row.operator("m4a1.next_cam", text="(Q) Previous Cam").previous = True
                row.operator("m4a1.next_cam", text="(W) Next Cam").previous = False

        row = column.split(align=True)
        row.operator("m4a1.make_cam_active")
        row.prop(scene, "camera", text="")

        row = column.split(align=True)
        row.operator("view3d.camera_to_view", text="Cam to view", icon='VIEW_CAMERA')

        text, icon = (_p("Unlock from View"), "UNLOCKED") if view.lock_camera else (_p("Lock to View"), "LOCKED")
        row.operator("wm.context_toggle", text=text, icon=icon).data_path = "space_data.lock_camera"

    def draw_other_views_box(self, layout):
        column = layout.column(align=True)

        column.scale_y = 1.2
        op = column.operator("m4a1.view_axis", text="Bottom")
        op.axis='BOTTOM'

        row = column.row(align=True)
        op = row.operator("m4a1.view_axis", text="Left")
        op.axis='LEFT'

        op = row.operator("m4a1.view_axis", text="Back")
        op.axis='BACK'

    def draw_custom_views_box(self, scene, layout):
        column = layout.column(align=True)

        row = column.split(factor=0.33, align=True)
        row.scale_y = 1.25
        row.label(text="Custom Views")
        row.prop(scene.M4, "custom_views_local", text='Local')
        row.prop(scene.M4, "custom_views_cursor", text='Cursor')

    def draw_view_properties_box(self, context, view, r3d, layout):
        column = layout.column(align=True)

        row = column.row(align=True)
        row.scale_y = 1.5

        if view.region_3d.view_perspective == 'CAMERA':
            cam = context.scene.camera

            text, icon = (_p("Orthographic"), "VIEW_ORTHO") if cam.data.type == "PERSP" else (_p("Perspective"), "VIEW_PERSPECTIVE")
            row.operator("m4a1.toggle_cam_persportho", text=text, icon=icon)

            if cam.data.type == "PERSP":
                column.prop(cam.data, "lens")

            elif cam.data.type == "ORTHO":
                column.prop(cam.data, "ortho_scale")

        else:
            text, icon = (_p("Orthographic"), "VIEW_ORTHO") if r3d.is_perspective else (_p("Perspective"), "VIEW_PERSPECTIVE")
            row.operator("m4a1.toggle_view_persportho", text=text, icon=icon)

            column.prop(view, "lens")

        column.operator("m4a1.reset_viewport", text=_p('Reset Viewport'))

class PieAlign(Menu):
    bl_idname = "M4A1_MT_align_pie"
    bl_label = "Align"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        m3 = context.scene.M4
        active = context.active_object
        sel = [obj for obj in context.selected_objects if obj != active]

        if m3.align_mode == 'AXES':
            self.draw_align_with_axes(pie, m3, sel)
        elif m3.align_mode == "VIEW":
            self.draw_align_with_view(pie, m3, sel)

    def draw_align_with_axes(self, pie, m3, sel):
        op = pie.operator("m4a1.align_editmesh", text="Y min")
        op.mode = "AXES"
        op.axis = "Y"
        op.type = "MIN"

        op = pie.operator("m4a1.align_editmesh", text="Y max")
        op.mode = "AXES"
        op.axis = "Y"
        op.type = "MAX"

        box = pie.split()
        column = box.column(align=True)

        column.separator()

        row = column.split(factor=0.2, align=True)
        row.separator()
        row.label(text="Center")

        row = column.row(align=True)
        row.scale_y = 1.2
        row.operator("m4a1.center_editmesh", text="X").axis = "X"
        row.operator("m4a1.center_editmesh", text="Y").axis = "Y"
        row.operator("m4a1.center_editmesh", text="Z").axis = "Z"

        column.separator()

        row = column.row(align=True)
        row.scale_y = 1.2
        row.operator("m4a1.straighten", text="Straighten")

        if sel:
            row = column.row(align=True)
            row.scale_y = 1.2
            row.operator("m4a1.align_object_to_vert", text="Align Object to Vert")

            row = column.row(align=True)
            row.scale_y = 1.2
            row.operator("m4a1.align_object_to_edge", text="Align Object to Edge")

        box = pie.split()
        column = box.column()

        row = column.split(factor=0.2)
        row.label(icon="ARROW_LEFTRIGHT")
        r = row.row(align=True)
        r.scale_y = 1.2
        op = r.operator("m4a1.align_editmesh", text="X")
        op.mode = "AXES"
        op.axis = "X"
        op.type = "AVERAGE"
        op = r.operator("m4a1.align_editmesh", text="Y")
        op.mode = "AXES"
        op.axis = "Y"
        op.type = "AVERAGE"
        op = r.operator("m4a1.align_editmesh", text="Z")
        op.mode = "AXES"
        op.axis = "Z"
        op.type = "AVERAGE"

        row = column.split(factor=0.2)
        row.label(icon="FREEZE")
        r = row.row(align=True)
        r.scale_y = 1.2
        op = r.operator("m4a1.align_editmesh", text="X")
        op.mode = "AXES"
        op.axis = "X"
        op.type = "ZERO"
        op = r.operator("m4a1.align_editmesh", text="Y")
        op.mode = "AXES"
        op.axis = "Y"
        op.type = "ZERO"
        op = r.operator("m4a1.align_editmesh", text="Z")
        op.mode = "AXES"
        op.axis = "Z"
        op.type = "ZERO"

        row = column.split(factor=0.2)
        row.label(icon="PIVOT_CURSOR")
        r = row.row(align=True)
        r.scale_y = 1.2
        op = r.operator("m4a1.align_editmesh", text="X")
        op.mode = "AXES"
        op.axis = "X"
        op.type = "CURSOR"
        op = r.operator("m4a1.align_editmesh", text="Y")
        op.mode = "AXES"
        op.axis = "Y"
        op.type = "CURSOR"
        op = r.operator("m4a1.align_editmesh", text="Z")
        op.mode = "AXES"
        op.axis = "Z"
        op.type = "CURSOR"

        column.separator()

        row = column.split(factor=0.15)
        row.separator()
        r = row.split(factor=0.8)
        rr = r.row(align=True)
        rr.prop(m3, "align_mode", expand=True)

        column.separator()

        op = pie.operator("m4a1.align_editmesh", text="X min")
        op.mode = "AXES"
        op.axis = "X"
        op.type = "MIN"

        op = pie.operator("m4a1.align_editmesh", text="X max")
        op.mode = "AXES"
        op.axis = "X"
        op.type = "MAX"

        op = pie.operator("m4a1.align_editmesh", text="Z min")
        op.mode = "AXES"
        op.axis = "Z"
        op.type = "MIN"

        op = pie.operator("m4a1.align_editmesh", text="Z max")
        op.mode = "AXES"
        op.axis = "Z"
        op.type = "MAX"

    def draw_align_with_view(self, pie, m3, sel):
        op = pie.operator("m4a1.align_editmesh", text="Left")
        op.mode = "VIEW"
        op.direction = "LEFT"

        op = pie.operator("m4a1.align_editmesh", text="Right")
        op.mode = "VIEW"
        op.direction = "RIGHT"

        op = pie.operator("m4a1.align_editmesh", text=_p("Bottom."))
        op.mode = "VIEW"
        op.direction = "BOTTOM"

        op = pie.operator("m4a1.align_editmesh", text=_p("Top."))
        op.mode = "VIEW"
        op.direction = "TOP"

        pie.separator()

        box = pie.split()
        column = box.column()

        row = column.row(align=True)
        row.prop(m3, "align_mode", expand=True)

        box = pie.split()
        column = box.column(align=True)

        column.separator()

        row = column.split(factor=0.25)
        row.label(text="Center")

        r = row.row(align=True)
        r.scale_y = 1.2
        op = r.operator("m4a1.center_editmesh", text="Horizontal")
        op.direction = "HORIZONTAL"
        op = r.operator("m4a1.center_editmesh", text="Vertical")
        op.direction = "VERTICAL"

        column.separator()
        row = column.split(factor=0.25, align=True)
        row.scale_y = 1.2
        row.separator()
        row.operator("m4a1.straighten", text="Straighten")

        if sel:
            row = column.split(factor=0.25, align=True)
            row.scale_y = 1.2
            row.separator()
            row.operator("m4a1.align_object_to_vert", text="Align Object to Vert")

            row = column.split(factor=0.25, align=True)
            row.scale_y = 1.2
            row.separator()
            row.operator("m4a1.align_object_to_edge", text="Align Object to Edge")

        box = pie.split()
        column = box.column(align=True)

        row = column.split(factor=0.2, align=True)
        row.label(icon="ARROW_LEFTRIGHT")

        r = row.row(align=True)
        row.scale_y = 1.2
        op = r.operator("m4a1.align_editmesh", text="Horizontal")
        op.mode = "VIEW"
        op.type = "AVERAGE"
        op.direction = "HORIZONTAL"
        op = r.operator("m4a1.align_editmesh", text="Vertical")
        op.mode = "VIEW"
        op.type = "AVERAGE"
        op.direction = "VERTICAL"

        row = column.split(factor=0.2, align=True)
        row.label(icon="FREEZE")

        r = row.row(align=True)
        r.scale_y = 1.2
        op = r.operator("m4a1.align_editmesh", text="Horizontal")
        op.mode = "VIEW"
        op.type = "ZERO"
        op.direction = "HORIZONTAL"
        op = r.operator("m4a1.align_editmesh", text="Vertical")
        op.mode = "VIEW"
        op.type = "ZERO"
        op.direction = "VERTICAL"

        row = column.split(factor=0.2, align=True)
        row.label(icon="PIVOT_CURSOR")

        r = row.row(align=True)
        row.scale_y = 1.2
        op = r.operator("m4a1.align_editmesh", text="Horizontal")
        op.mode = "VIEW"
        op.type = "CURSOR"
        op.direction = "HORIZONTAL"
        op = r.operator("m4a1.align_editmesh", text="Vertical")
        op.mode = "VIEW"
        op.type = "CURSOR"
        op.direction = "VERTICAL"

class PieUVAlign(Menu):
    bl_idname = "M4A1_MT_uv_align_pie"
    bl_label = "UV Align"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        m3 = context.scene.M4

        if m3.align_mode == 'AXES':
            self.draw_align_with_axes(pie, m3)
        elif m3.align_mode == "VIEW":
            self.draw_align_with_view(pie, m3)

    def draw_align_with_axes(self, pie, m3):
        op = pie.operator("m4a1.align_uv", text="V min")
        op.axis = "V"
        op.type = "MIN"

        op = pie.operator("m4a1.align_uv", text="V max")
        op.axis = "V"
        op.type = "MAX"

        pie.separator()

        box = pie.split()
        column = box.column()

        row = column.row(align=True)
        row.prop(m3, "align_mode", expand=True)

        column.separator()
        column.separator()

        op = pie.operator("m4a1.align_uv", text="U min")
        op.axis = "U"
        op.type = "MIN"

        op = pie.operator("m4a1.align_uv", text="U max")
        op.axis = "U"
        op.type = "MAX"

        op = pie.operator("m4a1.align_uv", text="U Cursor")
        op.axis = "U"
        op.type = "CURSOR"

        op = pie.operator("m4a1.align_uv", text="V Cursor")
        op.axis = "V"
        op.type = "CURSOR"

    def draw_align_with_view(self, pie, m3):
        op = pie.operator("m4a1.align_uv", text="Left")
        op.axis = "U"
        op.type = "MIN"

        op = pie.operator("m4a1.align_uv", text="Right")
        op.axis = "U"
        op.type = "MAX"

        op = pie.operator("m4a1.align_uv", text=_p("Bottom."))
        op.axis = "V"
        op.type = "MIN"

        op = pie.operator("m4a1.align_uv", text=_p("Top."))
        op.axis = "V"
        op.type = "MAX"

        pie.separator()

        box = pie.split()
        column = box.column()

        row = column.row(align=True)
        row.prop(m3, "align_mode", expand=True)

        pie.separator()

        box = pie.split()
        column = box.column()

        row = column.split(factor=0.2)

        row.label(icon="PIVOT_CURSOR")

        r = row.row(align=True)
        row.scale_y = 1.2
        op = r.operator("m4a1.align_uv", text="Horizontal")
        op.type = "CURSOR"
        op.axis = "U"
        op = r.operator("m4a1.align_uv", text="Vertical")
        op.type = "CURSOR"
        op.axis = "V"

class PieCursor(Menu):
    bl_idname = "M4A1_MT_cursor_pie"
    bl_label = "Cursor and Origin"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        global hypercursor

        if hypercursor is None:
            hypercursor = get_addon("HyperCursor")[0]

        if context.mode == 'EDIT_MESH':
            sel, icon = ('Vert', 'VERTEXSEL') if tuple(context.scene.tool_settings.mesh_select_mode) == (True, False, False) else ('Edge', 'EDGESEL') if tuple(context.scene.tool_settings.mesh_select_mode) == (False, True, False) else ('Face', 'FACESEL') if tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (False, False, True) else (None, None)
            pie.operator("m4a1.cursor_to_selected", text=_p("to %s") % (_p(sel)), icon="PIVOT_CURSOR")
        else:
            pie.operator("m4a1.cursor_to_selected", text="to Selected", icon="PIVOT_CURSOR")

        if context.mode == 'OBJECT':
            pie.operator("m4a1.selected_to_cursor", text="to Cursor", icon="RESTRICT_SELECT_OFF")

        else:
            pie.operator("view3d.snap_selected_to_cursor", text="to Cursor", icon="RESTRICT_SELECT_OFF").use_offset = False

        if context.mode in ['OBJECT', 'EDIT_MESH']:
            box = pie.split()
            column = box.column(align=True)

            if get_prefs().cursor_show_to_grid:
                column.separator()
                column.separator()

            if context.mode == 'OBJECT':
                row = column.split(factor=0.25)
                row.separator()
                row.label(text="Object Origin")

                column.scale_x = 1.1

                row = column.split(factor=0.5, align=True)
                row.scale_y = 1.5
                row.operator("object.origin_set", text="to Geometry", icon="MESH_DATA").type = "ORIGIN_GEOMETRY"
                row.operator("m4a1.origin_to_cursor", text="to Cursor", icon="LAYER_ACTIVE")

                row = column.split(factor=0.5, align=True)
                row.scale_y = 1.5
                row.operator("m4a1.origin_to_active", text="to Active", icon="TRANSFORM_ORIGINS")
                row.operator("m4a1.origin_to_bottom_bounds", text="to Bottom", icon="AXIS_TOP")

            elif context.mode == 'EDIT_MESH':
                row = column.split(factor=0.25)
                row.separator()
                row.label(text="Object Origin")

                column.scale_x = 1.1

                if tuple(context.scene.tool_settings.mesh_select_mode) in [(True, False, False), (False, True, False), (False, False, True)]:

                    sel, icon = ('Vert', 'VERTEXSEL') if tuple(context.scene.tool_settings.mesh_select_mode) == (True, False, False) else ('Edge', 'EDGESEL') if tuple(context.scene.tool_settings.mesh_select_mode) == (False, True, False) else ('Face', 'FACESEL') if tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (False, False, True) else (None, None)

                    row = column.row(align=True)
                    row.scale_y = 1.5
                    row.operator("m4a1.origin_to_active", text=_p("to %s") % (_p(sel)), icon=icon)
                    row.operator("m4a1.origin_to_cursor", text="to Cursor", icon='LAYER_ACTIVE')

                else:

                    row = column.split(factor=0.25, align=True)
                    row.scale_y = 1.5
                    row.separator()
                    row.operator("m4a1.origin_to_cursor", text="to Cursor", icon='LAYER_ACTIVE')

        else:
            pie.separator()

        if hypercursor and context.mode in ['OBJECT', 'EDIT_MESH']:
            tools = get_tools_from_context(context)
            pie.operator("m4a1.transform_cursor", text="   Drag Hyper Cursor", icon_value=tools['m4a1.tool_hyper_cursor']['icon_value']).mode = 'DRAG'
        else:
            pie.separator()

        pie.operator("m4a1.cursor_to_origin", text="to Origin", icon="PIVOT_CURSOR")

        pie.operator("view3d.snap_selected_to_cursor", text="to Cursor, Offset", icon="RESTRICT_SELECT_OFF").use_offset = True

        if get_prefs().cursor_show_to_grid:
            pie.operator("view3d.snap_cursor_to_grid", text="to Grid", icon="PIVOT_CURSOR")
        else:
            pie.separator()

        if get_prefs().cursor_show_to_grid:
            pie.operator("view3d.snap_selected_to_grid", text="to Grid", icon="RESTRICT_SELECT_OFF")
        else:
            pie.separator()

class PieTransform(Menu):
    bl_idname = "M4A1_MT_transform_pie"
    bl_label = "Transform"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        scene = context.scene
        m3 = context.scene.M4
        active = context.active_object

        op = pie.operator('m4a1.set_transform_preset', text='Local')
        op.pivot = 'MEDIAN_POINT'
        op.orientation = 'LOCAL'

        orientation = 'VIEW' if m3.custom_views_local or m3.custom_views_cursor else 'GLOBAL'
        op = pie.operator('m4a1.set_transform_preset', text=_p(orientation.capitalize()))
        op.pivot = 'MEDIAN_POINT'
        op.orientation = orientation

        op = pie.operator('m4a1.set_transform_preset', text='Active')
        op.pivot = 'ACTIVE_ELEMENT'
        op.orientation = 'NORMAL' if context.mode in ['EDIT_MESH', 'EDIT_ARMATURE'] else 'LOCAL'

        box = pie.split()

        b = box.box()
        column = b.column()
        self.draw_left_column(scene, column)

        b = box.box()
        column = b.column()
        self.draw_center_column(scene, column)

        b = box.box()
        column = b.column()
        self.draw_right_column(context, scene, active, column)

        pie.separator()

        pie.separator()

        op = pie.operator('m4a1.set_transform_preset', text='Individual')
        op.pivot = 'INDIVIDUAL_ORIGINS'
        op.orientation = 'NORMAL' if context.mode in ['EDIT_MESH', 'EDIT_ARMATURE'] else 'LOCAL'

        op = pie.operator('m4a1.set_transform_preset', text='Cursor')
        op.pivot = 'CURSOR'
        op.orientation = 'CURSOR'

    def draw_left_column(self, scene, layout):
        layout.scale_x = 3

        column = layout.column(align=True)
        column.label(text="Pivot Point")

        column.prop(scene.tool_settings, "transform_pivot_point", expand=True)

    def draw_center_column(self, scene, layout):
        slot = scene.transform_orientation_slots[0]
        custom = slot.custom_orientation

        column = layout.column(align=True)
        column.label(text="Orientation")

        column.prop(slot, "type", expand=True)

        column = layout.column(align=True)
        row = column.row(align=True)
        row.scale_y = 1.2
        row.operator("transform.create_orientation", text="Custom", icon='ADD', emboss=True).use = True

        if custom:
            row = column.row(align=True)
            row.prop(custom, "name", text="")
            row.operator("transform.delete_orientation", text="X", emboss=True)

    def draw_right_column(self, context, scene, active, layout):
        column = layout.column(align=True)

        if context.mode == 'OBJECT':
            column.label(text="Affect Only")

            col = column.column(align=True)
            col.scale_y = 1.2
            col.prop(scene.tool_settings, "use_transform_data_origin", text="Origins")
            col.prop(scene.tool_settings, "use_transform_pivot_point_align", text="Locations")
            col.prop(scene.tool_settings, "use_transform_skip_children", text="Parents")

            if get_prefs().activate_group and (context.active_object and context.active_object.M4.is_group_empty) or context.scene.M4.affect_only_group_origin:
                col.prop(scene.M4, "affect_only_group_origin", text="Group Origin")

        elif context.mode == 'EDIT_MESH':
            column.label(text="Transform")

            column.prop(scene.tool_settings, "use_transform_correct_face_attributes")

            row = column.row(align=True)
            row.active = scene.tool_settings.use_transform_correct_face_attributes
            row.prop(scene.tool_settings, "use_transform_correct_keep_connected")

            column.label(text="Mirror")

            row = column.row(align=True)
            row.prop(active.data, "use_mirror_x")
            row.prop(active.data, "use_mirror_y")
            row.prop(active.data, "use_mirror_z")

            row = column.row(align=True)
            row.active = any([active.data.use_mirror_x, active.data.use_mirror_y, active.data.use_mirror_z])
            row.prop(active.data, "use_mirror_topology", toggle=True)

class PieSnapping(Menu):
    bl_idname = "M4A1_MT_snapping_pie"
    bl_label = "Snapping"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        scene = context.scene
        ts = scene.tool_settings

        absolute_grid = get_prefs().snap_show_absolute_grid
        volume = get_prefs().snap_show_volume

        op = pie.operator('m4a1.set_snapping_preset', text='Vertex', depress=ts.snap_elements == {'VERTEX'} and ts.snap_target == 'CLOSEST' and not ts.use_snap_align_rotation, icon='SNAP_VERTEX')
        op.element = 'VERTEX'
        op.target = 'CLOSEST'
        op.align_rotation = False

        if absolute_grid or (absolute_grid and volume):
            op = pie.operator('m4a1.set_snapping_preset', text='Absolute Grid', depress=ts.snap_elements == {'INCREMENT'} and ts.use_snap_grid_absolute, icon='SNAP_GRID')
            op.element = 'INCREMENT'

        elif volume:
            op = pie.operator('m4a1.set_snapping_preset', text='Volume', depress=ts.snap_elements == {'VOLUME'}, icon='SNAP_VOLUME')
            op.element = 'VOLUME'

        else:
            op = pie.operator('m4a1.set_snapping_preset', text='Surface', depress=ts.snap_elements == {'FACE'} and ts.snap_target == 'MEDIAN' and ts.use_snap_align_rotation, icon='SNAP_FACE')
            op.element = 'FACE'
            op.target = 'MEDIAN'
            op.align_rotation = True

        if absolute_grid or volume:
            op = pie.operator('m4a1.set_snapping_preset', text='Surface', depress=ts.snap_elements == {'FACE'} and ts.snap_target == 'MEDIAN' and ts.use_snap_align_rotation, icon='SNAP_FACE')
            op.element = 'FACE'
            op.target = 'MEDIAN'
            op.align_rotation = True

        else:
            op = pie.operator('m4a1.set_snapping_preset', text='Edge', depress=ts.snap_elements == {'EDGE'} and ts.snap_target == 'CLOSEST' and not ts.use_snap_align_rotation, icon='SNAP_EDGE')
            op.element = 'EDGE'
            op.target = 'CLOSEST'
            op.align_rotation = False

        box = pie.split()

        b = box.box()
        column = b.column()
        self.draw_center_column(ts, column)

        pie.separator()

        pie.separator()

        if absolute_grid or volume:
            op = pie.operator('m4a1.set_snapping_preset', text='Edge', depress=ts.snap_elements == {'EDGE'} and ts.snap_target == 'CLOSEST' and not ts.use_snap_align_rotation, icon='SNAP_EDGE')
            op.element = 'EDGE'
            op.target = 'CLOSEST'
            op.align_rotation = False

        else:
            pie.separator()

        if absolute_grid and volume:
            op = pie.operator('m4a1.set_snapping_preset', text='Volume', depress=ts.snap_elements == {'VOLUME'}, icon='SNAP_VOLUME')
            op.element = 'VOLUME'

        else:
            pie.separator()

    def draw_center_column(self, tool_settings, layout):
        column = layout.column(align=True)

        if tool_settings.snap_elements == {'INCREMENT'}:
            column.scale_x = 1.5

        row = column.row(align=True)
        row.scale_y = 1.25
        row.popover(panel="VIEW3D_PT_snapping", text="More...")
        row.prop(get_prefs(), 'snap_show_volume', text='', icon='SNAP_VOLUME')
        row.prop(get_prefs(), 'snap_show_absolute_grid', text='', icon='SNAP_GRID')

        if tool_settings.snap_elements == {'INCREMENT'}:
            row = column.row(align=True)
            row.scale_y = 1.25
            row.prop(tool_settings, 'use_snap_grid_absolute')

        else:
            row = column.row(align=True)
            row.scale_y = 1.5
            row.scale_x = 0.9
            row.prop(tool_settings, 'snap_target', expand=True)

            row = column.row(align=True)
            row.scale_y = 1.25
            row.prop(tool_settings, 'use_snap_align_rotation')

class PieCollections(Menu):
    bl_idname = "M4A1_MT_collections_pie"
    bl_label = "Collections"

    def draw(self, context):
        global batchops, decalmachine

        sel = context.selected_objects
        active = context.active_object

        if batchops is None:
            batchops = get_addon("Batch Operations™")[0]
        
        if decalmachine is None:
            decalmachine = get_addon("DECALmachine")[0]

        if sel:
            collections = list(set(col for obj in sel for col in obj.users_collection if not (decalmachine and (col.DM.isdecaltypecol or col.DM.isdecalparentcol))))[:10]

            if decalmachine:
                decalparentcollections = list(set(col for obj in sel for col in obj.users_collection if col.DM.isdecalparentcol))[:10]

        else:
            if context.scene.collection.objects:
                collections = get_scene_collections(context.scene)[:9]
                collections.insert(0, context.scene.collection)

            else:
                collections = get_scene_collections(context.scene)[:10]

            if decalmachine:
                decalparentcollections = [col for col in get_scene_collections(context.scene, ignore_decals=False) if col.DM.isdecalparentcol][:10]

        if decalmachine:
            decalsname = ".Decals" if context.scene.DM.hide_decaltype_collections else "Decals"
            dcol = bpy.data.collections.get(decalsname)

        layout = self.layout
        pie = layout.menu_pie()

        if sel:
            pie.operator("m4a1.remove_from_collection", text="Remove from", icon="REMOVE")

        else:
            pie.separator()

        if sel:
            pie.operator("object.link_to_collection", text="Add to", icon="ADD")

        else:
            pie.separator()

        if sel:
            pie.operator("object.move_to_collection", text="Move to", icon="ADD")

        else:
            pie.operator("m4a1.create_collection", text="Create", icon="GROUP")

        if decalmachine and (decalparentcollections or dcol):

            if len(collections) <= 5 and len(decalparentcollections) <= 5:
                row = pie.split(factor=0.34)

            elif len(collections) > 5 and len(decalparentcollections) <= 5:
                row = pie.split(factor=0.25)
                row.scale_x = 0.8

            elif len(collections) <= 5 and len(decalparentcollections) > 5:
                row = pie.split(factor=0.25)
                row.scale_x = 0.8

            else:
                row = pie.split(factor=0.20)
                row.scale_x = 0.8

        else:
            if len(collections) <= 5:
                row = pie.split(factor=0.5)
                row.scale_x = 1.5

            elif len(collections) > 5:
                row = pie.split(factor=0.33)
                row.scale_x = 0.8

        column = row.column()

        box = column.box()
        self.draw_left_top_column(context, box)

        if decalmachine and (decalparentcollections or dcol):

            if len(collections) <= 5 and len(decalparentcollections) <= 5:
                r = row.split(factor=0.5)

            elif len(collections) > 5 and len(decalparentcollections) <= 5:
                r = row.split(factor=0.66)

            elif len(collections) <= 5 and len(decalparentcollections) > 5:
                r = row.split(factor=0.33)

            else:
                r = row.split(factor=0.5)

        else:
            r = row

        box = r.box()
        self.draw_center_column(context, batchops, sel, collections, box)

        if decalmachine and (decalparentcollections or dcol):

            column = r.column()

            if decalparentcollections:
                box = column.box()
                self.draw_right_top_column(context, batchops, sel, decalparentcollections, box)

            if dcol and dcol.DM.isdecaltypecol:
                box = column.box()
                self.draw_right_bottom_column(context, box)

        pie.separator()

        pie.separator()

        pie.separator()

        pie.separator()

    def draw_left_top_column(self, context, layout):
        column = layout.column()

        row = column.row()
        row.scale_y = 1.5
        row.operator("m4a1.purge_collections", text="Purge", icon='MONKEY')

    def draw_center_column(self, context, batchops, sel, collections, layout):
        if sel:
            layout.label(text="Scene Collections (Selection)")

        else:
            layout.label(text="Scene Collections")

        if len(collections) <= 5:
            column = layout.column(align=True)

            for col in collections:
                row = column.row(align=True)

                if col.children or col.objects:
                    icon = "RESTRICT_SELECT_ON" if col.objects and col.objects[0].hide_select else "RESTRICT_SELECT_OFF"
                    row.operator("m4a1.select_collection", text=col.name, icon=icon).name = col.name
                    row.prop(col, "hide_viewport", text="", icon="HIDE_OFF")

                else:
                    row.label(text=col.name)

                if batchops and col != context.scene.collection:
                    row.operator("batch_ops_collections.contextual_click", text="", icon="GROUP").idname = col.name

        else:
            layout.scale_x = 2

            cols1 = collections[:5]
            cols2 = collections[5:10]

            split = layout.split(factor=0.5)
            column = split.column(align=True)

            for col in cols1:
                row = column.row(align=True)
                if col.children or col.objects:
                    icon = "RESTRICT_SELECT_ON" if col.objects and col.objects[0].hide_select else "RESTRICT_SELECT_OFF"
                    row.operator("m4a1.select_collection", text=col.name, icon=icon).name = col.name
                    row.prop(col, "hide_viewport", text="", icon="HIDE_OFF")

                else:
                    row.label(text=col.name)

                if batchops:
                    row.operator("batch_ops_collections.contextual_click", text="", icon="GROUP").idname = col.name

            column = split.column(align=True)

            for col in cols2:
                row = column.row(align=True)
                if col.children or col.objects:
                    icon = "RESTRICT_SELECT_ON" if col.objects and col.objects[0].hide_select else "RESTRICT_SELECT_OFF"
                    row.operator("m4a1.select_collection", text=col.name, icon=icon).name = col.name
                    row.prop(col, "hide_viewport", text="", icon="HIDE_OFF")
                else:
                    row.label(text=col.name)

                if batchops:
                    row.operator("batch_ops_collections.contextual_click", text="", icon="GROUP").idname = col.name

    def draw_right_top_column(self, context, batchops, sel, collections, layout):
        if sel:
            layout.label(text="Decal Parent Collections (Selection)")

        else:
            layout.label(text="Decal Parent Collections")

        if len(collections) <= 5:
            column = layout.column(align=True)

            for col in collections:
                row = column.row(align=True)

                if col.children or col.objects:
                    icon = "RESTRICT_SELECT_ON" if col.objects and col.objects[0].hide_select else "RESTRICT_SELECT_OFF"
                    row.operator("m4a1.select_collection", text=col.name, icon=icon).name = col.name
                    row.prop(col, "hide_viewport", text="", icon="HIDE_OFF")

                else:
                    row.label(text=col.name)

                if batchops:
                    row.operator("batch_ops_collections.contextual_click", text="", icon="GROUP").idname = col.name

        else:
            layout.scale_x = 2

            cols1 = collections[:5]
            cols2 = collections[5:10]

            split = layout.split(factor=0.5)
            column = split.column(align=True)

            for col in cols1:
                row = column.row(align=True)
                if col.children or col.objects:
                    icon = "RESTRICT_SELECT_ON" if col.objects and col.objects[0].hide_select else "RESTRICT_SELECT_OFF"
                    row.operator("m4a1.select_collection", text=col.name, icon=icon).name = col.name
                    row.prop(col, "hide_viewport", text="", icon="HIDE_OFF")

                else:
                    row.label(text=col.name)

                if batchops:
                    row.operator("batch_ops_collections.contextual_click", text="", icon="GROUP").idname = col.name

            column = split.column(align=True)

            for col in cols2:
                row = column.row(align=True)
                if col.children or col.objects:
                    icon = "RESTRICT_SELECT_ON" if col.objects and col.objects[0].hide_select else "RESTRICT_SELECT_OFF"
                    row.operator("m4a1.select_collection", text=col.name, icon=icon).name = col.name
                    row.prop(col, "hide_viewport", text="", icon="HIDE_OFF")
                else:
                    row.label(text=col.name)

                if batchops:
                    row.operator("batch_ops_collections.contextual_click", text="", icon="GROUP").idname = col.name

    def draw_right_bottom_column(self, context, layout):
        layout.label(text="Decal Type Collections")

        row = layout.row(align=True)

        decalsname = ".Decals" if context.scene.DM.hide_decaltype_collections else "Decals"
        simplename = ".Simple" if context.scene.DM.hide_decaltype_collections else "Simple"
        subsetname = ".Subset" if context.scene.DM.hide_decaltype_collections else "Subset"
        infoname = ".Info" if context.scene.DM.hide_decaltype_collections else "Info"
        panelname = ".Panel" if context.scene.DM.hide_decaltype_collections else "Panel"

        op = row.operator("m4a1.select_collection", text="Decals")
        op.name = decalsname
        op.force_all = True

        decals = bpy.data.collections.get(decalsname)
        simple = bpy.data.collections.get(simplename)
        subset = bpy.data.collections.get(subsetname)
        info = bpy.data.collections.get(infoname)
        panel = bpy.data.collections.get(panelname)

        row.prop(decals, "hide_viewport", text="", icon="HIDE_OFF")

        if simple and simple.DM.isdecaltypecol and simple.objects:
            row.operator("m4a1.select_collection", text="Simple").name = simplename
            row.prop(simple, "hide_viewport", text="", icon="HIDE_OFF")
        else:
            row.label(text="Simple")

        if subset and subset.DM.isdecaltypecol and subset.objects:
            row.operator("m4a1.select_collection", text="Subset").name = subsetname
            row.prop(subset, "hide_viewport", text="", icon="HIDE_OFF")
        else:
            row.label(text="Subset")

        if panel and panel.DM.isdecaltypecol and panel.objects:
            row.operator("m4a1.select_collection", text="Panel").name = panelname
            row.prop(panel, "hide_viewport", text="", icon="HIDE_OFF")
        else:
            row.label(text="Panel")

        if info and info.DM.isdecaltypecol and info.objects:
            row.operator("m4a1.select_collection", text="Info").name = infoname
            row.prop(info, "hide_viewport", text="", icon="HIDE_OFF")
        else:
            row.label(text="Info")

class PieWorkspace(Menu):
    bl_idname = "M4A1_MT_workspace_pie"
    bl_label = "Workspaces"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        p = get_prefs()

        for piedir in ['left', 'right', 'bottom', 'top', 'top_left', 'top_right', 'bottom_left', 'bottom_right']:
            name = getattr(p, f'pie_workspace_{piedir}_name')
            text = getattr(p, f'pie_workspace_{piedir}_text')
            icon = getattr(p, f'pie_workspace_{piedir}_icon')

            if name:
                pie.operator("m4a1.switch_workspace", text=text if text else name, icon=icon if icon else 'BLENDER').name=name

            else:
                pie.separator()

class PieTools(Menu):
    bl_idname = "M4A1_MT_tools_pie"
    bl_label = "Tools"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        m3 = context.scene.M4

        global boxcutter, hardops, hypercursor, hypercursorlast

        if boxcutter is None:
            boxcutter = get_addon("BoxCutter")[1]

        if hardops is None:
            hardops = get_addon("Hard Ops 9")[0]

        if hypercursor is None:
            hypercursor = get_addon("HyperCursor")[0]

        tools = get_tools_from_context(context)

        if context.mode in ['OBJECT', 'EDIT_MESH']:

            if boxcutter in tools:
                tool = tools[boxcutter]
                pie.operator("m4a1.set_tool_by_name", text="   " + _p(tool['label']), depress=tool['active'], icon_value=tool['icon_value']).name = boxcutter
            else:
                pie.separator()

            if 'Hops' in tools:
                tool = tools['Hops']
                pie.operator("m4a1.set_tool_by_name", text="   " + _p(tool['label']), depress=tool['active'], icon_value=tool['icon_value']).name = 'Hops'
            else:
                pie.separator()

            if not (get_prefs().tools_show_quick_favorites and get_prefs().tools_show_tool_bar):
                if get_prefs().tools_show_quick_favorites:
                    pie.operator("wm.call_menu", text=_p("Quick Favorites")).name="SCREEN_MT_user_menu"
                elif get_prefs().tools_show_tool_bar:
                    pie.operator("wm.toolbar", text=_p("Tool Bar"))
                else:
                    pie.separator()
            else:
                pie.separator()

            if 'builtin.select_box' in tools:
                if hypercursor:
                    active_tool = get_active_tool(context).idname

                    if 'm4a1.tool_hyper_cursor' in active_tool:
                        hypercursorlast = active_tool

                    hc = hypercursorlast if hypercursorlast else 'm4a1.tool_hyper_cursor'

                    name = hc if active_tool == 'builtin.select_box' else 'builtin.select_box'
                    tool = tools[name]
                    pie.operator("m4a1.set_tool_by_name", text="   " + _p(tool['label']), depress=tool['active'], icon_value=tool['icon_value']).name=name

                else:
                    tool = tools['builtin.select_box']
                    pie.operator("m4a1.set_tool_by_name", text="   " + _p(tool['label']), depress=tool['active'], icon_value=tool['icon_value']).name='builtin.select_box'

            else:
                pie.separator()

            if get_prefs().tools_show_quick_favorites and get_prefs().tools_show_tool_bar:
                pie.operator("wm.call_menu", text=_p("Quick Favorites")).name="SCREEN_MT_user_menu"
            else:
                pie.separator()

            if get_prefs().tools_show_tool_bar and get_prefs().tools_show_quick_favorites:
                pie.operator("wm.toolbar", text=_p("Tool Bar"))
            else:
                pie.separator()

            if get_prefs().tools_show_boxcutter_presets and boxcutter in tools:
                box = pie.split()

                column = box.column(align=True)

                column.separator()
                column.separator()
                column.separator()
                column.separator()
                column.separator()
                column.separator()

                row = column.split(factor=0.25, align=True)
                row.scale_y = 1.25
                row.label(text='Box')
                op = row.operator('m4a1.set_boxcutter_preset', text='Add')
                op.shape_type = 'BOX'
                op.mode = 'MAKE'
                op.set_origin = 'BBOX'
                op = row.operator('m4a1.set_boxcutter_preset', text='Cut')
                op.shape_type = 'BOX'
                op.mode = 'CUT'

                row = column.split(factor=0.25, align=True)
                row.scale_y = 1.25
                row.label(text='Circle')
                op = row.operator('m4a1.set_boxcutter_preset', text='Add')
                op.shape_type = 'CIRCLE'
                op.mode = 'MAKE'
                op.set_origin = 'BBOX'
                op = row.operator('m4a1.set_boxcutter_preset', text='Cut')
                op.shape_type = 'CIRCLE'
                op.mode = 'CUT'

                row = column.split(factor=0.25, align=True)
                row.scale_y = 1.25
                row.label(text='NGon')
                op = row.operator('m4a1.set_boxcutter_preset', text='Add')
                op.shape_type = 'NGON'
                op.mode = 'MAKE'
                op.set_origin = 'BBOX'
                op = row.operator('m4a1.set_boxcutter_preset', text='Cut')
                op.shape_type = 'NGON'
                op.mode = 'CUT'

                column.separator()
                row = column.row(align=True)
                row.prop(m3, 'bcorientation', expand=True)

                column.separator()

                row = column.row(align=True)
                row.scale_y = 1.25
                row.operator('bc.smart_apply', icon='IMPORT')

            else:
                pie.separator()

            if get_prefs().tools_show_hardops_menu and hardops:
                HOps = importlib.import_module('HOps')

                icon = HOps.icons.get('sm_logo_white')
                pie.operator("wm.call_menu", text="Hard Ops Menu", icon_value=icon.icon_id).name="HOPS_MT_MainMenu"
            else:
                pie.separator()

from ..ui.npanels.align_helper import (set_axis, draw_ground,
                    draw_cursor_active_original,
                    draw_distribution_y, draw_distribution_x,
                    draw_center_align)
from ..utils.align_helper import screen_relevant_direction_3d_axis


class AlignHelperPieMenu(Menu):
    bl_label = 'POPOTI Align Helper'
    bl_idname = 'M4A1_MT_pie_popoti_align_helper'

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        direction = screen_relevant_direction_3d_axis(context)
        (x, x_), (y, y_) = direction
        set_axis(pie, {x_}, 'Align_Left')
        set_axis(pie, {x}, 'Align_Right')
        set_axis(pie, {y_}, 'Align_Down')
        set_axis(pie, {y}, 'Align_Up')

        draw_distribution_y(pie, y)

        col = pie.column(align=True)
        col.scale_y = 1.3
        draw_center_align(col, direction)

        draw_distribution_x(pie, x)

        col = pie.column(align=True)
        col.scale_y = 1.3
        draw_ground(col)
        draw_cursor_active_original(col)
