import bpy
from bpy.ops import ed
from bpy.props import IntProperty, BoolProperty, EnumProperty, FloatProperty
import bmesh
from math import radians
from ... utils.bmesh import ensure_custom_data_layers
from ... utils.draw import draw_fading_label
from ... utils.modifier import add_auto_smooth, get_auto_smooth, remove_mod, sort_mod
from ... utils.registration import get_addon 
from ... utils.system import printd
from ... items import shade_mode_items
from ... colors import yellow, white, red, orange, blue
from bpy.app.translations import pgettext as _
hypercursor = None

class Shade(bpy.types.Operator):
    bl_idname = "m4n1.shade"
    bl_label = "Shade"
    bl_description = "Set smooth shading in object and edit mode\nALT: Mark edges sharp if face angle > auto smooth angle"
    bl_options = {'REGISTER', 'UNDO'}

    shade_type: EnumProperty(name="Shade Mode", items=shade_mode_items, default='SMOOTH')
    include_children: BoolProperty(name="Include Children", default=False)
    include_boolean_objs: BoolProperty(name="Include Boolean Objects", default=False)

    sharpen: BoolProperty(name="Set Sharps", default=False)
    sharp_angle: FloatProperty(name="Angle", default=20 , min=0, max=180)
    sharpen_additively: BoolProperty(name="Additive Sharpen", description="Avoid removing existing sharps", default=True)
    avoid_sharpen_edge_bevels: BoolProperty(name="Avoid Sharpening HyperCursor's Edge Bevels", description="Avoid Sharpening Edges used by HyperCursor's Edge Bevels", default=True)
    boolean_auto_smooth: BoolProperty(name="Boolean Auto Smooth", description="Ensure Auto Smooth is enabled, for objects using Boolean Modifiers", default=True)
    is_mesh_obj: BoolProperty()
    has_edge_bevels: BoolProperty()
    has_boolean_mods: BoolProperty()

    clear: BoolProperty(name="Clear Sharps, BWeights, Creases and Seams", default=False)
    clear_sharps: BoolProperty(name="Clear Sharps, BWeights, Creases and Seams", default=True)
    clear_bweights: BoolProperty(name="Clear BWeights", default=True)
    clear_creases: BoolProperty(name="Clear Creases", default=True)
    clear_seams: BoolProperty(name="Clear Seams", default=True)
    avoid_clearing_subd_creases: BoolProperty(name="Avoid clearing SubD Creases", description="Avoid Clearing Creases on Objects with SubD mods in crease mode", default=True)
    has_crease_subd_mods: BoolProperty()

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.type in ['MESH', 'CURVE', 'SURFACE']]

        elif context.mode == 'EDIT_MESH':
            return context.active_object

    @classmethod
    def description(cls, context, properties):
        desc = _("Shade Smooth") if properties.shade_type == 'SMOOTH' else 'Smooth Flat'

        if properties.shade_type == 'SMOOTH':
            desc += _("\nALT: Mark MESH object edges sharp if face angle > auto smooth angle")

        elif properties.shade_type == 'FLAT':
            desc += _("\nALT: Clear MESH object sharps, bweights, creases and seams")

        desc += _("\n\nSHIFT: Include Children")
        desc += _("\nCTRL: Include Boolean Objects")

        return desc

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        if self.shade_type == 'SMOOTH':
            
            if self.has_boolean_mods:
                row = column.row(align=True)
                row.prop(self, 'boolean_auto_smooth', toggle=True)

            if self.is_mesh_obj:
                split = column.split(factor=0.5, align=True)
                split.prop(self, 'sharpen', toggle=True)
                r = split.row(align=True)
                r.active = self.sharpen or self.boolean_auto_smooth
                r.prop(self, 'sharp_angle')
                r.prop(self, 'sharpen_additively', text="", icon="ADD")

                if self.has_edge_bevels:
                    row = column.row(align=True)
                    row.active = self.sharpen
                    row.prop(self, 'avoid_sharpen_edge_bevels', text="Avoid HyperCursor's Edge Bevels", toggle=True)

        elif self.shade_type == 'FLAT':

            if self.is_mesh_obj:

                column.prop(self, 'clear', text='Clear' if self.clear else _('Clear Sharps, BWeights, Creases or Seams'), toggle=True)

                if self.clear:
                    row = column.row(align=True)
                    row.prop(self, 'clear_sharps', text='Sharps', toggle=True)
                    row.prop(self, 'clear_bweights', text='BWeights', toggle=True)
                    row.prop(self, 'clear_creases', text='Creases', toggle=True)
                    row.prop(self, 'clear_seams', text='Seams', toggle=True)

                    if self.has_crease_subd_mods:
                        row = column.row(align=True)
                        row.prop(self, 'avoid_clearing_subd_creases', text='Avoid Clearing SubD Creases', toggle=True)

        if context.mode == 'OBJECT':
            column.separator()

            row = column.row(align=True)
            row.prop(self, 'include_children', toggle=True)
            row.prop(self, 'include_boolean_objs', toggle=True)

    def invoke(self, context, event):
        if self.shade_type == 'SMOOTH':
            self.sharpen = event.alt

        elif self.shade_type == 'FLAT':
            self.clear = event.alt

        self.include_boolean_objs = event.ctrl
        self.include_children = event.shift
        return self.execute(context)

    def execute(self, context):
        global hypercursor

        if hypercursor is None:
            hypercursor = get_addon('HyperCursor')[0]

        objtypes = ['MESH', 'CURVE', 'SURFACE']

        if context.mode == "OBJECT":

            selected = set(obj for obj in context.selected_objects if obj.type in objtypes)

            children = set(c for obj in selected for c in obj.children_recursive if c.type in objtypes if c.name in context.view_layer.objects) if self.include_children else set()
            booleans = set(mod.object for obj in selected for mod in obj.modifiers if mod.type == 'BOOLEAN' and mod.object and mod.object.name in context.view_layer.objects) - children if self.include_boolean_objs else set()

            objects = selected | children | booleans

            self.poll_redo_panel(objects)

            data = self.get_object_states(context, objects)

            self.ensure_selection(data)

        elif context.mode == 'EDIT_MESH':

            objects = set(obj for obj in context.objects_in_mode)

            self.poll_redo_panel(objects)

            data = None

        if self.shade_type == 'SMOOTH':
            bpy.ops.object.shade_smooth() if context.mode == 'OBJECT' else bpy.ops.mesh.faces_shade_smooth()

            if self.boolean_auto_smooth:
                auto_smooth_count, auto_smooth_instances = self.ensure_boolean_auto_smooth(context, objects, data)
            else:
                auto_smooth_count = 0, False

            if self.sharpen:
                self.set_sharp_edges(context, objects, hypercursor)

        elif self.shade_type == 'FLAT':
            bpy.ops.object.shade_flat() if context.mode == 'OBJECT' else bpy.ops.mesh.faces_shade_flat()

            auto_smooth_count, auto_smooth_instances = self.avoid_auto_smooth(objects)

            if self.clear:
                self.clear_edge_props(context, objects)

        if context.mode == 'OBJECT':

            self.restore_object_states(context, self.shade_type, data)

            self.draw_fading_hud(context, selected, children, booleans, auto_smooth_count, auto_smooth_instances)

        return {'FINISHED'}

    def poll_redo_panel(self, objects):
        self.is_mesh_obj = any(obj.type == 'MESH' for obj in objects)

        self.has_boolean_mods = any(mod.type == 'BOOLEAN' for obj in objects for mod in obj.modifiers)

        self.has_crease_subd_mods = any(mod.type == 'SUBSURF' and mod.use_creases for obj in objects for mod in obj.modifiers)

    def get_object_states(self, context, objects):
        dg = context.evaluated_depsgraph_get()
        view = context.space_data

        data = {obj: {'auto_smooth': obj.data.use_auto_smooth if bpy.app.version < (4, 1, 0) and obj.type == 'MESH' else False,
                      'local_view': obj.evaluated_get(dg).local_view_get(view) if view.local_view else True,
                      'selected': obj.select_get(),
                      'visible': None} for obj in objects}
        
        if view.local_view:
            for obj, state, in data.items():
                if not state['local_view']:
                    obj.local_view_set(view, True)

        for obj, states in data.items():
            states['visible'] = obj.visible_get()

        return data

    def ensure_selection(self, data):
        for obj, state in data.items():
            if not state['visible']:
                obj.hide_set(False)
                obj.select_set(True)

            elif not state['selected']:
                obj.select_set(True)

    def ensure_boolean_auto_smooth(self, context, objects, data):
        count = 0

        booleans = [obj for obj in objects if any(mod.type == 'BOOLEAN' for mod in obj.modifiers)] 

        if bpy.app.version >= (4, 1, 0):
            boolean_meshes = set(obj.data for obj in booleans)
            boolean_instances = [obj for obj in bpy.data.objects if obj.data in boolean_meshes]

        else:
            boolean_instances = []

        for obj in booleans + boolean_instances:
            if bpy.app.version >= (4, 1, 0):
                if (mod := get_auto_smooth(obj)):
                    mod['Input_1'] = radians(self.sharp_angle)
                    mod.node_group.interface_update(context)

                else:
                    mod = add_auto_smooth(obj, angle=self.sharp_angle)
                    count += 1

                    sort_mod(mod)

            else:
                if not obj.data.use_auto_smooth:
                    obj.data.use_auto_smooth = True

                    if data and (obj_data := data.get(obj)):
                        if obj_data and not obj_data['auto_smooth']:
                            count += 1

                obj.data.auto_smooth_angle = radians(self.sharp_angle)

        return count, bool(boolean_instances)

    def avoid_auto_smooth(self, objects):
        count = 0

        if bpy.app.version >= (4, 1, 0):
            meshes = set(obj.data for obj in objects)
            instances = set(obj for obj in bpy.data.objects if obj.data in meshes and get_auto_smooth(obj))
        else:
            instances = set()

        for obj in objects | instances:
            if bpy.app.version >= (4, 1, 0):
                if mod := get_auto_smooth(obj):
                    remove_mod(mod)
                    count += 1

            elif obj.type == 'MESH':
                if obj.data.use_auto_smooth:
                    obj.data.use_auto_smooth = False
                    count += 1

        return count, bool(instances)

    def restore_object_states(self, context, shade_type, data):
        for obj, state in data.items():

            if not state['selected']:
                obj.select_set(False)

            if not state['visible']:
                obj.hide_set(True)

            if not state['local_view']:
                obj.local_view_set(context.space_data, False)

            if shade_type == 'SMOOTH' and state['auto_smooth'] and not obj.data.use_auto_smooth:
                obj.data.use_auto_smooth = True

    def set_sharp_edges(self, context, objects, hypercursor):
        self.has_edge_bevels = False

        angle = radians(self.sharp_angle)
        mesh_objects = [obj for obj in objects if obj.type == 'MESH']

        for obj in mesh_objects:

            if bpy.app.version < (4, 1, 0) and not obj.data.use_auto_smooth:
                obj.data.use_auto_smooth = True
                obj.data.auto_smooth_angle = angle

            if context.mode == 'OBJECT':
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                vglayer = bm.verts.layers.deform.verify()
            elif context.mode == 'EDIT_MESH':
                bm = bmesh.from_edit_mesh(obj.data)
                vglayer = bm.verts.layers.deform.verify()
                for f in bm.faces:
                    f.smooth = True

            bm.normal_update()

            edge_bevelled_edges = self.get_hypercursor_edge_bevelled_edges(obj, bm, vglayer) if hypercursor else []

            if edge_bevelled_edges:

                if not self.has_edge_bevels:
                    self.has_edge_bevels = True

                if not self.avoid_sharpen_edge_bevels:
                    edge_bevelled_edges = []

            sharp_edges = [e for e in bm.edges if e.index not in edge_bevelled_edges and len(e.link_faces) == 2 and e.calc_face_angle() > angle]

            if self.sharpen_additively:
                for e in sharp_edges:
                    e.smooth = False

            else:
                for e in bm.edges:
                    e.smooth = e not in sharp_edges

            if context.mode == 'OBJECT':
                bm.to_mesh(obj.data)
                bm.free()

            elif context.mode == 'EDIT_MESH':
                bmesh.update_edit_mesh(obj.data)

        if context.space_data.overlay.show_edge_sharp:
            context.space_data.overlay.show_edge_sharp = True

    def get_hypercursor_edge_bevelled_edges(self, obj, bm, vglayer, debug=False):
        vgroups = {vg.index: {'name': vg.name,
                              'verts': [],
                              'edges': []} for vg in obj.vertex_groups if 'Edge Bevel' in vg.name}

        verts = [v for v in bm.verts]

        for v in verts:

            for vgindex, weight in v[vglayer].items():
                if vgindex in vgroups and weight == 1:
                    vgroups[vgindex]['verts'].append(v.index)

        edge_bevelled_edges = []

        for e in bm.edges:

            for vgindex, vgdata in vgroups.items():
                if all(v.index in vgdata['verts'] for v in e.verts):
                    edge_bevelled_edges.append(e.index)

                    vgdata['edges'].append(e.index)

        if debug:
            print()
            printd(vgroups, 'vgroups')

        return edge_bevelled_edges

    def clear_edge_props(self, context, objects):
        mesh_objects = [obj for obj in objects if obj.type == 'MESH']
        
        for obj in mesh_objects:
            has_subd = any(mod.type == 'SUBSURF' and mod.use_creases for mod in obj.modifiers)

            if context.mode == 'OBJECT':
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                bm.normal_update()

            else:
                bm = bmesh.from_edit_mesh(obj.data)
                bm.normal_update()

                for f in bm.faces:
                    f.smooth = False

            _, bw, cr = ensure_custom_data_layers(bm)

            for e in bm.edges:
                if self.clear_sharps:
                    e.smooth = True

                if self.clear_bweights:
                    e[bw] = 0

                if self.clear_creases and not (has_subd and self.avoid_clearing_subd_creases):
                    e[cr] = 0

                if self.clear_seams:
                    e.seam = False

            if context.mode == 'OBJECT':
                bm.to_mesh(obj.data)
                bm.clear()

            else:
                bmesh.update_edit_mesh(obj.data)

    def draw_fading_hud(self, context, selected, children, booleans, auto_smooth_count, auto_smooth_instances):
        if context.mode == 'OBJECT':
            text = [_("{} Shaded {} selected Objects").format(self.shade_type.title(),len(selected))]
            color = [yellow]
            alpha = [1]

            if children:
                text.append(_("+ {} recursive Children").format(len(children)))
                color.append(white)
                alpha.append(1)

            if booleans:
                text.append(_(" + {} Boolean Mod Objects").format(len(booleans)))
                color.append(white)
                alpha.append(1)

            if self.shade_type == 'SMOOTH' and self.boolean_auto_smooth and auto_smooth_count:
                text.append(_("Enabled Auto Smooth on {} Objects carrying Boolean Mods").format(auto_smooth_count))
                color.append(blue)
                alpha.append(1)

                if auto_smooth_instances:
                    text.append(_("(incl. on Instances)"))
                    color.append(white)
                    alpha.append(0.5)

            elif self.shade_type == 'FLAT' and auto_smooth_count:
                text.append(_("Disabled Auto Smooth on {} Objects".format(auto_smooth_count)))
                color.append(red)
                alpha.append(1)

                if auto_smooth_instances:
                    text.append(_("(incl. on Instances)"))
                    color.append(white)
                    alpha.append(0.5)

            if self.shade_type == 'SMOOTH' and self.sharpen:
                text.append(_("Marked Edges Sharp {}based on Angle {}").format(_('additively ') if self.sharpen_additively else '',self.sharp_angle))
                color.append(red)
                alpha.append(1)

            elif self.shade_type == 'FLAT' and self.clear:
                cleared = []

                if self.clear_sharps:
                    cleared.append('Sharps')

                if self.clear_bweights:
                    cleared.append('BWeights')

                if self.clear_creases:
                    cleared.append('Creases')

                if self.clear_seams:
                    cleared.append('Seams')

                if cleared:
                    if len(cleared) > 1:
                        cleared_str = ', '.join(cleared[:-1]) + ' and ' + cleared[-1]

                    else:
                        cleared_str = cleared[0]

                    text.append(_("Cleared {} Edges").format(cleared_str))
                    color.append(orange)
                    color.append(1)

            draw_fading_label(context, text, color=color, alpha=alpha, move_y=40, time=3)

class ToggleAutoSmooth(bpy.types.Operator):
    bl_idname = "m4n1.toggle_auto_smooth"
    bl_label = "Toggle Auto Smooth"
    bl_options = {'REGISTER', 'UNDO'}

    angle: IntProperty(name="Auto Smooth Angle")

    @classmethod
    def poll(cls, context):
        return context.active_object

    @classmethod
    def description(cls, context, properties):
        if properties.angle == 0:
            if bpy.app.version >= (4, 1, 0):
                if get_auto_smooth(context.active_object):
                    return _("Remove existing 'Auto Smooth' modifier")
                else:
                    return _("Add 'Auto Smooth' modifier to smooth shade object angle based")
            else:
                return _("Toggle mesh's Auto Smooth property")
        else:
            return _("Auto Smooth Angle Preset: {}").format(properties.angle)

    def execute(self, context):
        active = context.active_object
        objtypes = ['MESH', 'CURVE']

        fading_hud_text = []
        fading_hud_colors = []
        fading_hud_alphas = []

        if active:
            sel = [obj for obj in context.selected_objects if obj.type in objtypes]

            if active not in sel:
                sel.append(active)

            if bpy.app.version >= (4, 1, 0):
                meshes = set(obj.data for obj in sel)
                instances = [obj for obj in bpy.data.objects if obj not in sel and obj.data in meshes]

                if instances:
                    fading_hud_text.append(_("(incl. on Instances)"))
                    fading_hud_colors.append(white)
                    fading_hud_alphas.append(0.5)

                state = not bool(get_auto_smooth(active)) if self.angle == 0 else True

                if context.mode == 'OBJECT' and state:
                    bpy.ops.object.shade_smooth()
                
                for obj in sel + instances:

                    if (mod := get_auto_smooth(obj)) and not state:
                        remove_mod(mod)
                    
                    elif not (mod := get_auto_smooth(obj)) and state:
                        mod = add_auto_smooth(obj)

                        sort_mod(mod)
                    
                    elif state:
                        mod = get_auto_smooth(obj)

                    if state and self.angle:
                        mod['Input_1'] = radians(self.angle)

                        mod.node_group.interface_update(context)

            else:
                state = not active.data.use_auto_smooth if self.angle == 0 else True
                
                if context.mode == 'OBJECT' and state:
                    bpy.ops.object.shade_smooth()

                for obj in [obj for obj in sel if obj.type == 'MESH']:
                    obj.data.use_auto_smooth = state

                    if state and self.angle:
                        obj.data.auto_smooth_angle = radians(self.angle)

            if state:
                if self.angle:
                    fading_hud_text.insert(0, _("Enabled Auto Smooth with angle {}").format(self.angle))
                else:
                    fading_hud_text.insert(0, _("Enabled Auto Smooth"))

                fading_hud_colors.insert(0, blue)

            else:
                fading_hud_text.insert(0, _("Disabled Auto Smooth"))
                fading_hud_colors.insert(0, red)

            fading_hud_alphas.insert(0, 1)

            draw_fading_label(context, text=fading_hud_text, color=fading_hud_colors, alpha=fading_hud_alphas, move_y=40, time=3)

        return {'FINISHED'}
