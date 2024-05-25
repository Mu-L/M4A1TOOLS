import bpy
import bmesh
from mathutils import Vector
import os
from .. utils.raycast import cast_obj_ray_from_mouse, cast_bvh_ray_from_mouse
from .. utils.draw import draw_label, update_HUD_location, draw_init
from .. utils.system import printd
from .. utils.ui import init_cursor, init_status, finish_status
from .. utils.asset import get_asset_details_from_space
from .. items import alt, ctrl
from .. colors import white, yellow, green, red
from bpy.app.translations import pgettext as _
def draw_material_pick_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text=_("Material Picker"))

        if op.assign_from_assetbrowser:
            row.label(text="Assign Material from Asset Browsr to Object under Mouse")

        else:
            row.label(text="", icon='MOUSE_LMB')
            
            if op.assign:
                row.label(text="Pick Material and Assign it to Selected Objects")

            else:
                row.label(text="Pick Material and Finish")

        row.label(text="", icon='MOUSE_MMB')
        row.label(text="Viewport")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.label(text="", icon='EVENT_SPACEKEY')
        row.label(text="Finish")

        row.separator(factor=10)

        row.label(text="", icon='EVENT_ALT')
        row.label(text=_("Assign Material: {}").format(op.assign))

        if op.asset_browser:
            row.label(text="", icon='EVENT_CTRL')
            row.label(text=_("Assign Material from Asset Browser: {}").format(op.assign_from_assetbrowser))

    return draw

class MaterialPicker(bpy.types.Operator):
    bl_idname = "m4n1.material_picker"
    bl_label = "M4N1: Material Picker"
    bl_description = "Pick a Material from the 3D View\nALT: Assign it to the Selection too"
    bl_options = {'REGISTER', 'UNDO'}

    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode in ['OBJECT', 'EDIT_MESH']:
            return context.area.type == 'VIEW_3D'

    def draw_HUD(self, context):
        draw_init(self, None)

        title, color = (_("Assign from Asset Browser "), green) if self.assign_from_assetbrowser else (_("Assign"), yellow) if self.assign else (_("Pick"), white)
        dims = draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), color=color, center=False)

        if self.assign_from_assetbrowser:

            if self.asset['error']:
                self.offset += 18
                draw_label(context, title=self.asset['error'], coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red, alpha=1)

            else:
                draw_label(context, title=self.asset['import_type'], coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=white, alpha=0.5)

                self.offset += 18

                title = f"{self.asset['library']} • {self.asset['blend_name']} • "
                dims = draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

                title = f"{self.asset['material_name']}"
                draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white)

        else:
            self.offset += 18

            color = red if self.pick_material_name == 'None' else white

            dims = draw_label(context, title=_('Material '), coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
            draw_label(context, title=self.pick_material_name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=1)

    def modal(self, context, event):
        context.area.tag_redraw()

        self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.mouse_pos_window = Vector((event.mouse_x, event.mouse_y))

        area_under_mouse = self.get_area_under_mouse(self.mouse_pos_window)

        if self.passthrough and area_under_mouse != 'ASSET_BROWSER':
            self.passthrough = False
            context.window.cursor_set("EYEDROPPER")

            self.asset = self.get_selected_asset(context, debug=False)

        if area_under_mouse == 'ASSET_BROWSER':
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif area_under_mouse == 'VIEW_3D':

            self.assign = event.alt

            if 'ASSET_BROWSER' in self.areas:
                self.assign_from_assetbrowser = event.ctrl

                if self.assign_from_assetbrowser:
                    self.assign = False

            if event.type in [*alt, *ctrl]:
                if event.value == 'PRESS':
                    context.window.cursor_set("PAINT_CROSS")

                elif event.value == 'RELEASE':
                    context.window.cursor_set("EYEDROPPER")
                
                if context.visible_objects:
                    context.visible_objects[0].select_set(context.visible_objects[0].select_get())

            if event.type == 'MOUSEMOVE':
                update_HUD_location(self, event)

                if not self.assign_from_assetbrowser:
                    hitobj, matindex = self.get_material_hit(context, self.mouse_pos, debug=False)

                    mat, self.pick_material_name = self.get_material_from_hit(hitobj, matindex)

            elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':

                hitobj, matindex = self.get_material_hit(context, self.mouse_pos, debug=False)

                if hitobj:

                    if self.assign_from_assetbrowser:

                        if not self.asset['error']:

                            mat = self.get_material_from_assetbrowser(context)

                            if context.mode == 'OBJECT':

                                if hitobj.material_slots:
                                    hitobj.material_slots[matindex].material = mat
                                else:
                                    hitobj.data.materials.append(mat)

                            elif context.mode == 'EDIT_MESH':
                                self.assign_material_in_editmode(context, mat)

                                self.finish(context)
                                return {'FINISHED'}

                    elif self.assign:
                        mat, matname = self.get_material_from_hit(hitobj, matindex)

                        if mat:

                            if context.mode == 'OBJECT':

                                sel = [obj for obj in context.selected_objects if obj != hitobj and obj.type in ['MESH', 'CURVE']]

                                for obj in sel:
                                    if not obj.material_slots:
                                        obj.data.materials.append(mat)

                                    else:
                                        obj.material_slots[obj.active_material_index].material = mat

                            elif context.mode == 'EDIT_MESH':
                                self.assign_material_in_editmode(context, mat)

                        self.finish(context)

                        return {'FINISHED'}

                    else:

                        iseditmode = context.mode == 'EDIT_MESH'

                        if context.active_object != hitobj:
                            context.view_layer.objects.active = hitobj

                            if iseditmode:
                                bpy.ops.object.mode_set(mode='EDIT')
                            
                        hitobj.active_material_index = matindex

                        self.finish(context)
                        return {'FINISHED'}

            elif event.type == 'SPACE':
                self.finish(context)
                return {'FINISHED'}

            elif event.type == 'MIDDLEMOUSE':
                return {'PASS_THROUGH'}

            elif event.type in ['RIGHTMOUSE', 'ESC']:
                self.finish(context)
                return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        context.window.cursor_set("DEFAULT")

        finish_status(self)

        if context.visible_objects:
            context.visible_objects[0].select_set(context.visible_objects[0].select_get())

    def invoke(self, context, event):
        self.assign = False 
        self.assign_from_assetbrowser = False 
        self.pick_material_name = "None"

        self.dg = context.evaluated_depsgraph_get()

        init_cursor(self, event)
        context.window.cursor_set("EYEDROPPER")

        self.areas, self.asset_browser = self.get_areas(context)

        self.asset = self.get_selected_asset(context, debug=False)

        init_status(self, context, func=draw_material_pick_status(self))

        if context.visible_objects:
            context.visible_objects[0].select_set(context.visible_objects[0].select_get())

        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def get_areas(self, context):
        areas = {}
        asset_browser = None

        for area in context.screen.areas:
            if area.type == 'FILE_BROWSER' and area.ui_type == 'ASSETS':
                area_type = 'ASSET_BROWSER'
                asset_browser = area.spaces.active

            else:
                area_type = area.type

            areas[area_type] = {'x': (area.x, area.x + area.width),
                                'y': (area.y, area.y + area.height)}

        return areas, asset_browser

    def get_area_under_mouse(self, mouse_pos):
        for areaname, coords in self.areas.items():
            if coords['x'][0] <= mouse_pos.x <= coords['x'][1]:

                if coords['y'][0] <= mouse_pos.y <= coords['y'][1]:
                    return areaname

    def get_selected_asset(self, context, debug=False):
        if self.asset_browser:
            libname, libpath, filename, import_type = get_asset_details_from_space(context, self.asset_browser, debug=debug)

            if libpath:

                path = filename.replace('\\', '/')

                if '/Material/' in path:

                    blendname, matname = path.split('/Material/')

                    if os.path.exists(os.path.join(libpath, blendname)):

                        directory = os.path.join(libpath, blendname, 'Material')

                        asset = {'error': None,
                                 'import_type': import_type.title().replace('_', ' '),
                                 'library': libname,
                                 'directory': directory,
                                 'blend_name': blendname.replace('.blend', ''),
                                 'material_name': matname}

                    else:
                        msg = _(".blend file does not exist: {}").format(os.path.join(libpath, blendname))
                        asset = {'error': msg}

                else:
                    msg = _("No material selected in asset browser!")
                    asset = {'error': msg}

            else:
                msg = _("LOCAL or unsupported library chosen!")
                asset = {'error': msg}

        else:
            msg = _("There is no asset browser in this workspace")
            asset = {'error': msg}

        if debug:
            printd(asset)

        return asset

    def get_material_hit(self, context, mousepos, debug=False):
        if debug:
            print("\nmaterial hitting at", mousepos)
        
        if context.mode == 'OBJECT':
            hitobj, hitobj_eval, _, _, hitindex, _ = cast_obj_ray_from_mouse(self.mouse_pos, depsgraph=self.dg, objtypes=['MESH', 'CURVE'], debug=False)

        elif context.mode == 'EDIT_MESH':
            hitobj, _, _, hitindex, _, _ = cast_bvh_ray_from_mouse(self.mouse_pos, candidates=[obj for obj in context.visible_objects], debug=False)

        if hitobj:
            if context.mode == 'OBJECT':
                if hitobj.type == 'MESH':
                    matindex = hitobj_eval.data.polygons[hitindex].material_index

                elif hitobj.type == 'CURVE':
                    matindex = 0

            elif context.mode == 'EDIT_MESH':
                matindex = hitobj.data.polygons[hitindex].material_index

            if debug:
                print(" hit object:", hitobj.name, "material index:", matindex)

            matindex = min(matindex, len(hitobj.material_slots) - 1)

            return hitobj, matindex

        if debug:
            print(" nothing hit")
        return None, None

    def get_material_from_hit(self, obj, index):
        if obj and index is not None:
            if obj.material_slots and obj.material_slots[index].material:
                mat = obj.material_slots[index].material
                return mat, mat.name
        return None, 'None'

    def get_material_from_assetbrowser(self, context):
        import_type = self.asset['import_type']
        directory = self.asset['directory']
        filename = self.asset['material_name']

        mat = bpy.data.materials.get(filename)

        if not mat:

            iseditmode = context.mode == 'EDIT_MESH'

            if iseditmode:
                bpy.ops.object.mode_set(mode='OBJECT')

            if 'Append' in import_type:
                reuse_local_id= 'Reuse' in import_type
                bpy.ops.wm.append(directory=directory, filename=filename, do_reuse_local_id=reuse_local_id)

            else:
                bpy.ops.wm.link(directory=directory, filename=filename)

            if iseditmode:
                bpy.ops.object.mode_set(mode='EDIT')

            mat = bpy.data.materials.get(filename)

            if mat.use_fake_user:
                mat.use_fake_user = False

        return mat

    def assign_material_in_editmode(self, context, mat):
        active = context.active_object

        if active.material_slots:
            bm = bmesh.from_edit_mesh(active.data)
            bm.normal_update()

            faces = [f for f in bm.faces if f.select]

            if faces:
                mat_indices = set(f.material_index for f in faces)

                if len(mat_indices) == 1:
                    index = mat_indices.pop()
                    mat_at_index = active.material_slots[index].material

                    if mat_at_index == mat:
                        active.active_material_index = index
                        return

                if mat.name in active.data.materials:
                    index = list(active.data.materials).index(mat)

                else:
                    index = len(active.material_slots)

                for f in faces:
                    f.material_index = index

                bmesh.update_edit_mesh(active.data)

                active.update_from_editmode()

                if mat.name not in active.data.materials:
                    active.data.materials.append(mat)

                active.active_material_index = index

        else:
            active.data.materials.append(mat)
