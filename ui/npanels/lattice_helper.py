import bpy
from ...operators.lattice_helper import Lattice_Operator, Apply_Lattice_Operator  # ,Remove_Lattice_Operator


class LATTICE_H_MT_Menus(bpy.types.Menu):
    bl_label = "Lattice Helper"
    bl_idname = "M4A1_PT_MT_latticehelper"

    def draw(self, context):
        layout = self.layout
        layout.operator(Lattice_Operator.bl_idname)
        layout.operator(Apply_Lattice_Operator.bl_idname, text='Apply lattice').mode = 'apply_lattice'
        layout.operator(Apply_Lattice_Operator.bl_idname, text='Delete lattice').mode = 'del_lattice'


def menu_func(self, context):
    support_type = ['LATTICE', "MESH", "CURVE", "FONT", "SURFACE", "HAIR", "GPENCIL"]


    selected_objects = [obj for obj in context.selected_objects if obj.type in support_type] \
        if context.mode == 'OBJECT' else \
        [obj for obj in context.selected_objects if obj.type == 'MESH' and context.mode == 'EDIT_MESH']
    # get所有可用物体列表,如果在网格编辑模式则只获取网格的

    modifiers_type = {modifiers.type for obj in selected_objects for modifiers in
                      (obj.modifiers if obj.type != 'GPENCIL' else obj.grease_pencil_modifiers)}


    if ('GP_LATTICE' in modifiers_type or 'LATTICE' in modifiers_type or 'LATTICE' in {obj.type for obj in
                                                                                       selected_objects}) and context.mode == 'OBJECT':
        self.layout.column().menu("LATTICE_H_MT_Menus", icon='MOD_LATTICE', )  # text="")
    else:
        self.layout.column().operator(Lattice_Operator.bl_idname)

    self.layout.separator()
LH_REG_TAG=False

def menu_register():
    global LH_REG_TAG
    if not LH_REG_TAG:
        bpy.types.VIEW3D_MT_object_context_menu.prepend(menu_func)
        bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(menu_func)
        LH_REG_TAG=True


def menu_unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)
    global LH_REG_TAG
    LH_REG_TAG=False