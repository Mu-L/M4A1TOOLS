import bpy
import re
from math import degrees
from mathutils import Vector, Quaternion, Matrix
from uuid import uuid4
from . object import parent, unparent
from . math import average_locations, get_loc_matrix, get_rot_matrix
from . mesh import get_coords
from . import registration as r
from bpy.app.translations import pgettext as _
def group(context, sel, location='AVERAGE', rotation='WORLD'):
    col = get_group_collection(context, sel)

    empty = bpy.data.objects.new(name=get_group_default_name(), object_data=None)
    empty.M4.is_group_empty = True
    empty.matrix_world = get_group_matrix(context, sel, location, rotation)
    col.objects.link(empty)

    context.view_layer.objects.active = empty
    empty.select_set(True)
    empty.show_in_front = True
    empty.empty_display_type = 'CUBE'

    empty.show_name = True
    empty.empty_display_size = r.get_prefs().group_size

    empty.M4.group_size = r.get_prefs().group_size

    for obj in sel:
        parent(obj, empty)
        obj.M4.is_group_object = True

    set_group_pose(empty, name=_('Inception'))

    return empty

def ungroup(empty):
    for obj in empty.children:
        unparent(obj)
        obj.M4.is_group_object = False

    bpy.data.objects.remove(empty, do_unlink=True)

def clean_up_groups(context):
    top_empties = []

    for obj in context.scene.objects:

        if obj.M4.is_group_empty:

            if r.get_prefs().group_remove_empty and not obj.children:
                print("INFO: Removing empty Group", obj.name)
                bpy.data.objects.remove(obj, do_unlink=True)
                continue

            if not obj.parent:
                top_empties.append(obj)

        elif obj.M4.is_group_object:
            if obj.parent:

                if not obj.parent.M4.is_group_empty:
                    obj.M4.is_group_object = False
                    print(f"INFO: {obj.name} is no longer a group object, because it's parent {obj.parent.name} is not a group empty")

            else:
                obj.M4.is_group_object = False
                print(f"INFO: {obj.name} is no longer a group object, because it doesn't have any parent")

        elif not obj.M4.is_group_object and obj.parent and obj.parent.M4.is_group_empty:
            obj.M4.is_group_object = True
            print(f"INFO: {obj.name} is now a group object, because it was manually parented to {obj.parent.name}")

    for empty in top_empties:
        propagate_pose_preview_alpha(empty)

    return top_empties

def get_group_polls(context):
    active_group = active if (active := context.active_object) and active.M4.is_group_empty and active.select_get() else None
    active_child = active if (active := context.active_object) and active.parent and active.M4.is_group_object and active.select_get() else None

    group_empties = bool([obj for obj in context.visible_objects if obj.M4.is_group_empty])
    groupable = bool([obj for obj in context.selected_objects if (obj.parent and obj.parent.M4.is_group_empty) or not obj.parent])
    ungroupable = bool([obj for obj in context.selected_objects if obj.M4.is_group_empty]) if group_empties else False

    addable = bool([obj for obj in context.selected_objects if obj != (active_group if active_group else active_child.parent) and obj not in (active_group.children if active_group else active_child.parent.children) and (not obj.parent or (obj.parent and obj.parent.M4.is_group_empty and not obj.parent.select_get()))]) if active_group or active_child else False

    removable = bool([obj for obj in context.selected_objects if obj.M4.is_group_object])
    selectable = bool([obj for obj in context.selected_objects if obj.M4.is_group_empty or obj.M4.is_group_object])
    duplicatable = bool([obj for obj in context.selected_objects if obj.M4.is_group_empty])
    groupifyable = bool([obj for obj in context.selected_objects if obj.type == 'EMPTY' and not obj.M4.is_group_empty and obj.children])

    batchposable = bool([obj for obj in active_group.children_recursive if obj.type == 'EMPTY' and obj.M4.is_group_empty]) if active_group else False

    return bool(active_group), bool(active_child), group_empties, groupable, ungroupable, addable, removable, selectable, duplicatable, groupifyable, batchposable

def get_group_collection(context, sel):
    collections = set(col for obj in sel for col in obj.users_collection)

    if len(collections) == 1:
        return collections.pop()

    else:
        return context.scene.collection

def get_group_matrix(context, objects, location_type='AVERAGE', rotation_type='WORLD'):

    if location_type == 'AVERAGE':
        location = average_locations([obj.matrix_world.to_translation() for obj in objects])

    elif location_type == 'ACTIVE':
        if context.active_object:
            location = context.active_object.matrix_world.to_translation()

        else:
            location = average_locations([obj.matrix_world.to_translation() for obj in objects])

    elif location_type == 'CURSOR':
        location = context.scene.cursor.location

    elif location_type == 'WORLD':
        location = Vector()

    if rotation_type == 'AVERAGE':
        rotation = Quaternion(average_locations([obj.matrix_world.to_quaternion().to_exponential_map() for obj in objects]))

    elif rotation_type == 'ACTIVE':
        if context.active_object:
            rotation = context.active_object.matrix_world.to_quaternion()

        else:
            rotation = Quaternion(average_locations([obj.matrix_world.to_quaternion().to_exponential_map() for obj in objects]))

    elif rotation_type == 'CURSOR':
        rotation = context.scene.cursor.matrix.to_quaternion()

    elif rotation_type == 'WORLD':
        rotation = Quaternion()

    return get_loc_matrix(location) @ get_rot_matrix(rotation)

def select_group_children(view_layer, empty, recursive=False):
    children = [c for c in empty.children if c.M4.is_group_object and c.name in view_layer.objects]

    if empty.hide_get():
        empty.hide_set(False)

        if empty.visible_get(view_layer=view_layer) and not empty.select_get(view_layer=view_layer):
            empty.select_set(True)

    for obj in children:
        if obj.visible_get(view_layer=view_layer) and not obj.select_get(view_layer=view_layer):
            obj.select_set(True)

        if obj.M4.is_group_empty and recursive:
            select_group_children(view_layer, obj, recursive=True)

def get_group_hierarchy(empty, up=False, layered=False):
    def get_group_child_empties_recursively(empty, empties, depth=0):
        child_empties = [e for e in empty.children if e.type == 'EMPTY' and e.M4.is_group_empty]

        if child_empties:
            depth += 1

            if depth + 1 > len(empties):
                empties.append([])

            for e in  child_empties:
                empties[depth].append(e)
                get_group_child_empties_recursively(e, empties, depth=depth)

    top_empty = empty

    if up:
        while top_empty.parent and top_empty.type == 'EMPTY' and top_empty.M4.is_group_empty:
            top_empty = top_empty.parent

    if layered:
        layered_empties = [top_empty]
        get_group_child_empties_recursively(top_empty, layered_empties, depth=0)

        return [layered_empties[0]] + [empty for layer in layered_empties[1:] for empty in layer]

    else:
        return [top_empty] + [obj for obj in top_empty.children_recursive if obj.type == 'EMPTY' and obj.M4.is_group_empty]

def get_child_depth(self, children, depth=0, init=False):
    if init or depth > self.depth:
        self.depth = depth

    for child in children:
        if child.children:
            get_child_depth(self, child.children, depth + 1, init=False)

    return self.depth

def fade_group_sizes(context, size=None, groups=[], init=False):
    if init:
        groups = [obj for obj in context.scene.objects if obj.M4.is_group_empty and not obj.parent]

    for group in groups:
        if size:
            factor = r.get_prefs().group_fade_factor

            group.empty_display_size = factor * size
            group.M4.group_size = group.empty_display_size

        sub_groups = [c for c in group.children if c.M4.is_group_empty]

        if sub_groups:
            fade_group_sizes(context, size=group.M4.group_size, groups=sub_groups, init=False)

def get_group_root_empty(empty):
    top_empty = empty

    while top_empty.parent and top_empty.type == 'EMPTY' and top_empty.M4.is_group_empty:
        top_empty = top_empty.parent

    return top_empty

def get_group_default_name():
    p = r.get_prefs()

    if r.get_prefs().group_auto_name:
        name = f"{p.group_prefix}{p.group_basename + '_001'}{p.group_suffix}"

        c = 0
        while name in bpy.data.objects:
            c += 1
            name = f"{p.group_prefix}{p.group_basename + '_' + str(c).zfill(3)}{p.group_suffix}"

        return name

    else:
        name = f"{p.group_basename}_001"

        c = 0
        while name in bpy.data.objects:
            c += 1
            name = f"{p.group_basename + '_' + str(c).zfill(3)}"

        return name

def update_group_name(group):
    p = r.get_prefs()
    prefix = p.group_prefix
    suffix = p.group_suffix

    name = group.name
    newname = name

    if not name.startswith(prefix):
        newname = prefix + newname

    if not name.endswith(suffix):
        newname = newname + suffix

    if name == newname:
        return

    c = 0
    while newname in bpy.data.objects:
        c += 1
        newname = f"{p.group_prefix}{name + '_' + str(c).zfill(3)}{p.group_suffix}"

    group.name = newname
   
def get_group_base_name(name, debug=False):
    p = r.get_prefs()

    if r.get_prefs().group_auto_name:
        basename = name

        if name.startswith(p.group_prefix):
            prefix = p.group_prefix
            basename = basename[len(prefix):]

        else:
            prefix = None

        if name.endswith(p.group_suffix):
            suffix = p.group_suffix
            basename = basename[:-len(suffix)]
        else:
            suffix = None

        if debug:
            print()
            print("name:", name)
            print("prefix:", prefix)
            print("basename:", basename)
            print("suffix:", suffix)

        return prefix, basename, suffix
    else:
        return None, name, None

def set_group_pose(empty, name='', uuid='', batch=False, debug=False) -> str:

    idx = len(empty.M4.group_pose_COL)

    if not name:
        name = f"Pose.{str(idx).zfill(3)}"

    if debug:
        print(f"Setting new pose {name} at index {idx}")

    pose = empty.M4.group_pose_COL.add()
    pose.index = idx

    pose.avoid_update = True
    pose.name = name

    pose.mx = empty.matrix_local
    pose.batch = batch

    if uuid:
        pose.uuid = uuid

    else:
        uuid = set_pose_uuid(pose)

    empty.M4.group_pose_IDX = pose.index

    set_pose_axis_and_angle(empty, pose)
    
    return uuid

def set_pose_axis_and_angle(empty, pose, inceptions=[]):
    if not inceptions:
        inceptions = [p for p in empty.M4.group_pose_COL if p.uuid == '00000000-0000-0000-0000-000000000000' and p != pose]

    if inceptions:
        inception_rotation = inceptions[0].mx.to_quaternion()
        rotation = pose.mx.to_quaternion()

        delta_rot = inception_rotation.rotation_difference(rotation)

        axis_vector = delta_rot.axis
        axis = 'X' if abs(round(axis_vector.x)) == 1 else 'Y' if abs(round(axis_vector.y)) == 1  else 'Z' if abs(round(axis_vector.z)) == 1 else None

        angle = degrees(delta_rot.angle)

        if axis:
            factor = -1 if getattr(axis_vector, axis.lower()) < 0 else 1

            pose.axis = axis
            pose.angle = factor * angle

def set_pose_uuid(pose):
    if pose.name == 'Inception':
        uuid = '00000000-0000-0000-0000-000000000000'

    elif pose.name == 'LegacyPose':
        uuid = '11111111-1111-1111-1111-111111111111'

    else:
        uuid = str(uuid4())

    pose.uuid = uuid

    return uuid

def retrieve_group_pose(empty, index=None, debug=False):

    idx = index if index is not None else empty.M4.group_pose_IDX

    if debug:
        print(f"Recalling {'active ' if index == empty.M4.group_pose_IDX else''}pose with index {idx}")

    if 0 <= idx < len(empty.M4.group_pose_COL):
        pose = empty.M4.group_pose_COL[idx]

        loc, _, sca = empty.matrix_local.decompose()
        rot = pose.mx.to_quaternion()
        empty.matrix_local = Matrix.LocRotScale(loc, rot, sca)

def get_remove_poses(self, active, uuid):
    remove_poses = []
    remove_indices = []

    if self.remove_batch:
        empties = get_group_hierarchy(active, up=self.remove_up)

    else:
        empties = [active]

    for obj in empties:
        for idx, pose in enumerate(obj.M4.group_pose_COL):
            if pose.uuid == uuid and pose.batch and (self.remove_unlinked or pose.batchlinked):
                remove_poses.append((obj == active, get_group_base_name(obj.name), pose.name, pose.batchlinked))

                remove_indices.append((obj, idx))
                break

    if not remove_poses:
        for idx, pose in enumerate(active.M4.group_pose_COL):
            if pose.uuid == uuid:
                remove_poses.append((True, get_group_base_name(active.name), pose.name, pose.batchlinked))

                remove_indices.append((active, idx))
                break
    
    bpy.types.M4A1_OT_remove_group_pose.remove_poses = remove_poses

    return remove_indices

def prettify_group_pose_names(poseCOL):
    nameRegex = re.compile(r"Pose\.[\d]{3}")

    for idx, pose in enumerate(poseCOL):
        pose.index = idx

        mo = nameRegex.match(pose.name)

        if not (pose.name.strip() and not mo):
            pose.avoid_update = True
            pose.name = f"Pose.{str(idx).zfill(3)}"

def get_batch_pose_name(objects, basename='BatchPose'):
    pose_names = set()

    for obj in objects:
        for pose in obj.M4.group_pose_COL:
            pose_names.add(pose.name)

    name = basename

    c = 0

    while name in pose_names:
        c += 1
        name = f"{basename}.{str(c).zfill(3)}"

    return name

def process_group_poses(empty, debug=False):

    if debug:
        print()
        print("processing group poses for empty:", empty.name)

    group_empties = get_group_hierarchy(empty, up=True)

    group_poses = {}

    if debug:
        print(" empties (initial):")

    for e in group_empties:
        if debug:
            print(" ", e.name)
            print("   poses:")

        for pose in e.M4.group_pose_COL:
            if debug:
                print("   ", pose.name)

            if pose.name == 'Inception' and pose.uuid != '00000000-0000-0000-0000-000000000000':
                if debug:
                    print("     setting Inception uuid!")

                pose.uuid = '00000000-0000-0000-0000-000000000000'
            
            elif pose.name == 'LegacyPose' and pose.uuid != '11111111-1111-1111-1111-111111111111':
                if debug:
                    print("     setting LegacyPose uuid!")

                pose.uuid = '11111111-1111-1111-1111-111111111111'

            if pose.uuid in group_poses:
                group_poses[pose.uuid].append(pose)

            else:
                group_poses[pose.uuid] = [pose]

    ex_inception_uuid = None
    ex_legacy_uuid = None

    if debug:
        print("\n uuids:")

    for uuid, poses in group_poses.items():
        if debug:
            print(" ", uuid)
            print("   poses:")

        for pose in poses:
            if debug:
                print("   ", pose.name, "on", pose.id_data.name)

            if len(poses) > 1 and not pose.batch:
                if debug:
                    print("     enabling batch")

                pose.batch = True

            elif len(poses) == 1 and pose.batch:
                if debug:
                    print("     disabling batch")

                pose.batch = False

                if pose.name.startswith('BatchPose'):
                    if debug:
                        print("     removing BatchPose name too")

                    pose.avoid_update = True
                    pose.name = f"Pose.{str(pose.index).zfill(3)}"

            if uuid == '00000000-0000-0000-0000-000000000000' and pose.name != 'Inception':
                if not ex_inception_uuid:
                    ex_inception_uuid = str(uuid4())

                if debug:
                    print("     turning ex-inception pose into regular pose with new uuid:", ex_inception_uuid)

                pose.uuid = ex_inception_uuid

            if uuid == '11111111-1111-1111-1111-111111111111' and pose.name != 'LegacyPose': 
                if not ex_legacy_uuid:
                    ex_legacy_uuid = str(uuid4())

                if debug:
                    print("     turning ex-legacy pose into regular pose with new uuid:", ex_legacy_uuid)

                pose.uuid = ex_legacy_uuid

    if debug:
        print("\n empties (final):")

    for e in group_empties:
        inceptions = [p for p in e.M4.group_pose_COL if p.uuid == '00000000-0000-0000-0000-000000000000']

        if debug:
            print(" ", e.name)
            print("   has inception:", bool(inceptions))

        if inceptions:

            for p in e.M4.group_pose_COL:
                if p not in inceptions and not p.axis:
                    if debug:
                        print("     calculating new axis/angle for pose", p.name)

                    set_pose_axis_and_angle(e, p, inceptions=inceptions)

        else:
            for p in e.M4.group_pose_COL:
                if p.axis:
                    if debug:
                        print("     clearing axis/angle for pose", p.name)

                    p.axis = ''

def propagate_pose_preview_alpha(empty, up=False):
    group_empties = get_group_hierarchy(empty, up=up)

    for e in group_empties:
        if e != empty:
            if e.M4.group_pose_alpha != empty.M4.group_pose_alpha:
                e.M4.avoid_update = True
                e.M4.group_pose_alpha = empty.M4.group_pose_alpha

def get_pose_batches(context, empty, pose, batches, children=None, dg=None, preview_batch_poses=False):
    if dg is None:
        dg = context.evaluated_depsgraph_get()

    if children is None:
        children = [obj for obj in empty.children_recursive if obj.name in context.view_layer.objects and obj.visible_get()]

    is_batch_pose = pose.batch and pose.batchlinked

    for obj in children:

        locals = [obj.matrix_local]

        ob = obj

        while ob.parent != empty:
            ob = ob.parent

            appended_batch_pose_mx_already = False

            if preview_batch_poses and is_batch_pose and ob.type == 'EMPTY' and ob.M4.is_group_empty:

                for p in ob.M4.group_pose_COL:

                    if p.batch and p.uuid == pose.uuid:

                        if p.batchlinked:

                            loc, _, sca = ob.matrix_local.decompose()
                            locals.append(Matrix.LocRotScale(loc, p.mx.to_quaternion(), sca))

                            appended_batch_pose_mx_already = True

                        break

            if not appended_batch_pose_mx_already:
                locals.append(ob.matrix_local)

        cumulative_local_mx = Matrix()

        for local in reversed(locals):
            cumulative_local_mx @= local

        loc, _, sca = empty.matrix_local.decompose()

        empty_local_posed_mx = Matrix.LocRotScale(loc, pose.mx.to_quaternion(), sca)
        
        mx = empty.parent.matrix_world @ empty_local_posed_mx @ cumulative_local_mx if empty.parent else empty_local_posed_mx @ cumulative_local_mx

        if obj.type in ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT']:

            obj = dg.objects.get(obj.name)
            mesh_eval = obj.to_mesh()

            batches.append(get_coords(mesh_eval, mx=mx, indices=True))

            del obj
            del mesh_eval

        elif obj.type == 'EMPTY':
            length = obj.M4.group_size if obj.M4.is_group_empty else obj.empty_display_size
            batches.append((mx, length))
