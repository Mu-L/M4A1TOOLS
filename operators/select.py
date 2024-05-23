import bpy
from bpy.props import EnumProperty, BoolProperty, StringProperty
from mathutils import Vector
from .. utils.draw import draw_fading_label, get_text_dimensions
from .. utils.modifier import get_mod_obj
from .. utils.object import get_object_hierarchy_layers, get_parent
from .. utils.registration import get_prefs
from .. utils.view import ensure_visibility
from .. colors import yellow, red, green, white
from bpy.app.translations import pgettext as _
axis_items = [("0", "X", ""),
              ("1", "Y", ""),
              ("2", "Z", "")]

class SelectCenterObjects(bpy.types.Operator):
    bl_idname = "m4n1.select_center_objects"
    bl_label = "M4N1: Select Center Objects"
    bl_description = "Selects Objects in the Center, objects, that have verts on both sides of the X, Y or Z axis."
    bl_options = {'REGISTER', 'UNDO'}

    axis: EnumProperty(name="Axis", items=axis_items, default="0")
    def draw(self, context):
        layout = self.layout

        column = layout.column()

        row = column.row()
        row.prop(self, "axis", expand=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        visible = [obj for obj in context.visible_objects if obj.type == "MESH"]

        if visible:

            bpy.ops.object.select_all(action='DESELECT')

            for obj in visible:
                mx = obj.matrix_world

                coords = [(mx @ Vector(co))[int(self.axis)] for co in obj.bound_box]

                if min(coords) < 0 and max(coords) > 0:
                    obj.select_set(True)

        return {'FINISHED'}

class SelectWireObjects(bpy.types.Operator):
    bl_idname = "m4n1.select_wire_objects"
    bl_label = "M4N1: Select Wire Objects"
    bl_description = "Select Objects set to WIRE display type\nALT: Hide Objects\nCLTR: Include Empties"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.visible_objects if obj.display_type in ['WIRE', 'BOUNDS'] or obj.type == 'EMPTY']

    def invoke(self, context, event):
        bpy.ops.object.select_all(action='DESELECT')

        for obj in context.visible_objects:
            if obj.display_type == '':
                obj.display_type = 'WIRE'

        if event.ctrl:
            objects = [obj for obj in context.visible_objects if obj.display_type in ['WIRE', 'BOUNDS'] or obj.type == 'EMPTY']
        else:
            objects = [obj for obj in context.visible_objects if obj.display_type in ['WIRE', 'BOUNDS']]

        for obj in objects:
            if event.alt:
                obj.hide_set(True)
            else:
                obj.select_set(True)

        return {'FINISHED'}

last_ret = ''

class SelectHierarchy(bpy.types.Operator):
    bl_idname = "m4n1.select_hierarchy"
    bl_label = "M4N1: Select Hierarchy"
    bl_description = "Select Hierarchy Down"
    bl_options = {'REGISTER', 'UNDO'}

    direction: StringProperty(name="Hierarchy Direction", default='DOWN')
    include_selection: BoolProperty(name="Include Selection", description="Include Current Selection", default=False)
    include_mod_objects: BoolProperty(name="Include Mod Objects", description="Include Mod Objects, even if they aren't parented", default=False)
    unhide: BoolProperty(name="Unhide + Select", description="Unhide and Select hidden Children/Parents, if you encounter them", default=False)
    recursive_down: BoolProperty(name="Select Recursive Children", description="Select Children Recursively", default=True)
    recursive_up: BoolProperty(name="Select Recursive Parents", description="Select Parents Recursively", default=False)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.selected_objects

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        row = column.row(align=True)
        row.prop(self, 'include_selection', toggle=True)

        if self.direction == 'DOWN':
            row.prop(self, 'include_mod_objects', toggle=True)

        row = column.row(align=True)
        row.prop(self, 'recursive_down' if self.direction == 'DOWN' else 'recursive_up', text="Recursive", toggle=True)
        row.prop(self, 'unhide', text="Unhide", toggle=True)

    def invoke(self, context, event):
        self.coords = Vector((event.mouse_region_x, event.mouse_region_y)) + Vector((30, -15))
        return self.execute(context)

    def execute(self, context):
        global last_ret

        time = get_prefs().HUD_fade_select_hierarchy
        scale = context.preferences.system.ui_scale

        layers = get_object_hierarchy_layers(context, debug=False)

        if self.direction == 'UP':
            ret = self.select_up(context, context.selected_objects, layers)

            if type(ret) == tuple:
                position, hidden_parents_count = ret

                if position == 'TOP':
                    text = [_("Reached Top of Hierarchy"),
                    _("with {} Hidden Parents".format(hidden_parents_count))]

                    y_offset = 18 * scale

                    draw_fading_label(context, text=text, x=self.coords[0], y=self.coords[1] + y_offset, center=False, size=12, color=[yellow, white], time=time, alpha=0.5)

                elif position == 'ABSOLUTE_TOP':
                    y_offset = 54 * scale if last_ret == 'TOP' else 18 * scale

                    draw_fading_label(context, text=_("Reached ABSOLUTE Top of Hierarchy"), x=self.coords[0], y=self.coords[1] + y_offset, center=False, size=12, color=green, time=time, alpha=1)

                last_ret = ret

            else:
                draw_fading_label(context, text=_("Selecting Up "), x=self.coords[0], y=self.coords[1], center=False, size=12, color=white, time=time, alpha=0.5)
                x_offset = get_text_dimensions(context, _("Selecting Up "), size=12)[0]

                if self.unhide:
                    draw_fading_label(context, text=_("+ Unhiding "), x=self.coords[0] + x_offset, y=self.coords[1] + 5 * scale, center=False, size=10, color=white, time=time, alpha=0.3)

                if self.recursive_up:
                    draw_fading_label(context, text=("+ Recursive "), x=self.coords[0] + x_offset, y=self.coords[1] - 5 * scale, center=False, size=10, color=white, time=time, alpha=0.3)

                if self.include_selection:
                    if self.unhide:
                        x_offset += get_text_dimensions(context, _("+ Unhiding "), size=10)[0]

                    draw_fading_label(context, text=_("+ Inclusive"), x=self.coords[0] + x_offset, y=self.coords[1] + 5 * scale, center=False, size=10, color=white, time=time, alpha=0.3)

            draw_fading_label(context, text="🔼", x=self.coords[0] - 70, y=self.coords[1] + 9 * scale, center=False, size=12, color=white, time=time, alpha=0.25)

        elif self.direction == 'DOWN':
            ret = self.select_down(context, context.selected_objects, layers)

            if type(ret) == tuple:
                position, hidden_children_count = ret

                if position == 'BOTTOM':
                    text = [_("Reached Bottom of Hierarchy"),
                    _("with {} Hidden Children").format(hidden_children_count)]

                    y_offset = 36 * scale

                    draw_fading_label(context, text=text, x=self.coords[0], y=self.coords[1] -  y_offset, center=False, size=12, color=[yellow, white], time=time, alpha=0.5)

                elif position == 'ABSOLUTE_BOTTOM':
                    y_offset = 54 * scale if last_ret == 'BOTTOM' else 18 * scale

                    draw_fading_label(context, text=_("Reached ABSOLUTE Bottom of Hierarchy"), x=self.coords[0], y=self.coords[1] - y_offset, center=False, size=12, color=red, time=time, alpha=1)

                last_ret = ret

            else:
                y_offset = 0 * scale

                draw_fading_label(context, text=_("Selecting Down "), x=self.coords[0], y=self.coords[1], center=False, size=12, color=white, time=time, alpha=0.5)
                x_offset = get_text_dimensions(context, _("Selecting Down "), size=12)[0]

                if self.unhide:
                    draw_fading_label(context, text=_("+ Unhiding "), x=self.coords[0] + x_offset, y=self.coords[1] + 5 * scale, center=False, size=10, color=white, time=time, alpha=0.3)

                if self.recursive_down:
                    draw_fading_label(context, text=_("+ Recursive "), x=self.coords[0] + x_offset, y=self.coords[1] - 5 * scale, center=False, size=10, color=white, time=time, alpha=0.3)

                if self.include_selection:
                    if self.unhide:
                        x_offset += get_text_dimensions(context, _("+ Unhiding "), size=10)[0]

                    draw_fading_label(context, text=_("+ Inclusive"), x=self.coords[0] + x_offset, y=self.coords[1] + 5 * scale, center=False, size=10, color=white, time=time, alpha=0.3)

            draw_fading_label(context, text="🔽", x=self.coords[0] - 70, y=self.coords[1] - 9 * scale, center=False, size=12, color=white, time=time, alpha=0.25)

        return {'FINISHED'}

    def select_up(self, context, objects, layers, debug=False): 

        parents = set()
        init_selection = set(objects)

        if debug:
            print()
            print("-----")
            print("selected:")

            for obj in init_selection:
                print("", obj.name)

        for obj in init_selection:

            if self.recursive_up:
                parents.update({p for p in get_parent(obj, recursive=True) if p.name in context.view_layer.objects})

            elif obj.parent:
                parents.add(obj.parent)

        if self.unhide:
            ensure_visibility(context, parents, unhide=True)

        visible_parents = set(p for p in parents if p.visible_get())
        hidden_parents = set(parents) - visible_parents

        if debug:
            print()
            print("parents (visible):")

            for obj in visible_parents:
                print("", obj.name)

            print()
            print("parents (hiddden)")

            for obj in hidden_parents:
                print("", obj.name)

        if not self.include_selection:

            if visible_parents:
                
                if (active := context.active_object) and active.M4.is_group_empty and context.scene.M4.group_select:
                    if debug:
                        print("NOTE: Avoiding de-selecting parents, as active is group empty and auto-select is enabled")

                else:
                    for obj in init_selection:
                        obj.select_set(False)

        for obj in visible_parents:
            obj.select_set(True)

        new_selection = set(obj for obj in context.selected_objects)

        if debug:
            print()
            print("new selected:")

            for obj in new_selection:
                print("", obj.name)

        if init_selection == new_selection:
            if hidden_parents:
                return 'TOP', len(hidden_parents)

            else:
                return 'ABSOLUTE_TOP', 0

        elif active := context.active_object:

            for layer in layers:
                if (top_lvl_parents := set(layer) & visible_parents):

                    if active not in top_lvl_parents:
                        
                        group_empties = [obj for obj in top_lvl_parents if obj.M4.is_group_empty]

                        if group_empties:
                            context.view_layer.objects.active = group_empties[0]
                        else:
                            context.view_layer.objects.active = top_lvl_parents.pop()

                    break

        return True

    def select_down(self, context, objects, layers, debug=False): 

        children = set()
        init_selection = set(objects)

        if debug:
            print()
            print("-----")
            print("selected:")

            for obj in init_selection:
                print("", obj.name)

        for obj in init_selection:

            if self.recursive_down:
                children.update({c for c in obj.children_recursive if c.name in context.view_layer.objects})
            else:
                children.update({c for c in obj.children if c.name in context.view_layer.objects})

            if self.include_mod_objects:
                for mod in obj.modifiers:
                    if mod.show_viewport:
                        modobj = get_mod_obj(mod)

                        if modobj and modobj.name in context.view_layer.objects:
                            children.add(modobj)

        if self.unhide:
            ensure_visibility(context, children, unhide=True)

        visible_children = set(c for c in children if c.visible_get())
        hidden_children = set(children) - visible_children

        if debug:
            print()
            print("children (visible):")

            for obj in visible_children:
                print("", obj.name)

            print()
            print("children (hiddden)")

            for obj in hidden_children:
                print("", obj.name)

        if not self.include_selection:

            if visible_children:
                for obj in init_selection:
                    obj.select_set(False)

        for obj in visible_children:
            obj.select_set(True)

        new_selection = set(obj for obj in context.selected_objects)

        if debug:
            print()
            print("new selected:")

            for obj in new_selection:
                print("", obj.name)

        if init_selection == new_selection:
            if hidden_children:
                return 'BOTTOM', len(hidden_children)

            else:
                return 'ABSOLUTE_BOTTOM', 0

        elif active := context.active_object:

            for layer in layers:
                if (top_lvl_children := set(layer) & visible_children):

                    if active not in top_lvl_children:
                    
                        group_empties = [obj for obj in top_lvl_children if obj.M4.is_group_empty]

                        if group_empties:
                            context.view_layer.objects.active = group_empties[0]
                        else:
                            context.view_layer.objects.active = top_lvl_children.pop()

                    break

        return True
