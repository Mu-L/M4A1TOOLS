import bpy
import bmesh
from bpy.props import EnumProperty, BoolProperty, IntProperty
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d, location_3d_to_region_2d
from bl_ui.space_statusbar import STATUSBAR_HT_header as statusbar
from mathutils import Vector, Matrix, Quaternion
from mathutils.geometry import intersect_line_plane, intersect_point_line, intersect_line_line, distance_point_to_plane
from math import radians, degrees
from .. utils.selection import get_selected_vert_sequences
from .. utils.math import average_locations, get_loc_matrix, get_face_center
from .. utils.draw import draw_point, draw_vector, draw_line, draw_points, draw_lines, draw_label
from .. utils.system import printd
from .. utils.property import step_enum
from .. utils.ui import get_zoom_factor
from .. utils.registration import get_prefs
from .. items import ctrl, alt, shift, axis_mapping_dict
from .. colors import normal, white, yellow, green, red, blue
from bpy.app.translations import pgettext as _
transform_mode_items = [('ROTATE', 'Rotate', ''),
                        ('SCALE', 'Scale', '')]

transform_axis_items = [('VIEW', 'View', ''),
                        ('X', 'X', ''),
                        ('Y', 'Y', ''),
                        ('Z', 'Z', '')]

constrain_mode_items = [('DIRECT', _('Direct'), ''),
                        ('PROXIMITY', _('Proximity'), ''),
                        ('INTERSECTION', _('Intersection'), ''),
                        ('PLANE_INTERSECTION', _('Plane Intersection'), ''),
                        ('PROJECTED_PLANE_INTERSECTION', _('Projected Plane Intersection'), ''),
                        ('DIRECT_PLANE_INTERSECTION', _('Direct Plane Intersection'), ''),
                        ('MOUSEDIR_PLANE_INTERSECTION', _('MouseDir Plane Intersection'), '')]

axis_color_mapping = {'X': red,
                      'Y': green,
                      'Z': blue}

def create_rotation_matrix_from_vector(vector, mx=None):
    normal = mx.to_3x3() @ vector if mx else vector
    binormal = normal.orthogonal()
    tangent = normal.cross(binormal)

    rot = Matrix()
    rot.col[0].xyz = tangent
    rot.col[1].xyz = binormal
    rot.col[2].xyz = normal

    return rot

def draw_edge_constrained_transform_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        if op.is_zero_scaling:
            text = 'Zero Scaling'
        elif op.transform_mode == 'SCALE':
            text = 'Scaling'
        elif op.transform_mode == 'ROTATE':
            text = 'Rotation'

        row.label(text=f"Edge Constrained {text}")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        if not op.is_axis_locking:
            row.label(text="", icon='EVENT_X')
            row.label(text="", icon='EVENT_Y')
            row.label(text="", icon='EVENT_Z')
            row.label(text="", icon='MOUSE_MMB')
            row.label(text="Axis")

        else:
            if not op.is_mmb:
                if op.transform_axis == 'X':
                    row.label(text="", icon='EVENT_Y')
                    row.label(text="", icon='EVENT_Z')

                elif op.transform_axis == 'Y':
                    row.label(text="", icon='EVENT_X')
                    row.label(text="", icon='EVENT_Z')

                elif op.transform_axis == 'Z':
                    row.label(text="", icon='EVENT_X')
                    row.label(text="", icon='EVENT_Y')

                row.label(text="Axis")

                row.label(text="", icon='EVENT_C')
                row.label(text="Clear Axis")

        if not op.is_zero_scaling:
            if op.transform_mode == 'SCALE':
                row.label(text="", icon='EVENT_R')
                row.label(text="Rotate")

            elif op.transform_mode == 'ROTATE':
                row.label(text="", icon='EVENT_S')
                row.label(text="Scale")

            row.label(text="", icon='EVENT_SHIFT')
            row.label(text="Zero Scale")

        if op.transform_mode == 'ROTATE' and not op.is_zero_scaling:
            row.label(text="", icon='MOUSE_MMB')
            row.label(text="Constrain Mode")

            row.label(text="", icon='EVENT_CTRL')
            row.label(text=f"Angle Snap")

        elif not op.is_direction_locking and not op.is_axis_locking and not op.is_zero_scaling:
            row.label(text="", icon='EVENT_ALT')
            row.label(text=f"Direction Lock")

        if op.draw_end_align:
            row.label(text="", icon='EVENT_E')
            row.label(text=f"Align Ends: {'Face' if op.end_align else 'Cross'}")

        if op.draw_face_align:
            row.label(text="", icon='EVENT_F')
            row.label(text=f"Face Alignment: {'True' if op.face_align else 'False'}")

        if len(op.data) > 1:
            row.label(text="", icon='EVENT_Q')
            row.label(text=f"Individual Origins: {op.individual_origins}")

    return draw

class TransformEdgeConstrained(bpy.types.Operator):
    bl_idname = "m4n1.transform_edge_constrained"
    bl_label = "M4N1: Transform Edge Constrained"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    objmode: BoolProperty(default=False)
    edgeindex: IntProperty()
    faceindex: IntProperty()

    transform_mode: EnumProperty(name='Transform Mode', items=transform_mode_items, default='ROTATE')
    transform_axis: EnumProperty(name='Transform Axis', items=transform_axis_items, default='VIEW')
    constrain_mode: EnumProperty(name='Constrain Mode', items=constrain_mode_items, default='DIRECT_PLANE_INTERSECTION')
    end_align: BoolProperty(name="Align Ends to Face Edge", default=True)
    draw_end_align: BoolProperty(name="Draw Align Ends Option", default=False)
    face_align: BoolProperty(name="Face Align", default=False)
    draw_face_align: BoolProperty(name="Draw Align Ends Option", default=False)
    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH':
            bm = bmesh.from_edit_mesh(context.active_object.data)
            return [e for e in bm.edges if e.select]
        elif context.mode == 'OBJECT':
            return True

    def draw_HUD(self, args):
        context, event = args

        scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale
        height = 10 * scale

        if self.is_zero_scaling:
            draw_label(context, title=_(f"ZERO SCALE"), coords=self.mousepos + Vector((20, height)), color=white, center=False)

        elif self.transform_mode == 'SCALE':
            draw_label(context, title=_("SCALE {:.2f}").format(self.amount), coords=self.mousepos + Vector((20, height)), color=yellow if self.is_snapping else white, center=False)

            if self.is_direction_locking:
                height -= 20 * scale
                draw_label(context, title=_(f"Direction Locked"), coords=self.mousepos + Vector((20, height)), color=white, alpha=0.5, center=False)

        elif self.transform_mode == 'ROTATE':
            draw_label(context, title=_("ROTATE {:.1f}").format(self.angle), coords=self.mousepos + Vector((20, height)), color=yellow if self.is_snapping else white, center=False)

            height -= 20 * scale
            print(self.constrain_mode)
            draw_label(context, title=f"{_(self.constrain_mode.title().replace('_', ' '))}", coords=self.mousepos + Vector((20, height)), alpha=0.5, center=False)

        if self.is_axis_locking:
            axis = self.transform_axis[-1]
            height -= 20 * scale
            draw_label(context, title=_('LOCAL {}'.format(self.transform_axis)), coords=self.mousepos + Vector((20, height)), color=axis_color_mapping[axis], center=False)

        if self.individual_origins:
            height -= 20 * scale
            draw_label(context, title=_('Individual Origins'), coords=self.mousepos + Vector((20, height)), color=yellow, center=False)

    def draw_VIEW3D(self):
        modal = True

        draw_point(self.origin, color=(1, 1, 0), alpha=0.5, modal=modal)

        if self.individual_origins:
            individual_origins = [seq['origin'] for seq in self.data.values()]
            draw_points(individual_origins, color=(1, 1, 0), size=4, alpha=0.5, modal=modal)

        if self.is_axis_locking:
            axis = self.transform_axis[-1]
            axis_vector = self.mx.col[axis_mapping_dict[axis]].xyz.normalized()
            draw_line([self.origin - axis_vector * 1000, self.origin, self.origin + axis_vector * 1000], color=axis_color_mapping[axis], alpha=0.5)

        for axis in ['X', 'Y', 'Z']:
            axis_vector = self.mx.col[axis_mapping_dict[axis]].xyz.normalized()
            draw_line([self.origin + axis_vector * 0.3 * self.zoom_factor, self.origin + axis_vector * self.zoom_factor], color=axis_color_mapping[axis], alpha=0.75)

        if self.is_direction_locking:
            draw_vector(self.scale, origin=self.origin, color=white, alpha=0.5, modal=modal)

        elif self.transform_mode == 'SCALE' and self.is_axis_locking:
            draw_vector(self.scale, origin=self.origin, color=white, alpha=0.5, modal=modal)

        elif not (self.is_zero_scaling and self.is_axis_locking):
            draw_line([self.origin, self.intersection], color=(0, 0, 0), alpha=0.5, modal=modal)

        if self.slide_coords:
            draw_lines(self.slide_coords, mx=self.mx, color=(0.5, 1, 0.5), width=2, alpha=0.3)

        if self.original_edge_coords:
            draw_lines(self.original_edge_coords, mx=self.mx, color=(1, 1, 1), width=1, alpha=0.1)

    def modal(self, context, event):
        context.area.tag_redraw()

        self.is_snapping = event.ctrl
        self.is_zero_scaling = event.shift

        if event.type in shift:
            self.update_transform_plane(context, init=True)

        self.is_direction_locking = event.alt and self.transform_mode == 'SCALE' and not self.is_zero_scaling and not self.is_axis_locking
        self.update_scale_direction_lock()

        events = ['MOUSEMOVE', *ctrl, *shift, *alt, 'ONE', 'TWO', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'E', 'R', 'S', 'X', 'Y', 'Z', 'C', 'MIDDLEMOUSE', 'F', 'Q']

        if event.type in events:

            if event.type in ['MOUSEMOVE']:
                self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y))
                self.update_transform_plane(context, init=False)

            if event.type in ['X', 'Y', 'Z', 'C'] and event.value == 'PRESS' or event.type == 'MIDDLEMOUSE':
                self.update_transform_axis(context, event)

            elif event.type in ['R'] and event.value == 'PRESS':
                self.transform_mode = 'ROTATE'

                self.update_transform_plane(context, init=True)

            elif event.type in ['S'] and event.value == 'PRESS':
                self.transform_mode = 'SCALE'

                self.update_transform_plane(context, init=True)

            elif event.type in ['ONE', 'WHEELUPMOUSE'] and event.value == 'PRESS' and self.transform_mode == 'ROTATE' and not self.is_zero_scaling:
                self.constrain_mode = step_enum(self.constrain_mode, items=constrain_mode_items, step=-1, loop=True)

            elif event.type in ['TWO', 'WHEELDOWNMOUSE'] and event.value == 'PRESS' and self.transform_mode == 'ROTATE' and not self.is_zero_scaling:
                self.constrain_mode = step_enum(self.constrain_mode, items=constrain_mode_items, step=1, loop=True)

            elif event.type in ['E'] and event.value == 'PRESS':
                self.end_align = not self.end_align

            elif event.type in ['F'] and event.value == 'PRESS':
                self.face_align = not self.face_align

            elif len(self.data) > 1 and event.type in ['Q'] and event.value == 'PRESS':
                self.individual_origins = not self.individual_origins

            self.transform(context)

        if event.type in {'LEFTMOUSE', 'SPACE'} and event.value == 'PRESS':
            self.finish()
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.reset_mesh()
            self.finish()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        statusbar.draw = self.bar_orig

        if self.objmode:
            bpy.ops.object.mode_set(mode='OBJECT')

    def invoke(self, context, event):
        self.active = context.active_object
        self.mx = self.active.matrix_world

        if self.objmode:

            if self.edgeindex != -1 or self.faceindex != -1:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='DESELECT')

                bm = bmesh.from_edit_mesh(self.active.data)

                if self.faceindex != -1:

                    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')

                    bm.faces.ensure_lookup_table()
                    bm.faces[self.faceindex].select_set(True)

                elif self.edgeindex != -1:

                    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')

                    bm.edges.ensure_lookup_table()
                    bm.edges[self.edgeindex].select_set(True)

                bmesh.update_edit_mesh(self.active.data)

            else:
                return {'CANCELLED'}

        self.slide_coords = []
        self.original_edge_coords = []
        self.init_debug_coords()

        self.bm = bmesh.from_edit_mesh(self.active.data)
        self.bm.normal_update()
        self.bm.verts.ensure_lookup_table()

        verts = [v for v in self.bm.verts if v.select]
        sequences = get_selected_vert_sequences(verts, ensure_seq_len=True, debug=False)

        self.data = self.get_data(self.bm, sequences)

        self.transform_axis = 'VIEW'

        pivot = context.scene.tool_settings.transform_pivot_point
        self.individual_origins = len(self.data) > 1 and pivot not in ['CURSOR', 'ACTIVE_ELEMENT']

        self.is_snapping = False
        self.is_zero_scaling = False
        self.is_axis_locking = False
        self.is_direction_locking = False
        self.is_mmb = False

        self.end_align = True
        self.face_align = False

        self.angle = 0
        self.rotation = Quaternion()
        self.amount = 1
        self.scale = Vector()
        self.locked_intersection = None

        self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.update_transform_plane(context, init=True)

        self.zoom_factor = get_zoom_factor(context, self.origin, scale=30)

        self.draw_end_align = False
        self.bar_orig = statusbar.draw
        statusbar.draw = draw_edge_constrained_transform_status(self)

        args = (context, event)
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (), 'WINDOW', 'POST_VIEW')
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (args, ), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def update_scale_direction_lock(self):
        if self.is_direction_locking and not self.locked_intersection:
            self.locked_intersection = self.intersection
        elif not self.is_direction_locking and self.locked_intersection:
            self.locked_intersection = None

    def get_data(self, bm, sequences):
        def get_next_and_prev_edges():
            if vdata['next_vert']:
                edge = bm.edges.get([v, vdata['next_vert']])
                vdata['next_edge'] = edge

                if edge not in data[sidx]['edges']:
                    data[sidx]['edges'].append(edge)

            if vdata['prev_vert']:
                edge = bm.edges.get([v, vdata['prev_vert']])
                vdata['prev_edge'] = edge

                if edge not in data[sidx]['edges']:
                    data[sidx]['edges'].append(edge)

        def get_directions():
            if vdata['prev_vert'] and vdata['next_vert']:
                vdir = ((vdata['next_vert'].co - vdata['co']).normalized() + (vdata['co'] - vdata['prev_vert'].co).normalized()).normalized()
                vdata['dir'] = vdir

            elif vdata['next_vert']:
                vdir = (vdata['next_vert'].co - vdata['co']).normalized()
                vdata['dir'] = vdir

            else:
                vdir = (vdata['co'] - vdata['prev_vert'].co).normalized()
                vdata['dir'] = vdir

            vdata['cross'] = vdata['no'].cross(vdir).normalized()

        def get_loop_and_faces():
            if vdata['next_edge']:
                edge = vdata['next_edge']
                loops = [l for l in edge.link_loops if l.vert == v]

                if loops:
                    vdata['loop'] = loops[0]

                    left_face = loops[0].face
                    right_face = loops[0].link_loop_radial_next.face

                    vdata['left_face'] = left_face

                    if right_face != left_face:
                        vdata['right_face'] = loops[0].link_loop_radial_next.face

                elif edge.link_loops:
                    loop = edge.link_loops[0]

                    vdata['right_face'] = loop.face

            else:
                vdata['loop'] = data[sidx][vdata['prev_vert']]['loop']
                vdata['left_face'] = data[sidx][vdata['prev_vert']]['left_face']
                vdata['right_face'] = data[sidx][vdata['prev_vert']]['right_face']

        def get_side_edges():
            connected_edges = [e for e in v.link_edges if e not in data[sidx]['edges']]

            for side in ['left', 'right']:

                if connected_edges:

                    edges = []

                    for e in connected_edges:
                        edge_dir = (e.other_vert(v).co - vdata['co']).normalized()
                        dot = edge_dir.dot(vdata['cross'])

                        if side == 'left' and dot > 0.2 or side == 'right' and dot < -0.2:
                            edges.append((e, abs(dot)))

                    if edges:
                        edge = max(edges, key=lambda x: x[1])[0]

                        vdata[f'{side}_edge'] = edge
                        vdata[f'{side}_edge_dir'] = (edge.other_vert(v).co - v.co).normalized()
                        vdata[f'{side}_edge_coords'] = [v.co.copy() for v in edge.verts]

                    if vdata.get(f'{side}_face'):

                        edges = [e for e in connected_edges if vdata.get(f'{side}_face') in e.link_faces]

                        if edges:
                            edge = edges[0]

                            vdata[f'{side}_face_edge'] = edge
                            vdata[f'{side}_face_edge_dir'] = (edge.other_vert(v).co - v.co).normalized()
                            vdata[f'{side}_face_edge_coords'] = [v.co.copy() for v in edge.verts]

                if vdata.get(f'{side}_face') and not vdata[f'{side}_edge']:

                    cross = vdata['cross'] if side == 'left' else - vdata['cross']
                    i = intersect_line_plane(vdata['co'] + cross, vdata['co'] + cross - vdata[f'{side}_face'].normal, vdata['co'], vdata[f'{side}_face'].normal)

                    if i:
                        face_dir = (i - vdata['co']).normalized()
                        vdata[f'{side}_face_dir'] = face_dir
                        vdata[f'{side}_face_coords'] = [vdata['co'], vdata['co'] + face_dir]

                        self.draw_face_align = True

        def get_flipped_side_edges():

            if vdata['left_edge'] and not vdata['right_edge']:

                vdata['right_edge'] = vdata['left_edge']
                vdata['right_edge_dir'] = - vdata['left_edge_dir']
                vdata['right_edge_coords'] = vdata['left_edge_coords']

            elif vdata['right_edge'] and not vdata['left_edge']:

                vdata['left_edge'] = vdata['right_edge']
                vdata['left_edge_dir'] = - vdata['right_edge_dir']
                vdata['left_edge_coords'] = vdata['right_edge_coords']

            if vdata['left_face_edge'] and not vdata['right_face_edge']:

                vdata['right_face_edge'] = vdata['left_face_edge']
                vdata['right_face_edge_dir'] = - vdata['left_face_edge_dir']
                vdata['right_face_edge_coords'] = vdata['left_face_edge_coords']

            elif vdata['right_face_edge'] and not vdata['left_face_edge']:

                vdata['left_face_edge'] = vdata['right_face_edge']
                vdata['left_face_edge_dir'] = - vdata['right_face_edge_dir']
                vdata['left_face_edge_coords'] = vdata['right_face_edge_coords']

            if vdata['left_face_dir'] and not vdata['right_face_dir']:

                vdata['right_face_dir'] = - vdata['left_face_dir']

            elif vdata['right_face_dir'] and not vdata['left_face_dir']:

                vdata['left_face_dir'] = - vdata['right_face_dir']

        data = {}
        self.draw_face_align = False

        for sidx, (seq, cyclic) in enumerate(sequences):
            data[sidx] = {'cyclic': cyclic,
                          'verts': seq,
                          'edges': [],
                          'origin': self.mx @ average_locations([v.co for v in seq])}

            for vidx, v in enumerate(seq):
                prev_vert = seq[(vidx - 1) % len(seq)]
                next_vert = seq[(vidx + 1) % len(seq)]

                data[sidx][v] = {'co': v.co.copy(),
                                 'no': v.normal.copy(),
                                 'dir': None,
                                 'cross': None,

                                 'prev_vert': prev_vert,
                                 'next_vert': next_vert,
                                 'prev_edge': None,
                                 'next_edge': None,

                                 'loop': None,
                                 'left_face': None,
                                 'right_face': None,

                                 'left_edge': None,
                                 'left_edge_dir': None,
                                 'left_edge_coords': None,
                                 'right_edge': None,
                                 'right_edge_dir': None,
                                 'right_edge_coords': None,

                                 'left_face_edge': None,
                                 'left_face_edge_dir': None,
                                 'left_face_edge_coords': None,
                                 'right_face_edge': None,
                                 'right_face_edge_dir': None,
                                 'right_face_edge_coords': None,

                                 'left_face_dir': None,
                                 'left_face_coords': None,
                                 'right_face_dir': None,
                                 'right_face_coords': None,

                                 }

            if not cyclic:
                data[sidx][seq[0]]['prev_vert'] = None
                data[sidx][seq[-1]]['next_vert'] = None

            for v in seq:
                vdata = data[sidx][v]

                get_next_and_prev_edges()

                get_directions()

                get_loop_and_faces()

                get_side_edges()

                if vdata['next_vert']:
                    self.original_edge_coords.extend([vdata['co'], data[sidx][vdata['next_vert']]['co']])

            for v in seq:
                vdata = data[sidx][v]

                get_flipped_side_edges()

        return data

    def debug_data(self, context, data, mx, factor=0.1):
        printd(data, 'data dict')

        for sidx, seq in data.items():

            origin = seq['origin']
            draw_point(origin, modal=False)

            for idx, v in enumerate(seq['verts']):
                vdata = seq[v]

                co = vdata['co']
                no = vdata['no']
                vdir = vdata['dir']
                cross = vdata['cross']

                draw_vector(no * factor, origin=co, mx=mx, color=normal, alpha=1, modal=False)
                draw_vector(vdir * factor, origin=co, mx=mx, color=(1, 1, 0), alpha=1, modal=False)

                draw_vector(cross * factor / 3, origin=co, mx=mx, color=(0, 1, 0), alpha=0.5, modal=False)
                draw_vector(-cross * factor / 3, origin=co, mx=mx, color=(1, 0, 0), alpha=0.5, modal=False)

                for side in ['left', 'right']:
                    edge_dir = vdata[f'{side}_edge_dir']

                    if edge_dir:
                        draw_line([vdata['co'], vdata['co'] + vdata[f'{side}_edge_dir'] * factor * 3], mx=mx, color=(0, 0.5, 1), alpha=0.75, modal=False)

                    face_edge_dir = vdata[f'{side}_face_edge_dir']

                    if face_edge_dir:
                        draw_line([vdata['co'], vdata['co'] + vdata[f'{side}_face_edge_dir'] * factor * 2], mx=mx, color=(0, 1, 0), alpha=0.75, modal=False)

                    face_dir = vdata[f'{side}_face_dir']

                    if face_dir:
                        draw_line([vdata['co'], vdata['co'] + vdata[f'{side}_face_dir'] * factor], mx=mx, color=(1, 0.5, 0), alpha=0.75, modal=False)

        context.area.tag_redraw()

    def update_transform_axis(self, context, event):
        if event.type == 'X':
            self.transform_axis = 'X'
            self.is_axis_locking = True

        elif event.type == 'Y':
            self.transform_axis = 'Y'
            self.is_axis_locking = True

        elif event.type == 'Z':
            self.transform_axis = 'Z'
            self.is_axis_locking = True

        elif event.type == 'C':
            self.transform_axis = 'VIEW'
            self.is_axis_locking = False

        elif event.type == 'MIDDLEMOUSE':

            if event.value == 'PRESS':
                origin_2d = location_3d_to_region_2d(context.region, context.region_data, self.origin)

                if not origin_2d:
                    return

                mouse_vector = (origin_2d - self.mousepos).normalized()

                axes_2d = []

                for axis in ['X', 'Y', 'Z']:

                    axis_vector = self.mx.col[axis_mapping_dict[axis]].xyz.normalized() * self.zoom_factor
                    axis_2d = origin_2d - location_3d_to_region_2d(context.region, context.region_data, self.origin + axis_vector)

                    if round(axis_2d.length):
                        axes_2d.append((axis, mouse_vector.dot(axis_2d.normalized())))

                axis = max(axes_2d, key=lambda x: abs(x[1]))[0]

                self.transform_axis = axis
                self.is_axis_locking = True
                self.is_mmb = True

            elif event.value == 'RELEASE':
                self.transform_axis = 'VIEW'
                self.is_axis_locking = False
                self.is_mmb = False

        self.update_transform_plane(context, init=True)

    def update_transform_plane(self, context, init=False):
        def get_origin():
            def get_active_edge_origin():
                for seq in self.data.values():
                    edges = seq['edges']
                    cyclic = seq['cyclic']

                    if not cyclic and edge in edges and len(edges) > 1:
                        verts = seq['verts']

                        if edge == edges[0]:
                            return self.mx @ verts[0].co

                        elif edge == edges[-1]:
                            return self.mx @ verts[-1].co

                return self.mx @ average_locations([v.co for v in edge.verts])

            pivot = context.scene.tool_settings.transform_pivot_point

            if pivot == 'CURSOR':
                origin = context.scene.cursor.location

            elif pivot == 'ACTIVE_ELEMENT':
                if self.bm.select_history and tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (True, False, False):
                    vert = self.bm.select_history[-1]
                    origin = self.mx @ vert.co

                elif self.bm.select_history and tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (False, True, False):
                    edge = self.bm.select_history[-1]
                    origin = get_active_edge_origin()

                elif self.bm.faces.active and tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (False, False, True):
                    face = self.bm.faces.active
                    origin = self.mx @ get_face_center(face)

                else:
                    verts = [v for seq in self.data.values() for v in seq['verts']]
                    origin = self.mx @ average_locations([v.co for v in verts])

            else:
                verts = [v for seq in self.data.values() for v in seq['verts']]

                origin = self.mx @ average_locations([v.co for v in verts])

            return origin

        def get_origin_dir():
            if self.transform_axis == 'VIEW':
                origin_dir = - region_2d_to_vector_3d(context.region, context.region_data, (context.region.width / 2, context.region.height / 2))

            elif self.transform_mode == 'SCALE' or self.is_zero_scaling:
                axis = self.transform_axis
                axis_vector = self.mx.col[axis_mapping_dict[axis]].xyz
                cross_vector = axis_vector.cross(view_dir)

                origin_dir = axis_vector.cross(cross_vector)

            elif self.transform_mode == 'ROTATE':
                axis = self.transform_axis[-1]
                origin_dir = self.mx.col[axis_mapping_dict[axis]].xyz

            return origin_dir

        view_origin = region_2d_to_origin_3d(context.region, context.region_data, self.mousepos)
        view_dir = region_2d_to_vector_3d(context.region, context.region_data, self.mousepos)

        if init:
            self.reset_mesh()

            self.origin = get_origin()
            self.origin_dir = get_origin_dir()

        i = intersect_line_plane(view_origin, view_origin + view_dir, self.origin, self.origin_dir)

        if not i or round(self.origin_dir.dot(view_dir), 5) == 0:
            self.transform_axis = 'VIEW'
            self.is_axis_locking = False

            self.origin_dir = - region_2d_to_vector_3d(context.region, context.region_data, (context.region.width / 2, context.region.height / 2))
            i = intersect_line_plane(view_origin, view_origin + view_dir, self.origin, self.origin_dir)

        if init:
            self.init_intersection = i

        self.intersection = i

    def reset_mesh(self):
        for selection in self.data.values():
            for v in selection['verts']:
                v.co = selection[v]['co']

        self.bm.normal_update()
        bmesh.update_edit_mesh(self.active.data)

    def transform(self, context):
        def get_rotation():
            rotation = (self.init_intersection - self.origin).rotation_difference(self.intersection - self.origin)

            if self.is_snapping:
                dangle = degrees(rotation.angle)
                mod = dangle % 5

                angle = radians(dangle + (5 - mod)) if mod >= 2.5 else radians(dangle - mod)
                rotation = Quaternion(rotation.axis, angle)

            self.angle = degrees(rotation.angle)
            return rotation

        def get_scale(per_sequence_origin=None):
            def lock_scale_direction():
                i = intersect_point_line(self.intersection, self.origin, self.locked_intersection)

                if i:
                    current_scale = i[0] - self.origin

                    dot = current_scale.normalized().dot((self.locked_intersection - self.origin).normalized())

                    if dot < 0:
                        amount = 0
                        current_scale = current_scale * 0.001

                    else:
                        amount = current_scale.length / init_scale.length

                return amount, current_scale

            def lock_scale_axis():
                axis = self.transform_axis
                axis_vector = self.mx.col[axis_mapping_dict[axis]].xyz

                i = intersect_point_line(self.intersection, self.origin, self.origin + axis_vector)

                if i:
                    current_scale = i[0] - self.origin

                    init_i = intersect_point_line(self.init_intersection, self.origin, self.origin + axis_vector)
                    init_scale = init_i[0] - self.origin

                    amount = current_scale.length / init_scale.length
                return amount, current_scale

            init_scale = self.init_intersection - self.origin
            current_scale = self.intersection - self.origin
            amount = current_scale.length / init_scale.length

            if self.is_axis_locking:
                amount, current_scale = lock_scale_axis()

            elif self.is_direction_locking:
                amount, current_scale = lock_scale_direction()

            if per_sequence_origin:
                origin_local = self.mx.inverted_safe() @ per_sequence_origin
            else:
                origin_local = self.mx.inverted_safe() @ self.origin

            rmx = create_rotation_matrix_from_vector(current_scale.normalized(), mx=self.mx.inverted_safe())

            space = rmx.inverted_safe() @ get_loc_matrix(origin_local).inverted_safe()

            if self.is_zero_scaling:
                amount = 0

            vec = Vector((1, 1, amount))

            self.amount = amount
            return vec, space, current_scale

        self.reset_mesh()

        verts = [v for seq in self.data.values() for v in seq['verts']]

        if self.transform_mode == 'SCALE' or self.is_zero_scaling:
            vec, space, self.scale = get_scale()

            if self.individual_origins:
                for seq in self.data.values():
                    origin = seq['origin']
                    verts = seq['verts']

                    _, space, _ = get_scale(per_sequence_origin=origin)
                    bmesh.ops.scale(self.bm, vec=vec, space=space, verts=verts)
            else:
                bmesh.ops.scale(self.bm, vec=vec, space=space, verts=verts)

        elif self.transform_mode == 'ROTATE':
            self.rotation = get_rotation()

            if self.individual_origins:
                for seq in self.data.values():
                    origin = seq['origin']
                    verts = seq['verts']

                    bmesh.ops.rotate(self.bm, cent=origin, matrix=self.rotation.to_matrix(), verts=verts, space=self.mx)
            else:
                bmesh.ops.rotate(self.bm, cent=self.origin, matrix=self.rotation.to_matrix(), verts=verts, space=self.mx)

        self.tdata = self.get_transformed_data()

        self.constrain_verts_to_edges()

        self.bm.normal_update()
        bmesh.update_edit_mesh(self.active.data)

    def constrain_verts_to_edges(self):
        for sidx, selection in self.tdata.items():
            for v in selection['verts']:
                tvdata = self.tdata[sidx][v]

                if not tvdata['edge_dir']:
                    continue

                if self.transform_mode == 'SCALE' or self.is_zero_scaling:
                    if tvdata['scale_plane_intersection_co']:
                        v.co = tvdata['scale_plane_intersection_co']

                else:

                    if self.constrain_mode == 'DIRECT':
                        if tvdata['direct_co']:
                            v.co = tvdata['direct_co']

                    elif self.constrain_mode == 'PROXIMITY':
                        if tvdata['proximity_co']:
                            v.co = tvdata['proximity_co']

                    elif self.constrain_mode == 'INTERSECTION':
                        if tvdata['intersection_co']:
                            v.co = tvdata['intersection_co']

                    elif self.constrain_mode == 'PLANE_INTERSECTION':
                        if tvdata['plane_intersection_co']:
                            v.co = tvdata['plane_intersection_co']

                    elif self.constrain_mode == 'PROJECTED_PLANE_INTERSECTION':
                        if tvdata['projected_plane_intersection_co']:
                            v.co = tvdata['projected_plane_intersection_co']

                        elif tvdata['direct_co']:
                            v.co = tvdata['direct_co']

                        elif tvdata['proximity_co']:
                            v.co = tvdata['proximity_co']

                    elif self.constrain_mode == 'DIRECT_PLANE_INTERSECTION':
                        if tvdata['direct_plane_intersection_co']:
                            v.co = tvdata['direct_plane_intersection_co']

                        elif tvdata['projected_plane_intersection_co']:
                            v.co = tvdata['projected_plane_intersection_co']

                        elif tvdata['direct_co']:
                            v.co = tvdata['direct_co']

                        elif tvdata['proximity_co']:
                            v.co = tvdata['proximity_co']

                    elif self.constrain_mode == 'MOUSEDIR_PLANE_INTERSECTION':
                        if tvdata['mousedir_plane_intersection_co']:
                            v.co = tvdata['mousedir_plane_intersection_co']

    def get_transformed_data(self):
        def check_if_flat():
            if len(verts) >= 3:
                plane_co = tdata[sidx][verts[1]]['init_co']

                plane_no = tdata[sidx][verts[1]]['init_no']

                off_plane_verts = [v for v in verts if v != verts[1]]

                for v in off_plane_verts:
                    d = distance_point_to_plane(tdata[sidx][v]['init_co'], plane_co, plane_no)

                    if abs(round(d, 6)) > 0:
                        return False
            return True

        def get_rotated_dir():
            if tvdata['prev_vert'] and tvdata['next_vert']:
                rvdir = ((tvdata['next_vert'].co - v.co).normalized() + (v.co - tvdata['prev_vert'].co).normalized()).normalized()
            elif tvdata['next_vert']:
                rvdir = (tvdata['next_vert'].co - v.co).normalized()
            else:
                rvdir = (v.co - tvdata['prev_vert'].co).normalized()

            tvdata['dir'] = rvdir

            return rvdir

        def get_rotated_normal_and_cross():
            rmx = self.mx.inverted_safe().to_quaternion() @ self.rotation @ self.mx.to_quaternion()
            tvdata['no'] = rmx @ init_no
            tvdata['cross'] = rvdir.cross(tvdata['no'])

        def get_edge_dir():
            def check_face_dir_alignment(edge_dir, slide_coords):
                if self.face_align:

                    if vdata['left_face_dir']:

                        dirs = [('edge_dir', moved_dir.dot(edge_dir)), ('left_face_dir', moved_dir.dot(vdata['left_face_dir'])), ('right_face_dir', moved_dir.dot(vdata['right_face_dir']))]
                        max_dir = max(dirs, key=lambda x: abs(x[1]))

                        if max_dir[0] != 'edge_dir':

                            edge_dir = vdata[max_dir[0]]
                            slide_coords = vdata[max_dir[0].replace('dir', 'coords')]

                return edge_dir, slide_coords

            edge_dir = None
            slide_coords = []

            moved_dir = (v.co - vdata['co']).normalized()
            dot = moved_dir.dot(cross)
            side = 'left' if dot > 0 else 'right'

            endvert = v == verts[0] or v == verts[-1]

            if self.end_align and not cyclic and endvert and vdata[f'{side}_face_edge_dir']:
                edge_dir = vdata[f'{side}_face_edge_dir']
                slide_coords = vdata[f'{side}_face_edge_coords']

            elif vdata[f'{side}_edge_dir']:
                edge_dir = vdata[f'{side}_edge_dir']
                slide_coords = vdata[f'{side}_edge_coords']

                edge_dir, slide_coords = check_face_dir_alignment(edge_dir, slide_coords)

            elif vdata[f'{side}_face_edge_dir']:
                edge_dir = vdata[f'{side}_face_edge_dir']
                slide_coords = vdata[f'{side}_face_edge_coords']

                edge_dir, slide_coords = check_face_dir_alignment(edge_dir, slide_coords)

            elif vdata[f'{side}_face_dir']:
                edge_dir = vdata[f'{side}_face_dir']
                slide_coords = vdata[f'{side}_face_coords']

                edge_dir, slide_coords = check_face_dir_alignment(edge_dir, slide_coords)

            tvdata['edge_dir'] = edge_dir

            edges_differ = False
            if vdata[f'{side}_edge'] and vdata[f'{side}_face_edge'] and vdata[f'{side}_edge'] != vdata[f'{side}_face_edge']:
                edges_differ = True

            if not cyclic and slide_coords and endvert and edges_differ:
                self.slide_coords.extend(slide_coords)
                self.draw_end_align = True

            return edge_dir

        def get_projected_co(debug=False):
            if self.individual_origins:
                i = intersect_line_plane(co, co + origin_dir_local, individual_origin_local, origin_dir_local)

            else:
                i = intersect_line_plane(co, co + origin_dir_local, origin_local, origin_dir_local)

            if i:
                tvdata['projected_co'] = i
                tvdata['projected_dir'] = i - co

            elif debug:
                print("failed projected dir", v.index)

        def get_direct_co():
            if self.individual_origins:
                i = intersect_line_line(individual_origin_local, co, init_co, init_co + edge_dir)

            else:
                i = intersect_line_line(origin_local, co, init_co, init_co + edge_dir)

            if i:
                tvdata['direct_co'] = i[1]

        def get_proximity_co():
            i, _ = intersect_point_line(co, init_co, init_co + edge_dir)
            tvdata['proximity_co'] = i

        def get_intersection_co():
            i = intersect_line_line(co, co + rvdir, init_co, init_co + edge_dir)[1]

            if i:
                tvdata['intersection_co'] = i

        def get_plane_intersection_co():
            i = intersect_line_plane(init_co, init_co + edge_dir, co, tvdata['cross'])

            if i:
                tvdata['plane_intersection_co'] = i

        def get_projected_plane_intersection_co(debug=False):
            projected_cross = rvdir.cross(tvdata['projected_dir'])

            i = intersect_line_plane(init_co, init_co + edge_dir, co, projected_cross)

            if i:
                tvdata['projected_plane_intersection_co'] = i

            elif debug:
                print("failed projected cross", v.index)

        def get_direct_plane_intersection_co(debug=False):
            if is_flat:
                tvdata['direct_plane_intersection_co'] = tvdata['projected_plane_intersection_co']
                return

            if self.individual_origins:
                direct_dir = (co - individual_origin_local).normalized()
            else:
                direct_dir = (co - origin_local).normalized()

            direct_cross = rvdir.cross(direct_dir)

            i = intersect_line_plane(init_co, init_co + edge_dir, co, direct_cross)

            if i:
                tvdata['direct_plane_intersection_co'] = i

            elif debug:
                print("failed direct cross", v.index)

        def get_mousedir_plane_intersection_co(debug=False):
            i = intersect_line_plane(init_co, init_co + edge_dir, co, init_mousedir_local)

            if i:
                tvdata['mousedir_plane_intersection_co'] = i

            elif debug:
                print("failed scale plane intersection", v.index)

        def get_scale_plane_intersection_co(debug=False):
            i = intersect_line_plane(init_co, init_co + edge_dir, co, current_scale_local)

            if i:
                tvdata['scale_plane_intersection_co'] = i

            elif debug:
                print("failed scale plane intersection", v.index)

        tdata = {}
        self.slide_coords = []

        origin_local = self.mx.inverted_safe() @ self.origin
        origin_dir_local = self.mx.inverted_safe().to_quaternion() @ self.origin_dir

        current_scale_local = self.mx.inverted_safe().to_quaternion() @ self.scale

        init_mousedir_local = self.mx.to_quaternion() @ (self.origin - self.init_intersection)

        for sidx, selection in self.data.items():
            verts = selection['verts']
            cyclic = selection['cyclic']
            individual_origin_local = self.mx.inverted_safe() @ selection['origin']

            tdata[sidx] = {'verts': verts, 'cyclic': cyclic}

            for v in verts:
                vdata = selection[v]

                co = v.co.copy()
                init_co = vdata['co']
                init_no = vdata['no']

                tdata[sidx][v] = {'co': co,
                                  'init_co': init_co,
                                  'dir': None,

                                  'no': None,
                                  'init_no': init_no,
                                  'cross': None,

                                  'prev_vert': vdata['prev_vert'],
                                  'next_vert': vdata['next_vert'],

                                  'edge_dir': None,

                                  'projected_co': None,
                                  'projected_dir': None,

                                  'direct_co': None,
                                  'proximity_co': None,
                                  'intersection_co': None,
                                  'plane_intersection_co': None,
                                  'projected_plane_intersection_co': None,
                                  'direct_plane_intersection_co': None,

                                  'scale_plane_intersection_co': None,
                                  'mousedir_plane_intersection_co': None,
                                  }

            is_flat = check_if_flat()

            for v in verts:
                vdata = self.data[sidx][v]
                tvdata = tdata[sidx][v]

                co = tvdata['co']
                init_co = tvdata['init_co']
                init_no = vdata['no']
                cross = vdata['cross']

                rvdir = get_rotated_dir()

                get_rotated_normal_and_cross()

                edge_dir = get_edge_dir()

                if self.transform_mode == 'SCALE' or self.is_zero_scaling:

                    get_scale_plane_intersection_co(debug=False)

                else:

                    get_projected_co(debug=False)

                    get_direct_co()

                    get_proximity_co()

                    get_intersection_co()

                    get_plane_intersection_co()

                    get_projected_plane_intersection_co(debug=False)

                    get_direct_plane_intersection_co(debug=False)

                    get_mousedir_plane_intersection_co(debug=False)

        return tdata

    def init_debug_coords(self):
        self.original_coords = []
        self.rotated_coords = []
        self.rotated_edge_dir_coords = []
        self.rotated_dir_coords = []

        self.original_normal_coords = []
        self.rotated_normal_coords = []
        self.rotated_cross_coords = []

        self.projected_coords = []
        self.projected_dir_coords = []

        self.direct_coords = []
        self.proximity_coords = []
        self.intersection_coords = []
        self.plane_intersection_coords = []
        self.projected_plane_intersection_coords = []

    def debug_transformed_data(self, context, factor=0.1):
        print()
        printd(self.tdata, 'transformed dict')

        self.init_debug_coords()

        for sidx, selection in self.tdata.items():
            for v in selection['verts']:
                tvdata = self.tdata[sidx][v]

                co = tvdata['co']
                init_co = tvdata['init_co']

                no = tvdata['no']
                init_no = tvdata['init_no']

                cross = tvdata['cross']

                projected = tvdata['projected_co']
                projected_dir = tvdata['projected_dir']

                self.original_coords.append(init_co)
                self.rotated_coords.append(co)

                self.original_normal_coords.extend((co, co + init_no * factor))
                self.rotated_normal_coords.extend((co, co + no * factor))
                self.rotated_cross_coords.extend((co, co + cross * factor))

                if tvdata['edge_dir']:
                    self.rotated_edge_dir_coords.extend((init_co, init_co + tvdata['edge_dir']))

                self.rotated_dir_coords.extend((co, co + tvdata['dir'] * factor))

                if self.transform_mode == 'ROTATE' and not self.is_zero_scaling:
                    self.projected_coords.append(projected)
                    self.projected_dir_coords.extend((co, co + projected_dir))

                    self.direct_coords.append(tvdata['direct_co'])

                    self.proximity_coords.append(tvdata['proximity_co'])

                    if tvdata['intersection_co']:
                        self.intersection_coords.append(tvdata['intersection_co'])

                    if tvdata['plane_intersection_co']:
                        self.plane_intersection_coords.append(tvdata['plane_intersection_co'])

                    if tvdata['projected_plane_intersection_co']:
                        self.projected_plane_intersection_coords.append(tvdata['projected_plane_intersection_co'])
