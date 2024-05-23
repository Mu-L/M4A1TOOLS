import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty, IntProperty
import os
from mathutils import Vector
from .. utils.asset import get_assetbrowser_bookmarks, get_catalogs_from_asset_libraries, get_libref_and_catalog, set_assetbrowser_bookmarks, validate_libref_and_catalog
from .. utils.registration import get_addon, get_prefs, get_path
from .. utils.ui import force_ui_update, popup_message, region_2d_to_location_3d
from .. utils.asset import get_asset_library_reference, set_asset_library_reference, update_asset_catalogs
from .. utils.object import parent
from .. utils.math import average_locations
from .. utils.system import printd
from .. items import create_assembly_asset_empty_location_items, create_assembly_asset_empty_collection_items, asset_browser_bookmark_props

import time

decalmachine = None
meshmachine = None

class CreateAssemblyAsset(bpy.types.Operator):
    bl_idname = "m4n1.create_assembly_asset"
    bl_label = "M4N1: Create Assembly Asset"
    bl_description = "Create Assembly Asset from the selected Objects"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Asset Name", default="AssemblyAsset")
    move: BoolProperty(name="Move instead of Copy", description="Move Objects into Asset Collection, instead of copying\nThis will unlink them from any existing collections", default=True)
    location: EnumProperty(name="Empty Location", items=create_assembly_asset_empty_location_items, description="Location of Asset's Empty", default='AVGFLOOR')
    emptycol: EnumProperty(name="Empty Collection", items=create_assembly_asset_empty_collection_items, description="Collections to put the the Asset's Empty in", default='SCENECOL')
    remove_decal_backups: BoolProperty(name="Remove Decal Backups", description="Remove DECALmachine's Decal Backups, if present", default=False)
    remove_stashes: BoolProperty(name="Remove Stashes", description="Remove MESHmachine's Stashes, if present", default=False)
    render_thumbnail: BoolProperty(name="Render Thumbnail", default=True)
    thumbnail_lens: FloatProperty(name="Thumbnail Lens", default=100)
    toggle_overlays: BoolProperty(name="Toggle Overlays", default=True)
    def update_hide_instance(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.hide_instance and self.hide_collection:
            self.avoid_update = True
            self.hide_collection = False

    def update_hide_collection(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.hide_collection and self.hide_instance:
            self.avoid_update = True
            self.hide_instance = False

    unlink_collection: BoolProperty(name="Unlink Collection", description="Unlink the Asset Collection\nUseful to clean up the scene, and optionally start using the Asset locally right away", default=True)
    hide_collection: BoolProperty(name="Hide Collection", default=True, description="Hide the Asset Collection\nUseful when you want to start using the Asset locally, while still having easy access to the individual objects", update=update_hide_collection)
    hide_instance: BoolProperty(name="Hide Instance", default=False, description="Hide the COllection Instance Empty\nUseful when you want to keep working on the Asset's objects", update=update_hide_instance)
    avoid_update: BoolProperty()

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def draw(self, context):
        global decalmachine, meshmachine

        layout = self.layout

        column = layout.column(align=True)
        column.prop(self, 'name')
        column.prop(context.window_manager, 'M3_asset_catalogs', text='Catalog')

        if decalmachine or meshmachine:
            column.separator()
            column.label(text="DECALmachine and MESHmachine" if decalmachine and meshmachine else "DECALmachine" if decalmachine else "MESHmachine")
            row = column.row(align=True)

            if decalmachine:
                row.prop(self, 'remove_decal_backups', toggle=True)

            if meshmachine:
                row.prop(self, 'remove_stashes', toggle=True)

        column.separator()
        column.label(text="Asset Object Collections")
        column.prop(self, 'move', toggle=True)

        column.separator()
        column.label(text="Asset Empty")
        row = column.row(align=True)
        row.prop(self, 'emptycol', expand=True)
        row = column.row(align=True)
        row.prop(self, 'location', expand=True)

        column.separator()
        column.label(text="Asset Collection")
        row = column.row(align=True)
        row.prop(self, 'unlink_collection', toggle=True)
        r = row.row(align=True)
        r.active = not self.unlink_collection
        r.prop(self, 'hide_collection', toggle=True)
        r.prop(self, 'hide_instance', toggle=True)

        column.separator()
        column.label(text="Asset Thumbnail")
        row = column.row(align=True)
        row.prop(self, 'render_thumbnail', text="Viewport Render", toggle=True)
        r = row.row(align=True)
        r.active = self.render_thumbnail
        r.prop(self, 'toggle_overlays', text="Toggle Overlays", toggle=True)
        r.prop(self, 'thumbnail_lens', text='Lens')

    def invoke(self, context, event):
        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        update_asset_catalogs(self, context)

        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        global decalmachine, meshmachine

        name = self.name.strip()

        if name:
            print(f"INFO: Creation Assembly Asset: {name}")

            objects = self.get_assembly_asset_objects(context)

            rootobjs, loc = self.get_empty_location(context, objects)

            if decalmachine and self.remove_decal_backups:
                self.delete_decal_backups(objects)

            if meshmachine and self.remove_stashes:
                self.delete_stashes(objects)

            instance = self.create_asset_instance_collection(context, name, objects, rootobjs, loc)

            self.adjust_workspace(context)

            if self.render_thumbnail:
                thumbpath = os.path.join(get_path(), 'resources', 'thumb.png')
                self.render_viewport(context, thumbpath)

                thumb = bpy.data.images.load(filepath=thumbpath)

                instance.preview_ensure()
                instance.preview.image_size = thumb.size
                instance.preview.image_pixels_float[:] = thumb.pixels  # CodeManX is a legend

                bpy.data.images.remove(thumb)
                bpy.data.images.remove(bpy.data.images['Render Result'])
                os.unlink(thumbpath)

            return {'FINISHED'}

        else:
            popup_message("The chosen asset name can't be empty", title="Illegal Name")

            return {'CANCELLED'}

    def get_assembly_asset_objects(self, context):
        sel = context.selected_objects
        objects = set()

        for obj in sel:
            objects.add(obj)

            if obj.parent and obj.parent not in sel:
                objects.add(obj.parent)

            booleans = [mod for mod in obj.modifiers if mod.type == 'BOOLEAN']

            for mod in booleans:
                if mod.object and mod.object not in sel:
                    objects.add(mod.object)

            mirrors = [mod for mod in obj.modifiers if mod.type == 'MIRROR']

            for mod in mirrors:
                if mod.mirror_object and mod.mirror_object not in sel:
                    objects.add(mod.mirror_object)

        for obj in context.visible_objects:
            if obj not in objects and obj.parent and obj.parent in objects:
                objects.add(obj)

        return objects

    def get_empty_location(self, context, objects):
        rootobjs = [obj for obj in objects if not obj.parent]

        if self.location in ['AVG', 'AVGFLOOR']:
            loc = average_locations([obj.matrix_world.decompose()[0] for obj in rootobjs])

            if self.location == 'AVGFLOOR':
                loc[2] = 0

        else:
            loc = Vector((0, 0, 0))

        return rootobjs, loc

    def delete_decal_backups(self, objects):
        decals_with_backups = [obj for obj in objects if obj.DM.isdecal and obj.DM.decalbackup]

        for decal in decals_with_backups:
            print(f"WARNING: Removing {decal.name}'s backup")

            if decal.DM.decalbackup:
                bpy.data.meshes.remove(decal.DM.decalbackup.data, do_unlink=True)

    def delete_stashes(self, objects):
        objs_with_stashes = [obj for obj in objects if obj.MM.stashes]

        for obj in objs_with_stashes:
            print(f"WARNING: Removing {obj.name}'s {len(obj.MM.stashes)} stashes")

            for stash in obj.MM.stashes:
                stashobj = stash.obj

                if stashobj:
                    print(" *", stash.name, stashobj.name)
                    bpy.data.meshes.remove(stashobj.data, do_unlink=True)

            obj.MM.stashes.clear()

    def create_asset_instance_collection(self, context, name, objects, rootobjs, loc):
        mcol = context.scene.collection
        acol = bpy.data.collections.new(name)
        mcol.children.link(acol)

        cols = {col for obj in objects for col in obj.users_collection}

        if self.move:
            for obj in objects:
                for col in obj.users_collection:
                    if col in cols:
                        col.objects.unlink(obj)

        for obj in objects:
            acol.objects.link(obj)

            if get_prefs().hide_wire_objects_when_creating_assembly_asset and obj.display_type in ['WIRE', 'BOUNDS']:
                obj.hide_set(True)

                obj.hide_viewport = True

        instance = bpy.data.objects.new(name, object_data=None)
        instance.instance_collection = acol
        instance.instance_type = 'COLLECTION'

        if self.emptycol == 'SCENECOL':
            mcol.objects.link(instance)

        else:
            for col in cols:
                col.objects.link(instance)

        instance.location = loc

        for obj in rootobjs:
            obj.location = obj.location - loc

        instance.asset_mark()

        catalog = context.window_manager.M4_asset_catalogs

        if catalog and catalog != 'NONE':
            for uuid, catalog_data in self.catalogs.items():
                if catalog == catalog_data['catalog']:
                    instance.asset_data.catalog_id = uuid

        if self.unlink_collection:
            mcol.children.unlink(acol)

        else:
            if self.hide_collection:
                context.view_layer.layer_collection.children[acol.name].hide_viewport = True
                instance.select_set(True)
                context.view_layer.objects.active = instance

            elif self.hide_instance:
                instance.hide_set(True)

        return instance

    def adjust_workspace(self, context):
        asset_browser_workspace = get_prefs().preferred_assetbrowser_workspace_name

        if asset_browser_workspace:
            ws = bpy.data.workspaces.get(asset_browser_workspace)

            if ws and ws != context.workspace:
                print("INFO: Switching to preffered Asset Browser Workspace")
                bpy.ops.m4n1.switch_workspace('INVOKE_DEFAULT', name=asset_browser_workspace)

                self.switch_asset_browser_to_LOCAL(ws)
                return

        ws = context.workspace

        self.switch_asset_browser_to_LOCAL(ws)

    def switch_asset_browser_to_LOCAL(self, workspace):
        for screen in workspace.screens:
            for area in screen.areas:
                if area.type == 'FILE_BROWSER' and area.ui_type == 'ASSETS':
                    for space in area.spaces:
                        if space.type == 'FILE_BROWSER':
                            if get_asset_library_reference(space.params) != 'LOCAL':
                                set_asset_library_reference(space.params, 'LOCAL')

                            space.show_region_tool_props = True

    def render_viewport(self, context, filepath):
        resolution = (context.scene.render.resolution_x, context.scene.render.resolution_y)
        file_format = context.scene.render.image_settings.file_format
        lens = context.space_data.lens
        show_overlays = context.space_data.overlay.show_overlays

        context.scene.render.resolution_x = 128
        context.scene.render.resolution_y = 128
        context.scene.render.image_settings.file_format = 'JPEG'

        context.space_data.lens = self.thumbnail_lens

        if show_overlays and self.toggle_overlays:
            context.space_data.overlay.show_overlays = False

        bpy.ops.render.opengl()

        thumb = bpy.data.images.get('Render Result')

        if thumb:
            thumb.save_render(filepath=filepath)

        context.scene.render.resolution_x = resolution[0]
        context.scene.render.resolution_y = resolution[1]
        context.space_data.lens = lens

        context.scene.render.image_settings.file_format = file_format

        if show_overlays and self.toggle_overlays:
            context.space_data.overlay.show_overlays = True

class AssembleInstanceCollection(bpy.types.Operator):
    bl_idname = "m4n1.assemble_instance_collection"
    bl_label = "M4N1: Assemle Instance Collection"
    bl_description = "Make Instance Collection objects accessible\nALT: Keep Empty as Root"
    bl_options = {'REGISTER'}

    keep_empty: BoolProperty(name="Keep Empty as Root", default=False)
    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active and active.type == 'EMPTY' and active.instance_collection and active.instance_type == 'COLLECTION'

    def invoke(self, context, event):
        self.keep_empty = event.alt
        return self.execute(context)

    def execute(self, context):
        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        active = context.active_object

        instances = {active} | {obj for obj in context.selected_objects if obj.type == 'EMPTY' and obj.instance_collection}

        if any((i.instance_collection.library for i in instances)):
            bpy.ops.object.make_local(type='ALL')

            for instance in instances:
                instance.select_set(True)

        for instance in instances:
            collection = instance.instance_collection

            root_children = self.assemble_instance_collection(context, instance, collection)

            if self.keep_empty:
                for child in root_children:
                    parent(child, instance)

                    instance.select_set(True)
                    context.view_layer.objects.active = instance
            else:
                bpy.data.objects.remove(instance, do_unlink=True)

        if decalmachine:
            decals = [obj for obj in context.scene.objects if obj.DM.isdecal]
            backups = [obj for obj in decals if obj.DM.isbackup]

            if decals:
                from DECALmachine.utils.collection import sort_into_collections

                for obj in decals:
                    sort_into_collections(context, obj, purge=False)

            if backups:
                bpy.ops.m4n1.sweep_decal_backups()

        if meshmachine:
            stashobjs = [obj for obj in context.scene.objects if obj.MM.isstashobj]

            if stashobjs:
                bpy.ops.m4n1.sweep_stashes()

        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        return {'FINISHED'}

    def assemble_instance_collection(self, context, instance, collection):
        cols = [col for col in instance.users_collection]
        imx = instance.matrix_world

        children = [obj for obj in collection.objects]

        bpy.ops.object.select_all(action='DESELECT')

        for obj in children:
            for col in cols:
                if obj.name not in col.objects:
                    col.objects.link(obj)
            obj.select_set(True)

            if get_prefs().hide_wire_objects_when_assembling_instance_collection and obj.display_type in ['WIRE', 'BOUNDS']:
                obj.hide_set(True)

                obj.hide_viewport = False

        if len(collection.users_dupli_group) > 1:

            bpy.ops.object.duplicate()

            for obj in children:
                for col in cols:
                    col.objects.unlink(obj)

            children = [obj for obj in context.selected_objects]

            for obj in children:
                if obj.name in collection.objects:
                    collection.objects.unlink(obj)

        root_children = [obj for obj in children if not obj.parent]

        for obj in root_children:
            obj.matrix_world = imx @ obj.matrix_world

            obj.select_set(True)
            context.view_layer.objects.active = obj

        instance.instance_type = 'NONE'
        instance.instance_collection = None

        if len(collection.users_dupli_group) == 0:
            bpy.data.collections.remove(collection)

        return root_children

class AssetBrowserBookmark(bpy.types.Operator):
    bl_idname = "m4n1.assetbrowser_bookmark"
    bl_label = "M4N1: Assetbrowser Bookmark"
    bl_description = "description"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index", default=1, min=1, max=10)
    save_bookmark: BoolProperty(name="Save Bookmark", default=False)
    clear_bookmark: BoolProperty(name="Clear Bookmark", default=False)
    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'FILE_BROWSER' and context.area.ui_type == 'ASSETS'

    @classmethod
    def description(cls, context, properties):
        idx = str(properties.index)

        desc = f"Bookmark: {idx}"

        bookmarks = get_assetbrowser_bookmarks(force=True)
        bookmark = bookmarks[idx]

        libref, _, catalog = get_libref_and_catalog(context, bookmark=bookmark)

        if catalog:
            if libref == 'ALL':
                desc += f"\n Library: ALL ({libref})"
            else:
                desc += f"\n Library: {libref}"

            desc += f"\n Catalog: {catalog['catalog']}"

        elif libref:
            desc += f"\n Library: {libref}"

        else:
            desc += "\nNone"

        if catalog:
            desc += "\n\nClick: Jump to this Bookmark's Library and Catalog"
        else:
            desc += "\n"

        desc += "\nSHIFT: Save the current Library and Catalog on this Bookmark"

        if catalog:
            desc += "\nCTRL: Remove the stored Bookmark"

        return desc

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

    def invoke(self, context, event):
        self.save_bookmark = event.shift
        self.clear_bookmark = event.ctrl

        space = context.space_data
        catalogs = get_catalogs_from_asset_libraries(context, debug=False)
        bookmarks = get_assetbrowser_bookmarks(force=True)

        if self.save_bookmark:
            libref = get_asset_library_reference(space.params)
            catalog_id = space.params.catalog_id
            display_size = space.params.display_size

            if catalog_id in catalogs:
                bookmark = {'libref': libref,
                            'catalog_id': catalog_id,
                            'display_size': display_size,
                            'valid': True}

                bookmarks[str(self.index)] = bookmark

                set_assetbrowser_bookmarks(bookmarks)

                if getattr(context.window_manager, 'M3_screen_cast', False):
                    force_ui_update(context)

            else:

                print("  WARNING: no catalog found under this id! Reload the blend file? Restart Blender?")
                return {'CANCELLED'}

        elif self.clear_bookmark:
            bookmark = bookmarks.get(str(self.index), None)
            
            if bookmark:

                bookmarks[str(self.index)] = {key: None for key in asset_browser_bookmark_props}
                
                set_assetbrowser_bookmarks(bookmarks)

                if getattr(context.window_manager, 'M3_screen_cast', False):
                    force_ui_update(context)

            else:
                print(f" WARNING: no bookmark found for {self.index}. This should not happen! Reload the blend file.")
                return {'CANCELLED'}

        else:
            bookmark = bookmarks.get(str(self.index), None)

            if bookmark:
                libref = bookmark.get('libref', None)
                catalog_id = bookmark.get('catalog_id', None)
                display_size = bookmark.get('display_size', None)
                valid = bookmark.get('valid', None)

                if libref and catalog_id:

                    if validate_libref_and_catalog(context, libref, catalog_id):
                        params = space.params

                        set_asset_library_reference(params, libref)
                        params.catalog_id = catalog_id

                        params.display_size = display_size

                        if not valid:
                            bookmark['valid'] = True

                            set_assetbrowser_bookmarks(bookmarks)

                    else:
                        bookmark['valid'] = False

                        set_assetbrowser_bookmarks(bookmarks)

            else:
                print(f" WARNING: no bookmark found for {self.index}. This should not happen! Reload the blend file.")
                return {'CANCELLED'}

        return {'FINISHED'}
