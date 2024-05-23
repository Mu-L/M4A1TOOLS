import bpy
from bpy.props import EnumProperty, BoolProperty, StringProperty, IntProperty
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
from math import radians, degrees
from mathutils import Vector, Matrix, Quaternion
from mathutils.geometry import intersect_line_plane
from .. utils.collection import get_collection_depth
from .. utils.draw import draw_cross_3d, draw_fading_label, draw_init, draw_point, draw_vector, draw_label, get_text_dimensions, update_HUD_location, draw_circle, draw_mesh_wire
from .. utils.group import get_group_base_name, group, process_group_poses, retrieve_group_pose, set_group_pose, ungroup, get_group_matrix, select_group_children, get_child_depth, clean_up_groups, fade_group_sizes, prettify_group_pose_names, get_pose_batches, get_batch_pose_name, get_group_hierarchy, get_remove_poses
from .. utils.math import dynamic_format, compare_quat
from .. utils.modifier import get_mods_as_dict, add_mods_from_dict
from .. utils.object import parent, unparent, compensate_children
from .. utils.registration import get_prefs
from .. utils.ui import force_ui_update, init_cursor, init_status, finish_status, navigation_passthrough
from .. utils.view import get_view_origin_and_dir, get_location_2d
from .. items import group_location_items, axis_items, axis_vector_mappings, ctrl, axis_color_mappings, axis_index_mapping
from .. colors import red, blue, green, yellow, white, normal
from bpy.app.translations import pgettext as _
class Group(bpy.types.Operator):
    bl_idname = "m4n1.group"
    bl_label = "M4N1: Group"
    bl_description = "Group Objects by Parenting them to an Empty"
    bl_options = {'REGISTER', 'UNDO'}

    location: EnumProperty(name="Location", items=group_location_items, default='AVERAGE')
    rotation: EnumProperty(name="Rotation", items=group_location_items, default='WORLD')
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            sel = [obj for obj in context.selected_objects]
            if len(sel) == 1:
                obj = sel[0]
                parent = obj.parent

                if parent:
                    booleans = [mod for mod in parent.modifiers if mod.type == 'BOOLEAN' and mod.object == obj]
                    if booleans:
                        return False
            return True

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        row = column.row()
        row.label(text="Location")
        row.prop(self, 'location', expand=True)

        row = column.row()
        row.label(text="Rotation")
        row.prop(self, 'rotation', expand=True)

    def invoke(self, context, event):
        self.coords = Vector((event.mouse_region_x, event.mouse_region_y))

        return self.execute(context)

    def execute(self, context):
        sel = {obj for obj in context.selected_objects if (obj.parent and obj.parent.M4.is_group_empty) or not obj.parent}

        if sel:
            self.group(context, sel, debug=False)

            return {'FINISHED'}

        text = ["ℹℹ Illegal Selection ℹℹ",
                "You can't create a group from a selection of Objects that are all already parented to something (other other than group empties)"]

        draw_fading_label(context, text=text, x=self.coords.x, y=self.coords.y, color=[yellow, white], alpha=0.75, time=get_prefs().HUD_fade_group * 4, delay=1)
        return {'CANCELLED'}

    def group(self, context, sel, debug=False):
        grouped = {obj for obj in sel if obj.parent and obj.parent.M4.is_group_empty}

        selected_empties = {obj for obj in sel if obj.M4.is_group_empty}

        if debug:
            print()
            print("               sel: ", [obj.name for obj in sel])
            print("           grouped: ", [obj.name for obj in grouped])
            print("  selected empties: ", [obj.name for obj in selected_empties])

        if grouped == sel:

            unselected_empties = {obj.parent for obj in sel if obj not in selected_empties and obj.parent and obj.parent.M4.is_group_empty and obj.parent not in selected_empties}

            top_level = {obj for obj in selected_empties | unselected_empties if obj.parent not in selected_empties | unselected_empties}

            if debug:
                print("unselected empties:", [obj.name for obj in unselected_empties])
                print("         top level:", [obj.name for obj in top_level])

            if len(top_level) == 1:
                new_parent = top_level.pop()

            else:
                parent_groups = {obj.parent for obj in top_level}

                if debug:
                    print("     parent_groups:", [obj.name if obj else None for obj in parent_groups])

                new_parent = parent_groups.pop() if len(parent_groups) == 1 else None

        else:
            new_parent = None

        if debug:
            print("        new parent:", new_parent.name if new_parent else None)
            print(20 * "-")

        ungrouped = {obj for obj in sel - grouped if obj not in selected_empties}

        top_level = {obj for obj in selected_empties if obj.parent not in selected_empties}

        grouped = {obj for obj in grouped if obj not in selected_empties and obj.parent not in selected_empties}

        if len(top_level) == 1 and new_parent in top_level:
            new_parent = list(top_level)[0].parent

            if debug:
                print("updated parent", new_parent.name)

        if debug:
            print("     top level:", [obj.name for obj in top_level])
            print("       grouped:", [obj.name for obj in grouped])
            print("     ungrouped:", [obj.name for obj in ungrouped])

        for obj in top_level | grouped:
            unparent(obj)

        empty = group(context, top_level | grouped | ungrouped, location=self.location, rotation=self.rotation)

        if new_parent:
            parent(empty, new_parent)
            empty.M4.is_group_object = True

        clean_up_groups(context)

        if get_prefs().group_fade_sizes:
            fade_group_sizes(context, init=True)

        process_group_poses(empty)

        text = f"{'Sub' if new_parent else 'Root'} Goup: {empty.name}"
        color = green if new_parent else yellow
        draw_fading_label(context, text=text, x=self.coords.x, y=self.coords.y, color=color, alpha=0.75, time=get_prefs().HUD_fade_group)

class UnGroup(bpy.types .Operator):
    bl_idname = "m4n1.ungroup"
    bl_label = "M4N1: Un-Group"
    bl_options = {'REGISTER', 'UNDO'}

    ungroup_all_selected: BoolProperty(name="Un-Group all Selected Groups", default=False)
    ungroup_entire_hierarchy: BoolProperty(name="Un-Group entire Hierarchy down", default=False)
    @classmethod
    def description(cls, context, properties):
        if context.scene.M4.group_recursive_select and context.scene.M4.group_select:
            return _("Un-Group selected top-level Groups\nALT: Un-Group all selected Groups")
        else:
            return "Un-Group selected top-level Groups\nALT: Un-Group all selected Groups\nCTRL: Un-Group entire Hierarchy down"

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        row = column.row(align=True)
        row.label(text="Un-Group")
        row.prop(self, 'ungroup_all_selected', text='All Selected', toggle=True)
        row.prop(self, 'ungroup_entire_hierarchy', text='Entire Hierarchy', toggle=True)

    def invoke(self, context, event):
        self.ungroup_all_selected = event.alt
        self.ungroup_entire_hierarchy = event.ctrl

        return self.execute(context)

    def execute(self, context):
        empties, all_empties = self.get_group_empties(context)

        if empties:
            self.ungroup(empties, all_empties)

            top_empties = clean_up_groups(context)

            for empty in top_empties:
                process_group_poses(empty)

            if get_prefs().group_fade_sizes:
                fade_group_sizes(context, init=True)

            return {'FINISHED'}
        return {'CANCELLED'}

    def get_group_empties(self, context):
        all_empties = [obj for obj in context.selected_objects if obj.M4.is_group_empty]

        if self.ungroup_all_selected:
            empties = all_empties
        else:
            empties = [e for e in all_empties if e.parent not in all_empties]

        return empties, all_empties

    def collect_entire_hierarchy(self, empties):
        for e in empties:
            children = [obj for obj in e.children if obj.M4.is_group_empty]

            for c in children:
                self.empties.append(c)
                self.collect_entire_hierarchy([c])

    def ungroup(self, empties, all_empties):
        if self.ungroup_entire_hierarchy:
            self.empties = empties
            self.collect_entire_hierarchy(empties)
            empties = set(self.empties)

        for empty in empties:
            ungroup(empty)

class Groupify(bpy.types.Operator):
    bl_idname = "m4n1.groupify"
    bl_label = "M4N1: Groupify"
    bl_description = "Turn any Empty Hirearchy into Group"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.type == 'EMPTY' and not obj.M4.is_group_empty and obj.children]

    def execute(self, context):
        all_empties = [obj for obj in context.selected_objects if obj.type == 'EMPTY' and not obj.M4.is_group_empty and obj.children]

        empties = [e for e in all_empties if e.parent not in all_empties]

        self.groupify(empties)

        top_empties = clean_up_groups(context)

        for empty in top_empties:
            process_group_poses(empty)

        if get_prefs().group_fade_sizes:
            fade_group_sizes(context, init=True)

        return {'FINISHED'}

    def groupify(self, objects):
        for obj in objects:

            if obj.type == 'EMPTY' and not obj.M4.is_group_empty and obj.children:
                obj.M4.is_group_empty = True
                obj.M4.is_group_object = True if obj.parent and obj.parent.M4.is_group_empty else False
                obj.show_in_front = True
                obj.empty_display_type = 'CUBE'
                obj.empty_display_size = get_prefs().group_size
                obj.show_name = True

                if not any([s in obj.name.lower() for s in ['grp', 'group']]):
                    obj.name = f"{obj.name}_GROUP"

                set_group_pose(obj, name='Inception')

                self.groupify(obj.children)

            else:
                obj.M4.is_group_object = True

class Select(bpy.types.Operator):
    bl_idname = "m4n1.select_group"
    bl_label = "M4N1: Select Group"
    bl_description = _("Select Group\nCTRL: Select entire Group Hierarchy down")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        if context.scene.M4.group_recursive_select:
            return _("Select entire Group Hierarchies down")
        else:
            return _("Select Top Level Groups\nCTRL: Select entire Group Hierarchy down")

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.M4.is_group_empty or obj.M4.is_group_object]

    def invoke(self, context, event):
        clean_up_groups(context)

        empties = {obj for obj in context.selected_objects if obj.M4.is_group_empty}
        objects = [obj for obj in context.selected_objects if obj.M4.is_group_object and obj not in empties]

        for obj in objects:
            if obj.parent and obj.parent.M4.is_group_empty:
                empties.add(obj.parent)

        for e in empties:
            if e.visible_get():
                e.select_set(True)

                if len(empties) == 1:
                    context.view_layer.objects.active = e

            select_group_children(context.view_layer, e, recursive=event.ctrl or context.scene.M4.group_recursive_select)

        if get_prefs().group_fade_sizes:
            fade_group_sizes(context, init=True)

        return {'FINISHED'}

class Duplicate(bpy.types.Operator):
    bl_idname = "m4n1.duplicate_group"
    bl_label = "M4N1: duplicate_group"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        if context.scene.M4.group_recursive_select:
            return _("Duplicate entire Group Hierarchies down\nALT: Create Instances")
        else:
            return _("Duplicate Top Level Groups\nALT: Create Instances\nCTRL: Duplicate entire Group Hierarchies down")

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.M4.is_group_empty]

    def invoke(self, context, event):
        empties = [obj for obj in context.selected_objects if obj.M4.is_group_empty]

        bpy.ops.object.select_all(action='DESELECT')

        for e in empties:
            e.select_set(True)
            select_group_children(context.view_layer, e, recursive=event.ctrl or context.scene.M4.group_recursive_select)

        if get_prefs().group_fade_sizes:
            fade_group_sizes(context, init=True)

        bpy.ops.object.duplicate_move_linked('INVOKE_DEFAULT') if event.alt else bpy.ops.object.duplicate_move('INVOKE_DEFAULT')

        return {'FINISHED'}

class Add(bpy.types.Operator):
    bl_idname = "m4n1.add_to_group"
    bl_label = "M4N1: Add to Group"
    bl_description = "Add Selection to Group"
    bl_options = {'REGISTER', 'UNDO'}

    realign_group_empty: BoolProperty(name="Re-Align Group Empty", default=False)
    location: EnumProperty(name="Location", items=group_location_items, default='AVERAGE')
    rotation: EnumProperty(name="Rotation", items=group_location_items, default='WORLD')
    add_mirror: BoolProperty(name="Add Mirror Modifiers, if there are common ones among the existing Group's objects, that are missing from the new Objects", default=True)
    is_mirror: BoolProperty()

    add_color: BoolProperty(name="Add Object Color, from Group's Empty", default=True)
    is_color: BoolProperty()

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        column.prop(self, 'realign_group_empty', toggle=True)

        row = column.row()
        row.active = self.realign_group_empty
        row.prop(self, 'location', expand=True)

        row = column.row()
        row.active = self.realign_group_empty
        row.prop(self, 'rotation', expand=True)

        row = column.row(align=True)

        if self.is_color:
            row.prop(self, 'add_color', text="Add Color", toggle=True)

        if self.is_mirror:
            row.prop(self, 'add_mirror', text="Add Mirror", toggle=True)

    def invoke(self, context, event):
        self.coords = Vector((event.mouse_region_x, event.mouse_region_y))
        return self.execute(context)

    def execute(self, context):
        debug = False

        active_group = context.active_object if context.active_object and context.active_object.M4.is_group_empty and context.active_object.select_get() else None

        if not active_group:

            active_group = context.active_object.parent if context.active_object and context.active_object.M4.is_group_object and context.active_object.select_get() else None

            if not active_group:
                return {'CANCELLED'}

        objects = [obj for obj in context.selected_objects if obj != active_group and obj not in active_group.children and (not obj.parent or (obj.parent and obj.parent.M4.is_group_empty and not obj.parent.select_get()))]

        if debug:
            print("active group", active_group.name)
            print("     addable", [obj.name for obj in objects])

        if objects:

            children = [c for c in active_group.children if c.M4.is_group_object and c.type == 'MESH' and c.name in context.view_layer.objects]

            self.is_mirror = any(obj for obj in children for mod in obj.modifiers if mod.type == 'MIRROR')

            self.is_color = any(obj.type == 'MESH' for obj in objects)

            for obj in objects:
                if obj.parent:
                    unparent(obj)

                parent(obj, active_group)

                obj.M4.is_group_object = True

                if obj.type == 'MESH':

                    if children and self.add_mirror:
                        self.mirror(obj, active_group, children)

                    if self.add_color:
                        obj.color = active_group.color

            if self.realign_group_empty:

                gmx = get_group_matrix(context, [c for c in active_group.children], self.location, self.rotation)

                compensate_children(active_group, active_group.matrix_world, gmx)

                active_group.matrix_world = gmx

            clean_up_groups(context)

            process_group_poses(active_group)

            if get_prefs().group_fade_sizes:
                fade_group_sizes(context, init=True)

            text = f"Added {len(objects)} objects to group '{active_group.name}'"
            draw_fading_label(context, text=text, x=self.coords.x, y=self.coords.y, color=green, time=get_prefs().HUD_fade_group)

            return {'FINISHED'}
        return {'CANCELLED'}

    def mirror(self, obj, active_group, children):
        all_mirrors = {}

        for c in children:
            if c.M4.is_group_object and not c.M4.is_group_empty and c.type == 'MESH':
                mirrors = get_mods_as_dict(c, types=['MIRROR'], skip_show_expanded=True)

                if mirrors:
                    all_mirrors[c] = mirrors

        if all_mirrors and len(all_mirrors) == len(children):

            obj_props = [props for props in get_mods_as_dict(obj, types=['MIRROR'], skip_show_expanded=True).values()]

            if len(all_mirrors) == 1:

                common_props = [props for props in next(iter(all_mirrors.values())).values() if props not in obj_props]

            else:
                common_props = []

                for c, mirrors in all_mirrors.items():
                    others = [obj for obj in all_mirrors if obj != c]

                    for name, props in mirrors.items():
                        if all(props in all_mirrors[o].values() for o in others) and props not in common_props:
                            if props not in obj_props:
                                common_props.append(props)

            if common_props:
                common_mirrors = {f"Mirror{'.' + str(idx).zfill(3) if idx else ''}": props for idx, props in enumerate(common_props)}

                add_mods_from_dict(obj, common_mirrors)

class Remove(bpy.types.Operator):
    bl_idname = "m4n1.remove_from_group"
    bl_label = "M4N1: Remove from Group"
    bl_description = "Remove Selection from Group"
    bl_options = {'REGISTER', 'UNDO'}

    realign_group_empty: BoolProperty(name="Re-Align Group Empty", default=False)
    location: EnumProperty(name="Location", items=group_location_items, default='AVERAGE')
    rotation: EnumProperty(name="Rotation", items=group_location_items, default='WORLD')
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return True

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        column.prop(self, 'realign_group_empty', toggle=True)

        row = column.row()
        row.active = self.realign_group_empty
        row.prop(self, 'location', expand=True)

        row = column.row()
        row.active = self.realign_group_empty
        row.prop(self, 'rotation', expand=True)

    def invoke(self, context, event):
        self.coords = Vector((event.mouse_region_x, event.mouse_region_y))
        return self.execute(context)

    def execute(self, context):
        debug = False

        all_group_objects = [obj for obj in context.selected_objects if obj.M4.is_group_object]

        group_objects = [obj for obj in all_group_objects if obj.parent not in all_group_objects]

        if debug:
            print()
            print("all group objects", [obj.name for obj in all_group_objects])
            print("    group objects", [obj.name for obj in group_objects])

        if group_objects:

            empties = set()

            for obj in group_objects:
                empties.add(obj.parent)

                unparent(obj)
                obj.M4.is_group_object = False

            if self.realign_group_empty:
                for e in empties:
                    children = [c for c in e.children]

                    if children:
                        gmx = get_group_matrix(context, children, self.location, self.rotation)

                        compensate_children(e, e.matrix_world, gmx)

                        e.matrix_world = gmx

            top_empties = clean_up_groups(context)

            for empty in top_empties:
                process_group_poses(empty)

            text = f"Removed {len(group_objects)} objects from their group"
            draw_fading_label(context, text=text, x=self.coords.x, y=self.coords.y, color=red, time=get_prefs().HUD_fade_group)

            return {'FINISHED'}
        return {'CANCELLED'}

class ToggleChildren(bpy.types.Operator):
    bl_idname = "m4n1.toggle_outliner_children"
    bl_label = "M4N1: Toggle Outliner Children"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'OUTLINER'

    def execute(self, context):
        area = context.area
        space = area.spaces[0]

        space.use_filter_children = not space.use_filter_children

        return {'FINISHED'}

class ToggleGroupMode(bpy.types.Operator):
    bl_idname = "m4n1.toggle_outliner_group_mode"
    bl_label = "M4N1: Toggle Outliner Group Mode"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'OUTLINER'

    def execute(self, context):
        area = context.area
        space = area.spaces[0]

        if space.use_filter_object_mesh:
            space.use_filter_collection = False
            space.use_filter_object_mesh = False
            space.use_filter_object_content = False
            space.use_filter_object_armature = False
            space.use_filter_object_light = False
            space.use_filter_object_camera = False
            space.use_filter_object_others = False
            space.use_filter_children = True

        else:
            space.use_filter_collection = True
            space.use_filter_object_mesh = True
            space.use_filter_object_content = True
            space.use_filter_object_armature = True
            space.use_filter_object_light = True
            space.use_filter_object_camera = True
            space.use_filter_object_others = True

        return {'FINISHED'}

class CollapseOutliner(bpy.types.Operator):
    bl_idname = "m4n1.collapse_outliner"
    bl_label = "M4N1: Collapse Outliner"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'OUTLINER'

    def execute(self, context):
        col_depth = get_collection_depth(self, [context.scene.collection], init=True)

        child_depth = get_child_depth(self, [obj for obj in context.scene.objects if obj.children], init=True)

        for i in range(max(col_depth, child_depth) + 1):
            bpy.ops.outliner.show_one_level(open=False)

        return {'FINISHED'}

class ExpandOutliner(bpy.types.Operator):
    bl_idname = "m4n1.expand_outliner"
    bl_label = "M4N1: Expand Outliner"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'OUTLINER'

    def execute(self, context):
        bpy.ops.outliner.show_hierarchy()

        depth = get_collection_depth(self, [context.scene.collection], init=True)

        for i in range(depth):
            bpy.ops.outliner.show_one_level(open=True)

        return {'FINISHED'}

def draw_transform_group(op):
    def draw(self, context):
        layout = self.layout

        if op.pidx > 0:
            pose = op.poseCOL[op.pidx - 1]
        else:
            pose = None

        row = layout.row(align=True)

        row.label(text="Transform Group")

        row.label(text="", icon='MOUSE_LMB')

        if op.pidx == 0 or pose.remove:
            row.label(text="Finish")

        else:
            row.label(text="Recall Pose + Finish")

            row.label(text="", icon='EVENT_SPACEKEY')
            row.label(text="Finish")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.label(text="", icon='EVENT_G')
        row.label(text="Select Group Empty")

        row.label(text="", icon='EVENT_Q')
        row.label(text="Setup Group Gizmos")

        row.separator(factor=10)

        row.label(text="", icon='EVENT_CTRL')
        row.label(text="5° Angle Snap")

        if op.poseCOL:
            row.separator(factor=1)
            row.label(text="", icon='MOUSE_MMB')
            row.label(text=f"Pose: {pose.name if pose else 'None'}{' (remove)' if pose and pose.remove else ''}")

            if op.pidx > 0:
                row.separator(factor=1)
                row.label(text="", icon='EVENT_ALT')
                row.label(text="", icon='MOUSE_MMB')
                row.label(text=f"Preview Alpha: {dynamic_format(op.empty.M4.group_pose_alpha, 0)}")

        row.separator(factor=2)
        row.label(text="", icon='EVENT_S')
        row.label(text=f"Set Pose + Finish")

        row.separator(factor=2)

        if op.pidx > 0:
            row.label(text="", icon='EVENT_X')
            row.label(text=f"Mark Pose for Removal")

        if op.poseCOL:
            row.separator(factor=1)
            row.label(text="", icon='EVENT_A')
            row.label(text=f"Mark All Poses for Removal")

    return draw

class TransformGroup(bpy.types.Operator):
    bl_idname = "m4n1.transform_group"
    bl_label = "M4N1: Transform Group"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Group Empty Name")
    axis: EnumProperty(name="Rotation Axis", items=axis_items, default='X')
    @classmethod
    def description(cls, context, properties):
        return f"Rotate Group '{properties.name}' around its {properties.axis} Axis"

    def draw_HUD(self, context):
        if self.area == context.area:
            draw_init(self, None)

            color = axis_color_mappings[self.axis]
            draw_vector(self.mousepos.resized(3) - self.group_location_2d.resized(3), origin=self.group_location_2d.resized(3), color=color, fade=True)

            prefix, basename, suffix = get_group_base_name(self.empty.name)

            if prefix:
                dims = draw_label(context, title=prefix, coords=Vector((self.HUD_x, self.HUD_y)), center=False, size=10, color=white, alpha=0.3)
            else:
                dims = (0, 0)

            dims2 = draw_label(context, title=basename, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=yellow, alpha=1)

            if suffix:
                draw_label(context, title=suffix, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.3)

            self.offset += 18
            dims = draw_label(context, title="Rotate Group", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)
            dims2 = draw_label(context, title=" around ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=white, alpha=0.5)
            draw_label(context, title=self.axis, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=red if self.axis == 'X' else green if self.axis == 'Y' else blue, alpha=1)

            self.offset += 18
            dims = draw_label(context, title="Angle: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
            alpha = 1 if self.pidx == 0 else 0.5

            angle = dynamic_format(self.HUD_angle, decimal_offset=0 if self.is_angle_snapping else 2)
            dims2 = draw_label(context, title=f"{angle}° ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=yellow if self.is_angle_snapping else white, alpha=alpha)

            if self.is_angle_snapping:
                draw_label(context, title="Snapping", coords=Vector((self.HUD_x+ dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=alpha)

            self.offset += 24
            dims = draw_label(context, title="Pose: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

            max_dim = max([get_text_dimensions(context, f"{name}  ")[0] for name in self.poses])

            pose_axes_differ = len(set(pose.axis for pose in self.poseCOL if pose.axis)) > 1

            if self.pidx > 0:
                alpha_dims = draw_label(context, title="Alpha: ", coords=Vector((self.HUD_x + dims[0] + max_dim, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                draw_label(context, title=dynamic_format(self.empty.M4.group_pose_alpha, 0), coords=Vector((self.HUD_x + dims[0] + max_dim + alpha_dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            for idx, name in enumerate(self.poses):

                if idx > 0:
                    self.offset += 18

                    pose = self.poseCOL[idx - 1]
                    color = red if pose.remove else green if name == 'Inception' else yellow if name == 'LegacyPose' else blue

                else:
                    color = white

                alpha, size = (1, 12) if idx == self.pidx else (0.5, 10)
                
                if idx == 0:
                    draw_label(context, title=name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=size, color=color, alpha=alpha)

                elif idx == self.pidx:
                    pose_emoji = '❌ ' if pose.remove else '🏃'
                    offset_x = get_text_dimensions(context, f"{pose_emoji}")[0]

                    draw_label(context, title=f"{pose_emoji}{name}", coords=Vector((self.HUD_x + dims[0] - offset_x, self.HUD_y)), offset=self.offset, center=False, size=size, color=color, alpha=alpha)

                else:
                    draw_label(context, title=name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=size, color=color, alpha=alpha)

                if idx > 0 and pose.axis:

                    if pose_axes_differ:
                        color = red if pose.axis == 'X' else green if pose.axis == 'Y' else blue
                        axis_dim = draw_label(context, title=f"{pose.axis} ", coords=Vector((self.HUD_x + dims[0] + max_dim, self.HUD_y)), offset=self.offset, center=False, size=size, color=color, alpha=alpha)
                    else:
                        axis_dim = (0, 0)

                    draw_label(context, title=f"{dynamic_format(pose.angle, decimal_offset=1)}°", coords=Vector((self.HUD_x + dims[0] + max_dim + axis_dim[0], self.HUD_y)), offset=self.offset, center=False, size=size, color=white, alpha=alpha)

    def draw_VIEW3D(self, context):
        if self.area == context.area:

            if self.pidx > 0:
                selected_pose = self.poseCOL[self.pidx - 1]
                alpha = self.empty.M4.group_pose_alpha

                for pose, batches in self.pose_batche_coords.items():

                    if batches:
                        color = red if pose.remove else green if pose.name == 'Inception' else yellow if pose.name == 'LegacyPose' else blue

                        if pose == selected_pose:
                            for batch in batches:

                                if isinstance(batch[0], Matrix):
                                    mx, length = batch
                                    draw_cross_3d(Vector(), mx=mx, length=length, color=normal)

                                else:
                                    draw_mesh_wire(batch, color=color, alpha=alpha)

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y))
            update_HUD_location(self, event, offsetx=20, offsety=20)

        self.is_angle_snapping = event.ctrl

        events = ['MOUSEMOVE', 'S', 'X', 'A', 'K', *ctrl, 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'G', 'Q']

        if event.type in events:

            if event.type in ['MOUSEMOVE', *ctrl]:

                rotation = self.get_rotation(context)

                self.empty.matrix_world = Matrix.LocRotScale(self.init_location, rotation, self.init_scale)

            elif event.type in ['WHEELUPMOUSE', 'WHEELDOWNMOUSE'] and self.poseCOL:

                if event.alt and self.pidx > 0:
                    alpha = self.empty.M4.group_pose_alpha

                    if event.type == 'WHEELUPMOUSE':
                        if alpha <= 0.1:
                            alpha += 0.01

                        else:
                            alpha += 0.1

                    else:
                        if alpha <= 0.11:
                            alpha -= 0.01

                        else:
                            alpha -= 0.1

                    alpha = min(max(alpha, 0.01), 1)

                    for e in self.empties:
                        e.M4.avoid_update = True
                        e.M4.group_pose_alpha = alpha

                else:

                    if event.type == 'WHEELUPMOUSE':
                        self.pidx -= 1

                    else:
                        self.pidx += 1

                    if self.pidx < 0:
                        self.pidx = len(self.poses) - 1

                    elif self.pidx >= len(self.poses):
                        self.pidx = 0

                if not self.pose_batche_coords[self.poseCOL[self.pidx - 1]]:
                    get_pose_batches(context, self.empty, pose := self.poseCOL[self.pidx - 1], self.pose_batche_coords[pose], children=self.group_children, dg=self.dg)

                force_ui_update(context)

            elif event.type in ['S', 'X', 'A', 'K'] and event.value == 'PRESS':

                if event.type == 'S':
                    self.finish()

                    set_group_pose(self.empty)

                    location = self.empty.matrix_world.to_translation()
                    bpy.ops.m4n1.draw_group_rest_pose(location=location, size=self.gizmo_size, time=1, alpha=0.2, reverse=False)

                    self.is_setting_rest_pose = True

                    self.auto_keyframe(context)

                    return {'FINISHED'}

                elif event.type == 'X' and self.pidx > 0:
                    pose = self.poseCOL[self.pidx - 1]
                    pose.remove = not pose.remove

                elif event.type == 'A':

                    state = not self.poseCOL[0].remove

                    for pose in self.poseCOL:
                        pose.remove = state

                force_ui_update(context)

            elif event.type == 'G' and event.value == 'PRESS':
                self.empty.matrix_world = Matrix.LocRotScale(self.init_location, self.init_rotation, self.init_scale)

                self.finish()

                bpy.ops.object.select_all(action='DESELECT')
                self.empty.select_set(True)
                context.view_layer.objects.active = self.empty

                return {'FINISHED'}

            elif event.type == 'Q' and event.value == 'PRESS':
                self.empty.matrix_world = Matrix.LocRotScale(self.init_location, self.init_rotation, self.init_scale)

                self.finish()

                bpy.ops.object.select_all(action='DESELECT')
                self.empty.select_set(True)
                context.view_layer.objects.active = self.empty

                bpy.ops.m4n1.setup_group_gizmos('INVOKE_DEFAULT')

                return {'FINISHED'}

        elif event.type in {'LEFTMOUSE', 'SPACE'}:
            self.finish()

            remove_poses = [pose for pose in self.poseCOL if pose.remove]
            recall_pose = self.poseCOL[self.pidx - 1] if self.pidx > 0 else None

            if recall_pose and recall_pose not in remove_poses and event.type == 'LEFTMOUSE':

                self.empty.M4.group_pose_IDX = self.pidx - 1

                retrieve_group_pose(self.empty)

                location = self.empty.matrix_world.to_translation()
                bpy.ops.m4n1.draw_group_rest_pose(location=location, size=self.gizmo_size, time=1, alpha=0.2, reverse=True)

                self.is_recalling_rest_pose = True

            if remove_poses:
                remaining = [(pose.name, pose.mx.copy(), pose.uuid, pose.batch, pose.batchlinked, pose.axis, pose.angle) for pose in self.poseCOL if not pose.remove]

                is_inception_removal = any(p.uuid == '00000000-0000-0000-0000-000000000000' for p in remove_poses)
                print("is inception removal:", is_inception_removal)
                
                self.empty.M4.group_pose_COL.clear()
                
                for idx, (name, mx, uuid, batch, batchlinked, axis, angle) in enumerate(remaining):
                    pose = self.empty.M4.group_pose_COL.add()
                    pose.index = idx

                    pose.avoid_update = True
                    pose.name = name

                    pose.mx = mx
                    pose.uuid = uuid
                    pose.batch = batch
                    pose.batchlinked = batchlinked

                    if not is_inception_removal:
                        pose.axis = axis
                        pose.angle = angle

                process_group_poses(self.empty)

                self.empty.M4.group_pose_IDX = 0 if remaining else -1

                prettify_group_pose_names(self.empty.M4.group_pose_COL)

            self.auto_keyframe(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.empty.matrix_world = Matrix.LocRotScale(self.init_location, self.init_rotation, self.init_scale)

            self.finish()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        finish_status(self)

    def invoke(self, context, event):
        self.gzm_grp = context.gizmo_group

        self.empty = bpy.data.objects.get(self.name)

        if self.empty and self.gzm_grp:

            self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y))
            self.HUD_angle = 0
            self.is_angle_snapping = False

            self.empty_dir = None

            self.axis_direction = axis_vector_mappings[self.axis]
            self.init_rotation_intersect = None

            self.init_mx = self.empty.matrix_world.copy()
            self.init_location, self.init_rotation, self.init_scale = self.init_mx.decompose()

            self.group_location_2d = get_location_2d(context, self.init_location)

            self.is_setting_rest_pose = False
            self.is_recalling_rest_pose = False

            self.empties = get_group_hierarchy(self.empty, up=True)

            self.gzm, self.others = self.get_gizmos(self.gzm_grp)

            self.gizmo_size = self.gzm.scale_basis

            self.init_poses(context)

            init_cursor(self, event, offsetx=20, offsety=20)

            init_status(self, context, func=draw_transform_group(self))

            if context.visible_objects:
                context.visible_objects[0].select_set(context.visible_objects[0].select_get())

            self.area = context.area
            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        return {'CANCELLED'}

    def get_gizmos(self, gzm_group):
        active_gzm = None
        other_gizmos = []

        if gzm_group:
            for gzm in gzm_group.gizmos:
                if gzm.is_modal:
                    active_gzm = gzm

                else:
                    other_gizmos.append(gzm)

        return active_gzm, other_gizmos

    def init_poses(self, context):
        self.dg = context.evaluated_depsgraph_get()
        
        self.poseCOL = self.empty.M4.group_pose_COL
        self.poses = ['None']

        self.pidx = 0

        self.pose_batche_coords = {}

        self.group_children = [obj for obj in self.empty.children_recursive if obj.name in context.view_layer.objects and obj.visible_get()]

        for idx, pose in enumerate(self.poseCOL):
            self.poses.append(pose.name)

            pose.remove = False

            if self.pidx == 0 and pose.name not in ['Inception', 'LegacyPose'] and compare_quat(pose.mx.to_quaternion(), self.empty.matrix_local.to_quaternion(), precision=5, debug=False):
                self.pidx = idx + 1

            self.pose_batche_coords[pose] = []

        if self.pidx > 0:
            get_pose_batches(context, self.empty, pose := self.poseCOL[self.pidx - 1], self.pose_batche_coords[pose], children=self.group_children, dg=self.dg)

    def get_rotation(self, context):
        mx = self.empty.matrix_world

        self.view_origin = region_2d_to_origin_3d(context.region, context.region_data, self.mousepos)
        self.view_dir = region_2d_to_vector_3d(context.region, context.region_data, self.mousepos)

        self.empty_origin = mx.to_translation()

        if self.empty_dir is None:
            self.empty_dir = (mx.to_quaternion() @ self.axis_direction)

        i = intersect_line_plane(self.view_origin, self.view_origin + self.view_dir, self.empty_origin, self.empty_dir)

        if i:

            if not self.init_rotation_intersect:
                self.init_rotation_intersect = i
                return self.init_rotation

            else:
                v1 = self.init_rotation_intersect - self.empty_origin
                v2 = i - self.empty_origin

                deltarot = v1.rotation_difference(v2).normalized()

                angle = v1.angle(v2)

                if self.is_angle_snapping:
                    step = 5

                    dangle = degrees(angle)
                    mod = dangle % step

                    angle = radians(dangle + (step - mod)) if mod >= (step / 2) else radians(dangle - mod)

                    deltarot = Quaternion(deltarot.axis, angle)

                rotation = (deltarot @ self.init_rotation).normalized()

                dot = round(self.empty_dir.dot(deltarot.axis))

                self.HUD_angle = dot * degrees(angle)

                return rotation
            return self.init_rotation

    def auto_keyframe(self, context, init=False):

        return

        scene = context.scene

        self.empty.rotation_mode = 'QUATERNION'

        if init and not scene.tool_settings.use_keyframe_insert_auto:
            scene.tool_settings.use_keyframe_insert_auto = True

        if scene.tool_settings.use_keyframe_insert_auto:
            frame = scene.frame_current
            mode = self.empty.rotation_mode
            data_path = 'rotation_quaternion'

            self.empty.keyframe_insert(data_path=data_path, frame=frame)

            print("INFO: Auto-keyed rotation of", self.empty.name, "at frame", frame)

class BakeGroupGizmoSize(bpy.types.Operator):
    bl_idname = "m4n1.bake_group_gizmo_size"
    bl_label = "M4N1: Bake Group Gizmo Size"
    bl_description = "Set Global Size to 1, and compensate each Group's Size accordingly."
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.M4.group_gizmo_size != 1

    def execute(self, context):
        gizmo_size = context.scene.M4.group_gizmo_size
        divider = 1 / gizmo_size

        group_empties = [obj for obj in bpy.data.objects if obj.type == 'EMPTY' and obj.M4.is_group_empty]

        for obj in group_empties:
            obj.M4.group_gizmo_size /= divider

        context.scene.M4.group_gizmo_size = 1
        return {'FINISHED'}

def draw_setup_group_gizmos_status(op):
    def draw(self, context):
        decimal_offset = 2 if op.empty.M4.group_gizmo_size > 1 else 1

        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"Setup Group Gizmos")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text="", icon='MOUSE_MMB')
        row.label(text=f"Adjust Size: {dynamic_format(op.empty.M4.group_gizmo_size, decimal_offset=decimal_offset)}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_TAB')
        row.label(text=f"Toggle Axis Gizmo based on View: {op.aligned_axis}")

        row.separator(factor=1)

        row.label(text="", icon='EVENT_X')
        row.label(text=f"X Axis Gizmo: {op.empty.M4.show_group_x_rotation}")

        row.separator(factor=1)

        row.label(text="", icon='EVENT_Y')
        row.label(text=f"Y Axis Gizmo: {op.empty.M4.show_group_y_rotation}")

        row.separator(factor=1)

        row.label(text="", icon='EVENT_Z')
        row.label(text=f"Z Axis Gizmo: {op.empty.M4.show_group_z_rotation}")

        row.separator(factor=1)

        row.label(text="", icon='EVENT_A')
        row.label(text="Toggle All")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_R')
        row.label(text=f"Lock Axes without Gizmos: {op.lock_axes}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_S')
        row.label(text=f"Show Gizmo{'s' if len(op.axes) > 1 else''}: {op.empty.M4.show_group_gizmo}")

    return draw

class SetupGroupGizmos(bpy.types.Operator):
    bl_idname = "m4n1.setup_group_gizmos"
    bl_label = "M4N1: Setup Group Gizmos"
    bl_description = "Setup Group Gizmos"
    bl_options = {'REGISTER', 'UNDO'}

    lock_axes: BoolProperty(name="Lock Rotational Axes without Gizmos", default=True)
    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.M4.is_group_empty

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

    def draw_HUD(self, context):
        if self.area == context.area:
            draw_init(self, None)

            prefix, basename, suffix = get_group_base_name(self.empty.name)

            if prefix:
                dims = draw_label(context, title=prefix, coords=Vector((self.HUD_x, self.HUD_y)), center=False, size=10, color=white, alpha=0.3)
            else:
                dims = (0, 0)

            dims2 = draw_label(context, title=basename, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=yellow, alpha=1)

            if suffix:
                draw_label(context, title=suffix, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.3)

            self.offset += 18
            alpha = 1 if self.empty.M4.show_group_gizmo else 0.25
            dims = draw_label(context, title="Setup Group Gizmos ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=alpha)

            if not self.empty.M4.show_group_gizmo:
                draw_label(context, title=" Disabled", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=white, alpha=0.5)

            self.offset += 18
            axis_offset = 0

            axes = self.axes.copy()

            if self.aligned_axis not in axes:
                axes.append(self.aligned_axis)
                axes.sort()

            dims = draw_label(context, title="Axes: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

            for axis in axes:
                if axis == self.aligned_axis and not getattr(self.empty.M4, f"show_group_{axis.lower()}_rotation"):
                    color, alpha = white, 0.3
                else:
                    color = red if axis == 'X' else green if axis == 'Y' else blue
                    alpha = 1

                axis_dims = draw_label(context, title=f"{axis} ", coords=Vector((self.HUD_x + dims[0] + axis_offset, self.HUD_y)), offset=self.offset, center=False, color=color, alpha=alpha)
                axis_offset += axis_dims[0]

            self.offset += 18

            dims = draw_label(context, title="Size: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

            decimal_offset = 1 if self.empty.M4.group_gizmo_size > 1 else 0

            if self.is_shift:
                decimal_offset += 1
            elif self.is_ctrl:
                decimal_offset -= 1

            dims2 = draw_label(context, title=f"{dynamic_format(self.empty.M4.group_gizmo_size, decimal_offset=decimal_offset)} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            if self.is_shift or self.is_ctrl:
                dims3 = draw_label(context, title="🔍 " if self.is_shift else "💪 ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, size=12, color=white, alpha=0.5)

            else:
                dims3 = (0, 0)
            
            if context.scene.M4.group_gizmo_size != 1:
                dims4 = draw_label(context, title=" ⚠", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, size=20, color=yellow, alpha=1)
                draw_label(context, title=f" Global: {dynamic_format(context.scene.M4.group_gizmo_size)}", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.25)

            if self.lock_axes:
                self.offset += 18

                dims = draw_label(context, title="Lock Rotational Axes ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)
                draw_label(context, title="(those without Gizmos)", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=white, alpha=0.5)

    def draw_VIEW3D(self, context):
        if context.area == self.area:

            scale = context.preferences.system.ui_scale
            size = self.empty.M4.group_gizmo_size * context.scene.M4.group_gizmo_size * (self.empty.empty_display_size / 0.2) * (sum(self.gmx.to_scale()) / 3)

            axes = [axis.capitalize() for axis in ['x', 'y', 'z'] if getattr(self.empty.M4, f"show_group_{axis}_rotation")]

            if self.aligned_axis in axes:
                color = red if self.aligned_axis == 'X' else green if self.aligned_axis == 'Y' else blue
                alpha, width = 0.3, 5

            else:
                color, alpha, width = white, 0.03, 10

            radius = size * scale

            draw_circle(loc=self.gloc, rot=self.aligned_rot, radius=radius, segments=100, width=width, color=color, alpha=alpha)

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y))
            update_HUD_location(self, event, offsetx=20, offsety=20)

        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        events = ['MOUSEMOVE', 'A', 'X', 'Y', 'Z', 'T', 'TAB', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'ONE', 'TWO', 'S', 'D', 'R', 'L']

        if event.type in events:
            if event.type == 'MOUSEMOVE':
                if self.passthrough:
                    self.aligned_axis, self.aligned_rot = self.get_group_axis_aligned_with_view(context, debug=False)
                    self.passthrough = False

                    force_ui_update(context)

            elif event.type in ['WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'ONE', 'TWO']:
                if event.type in ['WHEELUPMOUSE', 'ONE']:
                    self.empty.M4.group_gizmo_size += 0.01 if self.is_shift else 1 if self.is_ctrl else 0.1
                else:
                    self.empty.M4.group_gizmo_size -= 0.01 if self.is_shift else 1 if self.is_ctrl else 0.1

            if event.type == 'A' and event.value == 'PRESS':
                axes = [getattr(self.empty.M4, f"show_group_{axis}_rotation") for axis in ['x', 'y', 'z']]

                if all(axes):
                    for axis in ['x', 'y', 'z']:
                        self.empty.M4.avoid_update = False
                        setattr(self.empty.M4, f"show_group_{axis}_rotation", False)

                else:
                    for axis in ['x', 'y', 'z']:
                        if not getattr(self.empty.M4, f"show_group_{axis}_rotation"):
                            self.empty.M4.avoid_update = False
                            setattr(self.empty.M4, f"show_group_{axis}_rotation", True)

                self.get_enabled_axes()

                self.set_axes_locks()

            elif event.type in ['X', 'Y', 'Z', 'TAB', 'T'] and event.value == 'PRESS':

                if event.type == 'X':
                    axis = 'X'

                elif event.type == 'Y':
                    axis = 'Y'

                elif event.type == 'Z':
                    axis = 'Z'

                elif event.type in ['TAB', 'T'] and event.value == 'PRESS':
                    axis = self.aligned_axis

                self.empty.M4.avoid_update = True
                setattr(self.empty.M4, f"show_group_{axis.lower()}_rotation", not getattr(self.empty.M4, f"show_group_{axis.lower()}_rotation"))

                self.get_enabled_axes()

                self.set_axes_locks()

            elif event.type in ['S', 'D'] and event.value == 'PRESS':
                self.empty.M4.show_group_gizmo = not self.empty.M4.show_group_gizmo

            elif event.type in ['R', 'L'] and event.value == 'PRESS':
                self.lock_axes = not self.lock_axes

                self.set_axes_locks()

        if navigation_passthrough(event, alt=True, wheel=False):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE'] and event.value == 'PRESS':
            self.finish(context)

            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
            self.finish(context)

            self.restore_initial_state(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        finish_status(self)

    def invoke(self, context, event):
        self.empty = context.active_object
        self.gmx = self.empty.matrix_world
        self.gloc = self.gmx.to_translation()

        self.fetch_initial_state(context)

        self.aligned_axis, self.aligned_rot = self.get_group_axis_aligned_with_view(context, debug=False)

        if not context.scene.M4.show_group_gizmos:
            context.scene.M4.avoid_update = True
            context.scene.M4.show_group_gizmos = True

        if not self.empty.M4.show_group_gizmo:
            self.empty.M4.avoid_update = True
            self.empty.M4.show_group_gizmo = True

            if not any([getattr(self.empty.M4, f"show_group_{axis}_rotation") for axis in ['x', 'y', 'z']]):

                self.empty.M4.avoid_update = True
                setattr(self.empty.M4, f"show_group_{self.aligned_axis.lower()}_rotation", True)

        self.get_enabled_axes()

        self.set_axes_locks()

        force_ui_update(context)

        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        init_cursor(self, event, offsetx=20, offsety=20)
        self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        init_status(self, context, func=draw_setup_group_gizmos_status(self))

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def fetch_initial_state(self, context):
        self.init_props = {'show_group_gizmos': context.scene.M4.show_group_gizmos,
                           'show_group_gizmo': self.empty.M4.show_group_gizmo,

                           'show_group_x_rotation': self.empty.M4.show_group_x_rotation,
                           'show_group_y_rotation': self.empty.M4.show_group_y_rotation,
                           'show_group_z_rotation': self.empty.M4.show_group_z_rotation,

                           'lock_rotation_x': self.empty.lock_rotation[0],
                           'lock_rotation_y': self.empty.lock_rotation[1],
                           'lock_rotation_z': self.empty.lock_rotation[2],

                           'group_gizmo_size': self.empty.M4.group_gizmo_size}

    def get_enabled_axes(self):
        self.axes = [axis.capitalize() for axis in ['x', 'y', 'z'] if getattr(self.empty.M4, f"show_group_{axis}_rotation")]

    def set_axes_locks(self):
        for idx, (axis, _, _) in enumerate(axis_items):
            if self.lock_axes:
                self.empty.lock_rotation[idx] = self.empty.M4.show_group_gizmo and axis not in self.axes 

            else:
                if self.empty.lock_rotation[idx] != (init_state := self.init_props[f"lock_rotation_{axis.lower()}"]):
                    self.empty.lock_rotation[idx] = init_state

    def restore_initial_state(self, context):
        for prop, state in self.init_props.items():
            if prop == 'show_group_gizmos':
                context.scene.M4.avoid_update = True
                setattr(context.scene.M4, prop, state)

            elif 'lock_rotation_' in prop:
                axis = prop.replace('lock_rotation_', '').capitalize()
                self.empty.lock_rotation[axis_index_mapping[axis]] = state
                
            else:
                self.empty.M4.avoid_update = True
                setattr(self.empty.M4, prop, state)

    def get_group_axis_aligned_with_view(self, context, debug=False):
        view_center = Vector((context.region.width / 2, context.region.height / 2))

        view_origin, view_dir = get_view_origin_and_dir(context, view_center)

        if debug:
            draw_point(view_origin, modal=False)
            draw_vector(view_dir, origin=view_origin, modal=False)

        axes = []

        group_loc, group_rot, _ = self.gmx.decompose()
        group_up = group_rot @ Vector((0, 0, 1))

        for axis in ['X', 'Y', 'Z']:
            group_axis_dir = group_rot @ axis_vector_mappings[axis]

            if debug:
                draw_vector(group_axis_dir, origin=group_loc, modal=False)

            dot = group_axis_dir.dot(view_dir)

            axis_rot = group_axis_dir.rotation_difference(group_up) @ group_rot

            axes.append((axis, axis_rot, dot))

            if debug:
                print(axis, dot)

        aligned = max(axes, key=lambda x: abs(x[2]))

        if debug:
            print("aligned axis:", aligned[0])
            print("aligned rotation:", aligned[1])

        return aligned[0], aligned[1]

class SetGroupPose(bpy.types.Operator):
    bl_idname = "m4n1.set_group_pose"
    bl_label = "M4N1: Set Group Pose"
    bl_description = "Set Group Pose"
    bl_options = {'REGISTER', 'UNDO'}

    batch: BoolProperty(name="Batch Pose", default=False)
    @classmethod
    def description(cls, context, properties):
        active = context.active_object

        if properties.batch:
            return _("Create linked Batch Poses for {} and all Group Empties under it").format(active.name)

        else:
            return _("Create new Pose based on {}'s current Rotation").format(active.name)

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.type == 'EMPTY' and active.M4.is_group_empty

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

    def execute(self, context):
        active = context.active_object

        if self.batch:
            group_empties = get_group_hierarchy(active, up=False)

            if group_empties:

                name = get_batch_pose_name(group_empties)

                uuid = set_group_pose(active, name=name, batch=True)

                for obj in group_empties:
                    if obj != active:
                        set_group_pose(obj, name=name, uuid=uuid, batch=True)

            else:
                return {'CANCELLED'}

        else:
            set_group_pose(active)

        return {'FINISHED'}

class UpdateGroupPose(bpy.types.Operator):
    bl_idname = "m4n1.update_group_pose"
    bl_label = "M4N1: Update Group Pose"
    bl_description = "Update active Pose from current Group Empty Rotation"
    bl_options = {'REGISTER', 'UNDO'}

    is_batch = BoolProperty(name="Batch Retrieval", default=False)
    update_up: BoolProperty(name="Update Up", description="Update Poses Up the Hierarchy too", default=False)
    update_unlinked: BoolProperty(name="Update Unlinked", description="Update Poses, that have been unlinked too", default=False)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.type == 'EMPTY' and active.M4.is_group_empty and (poseCOL := active.M4.group_pose_COL) and 0 <= active.M4.group_pose_IDX < len(poseCOL)

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        if self.is_batch:
            row = column.row(align=True)

            row.prop(self, 'update_up', toggle=True)
            row.prop(self, 'update_unlinked', toggle=True)

    def invoke(self, context, event):
        active = context.active_object
        poseCOL = active.M4.group_pose_COL
        pose = poseCOL[active.M4.group_pose_IDX]

        self.is_batch = pose.batch
        return self.execute(context)

    def execute(self, context):
        active = context.active_object
        poseCOL = active.M4.group_pose_COL
        pose = poseCOL[active.M4.group_pose_IDX]

        pose.mx = active.matrix_local

        if pose.uuid == '00000000-0000-0000-0000-000000000000':
            for pose in active.M4.group_pose_COL:
                if pose.axis:
                    pose.axis = ''

        elif pose.axis:
            pose.axis = ''

        pose = poseCOL[active.M4.group_pose_IDX]
        uuid = pose.uuid

        if pose.batch and pose.batchlinked:
            group_empties = get_group_hierarchy(active, up=self.update_up)

            for empty in group_empties:
                if empty != active:

                    batch_poses = [p for p in empty.M4.group_pose_COL if p.batch and p.uuid == uuid]

                    if batch_poses:
                        batch_pose = batch_poses[0]

                        if self.update_unlinked or batch_pose.batchlinked:
                            batch_pose.mx = empty.matrix_local

                            if batch_pose.axis:
                                batch_pose.axis = ''

                            if batch_pose.uuid == '00000000-0000-0000-0000-000000000000':
                                for p in empty.M4.group_pose_COL:
                                    if p.axis:
                                        p.axis = ''

                            elif batch_pose.axis:
                                batch_pose.axis = ''
        
        process_group_poses(active, debug=False)

        force_ui_update(context)

        return {'FINISHED'}

class RetrieveGroupPose(bpy.types.Operator):
    bl_idname = "m4n1.retrieve_group_pose"
    bl_label = "M4N1: Retrieve Group Pose"
    bl_description = "Retrieve Selected Group Pose"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    is_batch = BoolProperty(name="Batch Retrieval", default=False)
    retrieve_up: BoolProperty(name="Retrieve Up", description="Retrieve Poses Up the Hierarchy too", default=False)
    retrieve_unlinked: BoolProperty(name="Retrieve Unlinked", description="Retrieve Poses, that have been unlinked too", default=False)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.type == 'EMPTY' and active.M4.is_group_empty and active.M4.group_pose_COL

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        if self.is_batch:
            row = column.row(align=True)

            row.prop(self, 'retrieve_up', toggle=True)
            row.prop(self, 'retrieve_unlinked', toggle=True)

    def invoke(self, context, event):
        active = context.active_object

        if 0 <= self.index < len(active.M4.group_pose_COL):
            pose = active.M4.group_pose_COL[self.index]

            self.is_batch = pose.batch
            return self.execute(context)
        return {'CANCELLED'}

    def execute(self, context):
        dg = context.evaluated_depsgraph_get()

        active = context.active_object
        poseCOL = active.M4.group_pose_COL

        pose = poseCOL[self.index]

        if pose.batch and pose.batchlinked:

            uuid = pose.uuid

            group_empties = get_group_hierarchy(active, up=self.retrieve_up)

            for empty in group_empties:

                for p in empty.M4.group_pose_COL:
                    if p.uuid == uuid and p.batch and (self.retrieve_unlinked or p.batchlinked):
                        retrieve_group_pose(empty, index=p.index)
                        break

        else:
            retrieve_group_pose(active, index=self.index)

        if active.M4.draw_active_group_pose:
            active.M4.group_pose_COL[active.M4.group_pose_IDX].forced_preview_update = True

        return {'FINISHED'}

class SortGroupPose(bpy.types.Operator):
    bl_idname = "m4n1.sort_group_pose"
    bl_label = "M4N1: Sort Group Pose"
    bl_options = {'REGISTER', 'UNDO'}

    direction: StringProperty()
    index: IntProperty()

    @classmethod
    def description(cls, context, properties):
        return _("Move Selected Group Pose {}").format(properties.direction.title())

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.type == 'EMPTY' and active.M4.is_group_empty and len(active.M4.group_pose_COL) > 1

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

    def execute(self, context):
        active = context.active_object
        poseCOL = active.M4.group_pose_COL

        if self.direction == 'UP' and self.index > 0:
            new_idx = self.index - 1

        elif self.direction == 'DOWN' and self.index < len(poseCOL) - 1:
            new_idx = self.index + 1

        else:
            return {'CANCELLED'}

        poseCOL.move(self.index, new_idx)

        active.M4.group_pose_IDX = new_idx

        prettify_group_pose_names(poseCOL)
        
        return {'FINISHED'}

class RemoveGroupPose(bpy.types.Operator):
    bl_idname = "m4n1.remove_group_pose"
    bl_label = "M4N1: Remove Group Pose"
    bl_description = "description"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def update_remove_poses(self, context):
        active = context.active_object
        poseCOL = active.M4.group_pose_COL

        if poseCOL and 0 <= self.index < len(poseCOL):
            pose = active.M4.group_pose_COL[self.index]
            uuid = pose.uuid

            get_remove_poses(self, active, uuid)

    is_batch = BoolProperty(name="Batch Retrieval", default=False)
    remove_batch: BoolProperty(name="Remove related Batch Poses", description="Remove all related Batch Poses in the Group Hierarchy", default=True, update=update_remove_poses)
    remove_up: BoolProperty(name="Remove Up", description="Remove Batch Poses further Up the Hierarchy too", default=False, update=update_remove_poses)
    remove_unlinked: BoolProperty(name="Remove Disconnected", description="Remove Batch Poses, that have been unlinked too", default=False, update=update_remove_poses)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.type == 'EMPTY' and active.M4.is_group_empty and active.M4.group_pose_COL

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        if self.is_batch:
            column.prop(self, 'remove_batch', toggle=True)

            row = column.row(align=True)
            row.enabled = self.remove_batch
            row.prop(self, 'remove_up', toggle=True)
            row.prop(self, 'remove_unlinked', toggle=True)

            column.separator()
            column.label(text="Batch Poses to be Removed:")

            for is_active_empty, objname, posename, linked in self.remove_poses:
                row = column.row(align=False)

                r = row.row()
                r.active = is_active_empty
                r.label(text='', icon='SPHERE' if is_active_empty else 'CUBE')

                s = row.split(factor=0.4)

                row = s.row(align=True)
                row.alignment = 'LEFT'

                prefix, basename, suffix = objname

                if prefix:
                    r = row.row(align=True)
                    r.alignment = 'LEFT'
                    r.active = False
                    r.label(text=prefix)

                row.label(text=basename)

                if suffix:
                    r = row.row(align=True)
                    r.alignment = 'LEFT'
                    r.active = False
                    r.label(text=suffix)

                s.label(text=posename, icon='LINKED' if linked else 'UNLINKED')

    def invoke(self, context, event):
        self.remove_batch = True

        active = context.active_object

        if 0 <= self.index < len(active.M4.group_pose_COL):
            pose = active.M4.group_pose_COL[self.index]

            self.is_batch = pose.batch

            if self.is_batch:

                uuid = pose.uuid

                get_remove_poses(self, active, uuid)

                return context.window_manager.invoke_props_dialog(self, width=300)
            return self.execute(context)

        return {'CANCELLED'}

    def execute(self, context):
        active = context.active_object
        poseCOL = active.M4.group_pose_COL

        if self.is_batch and self.remove_batch: 
            pose = poseCOL[self.index]

            for obj, idx in get_remove_poses(self, active, pose.uuid):
                obj.M4.group_pose_COL.remove(idx)

                if obj.M4.group_pose_COL:
                    if idx < obj.M4.group_pose_IDX or obj.M4.group_pose_IDX >= len(obj.M4.group_pose_COL):
                        obj.M4.group_pose_IDX -= 1
                else:
                    obj.M4.group_pose_IDX = -1

                prettify_group_pose_names(obj.M4.group_pose_COL)

        else:
            poseCOL.remove(self.index)

            if poseCOL:
                if self.index < active.M4.group_pose_IDX or active.M4.group_pose_IDX >= len(poseCOL):
                    active.M4.group_pose_IDX -= 1
            else:
                active.M4.group_pose_IDX = -1

            prettify_group_pose_names(poseCOL)

        process_group_poses(active)

        if active.M4.draw_active_group_pose or self.is_batch:
            force_ui_update(context, active=active)

        return {'FINISHED'}
