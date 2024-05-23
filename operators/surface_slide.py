import bpy
from bpy.ops import ed
from uuid import uuid4
from .. utils.modifier import add_shrinkwrap, add_surface_slide, get_surface_slide, move_mod
from .. utils.object import parent

class SurfaceSlide(bpy.types.Operator):
    bl_idname = "m4n1.surface_slide"
    bl_label = "M4N1: Surface Slide"
    bl_description = "Start Surface Sliding: modifify the topology while keeping the inital form intact"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH':
            return not get_surface_slide(context.active_object)

    def execute(self, context):
        active = context.active_object
        active.update_from_editmode()

        active_mesh = active.data

        instances = [obj for obj in bpy.data.objects if obj != active and obj.data == active.data]

        if instances:
            print(f"INFO: Object '{active.name}' has {len(instances)} instances: {','.join(obj.name for obj in instances)}, creating temporary unique mesh data")

            bpy.ops.object.mode_set(mode='OBJECT')

            instance_mesh = active_mesh.copy()
            instance_mesh.name = f"{active.name}_INSTANCE"
            active.data = instance_mesh

            bpy.ops.object.mode_set(mode='EDIT')

            hash = str(uuid4())

            active.M4.dup_hash = hash
            
            for obj in instances:
                obj.M4.dup_hash = hash

        target = bpy.data.objects.new(name=f"{active.name}_SURFACE", object_data=active_mesh.copy())
        target.data.name = f"{active_mesh.name}_SURFACE"
        target.use_fake_user = True
        target.matrix_world = active.matrix_world

        mod = add_surface_slide(active, target)
        mod.name = 'SurfaceSlide'

        if len(active.modifiers) > 1:
            move_mod(mod, 0)

        parent(target, active)

        return {'FINISHED'}

class FinishSurfaceSlide(bpy.types.Operator):
    bl_idname = "m4n1.finish_surface_slide"
    bl_label = "M4N1: Finish Surface Slide"
    bl_description = "Stop Surface Sliding"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active = context.active_object if context.active_object else None
        if active:
            return [mod for mod in context.active_object.modifiers if mod.type == 'SHRINKWRAP' and 'SurfaceSlide' in mod.name]

    def execute(self, context):
        active = context.active_object
        active_mesh = active.data

        surfaceslide = get_surface_slide(active)
        surface = surfaceslide.target

        editmode = context.mode == 'EDIT_MESH'

        if editmode:
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.modifier_apply(modifier=surfaceslide.name)

        if editmode:
            bpy.ops.object.mode_set(mode='EDIT')

        if surface:
            bpy.data.meshes.remove(surface.data, do_unlink=True)

        if hash := active.M4.dup_hash:
            instances = [obj for obj in bpy.data.objects if obj != active and obj.M4.dup_hash == hash]

            dup_mesh = None

            for obj in instances:
                if dup_mesh is None:
                    dup_mesh = obj.data

                obj.data = active_mesh
                obj.M4.dup_hash = ''

            active.M4.dup_hash = ''
            active_mesh.name = active_mesh.name.replace('_INSTANCE', '')

            if not dup_mesh.users:
                bpy.data.meshes.remove(dup_mesh, do_unlink=True)

        return {'FINISHED'}
