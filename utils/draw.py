import bpy
from mathutils import Vector, Matrix, Quaternion
from math import sin, cos, pi
from typing import Tuple
import gpu
from gpu_extras.batch import batch_for_shader
import blf
from . wm import get_last_operators
from . registration import get_prefs, get_addon
from . ui import get_zoom_factor
from . tools import get_active_tool
from .. colors import red, green, blue, black, white, orange, normal, yellow

def get_builtin_shader_name(name, prefix='3D'):
    if bpy.app.version >= (4, 0, 0):
        return name
    else:
        return f"{prefix}_{name}"

def draw_point(co, mx=Matrix(), color=(1, 1, 1), size=6, alpha=1, xray=True, modal=True, screen=False):
    def draw():
        shader = gpu.shader.from_builtin(get_builtin_shader_name('UNIFORM_COLOR'))
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.point_size_set(size)

        batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co]})
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_points(coords, indices=None, mx=Matrix(), color=(1, 1, 1), size=6, alpha=1, xray=True, modal=True, screen=False):
    def draw():
        shader = gpu.shader.from_builtin(get_builtin_shader_name('UNIFORM_COLOR'))
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.point_size_set(size)

        if indices:
            if mx != Matrix():
                batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co for co in coords]}, indices=indices)
            else:
                batch = batch_for_shader(shader, 'POINTS', {"pos": coords}, indices=indices)

        else:
            if mx != Matrix():
                batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co for co in coords]})
            else:
                batch = batch_for_shader(shader, 'POINTS', {"pos": coords})

        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_line(coords, indices=None, mx=Matrix(), color=(1, 1, 1), alpha=1, width=1, xray=True, modal=True, screen=False):
    def draw():
        nonlocal indices

        if indices is None:
            indices = [(i, i + 1) for i in range(0, len(coords)) if i < len(coords) - 1]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_lines(coords, indices=None, mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True, screen=False):
    def draw():
        nonlocal indices

        if not indices:
            indices = [(i, i + 1) for i in range(0, len(coords), 2)]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_vector(vector, origin=Vector((0, 0, 0)), mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, fade=False, normal=False, xray=True, modal=True, screen=False):
    def draw():
        if normal:
            coords = [mx @ origin, mx @ origin + get_world_space_normal(vector, mx)]
        else:
            coords = [mx @ origin, mx @ origin + mx.to_3x3() @ vector]

        colors = ((*color, alpha), (*color, alpha / 10 if fade else alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": coords, "color": colors})
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_vectors(vectors, origins, mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, fade=False, normal=False, xray=True, modal=True, screen=False):
    def draw():
        coords = []
        colors = []

        for v, o in zip(vectors, origins):
            coords.append(mx @ o)

            if normal:
                coords.append(mx @ o + get_world_space_normal(v, mx))
            else:
                coords.append(mx @ o + mx.to_3x3() @ v)

            colors.extend([(*color, alpha), (*color, alpha / 10 if fade else alpha)])

        indices = [(i, i + 1) for i in range(0, len(coords), 2)]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": coords, "color": colors})
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_circle(loc=Vector(), rot=Quaternion(), radius=100, segments='AUTO', width=1, color=(1, 1, 1), alpha=1, xray=True, modal=True, screen=False):
    def draw():
        nonlocal segments

        if segments == 'AUTO':
            segments = max(int(radius), 16)

        else:
            segments = max(segments, 16)

        indices = [(i, i + 1) if i < segments - 1 else (i, 0) for i in range(segments)]

        coords = []

        for i in range(segments):

            theta = 2 * pi * i / segments

            x = radius * cos(theta)
            y = radius * sin(theta)

            coords.append(Vector((x, y, 0)))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        if len(loc) == 2:
            mx = Matrix()
            mx.col[3] = loc.resized(4)
            batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)

        else:
            mx = Matrix.LocRotScale(loc, rot, Vector.Fill(3, 1))
            batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)

        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_cross_3d(co, mx=Matrix(), color=(1, 1, 1), width=1, length=1, alpha=1, xray=True, modal=True):
    def draw():
        x = Vector((1, 0, 0))
        y = Vector((0, 1, 0))
        z = Vector((0, 0, 1))

        coords = [(co - x) * length, (co + x) * length,
                  (co - y) * length, (co + y) * length,
                  (co - z) * length, (co + z) * length]

        indices = [(0, 1), (2, 3), (4, 5)]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_tris(coords, indices=None, mx=Matrix(), color=(1, 1, 1), alpha=1, xray=True, modal=True):
    def draw():

        shader = gpu.shader.from_builtin(get_builtin_shader_name('UNIFORM_COLOR'))
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')

        if mx != Matrix():
            batch = batch_for_shader(shader, 'TRIS', {"pos": [mx @ co for co in coords]}, indices=indices)

        else:
            batch = batch_for_shader(shader, 'TRIS', {"pos": coords}, indices=indices)

        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_mesh_wire(batch, color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True):
    def draw():
        nonlocal batch
        coords, indices = batch

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        b = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
        b.draw(shader)

        del shader
        del b

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_bbox(bbox, mx=Matrix(), color=(1, 1, 1), corners=0, width=1, alpha=1, xray=True, modal=True):
    def draw():
        if corners:
            length = corners

            coords = [bbox[0], bbox[0] + (bbox[1] - bbox[0]) * length, bbox[0] + (bbox[3] - bbox[0]) * length, bbox[0] + (bbox[4] - bbox[0]) * length,
                      bbox[1], bbox[1] + (bbox[0] - bbox[1]) * length, bbox[1] + (bbox[2] - bbox[1]) * length, bbox[1] + (bbox[5] - bbox[1]) * length,
                      bbox[2], bbox[2] + (bbox[1] - bbox[2]) * length, bbox[2] + (bbox[3] - bbox[2]) * length, bbox[2] + (bbox[6] - bbox[2]) * length,
                      bbox[3], bbox[3] + (bbox[0] - bbox[3]) * length, bbox[3] + (bbox[2] - bbox[3]) * length, bbox[3] + (bbox[7] - bbox[3]) * length,
                      bbox[4], bbox[4] + (bbox[0] - bbox[4]) * length, bbox[4] + (bbox[5] - bbox[4]) * length, bbox[4] + (bbox[7] - bbox[4]) * length,
                      bbox[5], bbox[5] + (bbox[1] - bbox[5]) * length, bbox[5] + (bbox[4] - bbox[5]) * length, bbox[5] + (bbox[6] - bbox[5]) * length,
                      bbox[6], bbox[6] + (bbox[2] - bbox[6]) * length, bbox[6] + (bbox[5] - bbox[6]) * length, bbox[6] + (bbox[7] - bbox[6]) * length,
                      bbox[7], bbox[7] + (bbox[3] - bbox[7]) * length, bbox[7] + (bbox[4] - bbox[7]) * length, bbox[7] + (bbox[6] - bbox[7]) * length]

            indices = [(0, 1), (0, 2), (0, 3),
                       (4, 5), (4, 6), (4, 7),
                       (8, 9), (8, 10), (8, 11),
                       (12, 13), (12, 14), (12, 15),
                       (16, 17), (16, 18), (16, 19),
                       (20, 21), (20, 22), (20, 23),
                       (24, 25), (24, 26), (24, 27),
                       (28, 29), (28, 30), (28, 31)]

        else:
            coords = bbox
            indices = [(0, 1), (1, 2), (2, 3), (3, 0),
                       (4, 5), (5, 6), (6, 7), (7, 4),
                       (0, 4), (1, 5), (2, 6), (3, 7)]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_init(self, event):
    self.font_id = 1
    self.offset = 0

def get_text_dimensions(context, text='', size=12):
    scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

    font = 1
    fontsize = int(size * scale)

    blf.size(font, fontsize)
    return blf.dimensions(font, text)

def update_HUD_location(self, event, offsetx=20, offsety=20):
    self.HUD_x = event.mouse_x - self.region_offset_x + offsetx
    self.HUD_y = event.mouse_y - self.region_offset_y + offsety

def draw_label(context, title='', coords=None, offset=0, center=True, size=12, color=(1, 1, 1), alpha=1):
    if not coords:
        region = context.region
        width = region.width / 2
        height = region.height / 2
    else:
        width, height = coords

    scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

    font = 1
    fontsize = int(size * scale)

    blf.size(font, fontsize)
    blf.color(font, *color, alpha)

    if center:
        dims = blf.dimensions(font, title)
        blf.position(font, width - (dims[0] / 2), height - (offset * scale), 1)

    else:
        blf.position(font, width, height - (offset * scale), 1)

    blf.draw(font, title)

    return blf.dimensions(font, title)

def draw_fading_label(context, text='', x=None, y=100, gap=18, center=True, size=12, color=(1, 1, 1), alpha=1, move_y=0, time=5, delay=1, cancel=''):
    scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

    if x is None:
        x = (context.region.width / 2)

    if isinstance(text, list):

        coords = (x, y + gap * (len(text) - 1) * scale)

        for idx, t in enumerate(text):
            line_coords = (coords[0], coords[1] - (idx * gap * scale))
            line_color = color if isinstance(color, tuple) else color[idx if idx < len(color) else len(color) - 1]
            line_alpha = alpha if (isinstance(alpha, int) or isinstance(alpha, float)) else alpha[idx if idx < len(alpha) else len(alpha) - 1]
            line_move = int(move_y + (idx * gap)) if move_y > 0 else 0
            line_time = time + idx * delay
            
            bpy.ops.m4n1.draw_label(text=t, coords=line_coords, center=center, size=size, color=line_color, alpha=line_alpha, move_y=line_move, time=line_time, cancel=cancel)

    else:
        coords = (x, y)

        bpy.ops.m4n1.draw_label(text=text, coords=coords, center=center, size=size, color=color, alpha=alpha, move_y=move_y, time=time, cancel=cancel)

def draw_split_row(self, layout, prop='prop', text='', label='Label', factor=0.2, align=True, toggle=True, expand=True, info=None, warning=None):
    row = layout.row(align=align)
    split = row.split(factor=factor, align=align)
    
    text = text if text else str(getattr(self, prop)) if str(getattr(self, prop)) in ['True', 'False'] else ''
    split.prop(self, prop, text=text, toggle=toggle, expand=expand)

    if label:
        split.label(text=label)

    if info:
        split.label(text=info, icon='INFO')

    if warning:
        split.label(text=warning, icon='ERROR')

    return row

hypercursor = None

def draw_axes_HUD(context, objects):
    global hypercursor
    
    if hypercursor is None:
        hypercursor = get_addon('HyperCursor')[0]

    if context.space_data.overlay.show_overlays:
        m3 = context.scene.M4

        size = m3.draw_axes_size
        alpha = m3.draw_axes_alpha

        screenspace = m3.draw_axes_screenspace
        scale = context.preferences.system.ui_scale

        show_cursor = context.space_data.overlay.show_cursor
        show_hyper_cursor = hypercursor and get_active_tool(context).idname in ['m4n1.tool_hyper_cursor', 'm4n1.tool_hyper_cursor_simple'] and context.scene.HC.show_gizmos

        axes = [(Vector((1, 0, 0)), red), (Vector((0, 1, 0)), green), (Vector((0, 0, 1)), blue)]

        for axis, color in axes:
            coords = []

            for obj in objects:

                if obj == 'CURSOR':

                    if not show_hyper_cursor:
                        mx = context.scene.cursor.matrix
                        rot = mx.to_quaternion()
                        origin = mx.to_translation()

                        factor = get_zoom_factor(context, origin, scale=300, ignore_obj_scale=True) if screenspace else 1

                        if show_cursor and screenspace:
                            coords.append(origin + (rot @ axis).normalized() * 0.1 * scale * factor * 0.8)
                            coords.append(origin + (rot @ axis).normalized() * 0.1 * scale * factor * 1.2)

                        else:
                            coords.append(origin + (rot @ axis).normalized() * size * scale * factor * 0.9)
                            coords.append(origin + (rot @ axis).normalized() * size * scale * factor)

                            coords.append(origin + (rot @ axis).normalized() * size * scale * factor * 0.1)
                            coords.append(origin + (rot @ axis).normalized() * size * scale * factor * 0.7)

                elif str(obj) != '<bpy_struct, Object invalid>':
                    mx = obj.matrix_world
                    rot = mx.to_quaternion()
                    origin = mx.to_translation()

                    factor = get_zoom_factor(context, origin, scale=300, ignore_obj_scale=True) if screenspace else 1

                    coords.append(origin + (rot @ axis).normalized() * size * scale * factor * 0.1)
                    coords.append(origin + (rot @ axis).normalized() * size * scale * factor)

            if coords:
                indices = [(i, i + 1) for i in range(0, len(coords), 2)]

                gpu.state.depth_test_set('NONE')
                gpu.state.blend_set('ALPHA')

                shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
                shader.uniform_float("color", (*color, alpha))
                shader.uniform_float("lineWidth", 2)
                shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
                shader.bind()

                batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
                batch.draw(shader)

def draw_focus_HUD(context, color=(1, 1, 1), alpha=1, width=2):
    if context.space_data.overlay.show_overlays:
        region = context.region
        view = context.space_data
        bprefs = context.preferences

        if view.local_view:
            region_overlap = bprefs.system.use_region_overlap
            header_alpha = bprefs.themes['Default'].view_3d.space.header[3]

            top_header = [r for r in context.area.regions if r.type == 'HEADER' and r.alignment == 'TOP']
            top_tool_header = [r for r in context.area.regions if r.type == 'TOOL_HEADER' and r.alignment == 'TOP']

            coords = [(width, width), (region.width - width, width), (region.width - width, region.height - width), (width, region.height - width)]
            indices =[(0, 1), (1, 2), (2, 3), (3, 0)]

            shader = gpu.shader.from_builtin(get_builtin_shader_name('UNIFORM_COLOR', '2D'))
            shader.bind()
            shader.uniform_float("color", (*color, alpha / 4))

            gpu.state.depth_test_set('NONE')
            gpu.state.blend_set('ALPHA' if (alpha / 4) < 1 else 'NONE')
            gpu.state.line_width_set(width)

            batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
            batch.draw(shader)

            scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

            offset_y = 5 * scale

            if region_overlap:

                if top_header and header_alpha < 1:
                    offset_y += top_header[0].height

                if top_tool_header:
                    offset_y += top_tool_header[0].height

            text = f"Focus Level: {len(context.scene.M4.focus_history)}"

            font = 1
            fontsize = int(12 * scale)

            dims = blf.dimensions(font, text)

            blf.size(font, fontsize)
            blf.color(font, *color, alpha)
            blf.position(font, (region.width / 2) - (blf.dimensions(font, text)[0] / 2), region.height - offset_y - fontsize, 0)

            blf.draw(font, text)

def draw_surface_slide_HUD(context, color=(1, 1, 1), alpha=1, width=2):
    if context.space_data.overlay.show_overlays:
        region = context.region
        bprefs = context.preferences

        region_overlap = bprefs.system.use_region_overlap
        header_alpha = bprefs.themes['Default'].view_3d.space.header[3]

        bottom_header = [r for r in context.area.regions if r.type == 'HEADER' and r.alignment == 'BOTTOM']
        bottom_tool_header = [r for r in context.area.regions if r.type == 'TOOL_HEADER' and r.alignment == 'BOTTOM']

        scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale
        offset_y = 0

        if region_overlap:

            if bottom_header and header_alpha < 1:
                offset_y += bottom_header[0].height

            if bottom_tool_header:
                offset_y += bottom_tool_header[0].height

        text = "Surface Sliding"

        font = 1
        fontsize = int(12 * scale)

        blf.size(font, fontsize)
        blf.color(font, *color, alpha)
        blf.position(font, (region.width / 2) - (blf.dimensions(font, text)[0] / 2), 0 + offset_y + int(fontsize), 0)

        blf.draw(font, text)

def draw_screen_cast_HUD(context):
    bprefs = context.preferences

    region_overlap = bprefs.system.use_region_overlap
    header_alpha = bprefs.themes['Default'].view_3d.space.header[3]

    p = get_prefs()
    operators = get_last_operators(context, debug=False)[-p.screencast_operator_count:]

    font = 0
    scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

    tools = [r for r in context.area.regions if r.type == 'TOOLS']
    offset_x = tools[0].width if tools else 0

    offset_x += (7 if p.screencast_show_addon else 15) * scale

    redo = [r for r in context.area.regions if r.type == 'HUD' and r.y]
    bottom_header = [r for r in context.area.regions if r.type == 'HEADER' and r.alignment == 'BOTTOM']
    bottom_tool_header = [r for r in context.area.regions if r.type == 'TOOL_HEADER' and r.alignment == 'BOTTOM']

    offset_y = 20 * scale

    if redo:
        offset_y += redo[0].height

    if region_overlap:
        if bottom_header and header_alpha < 1:
            offset_y += bottom_header[0].height

        if bottom_tool_header:
            offset_y += bottom_tool_header[0].height

    emphasize = 1.25

    if p.screencast_show_addon:
        blf.size(font, round(p.screencast_fontsize * scale * emphasize))
        addon_offset_x = blf.dimensions(font, 'MM')[0]
    else:
        addon_offset_x = 0

    y = 0
    hgap = 10

    for idx, (addon, label, idname, prop) in enumerate(reversed(operators)):
        size = round(p.screencast_fontsize * scale * (emphasize if idx == 0 else 1))
        vgap = round(size / 2)

        color = green if idname.startswith('m4n1.') and p.screencast_highlight_m4n1 else white
        alpha = (len(operators) - idx) / len(operators)

        if idx == 0:
            blf.enable(font, blf.SHADOW)

            blf.shadow_offset(font, 3, -3)
            blf.shadow(font, 5, *black, 1.0)

        text = f"{label}: {prop}" if prop else label

        x = offset_x + addon_offset_x
        y = offset_y if idx == 0 else y + (blf.dimensions(font, text)[1] + vgap)

        blf.size(font, size)
        blf.color(font, *color, alpha)
        blf.position(font, x, y, 0)

        blf.draw(font, text)

        if p.screencast_show_idname:
            x += blf.dimensions(font, text)[0] + hgap

            blf.size(font, size - 2)
            blf.color(font, *color, alpha * 0.3)
            blf.position(font, x, y, 0)

            blf.draw(font, f"{idname}")

            blf.size(font, size)

        if idx == 0:
            blf.disable(font, blf.SHADOW)

        if addon and p.screencast_show_addon:
            blf.size(font, size)

            x = offset_x + addon_offset_x - blf.dimensions(font, addon)[0] - (hgap / 2)

            blf.color(font, *white, alpha * 0.3)
            blf.position(font, x, y, 0)

            blf.draw(font, addon)

        if idx == 0:
            y += blf.dimensions(font, text)[1]

def draw_group_poses_VIEW3D(pose, batches, alpha):
    color = orange if pose.batch and pose.batchlinked else green if pose.name == 'Inception' else yellow if pose.name == 'LegacyPose' else blue

    for batch in batches:

        if isinstance(batch[0], Matrix):
            mx, length = batch
            draw_cross_3d(Vector(), mx=mx, length=length, color=normal)

        else:
            draw_mesh_wire(batch, color=color, alpha=alpha)
