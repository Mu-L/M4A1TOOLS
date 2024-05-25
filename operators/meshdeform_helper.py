# import shutil
# from typing import List
# import bpy
# import random
# import numpy as np
# from array import array as Array
# from time import time
# # try:
# #     from pyconvex.convex import ConvexHull
# # except:
# #     from .convex import ConvexHull
#
# #ConvexHull
# from ctypes import RTLD_GLOBAL, POINTER, CDLL, c_int64, c_longlong, c_uint64, cdll, cast, c_void_p, c_int, c_float
# from array import array as Array
# import os
# import sys
# import ctypes
# import platform
# import pathlib
# OS = platform.system()
#
# if OS == "Windows":
#     dll_close = ctypes.windll.kernel32.FreeLibrary
# elif OS == "Darwin":
#     try:
#         try:
#             stdlib = ctypes.CDLL("libc.dylib")
#         except OSError:
#             stdlib = ctypes.CDLL("libSystem")
#     except OSError:
#         stdlib = ctypes.CDLL("/usr/lib/system/libsystem_c.dylib")
#     dll_close = stdlib.dlclose
# elif OS == "Linux":
#     try:
#         stdlib = ctypes.CDLL("")
#     except OSError:
#         stdlib = ctypes.CDLL("libc.so")
#     dll_close = stdlib.dlclose
# elif sys.platform == "msys":
#     stdlib = ctypes.CDLL("msys-2.0.dll")
#     dll_close = stdlib.dlclose
# elif sys.platform == "cygwin":
#     stdlib = ctypes.CDLL("cygwin1.dll")
#     dll_close = stdlib.dlclose
# elif OS == "FreeBSD":
#     stdlib = ctypes.CDLL("libc.so.7")
#     dll_close = stdlib.close
# else:
#     raise NotImplementedError("Unknown platform.")
#
# dll_close.argtypes = [ctypes.c_void_p]
#
# dll = []
#
# cur_path=pathlib.Path(__file__)
# # print('dangqian',cur_path)
# def copy_create_folder(source_file,folder_name):
#     # 使用 pathlib 的 Path 对象来处理路径，source_file 应是一个 Path 对象
#     # 创建目标 DLL 文件夹的完整路径
#     dll_path = source_file.parent.parent.joinpath('dll')
#     # 使用 rglob 方法递归获取 dll 目录下的所有文件的路径列表
#     files_list = list(dll_path.rglob('*'))  # '*' 匹配所有文件和子目录
#
#     # 获取源文件的上级目录
#     grandparent_directory = source_file.parent.parent.parent
#     # 在上级目录下创建新的文件夹路径
#     new_folder_path = grandparent_directory / folder_name
#
#     # 检查新建文件夹路径是否存在
#     if not new_folder_path.exists():
#         # 如果不存在，则创建该文件夹
#         new_folder_path.mkdir()
#
#     # 尝试复制文件
#     try:
#         # 遍历所有文件路径
#         for file_path in files_list:
#             # 确保当前路径是文件而非目录
#             if file_path.is_file():
#                 # 计算目标文件的完整路径
#                 destination = new_folder_path / file_path.name
#                 # 使用 shutil 的 copy 函数将文件复制到目标路径
#                 shutil.copy(file_path, destination)
#
#     except Exception as e:
#         # 如果复制过程中出现任何异常，打印错误信息
#         print(f"错误: {e}")
# copy_create_folder(cur_path,"M4ToolsDll")
# def is_support():
#     return sys.platform == "win32"
#
#
# if is_support():
#     # old_path = os.getcwd()
#     # os.chdir(os.path.dirname(__file__))
#     if sys.platform == "darwin":
#         CGAL = cdll.LoadLibrary("convex.dylib")
#     elif sys.platform == "win32":
#         from ctypes import WinDLL
#         # dll_path = os.path.join(os.path.dirname(os.getcwd()), "dll", "convex.dll")
#         dll_path = str(pathlib.Path(__file__).parent.parent.parent / "M4ToolsDll" / "convex.dll")
#         if sys.version_info >= (3, 9, 0):
#             os.add_dll_directory(os.getcwd())
#             try:
#                 CGAL = WinDLL(dll_path, winmode=RTLD_GLOBAL)
#             except BaseException:
#                 CGAL = CDLL(dll_path, winmode=RTLD_GLOBAL)
#         else:
#             CGAL = cdll.LoadLibrary(dll_path)
#
#     class Verts(ctypes.Structure):
#         _fields_ = [("num", ctypes.c_int),
#                     ("data", POINTER(c_float))]
#
#     class Edges(ctypes.Structure):
#         _fields_ = [("num", ctypes.c_int),
#                     ("data", POINTER(c_int))]
#
#     class Faces(ctypes.Structure):
#         _fields_ = [("num", ctypes.c_int),
#                     ("data", POINTER(c_int)),
#                     ("n", POINTER(c_int))]
#     CGAL.convexhull_fromme.argtypes = [c_void_p, c_int, c_int]
#     CGAL.convexhull_fromary.argtypes = [c_void_p, c_int]
#     CGAL.getvert.restype = c_void_p
#     CGAL.getedge.restype = c_void_p
#     CGAL.getface.restype = c_void_p
#     CGAL.destroy.argtypes = None
#     CGAL.init()
#     CGAL.destroy()
#
#     class ConvexHull:
#         def __init__(self):
#
#             CGAL.init()
#
#             self._verts = Verts.from_address(CGAL.getvert())
#             self._edges = Edges.from_address(CGAL.getedge())
#             self._faces = Faces.from_address(CGAL.getface())
#
#         def convexhull_fromme(self, me, version=300):
#             CGAL.destroy()
#             CGAL.convexhull_fromme(c_void_p(me.as_pointer()), me.vertices.__len__(), version)
#             return self.get()
#
#         def convexhull_fromary(self, ary: Array):
#             CGAL.destroy()
#             CGAL.convexhull_fromary(c_void_p(ary.buffer_info()[0]), int(len(ary) / 3))
#             return self.get()
#
#         def get(self):
#             verts, verts_num = cast(self._verts.data, POINTER(ctypes.c_float * (self._verts.num * 3))).contents, self._verts.num
#             edges, edges_num = cast(self._edges.data, POINTER(ctypes.c_int * (self._edges.num * 2))).contents, self._edges.num
#             faces_n = cast(self._faces.n, POINTER(ctypes.c_int * self._faces.num)).contents
#             faces, faces_num = cast(self._faces.data, POINTER(ctypes.c_int * (sum(faces_n)))).contents, self._faces.num
#
#             return verts_num, verts, edges_num, edges, faces_num, faces, faces_n
#
#         def __del__(self):
#             CGAL.destroy()
#             # return
#     dll.append(CGAL)
#
#
# def convex_unreg():
#     if not is_support():
#         return
#
#     if sys.platform == "win32":
#         for d in dll:
#             dll_close(d._handle)
#
#
# def timeit(func):
#     def wrap(*args, **kwargs):
#         tstart = time()
#         res = func(*args, **kwargs)
#         print(f"Function {func.__name__} run time: {time()-tstart:.4f}s")
#         return res
#     return wrap
#
#
#
#
# class Convex_Meshdeform(bpy.types.Operator):
#     bl_idname = "m4a1.convex_meshdeform"
#     bl_label = "Grid overlay"
#     bl_description = "Automatically add grid overlay to selected objects"
#     bl_options = {"REGISTER", "UNDO"}
#
#     # 凸包生成
#     @timeit
#     def create_convex(self, objects: List[bpy.types.Object]):
#         CH = ConvexHull()
#         temp_mesh = bpy.data.meshes.new(name="%f" % random.random())
#         vertices_buffer = Array('f')
#         name = "MD_Group"
#         version = 300
#         if (2, 9, 0) <= bpy.app.version < (3, 0, 0):
#             version = 293
#         elif (3, 1, 0) <= bpy.app.version < (3, 2, 0):
#             version = 310
#         elif (3, 2, 0) <= bpy.app.version < (3, 3, 0):
#             version = 320
#         elif bpy.app.version >= (3, 3, 0):
#             version = 320
#         if bpy.app.version >= (3, 4, 0):
#             self.report({"ERROR"}, "Not supported in Blender 3.4 and above")
#             return
#         for o in objects:
#             if o.type == "MESH":
#                 ch = CH.convexhull_fromme(o.data, version)
#                 verts = ch[:2]
#                 npary = np.frombuffer(verts[1], dtype=np.float32, count=verts[0] * 3)
#                 npm = np.array(o.matrix_world.to_3x3())
#                 tpary = npary.reshape(-1, 3)
#                 npary[:] = (npm.dot(tpary.T).T + o.matrix_world.translation).flatten()
#                 vertices_buffer.extend(npary)
#                 name += "_" + o.name[0]
#         temp_mesh.name = name
#         ch = CH.convexhull_fromary(vertices_buffer)
#         # 设置顶点
#         verts = ch[:2]
#         temp_mesh.vertices.add(verts[0])
#         temp_mesh.vertices.foreach_set("co", verts[1])
#         # 有face的情况下 不需要 edge 信息
#         # edges = ch[2:4]
#         # temp_mesh.edges.add(edges[0])
#         # temp_mesh.edges.foreach_set("vertices", edges[1])
#
#         # 设置 面信息
#         faces = ch[4:]
#         temp_mesh.loops.add(sum(faces[2]))
#         temp_mesh.loops.foreach_set("vertex_index", faces[1])
#         temp_mesh.polygons.add(faces[0])
#         temp_mesh.polygons.foreach_set("loop_total", faces[2])
#         # 计算 loop_start
#         start = 0
#         loop_start = []
#         for n in faces[2]:
#             loop_start.append(start)
#             start += n
#         temp_mesh.polygons.foreach_set("loop_start", loop_start)
#         # 网格有效化
#         temp_mesh.validate()
#         temp_obj = bpy.data.objects.new(name=temp_mesh.name, object_data=temp_mesh)
#         bpy.context.collection.objects.link(temp_obj)
#         bpy.ops.object.select_all(action="DESELECT")
#         bpy.context.view_layer.objects.active = temp_obj
#         temp_obj.select_set(True)
#         temp_mesh.update()
#         return temp_obj
#
#     def parent_set(self, child: bpy.types.Object, parent: bpy.types.Object, reverse=False):
#         bpy.context.view_layer.update()
#         if reverse:
#             parent.parent = child
#             parent.matrix_parent_inverse = child.matrix_world.inverted()
#         else:
#             child.parent = parent
#             child.matrix_parent_inverse = parent.matrix_world.inverted()
#
#     # 计算物体原点
#     @timeit
#     def origin_set(self, object: bpy.types.Object):
#         vertices_buffer = np.zeros(object.data.vertices.__len__() * 3)
#         object.data.vertices.foreach_get("co", vertices_buffer)
#         vertices_buffer = vertices_buffer.reshape(-1, 3)
#         location = vertices_buffer.mean(axis=0)
#         vertices_buffer -= location
#         object.data.vertices.foreach_set("co", vertices_buffer.ravel())
#         object.location = location
#
#     def execute(self, context):
#         # 1 凸壳生成器（支持多物体和单物体）
#         #   - 目前手工思路 复制物体 生成凸壳 网格重构（保持体积）
#         #   - 网格重构参数= 凸壳缩放 + 网格重构
#         selected_objects = bpy.context.selected_objects[:]
#         ch = self.create_convex(selected_objects)
#         if not ch:
#             return {"FINISHED"}
#         self.origin_set(ch)
#         ch.scale *= 1.06
#         ch.display_type = "WIRE"
#         ch.hide_render = True
#
#         for o in selected_objects:
#             if o.type == 'MESH':
#                 self.parent_set(o, ch)
#         return {"FINISHED"}
#
#
# class Bind_Meshdeform(bpy.types.Operator):
#     bl_idname = "m4a1.bind_meshdeform"
#     bl_label = "Grid binding"
#     bl_description = "Add grid modifier to a subset of this grid"
#     bl_options = {"REGISTER", "UNDO"}
#
#     def execute(self, context):
#         # 2 绑定器（支持多物体和单物体）
#         #   - 能多个物体绑定
#         #   - 绑定凸壳为父级
#         ch = bpy.context.object
#         for child in ch.children:
#             if child.type == 'MESH':
#                 bpy.context.view_layer.objects.active = child
#                 mod = child.modifiers.new(name="GP_MESHDEFORM", type="MESH_DEFORM")
#                 mod.object = ch
#                 bpy.ops.object.meshdeform_bind(modifier=mod.name)
#
#         return {"FINISHED"}
#
#
# class Apply_Meshdeform(bpy.types.Operator):
#     bl_idname = "m4a1.apply_meshdeform"
#     bl_label = "Apply deformation modifier"
#     bl_description = "Automatically apply deformation modifier"
#     bl_options = {"REGISTER", "UNDO"}
#
#     def update_mode(self, context):
#         if self.mode == 'keep_modifier_apply_as_shapekey':
#             self.del_ = False
#         else:
#             self.del_ = True
#
#     mode: bpy.props.EnumProperty(name="模式",
#                                  default="apply",
#                                  items=[
#                                      ("apply", "Apply modifier", ""),
#                                      ("modifier_apply_as_shapekey", "Apply modifier as a shape key", ""),
#                                      ("keep_modifier_apply_as_shapekey", "Save modifier as a shape key", ""),
#                                      ("del_", "Delete modifier", ""),
#                                  ],
#                                  update=update_mode)
#
#     del_: bpy.props.BoolProperty(default=True, name="Delete the grid used by the deformation modifier", description='''When applying or deleting the modifier, remove the specified grid for the selected modifier or selected objects with a deformation modifier''')
#
#     def execute(self, context):
#
#         selected_objects = {obj for obj in context.selected_objects if obj.type == 'MESH'}
#         tmp_del_obj_dict = {}
#
#         not_modifiers_objs = []
#         for i in selected_objects:
#             if i.type == 'MESH':
#                 if 'MESH_DEFORM' in {j.type for j in i.modifiers}:
#                     pass
#                 else:
#                     if i not in not_modifiers_objs:
#                         not_modifiers_objs.append(i)
#
#         for obj in context.scene.objects:
#             if obj.type == 'MESH':
#                 for mod in obj.modifiers:
#                     if mod.type == 'MESH_DEFORM' and mod.object is not None:
#                         if mod.object in not_modifiers_objs:
#                             context.view_layer.objects.active = obj
#                             if self.del_:
#                                 if mod.object not in tmp_del_obj_dict:
#                                     tmp_del_obj_dict[mod.object] = []
#                                 if obj not in tmp_del_obj_dict[mod.object]:
#                                     tmp_del_obj_dict[mod.object].append(obj)
#
#                             if self.mode == 'apply':
#                                 bpy.ops.object.modifier_apply(modifier=mod.name)
#
#                             elif self.mode == 'del_':
#                                 bpy.ops.object.modifier_remove(modifier=mod.name)
#                             elif self.mode == 'modifier_apply_as_shapekey':
#                                 bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=False, modifier=mod.name)
#                             elif self.mode == 'keep_modifier_apply_as_shapekey':
#                                 bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=mod.name)
#
#         for obj in selected_objects:
#             for mod in obj.modifiers:
#                 if mod.type == 'MESH_DEFORM' and mod.object is not None:
#                     if obj.type == 'MESH':
#                         context.view_layer.objects.active = obj
#                         if self.del_:
#                             if mod.object not in tmp_del_obj_dict:
#                                 tmp_del_obj_dict[mod.object] = []
#
#                             if obj not in tmp_del_obj_dict[mod.object]:
#                                 tmp_del_obj_dict[mod.object].append(obj)
#
#                         if self.mode == 'apply':
#                             bpy.ops.object.modifier_apply(modifier=mod.name)
#
#                         elif self.mode == 'del_':
#                             bpy.ops.object.modifier_remove(modifier=mod.name)
#
#                         elif self.mode == 'modifier_apply_as_shapekey':
#                             bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=False, modifier=mod.name)
#                         elif self.mode == 'keep_modifier_apply_as_shapekey':
#                             bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=mod.name)
#
#         tmp_obj_mat_dict = {}
#         if self.del_:
#             bpy.ops.object.select_all(action='DESELECT')
#             for obj in tmp_del_obj_dict:
#                 obj.select_set(True, view_layer=context.view_layer)
#                 for i in tmp_del_obj_dict[obj]:
#                     tmp_obj_mat_dict[i] = i.matrix_world.copy()
#             bpy.ops.object.delete(use_global=True)
#
#             for obj in tmp_obj_mat_dict:
#                 obj.matrix_world = tmp_obj_mat_dict[obj]
#
#         return {'FINISHED'}
#
#     def draw(self, context):
#         layout = self.layout
#         layout.prop(self, "mode", expand=True)
#         row = layout.row()
#         row.prop(self, "del_")
#
#
