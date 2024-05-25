import bpy
from bpy.props import StringProperty

class CallM4A1toolsPie(bpy.types.Operator):
    bl_idname = "m4a1.call_m4a1tools_pie"
    bl_label = "M4A1: Call M4A1tools Pie"
    bl_options = {'REGISTER', 'UNDO'}

    idname: StringProperty()

    def invoke(self, context, event):
        view = context.space_data

        if view.type == 'VIEW_3D':
            scene = context.scene
            m3 = scene.M4

            if self.idname == 'shading_pie':
                engine = scene.render.engine
                device = scene.cycles.device
                shading = view.shading
                active = context.active_object

                if engine != m3.render_engine and engine in ['BLENDER_EEVEE', 'CYCLES']:
                    m3.avoid_update = True
                    m3.render_engine = engine

                if engine == 'CYCLES' and device != m3.cycles_device:
                    m3.avoid_update = True
                    m3.cycles_device = device

                if shading.light != m3.shading_light:
                    m3.avoid_update = True
                    m3.shading_light = shading.light

                    m3.avoid_update = True
                    m3.use_flat_shadows = shading.show_shadows

                if bpy.app.version >= (3, 5, 0) and shading.type in ['MATERIAL', 'RENDERED']:
                    m3.avoid_update = True
                    m3.use_compositor = shading.use_compositor

                if active and not active.display_type:
                    active.display_type = 'WIRE' if active.hide_render or not active.visible_camera else 'TEXTURED'

                bpy.ops.wm.call_menu_pie(name='M4A1_MT_%s' % (self.idname))

            elif self.idname == 'tools_pie':
                if context.mode in ['OBJECT', 'EDIT_MESH']:
                    bpy.ops.wm.call_menu_pie(name='M4A1_MT_%s' % (self.idname))

                else:
                    return {'PASS_THROUGH'}

        return {'FINISHED'}
