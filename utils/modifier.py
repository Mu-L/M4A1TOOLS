import bpy
from math import radians
import os
from . registration import get_prefs
from . append import append_nodetree
from .. items import mirror_props
from . nodes import get_nodegroup_input_identifier
from bpy.app.translations import pgettext as _
def add_triangulate(obj):
    mod = obj.modifiers.new(name="Triangulate", type="TRIANGULATE")
    mod.keep_custom_normals = True
    mod.quad_method = 'FIXED'
    mod.show_expanded = True
    return mod

def add_shrinkwrap(obj, target):
    mod = obj.modifiers.new(name="Shrinkwrap", type="SHRINKWRAP")

    mod.target = target
    mod.show_on_cage = True
    mod.show_expanded = False
    return mod

def add_surface_slide(obj, target):
    mod = add_shrinkwrap(obj, target)
    mod.name = _('Surface Slide')
    return mod

def add_mods_from_dict(obj, modsdict):
    for name, props in modsdict.items():
        mod = obj.modifiers.new(name=name, type=props['type'])

        for pname, pvalue in props.items():
            if pname != 'type':
                setattr(mod, pname, pvalue)

def add_bevel(obj, method='WEIGHT'):
    mod = obj.modifiers.new(name='Bevel', type='BEVEL')
    mod.limit_method = method

    mod.show_expanded = False
    return mod

def add_boolean(obj, operator, method='DIFFERENCE', solver='FAST'):
    boolean = obj.modifiers.new(name=method.title(), type="BOOLEAN")

    boolean.object = operator
    boolean.operation = 'DIFFERENCE' if method == 'SPLIT' else method
    boolean.show_in_editmode = True

    if method == 'SPLIT':
        boolean.show_viewport = False

    boolean.solver = solver

    return boolean

def add_auto_smooth(obj, angle=20):
    smooth_by_angles = [tree for tree in bpy.data.node_groups if tree.name.startswith('Smooth by Angle')]

    if smooth_by_angles:
        ng = smooth_by_angles[0]

    else:
        path = os.path.join(bpy.utils.system_resource('DATAFILES'), 'assets', 'geometry_nodes', 'smooth_by_angle.blend')
        ng = append_nodetree(path, 'Smooth by Angle')

        if not ng:
            print("WARNING: Could not import Smooth by Angle node group from ESSENTIALS! This should never happen")
            return

    mod = obj.modifiers.new(name="Auto Smooth", type="NODES")
    mod.node_group = ng
    mod.show_expanded = get_prefs().auto_smooth_show_expanded

    set_mod_input(mod, 'Angle', radians(angle))

    mod.id_data.update_tag()
    return mod

def get_auto_smooth(obj):
    if (mod := obj.modifiers.get('Auto Smooth', None)) and mod.type == 'NODES':
        return mod

    elif (mod := obj.modifiers.get('Smooth by Angle', None)) and mod.type == 'NODES':
        return mod
    
    else:
        mods = [mod for mod in obj.modifiers if mod.type == 'NODES' and (ng := mod.node_group) and ng.name.startswith('Smooth by Angle')]

        if mods:
            return mods[0]

def get_surface_slide(obj):
    mods = [mod for mod in obj.modifiers if mod.type == 'SHRINKWRAP' and 'SurfaceSlide' in mod.name]

    if mods:
        return mods[0]

def remove_mod(mod):
    obj = mod.id_data

    if isinstance(mod, bpy.types.Modifier):
        obj.modifiers.remove(mod)

    elif isinstance(mod, bpy.types.GpencilModifier):
        obj.grease_pencil_modifiers.remove(mod)

    else:
        print(f"WARNING: Could not remove modiifer {mod.name} of type {mod.type}")

def remove_triangulate(obj):
    lastmod = obj.modifiers[-1] if obj.modifiers else None

    if lastmod and lastmod.type == 'TRIANGULATE':
        obj.modifiers.remove(lastmod)
        return True

def get_mod_as_dict(mod, skip_show_expanded=False):
    d = {}

    if mod.type == 'MIRROR':
        for prop in mirror_props:
            if skip_show_expanded and prop == 'show_expanded':
                continue

            if prop in ['use_axis', 'use_bisect_axis', 'use_bisect_flip_axis']:
                d[prop] = tuple(getattr(mod, prop))
            else:
                d[prop] = getattr(mod, prop)

    return d

def get_mods_as_dict(obj, types=[], skip_show_expanded=False):
    mods = []

    for mod in obj.modifiers:
        if types:
            if mod.type in types:
                mods.append(mod)

        else:
            mods.append(mod)

    modsdict = {}

    for mod in mods:
        modsdict[mod.name] = get_mod_as_dict(mod, skip_show_expanded=skip_show_expanded)

    return modsdict

def apply_mod(modname):
    bpy.ops.object.modifier_apply(modifier=modname)

def get_mod_obj(mod):
    if mod.type in ['BOOLEAN', 'HOOK', 'LATTICE', 'DATA_TRANSFER', 'GP_MIRROR']:
        return mod.object
    elif mod.type == 'MIRROR':
        return mod.mirror_object
    elif mod.type == 'ARRAY':
        return mod.offset_object

def move_mod(mod, index=0):
    obj = mod.id_data
    current_index = list(obj.modifiers).index(mod)

    if current_index != index:
        obj.modifiers.move(current_index, index)

def sort_mod(mod):
    def is_mirror(mod):
        return mod.type == 'MIRROR'

    def is_array(mod):
        return mod.type == 'ARRAY'

    def is_auto_smooth(mod):
        return mod.type == 'NODES' and mod.node_group and 'Smooth by Angle' in mod.node_group.name

    def should_preceed(mod, prev_mod):
        if is_auto_smooth(mod):
            return any([is_mirror(prev_mod), is_array(prev_mod)])

    if is_auto_smooth(mod):
        obj = mod.id_data
        mods = list(obj.modifiers)

        if len(mods) > 1:

            move_mod(mod, len(mods) - 1)

            index = len(mods) - 1

            while index:
                index -= 1
                prev_mod = obj.modifiers[index]

                if should_preceed(mod, prev_mod):

                    if index == 0:
                        move_mod(mod, index)
                    continue

                else:
                    move_mod(mod, index + 1)
                    break
def get_mod_input(mod, name):
    if ng := mod.node_group:
        identifier, socket_type = get_nodegroup_input_identifier(ng, name)

        if identifier:
            return mod[identifier]

def set_mod_input(mod, name, value):
    if ng := mod.node_group:
        identifier, socket_type = get_nodegroup_input_identifier(ng, name)

        mod[identifier] = value
