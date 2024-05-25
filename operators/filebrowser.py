import bpy
from bpy.props import StringProperty, BoolProperty
import os
from .. utils.draw import draw_fading_label
from .. utils.system import abspath, open_folder
from .. utils.property import step_list
from .. utils.asset import get_asset_library_reference, get_registered_library_references, set_asset_library_reference, get_asset_import_method, set_asset_import_method, get_asset_details_from_space, get_asset_ids
from .. utils.workspace import get_window_region_from_area, get_3dview_area
from .. utils.registration import get_prefs
from .. colors import red

class Open(bpy.types.Operator):
    bl_idname = "m4a1.filebrowser_open"
    bl_label = "M4A1: Open in System's filebrowser"
    bl_description = "Open the current location in the System's own filebrowser\nALT: Open .blend file"

    path: StringProperty(name="Path")
    blend_file: BoolProperty(name="Open .blend file")

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'FILE_BROWSER'

    def execute(self, context):
        space = context.space_data
        params = space.params

        directory = abspath(params.directory.decode())
        active_file = context.active_file

        active, id_type, local_id = get_asset_ids(context)

        if active:

            if self.blend_file:
                if active_file.asset_data:

                    if not local_id:
                        bpy.ops.asset.open_containing_blend_file()

                    else:

                        area = get_3dview_area(context)

                        if area:
                            region, region_data = get_window_region_from_area(area)

                            with context.temp_override(area=area, region=region, region_data=region_data):
                                draw_fading_label(context, text="The blend file containing this asset is already open.", color=red)

                else:
                    path = os.path.join(directory, active_file.relative_path)
                    bpy.ops.m4a1.open_library_blend(blendpath=path)

            else:

                if active_file.asset_data:
                    _, libpath, _, _ = get_asset_details_from_space(context, space, debug=False)

                    if libpath:
                        open_folder(libpath)

                else:
                    open_folder(directory)

            return {'FINISHED'}
        return {'CANCELLED'}

class Toggle(bpy.types.Operator):
    bl_idname = "m4a1.filebrowser_toggle"
    bl_label = "M4A1: Toggle Filebrowser"
    bl_description = ""

    type: StringProperty()

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'FILE_BROWSER'

    def execute(self, context):
        params = context.space_data.params

        if self.type == 'SORT':

            if context.area.ui_type == 'FILES':
                if params.sort_method == 'FILE_SORT_ALPHA':
                    params.sort_method = 'FILE_SORT_TIME'

                else:
                    params.sort_method = 'FILE_SORT_ALPHA'

            elif context.area.ui_type == 'ASSETS':
                asset_libraries = get_registered_library_references(context)

                current = get_asset_library_reference(params)
                next = step_list(current, asset_libraries, 1)
                set_asset_library_reference(params, next)

        elif self.type == 'DISPLAY_TYPE':

            if context.area.ui_type == 'FILES':
                if params.display_type == 'LIST_VERTICAL':
                    params.display_type = 'THUMBNAIL'

                else:
                    params.display_type = 'LIST_VERTICAL'

            elif context.area.ui_type == 'ASSETS':

                current = get_asset_library_reference(params)

                if current != 'LOCAL':
                    import_methods = ['LINK', 'APPEND', 'APPEND_REUSE']

                    if bpy.app.version >= (3, 5, 0):
                        import_methods.insert(0, 'FOLLOW_PREFS')

                    current = get_asset_import_method(params)
                    next = step_list(current, import_methods, 1)
                    set_asset_import_method(params, next)

        elif self.type == 'HIDDEN':
            if context.area.ui_type == 'FILES':
                params.show_hidden = not params.show_hidden
                params.use_filter_backup = params.show_hidden

        return {'FINISHED'}

class CycleThumbs(bpy.types.Operator):
    bl_idname = "m4a1.filebrowser_cycle_thumbnail_size"
    bl_label = "M4A1: Cycle Thumbnail Size"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    reverse: BoolProperty(name="Reverse Cycle Diretion")

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'FILE_BROWSER' and context.space_data.params.display_type == 'THUMBNAIL'

    def execute(self, context):
        params = context.space_data.params

        if bpy.app.version >= (4, 0, 0):
            if params.display_size == 256 and not self.reverse:
                params.display_size = 16

            elif params.display_size == 16 and self.reverse:
                params.display_size = 256

            else:
                params.display_size += -20 if self.reverse else 20

        else:
            sizes = ['TINY', 'SMALL', 'NORMAL', 'LARGE']
            params.display_size = step_list(params.display_size, sizes, -1 if self.reverse else 1, loop=True)

        return {'FINISHED'}
