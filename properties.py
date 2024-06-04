import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty, CollectionProperty, PointerProperty, EnumProperty, FloatProperty, FloatVectorProperty
from mathutils import Matrix
import bmesh
from . utils.math import flatten_matrix
from . utils.world import get_world_output
from . utils.system import abspath
from . utils.registration import get_addon, get_prefs, get_addon_prefs
from . utils.tools import get_active_tool
from . utils.light import adjust_lights_for_rendering, get_area_light_poll
from . utils.view import sync_light_visibility
from . utils.material import adjust_bevel_shader
from . utils.ui import force_ui_update
from . utils.group import get_group_hierarchy, get_batch_pose_name, process_group_poses, propagate_pose_preview_alpha
from . items import eevee_preset_items, align_mode_items, render_engine_items, cycles_device_items, driver_limit_items, axis_items, driver_transform_items, driver_space_items, bc_orientation_items, shading_light_items, compositor_items

decalmachine = None
from .utils.simple_deform_helper import GizmoUtils
class SimpleDeformGizmoObjectPropertyGroup(bpy.types.PropertyGroup, GizmoUtils):
    def _limits_up(self, context):
        if self.active_modifier_is_simple_deform:
            self.modifier.limits[1] = self.up_limits

    up_limits: FloatProperty(name='up',
                             description='UP Limits(Red)',
                             default=1,
                             update=_limits_up,
                             max=1,
                             min=0)

    def _limits_down(self, context):
        if self.active_modifier_is_simple_deform:
            self.modifier.limits[0] = self.down_limits

    down_limits: FloatProperty(name='down',
                               description='Lower limit(Green)',
                               default=0,
                               update=_limits_down,
                               max=1,
                               min=0)

    origin_mode_items = (
        ('UP_LIMITS',
         'Follow Upper Limit(Red)',
         'Add an empty object origin as the rotation axis (if there is an origin, do not add it), and set the origin '
         'position as the upper limit during operation'),
        ('DOWN_LIMITS',
         'Follow Lower Limit(Green)',
         'Add an empty object origin as the rotation axis (if there is an origin, do not add it), and set the origin '
         'position as the lower limit during operation'),
        ('LIMITS_MIDDLE',
         'Middle',
         'Add an empty object origin as the rotation axis (if there is an origin, do not add it), and set the '
         'origin position between the upper and lower limits during operation'),
        ('MIDDLE',
         'Bound Middle',
         'Add an empty object origin as the rotation axis (if there is an origin, do not add it), and set the origin '
         'position as the position between the bounding boxes during operation'),
        ('NOT', 'No origin operation', ''),
    )

    origin_mode: EnumProperty(name='Origin control mode',
                              default='NOT',
                              items=origin_mode_items)

class ModifierProper(bpy.types.PropertyGroup):

    @property
    def sum_frame(self) -> int:
        mod = self.mod
        a = int(mod.lifetime + mod.damping_time)

        if self.is_out:
            return a
        else:
            return self.frame_stop

    @property
    def mod(self) -> bpy.types.WaveModifier:
        obj = bpy.context.object
        if not obj:
            return
        mod = obj.modifiers.active
        return mod

    @property
    def is_out(self):
        return self.direction == 'out'

    @property
    def factor(self) -> float:
        if self.width_use_high_precision:
            import math
            return math.e
        return 2

    def set_wave(self, context: 'bpy.context'):
        """
        TODO 设置时间帧内波次数

        # 启动

        宽度
        窄度值大于 2/宽

        """

        mod = self.mod
        mod.narrowness = (self.factor * 2) / self.width
        mod.width = (self.space + self.width) / 2

        self.set_speed(context)

    @property
    def start_frame(self):
        """获取开始帧

        Returns:
            _type_: _description_
        """
        if self.is_out:
            return self.frame_start
        else:
            return 0

    @property
    def end_frame(self):
        """获取结束帧

        Returns:
            _type_: _description_
        """
        if self.is_out:
            return self.frame_end
        else:
            return bpy.context.scene.frame_end

    def set_speed(self, context: 'bpy.context'):
        """设置速度

        Args:
            context (bpy.context): _description_
        """
        mod = self.mod

        if self.is_out:
            mod.time_offset = self.frame_start + int(self.mod.width)
            mod.lifetime = self.frame_end - mod.time_offset
        else:
            mod.time_offset = self.frame_stop
            mod.lifetime = (self.frame_zero - self.frame_stop)
            mod.damping_time = self.frame_stop - self.frame_zero

        scene = context.scene

        speed = ((mod.width * 2.0) /
                 ((scene.frame_end - scene.frame_start) + 1.0))
        mod.speed = speed * self.frequency

        if not self.is_out:
            mod.speed *= -1

    def update_cycle(self, context):
        """设置循环

        Args:
            context (_type_): _description_
        """
        if self.cycle:
            frame = context.scene.frame_end - context.scene.frame_start
            value = (114 if not self.is_out else -514)
            self.mod.time_offset = frame * value
            self.mod.lifetime = self.mod.damping_time = 0

            self.mod.time_offset += self.offset

    def set_modifier_prop(self, context):
        """设置修改器属性
        如果活动修改器是波则修改值"""
        obj = bpy.context.active_object
        mod = (obj and obj.modifiers.active)
        typ = (mod and (mod.type == 'WAVE'))
        if typ:
            self.set_wave(context)
            self.update_cycle(context)

    offset: IntProperty(name='Offset',
                        default=0,
                        update=set_modifier_prop,
                        )

    cycle: BoolProperty(name='Set loop animation',
                        update=set_modifier_prop,
                        )

    width: FloatProperty(name='Width',
                         description='Width of each wave',
                         update=set_modifier_prop,
                         default=1,
                         min=0.01
                         )

    width_use_high_precision: BoolProperty(name='High precision',
                                           update=set_modifier_prop,
                                           default=False,
                                           )

    space: FloatProperty(name='Wave spacing',
                         description='The spacing between each wave',
                         update=set_modifier_prop,
                         min=0,
                         )
    frequency: IntProperty(name='Frequency',
                           description='In one second, the number of oscillations of particles, directly expressed as the reciprocal of the period',
                           update=set_modifier_prop,
                           default=10,
                           min=1,
                           )

    direction: EnumProperty(name='Direction',
                            items=[('out', 'Diffusion', ''),
                                   ('in', 'Shrink', ''),
                                   ],
                            update=set_modifier_prop,
                            )

    frame_end: IntProperty(name='Frame End',
                           update=set_modifier_prop,
                           default=100)
    frame_start: IntProperty(name='Frame Start',
                             update=set_modifier_prop,
                             default=0)

    def get_zero(self):
        if 'zero' in self:
            return self['zero']
        return 5

    def set_zero(self, value):
        self['zero'] = value
        if value >= self.frame_stop:
            self.frame_stop = self.frame_zero + 1

    frame_zero: IntProperty(name='Frame Zero',
                            update=set_modifier_prop,
                            get=get_zero,
                            set=set_zero,
                            default=10,
                            )

    def get_stop(self):
        if 'stop' in self:
            return self['stop']
        return 10

    def set_stop(self, value):
        self['stop'] = value
        print(self.frame_zero, value)
        if self.frame_zero >= value:
            self.frame_zero = value - 1

    frame_stop: IntProperty(name='Frame Stop',
                            update=set_modifier_prop,
                            get=get_stop,
                            set=set_stop,
                            )

class Mirror_Settings(bpy.types.PropertyGroup):
    mirror_method: bpy.props.EnumProperty(
        name=("Mirror method"),
        description=(
            "When left and right are symmetrical, the nearest point effect is better; when they are not symmetrical, use face interpolation."),
        items=(("NEAREST", "Nearest", "Nearest vertex"),
               ("POLYINTERP_NEAREST", "Polyinterp", "Nearest face interpolation"),
               ))
    left_right: bpy.props.EnumProperty(
        name="Mirror direction",
        description="Select mirror direction",
        items=(("-x", "", "(-x arrow<-) Use the weight on the right side +x -> -x", 'BACK', 1),
               ("+x", "", "(+x arrow->) Use the weight on the left side -x -> +x", 'FORWARD', 2),
               )

    )
    # 此处图标名'FILE_TICK'和'FILE_NEW'应替换为有效的Blender图标名称
    is_center: bpy.props.BoolProperty(name='Symmetric',
                                      description="When enabled, make the middle bone symmetrical weight; when disabled, mirror the weight between the left and right bones.")

    is_multiple: bpy.props.BoolProperty(name='Multiple vertex groups',
                                        description="Mirror or symmetrize multiple vertex groups.")
    is_selected: bpy.props.BoolProperty(name='Selected',default=False,
                                        description="Mirror or symmetrize selected vertex groups (selected bones, in weight paint mode)")


class AppendMatsCollection(bpy.types.PropertyGroup):
    name: StringProperty()

class HistoryObjectsCollection(bpy.types.PropertyGroup):
    name: StringProperty()
    obj: PointerProperty(name="History Object", type=bpy.types.Object)

class HistoryUnmirroredCollection(bpy.types.PropertyGroup):
    name: StringProperty()
    obj: PointerProperty(name="History Unmirror", type=bpy.types.Object)

class HistoryEpochCollection(bpy.types.PropertyGroup):
    name: StringProperty()
    objects: CollectionProperty(type=HistoryObjectsCollection)
    unmirrored: CollectionProperty(type=HistoryUnmirroredCollection)

class GroupPoseCollection(bpy.types.PropertyGroup):
    def update_name(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        empty = active if (active := context.active_object) and active.type == 'EMPTY' and active.M4.is_group_empty else None

        if empty:
            is_batch = self.batch

            if is_batch:

                group_empties = get_group_hierarchy(empty, up=True)
                other_empties = [obj for obj in group_empties if obj != empty]

                skip_get_batch_pose_name = False

                if self.name.strip():
                    pose_name = self.name.strip()

                    if pose_name == 'Inception':

                        matching_empties = [e for e in group_empties if any(p.uuid == self.uuid for p in e.M4.group_pose_COL)]

                        if any(p.uuid == '00000000-0000-0000-0000-000000000000' for e in matching_empties for p in e.M4.group_pose_COL):

                            self.avoid_update = True
                            self.name = 'BatchPose'
                            pose_name = 'BatchPose'

                        else:
                            skip_get_batch_pose_name = True
                            name = 'Inception'

                            for e in matching_empties:
                                for p in e.M4.group_pose_COL:
                                    if p.axis:
                                        p.axis = ''

                else:
                    pose_name = 'BatchPose'

                if not skip_get_batch_pose_name:
                    name = get_batch_pose_name(other_empties, basename=pose_name)

                empties = other_empties + [empty] if name != self.name else other_empties 

                for obj in empties:
                    for pose in obj.M4.group_pose_COL:
                        if pose.uuid == self.uuid:
                            pose.avoid_update = True
                            pose.name = name
                            break

            else:
                if not self.name.strip():
                    self.avoid_update = True
                    self.name = f"Pose.{str(self.index).zfill(3)}"

                elif self.name == 'Inception':
                    other_inception_pose = any(pose.uuid == '00000000-0000-0000-0000-000000000000' for pose in empty.M4.group_pose_COL)

                    if other_inception_pose:
                        self.avoid_update = True
                        self.name = f"Pose.{str(self.index).zfill(3)}"

                    else:
                        for pose in empty.M4.group_pose_COL:
                            if pose.axis:
                                pose.axis = ''

            process_group_poses(empty)

    name: StringProperty(update=update_name)
    index: IntProperty()

    mx: FloatVectorProperty(name="Group Pose Matrix", subtype="MATRIX", size=(4, 4))

    remove: BoolProperty(name="Remove Pose", default=False)
    axis: StringProperty()
    angle: FloatProperty()

    uuid: StringProperty()
    batch: BoolProperty(default=False)
    batchlinked: BoolProperty(name="Batch Pose", description="Toggle Connection to Other Batch Poses in this Group Hierarchy\n\nIf the active pose is disconnected, it will be retrieved like a regular single Pose.\nDisconnected Batch Poses in the Group Hierarchy below, will not be previewed, retrieved or removed, unless overriden in the Retrieve/Remove ops", default=True)
    avoid_update: BoolProperty()
    forced_preview_update: BoolProperty()

selected = []

class M4SceneProperties(bpy.types.PropertyGroup):

    control_move_offset : FloatProperty(name="Control Move Offset", default=0.1, max=1000, min=0.001)
    focus_history: CollectionProperty(type=HistoryEpochCollection)

    use_undo_save: BoolProperty(name="Use Undo Save", description="Save before Undoing\nBe warned, depending on your scene complexity, this can noticably affect your undo speed", default=False)
    use_redo_save: BoolProperty(name="Use Redo Save", description="Also save before first Operator Redos", default=False)

    def update_xray(self, context):
        x = (self.pass_through, self.show_edit_mesh_wire)
        shading = context.space_data.shading

        shading.show_xray = True if any(x) else False

        if self.show_edit_mesh_wire:
            shading.xray_alpha = 0.1

        elif self.pass_through:
            shading.xray_alpha = 1 if context.active_object and context.active_object.type == "MESH" else 0.5

    def update_uv_sync_select(self, context):
        ts = context.scene.tool_settings
        ts.use_uv_select_sync = self.uv_sync_select

        global selected
        active = context.active_object

        if ts.use_uv_select_sync:
            bpy.ops.mesh.select_all(action='DESELECT')

            bm = bmesh.from_edit_mesh(active.data)
            bm.normal_update()
            bm.verts.ensure_lookup_table()

            if selected:
                for v in bm.verts:
                    if v.index in selected:
                        v.select_set(True)

            bm.select_flush(True)

            bmesh.update_edit_mesh(active.data)

        else:
            bm = bmesh.from_edit_mesh(active.data)
            bm.normal_update()
            bm.verts.ensure_lookup_table()

            selected = [v.index for v in bm.verts if v.select]

            bpy.ops.mesh.select_all(action="SELECT")

            mode = tuple(ts.mesh_select_mode)

            if mode == (False, True, False):
                ts.uv_select_mode = "EDGE"

            else:
                ts.uv_select_mode = "VERTEX"

    pass_through: BoolProperty(name="Pass Through", default=False, update=update_xray)
    show_edit_mesh_wire: BoolProperty(name="Show Edit Mesh Wireframe", default=False, update=update_xray)
    uv_sync_select: BoolProperty(name="Sync Selection", default=False, update=update_uv_sync_select)
    def update_show_cavity(self, context):
        t = (self.show_cavity, self.show_curvature)
        shading = context.space_data.shading

        shading.show_cavity = True if any(t) else False

        if t == (True, True):
            shading.cavity_type = "BOTH"

        elif t == (True, False):
            shading.cavity_type = "WORLD"

        elif t == (False, True):
            shading.cavity_type = "SCREEN"

    show_cavity: BoolProperty(name="Cavity", default=True, update=update_show_cavity)
    show_curvature: BoolProperty(name="Curvature", default=False, update=update_show_cavity)

    def update_eevee_preset(self, context):
        eevee = context.scene.eevee
        shading = context.space_data.shading

        if self.eevee_preset == 'NONE':
            eevee.use_ssr = False
            eevee.use_gtao = False
            eevee.use_bloom = False
            eevee.use_volumetric_lights = False

            if self.eevee_preset_set_use_scene_lights:
                shading.use_scene_lights = False

            if self.eevee_preset_set_use_scene_world:
                shading.use_scene_world = False

            if context.scene.render.engine == 'BLENDER_EEVEE':
                if self.eevee_preset_set_use_scene_lights:
                    shading.use_scene_lights_render = False

                if self.eevee_preset_set_use_scene_world:
                    shading.use_scene_world_render = False

        elif self.eevee_preset == 'LOW':
            eevee.use_ssr = True
            eevee.use_ssr_halfres = True
            eevee.use_ssr_refraction = False
            eevee.use_gtao = True
            eevee.use_bloom = False
            eevee.use_volumetric_lights = False

            if self.eevee_preset_set_use_scene_lights:
                shading.use_scene_lights = True

            if self.eevee_preset_set_use_scene_world:
                shading.use_scene_world = False

            if context.scene.render.engine == 'BLENDER_EEVEE':
                if self.eevee_preset_set_use_scene_lights:
                    shading.use_scene_lights_render = True

                if self.eevee_preset_set_use_scene_world:
                    shading.use_scene_world_render = False

        elif self.eevee_preset == 'HIGH':
            eevee.use_ssr = True
            eevee.use_ssr_halfres = False
            eevee.use_ssr_refraction = True
            eevee.use_gtao = True
            eevee.use_bloom = True
            eevee.use_volumetric_lights = False

            if self.eevee_preset_set_use_scene_lights:
                shading.use_scene_lights = True

            if self.eevee_preset_set_use_scene_world:
                shading.use_scene_world = False

            if context.scene.render.engine == 'BLENDER_EEVEE':
                if self.eevee_preset_set_use_scene_lights:
                    shading.use_scene_lights_render = True

                if self.eevee_preset_set_use_scene_world:
                    shading.use_scene_world_render = False

        elif self.eevee_preset == 'ULTRA':
            eevee.use_ssr = True
            eevee.use_ssr_halfres = False
            eevee.use_ssr_refraction = True
            eevee.use_gtao = True
            eevee.use_bloom = True
            eevee.use_volumetric_lights = True

            if self.eevee_preset_set_use_scene_lights:
                shading.use_scene_lights = True

            if context.scene.render.engine == 'BLENDER_EEVEE':
                if self.eevee_preset_set_use_scene_lights:
                    shading.use_scene_lights_render = True

            if self.eevee_preset_set_use_scene_lights:
                world = context.scene.world
                if world:
                    shading.use_scene_world = True

                    if context.scene.render.engine == 'BLENDER_EEVEE':
                        shading.use_scene_world_render = True

                    output = get_world_output(world)
                    links = output.inputs[1].links

                    if not links:
                        tree = world.node_tree

                        volume = tree.nodes.new('ShaderNodeVolumePrincipled')
                        tree.links.new(volume.outputs[0], output.inputs[1])

                        volume.inputs[2].default_value = 0.1
                        volume.location = (-200, 200)

    def update_eevee_gtao_factor(self, context):
        context.scene.eevee.gtao_factor = self.eevee_gtao_factor

    def update_eevee_bloom_intensity(self, context):
        context.scene.eevee.bloom_intensity = self.eevee_bloom_intensity

    def update_render_engine(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        context.scene.render.engine = self.render_engine

        if get_prefs().activate_render and get_prefs().activate_shading_pie and get_prefs().render_adjust_lights_on_render and get_area_light_poll() and self.adjust_lights_on_render:
            last = self.adjust_lights_on_render_last

            debug = False

            if last in ['NONE', 'INCREASE'] and self.render_engine == 'CYCLES':
                self.adjust_lights_on_render_last = 'DECREASE'

                if debug:
                    print("decreasing on switch to cycies engine")

                adjust_lights_for_rendering(mode='DECREASE')

            elif last == 'DECREASE' and self.render_engine == 'BLENDER_EEVEE':
                self.adjust_lights_on_render_last = 'INCREASE'

                if debug:
                    print("increasing on switch to eevee engine")

                adjust_lights_for_rendering(mode='INCREASE')

        if get_prefs().activate_render and get_prefs().render_sync_light_visibility:
            sync_light_visibility(context.scene)

        if get_prefs().activate_render and get_prefs().activate_shading_pie and get_prefs().render_use_bevel_shader and self.use_bevel_shader:
            if context.scene.render.engine == 'CYCLES':
                adjust_bevel_shader(context)

    def update_cycles_device(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        context.scene.cycles.device = self.cycles_device

    def update_use_compositor(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        context.space_data.shading.use_compositor = self.use_compositor

    def update_shading_light(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        shading = context.space_data.shading
        shading.light = self.shading_light

        if self.use_flat_shadows:
            shading.show_shadows = shading.light == 'FLAT'

    def update_use_flat_shadows(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        shading = context.space_data.shading

        if shading.light == 'FLAT':
            shading.show_shadows = self.use_flat_shadows

    def update_custom_views_local(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.custom_views_local and self.custom_views_cursor:
            self.avoid_update = True
            self.custom_views_cursor = False

        context.space_data.overlay.show_ortho_grid = not self.custom_views_local

        if get_prefs().custom_views_use_trackball:
            context.preferences.inputs.view_rotate_method = 'TRACKBALL' if self.custom_views_local else 'TURNTABLE'

        if get_prefs().activate_transform_pie and get_prefs().custom_views_set_transform_preset:
            bpy.ops.m4a1.set_transform_preset(pivot='MEDIAN_POINT', orientation='LOCAL' if self.custom_views_local else 'GLOBAL')

    def update_custom_views_cursor(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.custom_views_cursor and self.custom_views_local:
            self.avoid_update = True
            self.custom_views_local = False

        context.space_data.overlay.show_ortho_grid = not self.custom_views_cursor

        if get_prefs().custom_views_use_trackball:
            context.preferences.inputs.view_rotate_method = 'TRACKBALL' if self.custom_views_cursor else 'TURNTABLE'

        if 'm4a1.tool_hyper_cursor' not in get_active_tool(context).idname:

            if get_prefs().activate_transform_pie and get_prefs().custom_views_set_transform_preset:
                bpy.ops.m4a1.set_transform_preset(pivot='CURSOR' if self.custom_views_cursor else 'MEDIAN_POINT', orientation='CURSOR' if self.custom_views_cursor else 'GLOBAL')

    def update_enforce_hide_render(self, context):
        from . ui.operators import shading

        for _, name in shading.render_visibility:
            obj = bpy.data.objects.get(name)

            if obj:
                obj.hide_set(obj.visible_get())

    def update_use_bevel_shader(self, context):
        adjust_bevel_shader(context)
                
    def update_bevel_shader(self, context):
        if self.use_bevel_shader:
            adjust_bevel_shader(context)

    eevee_preset: EnumProperty(name="Eevee Preset", description="Eevee Quality Presets", items=eevee_preset_items, default='NONE', update=update_eevee_preset)
    eevee_preset_set_use_scene_lights: BoolProperty(name="Set Use Scene Lights", description="Set Use Scene Lights when changing Eevee Preset", default=False)
    eevee_preset_set_use_scene_world: BoolProperty(name="Set Use Scene World", description="Set Use Scene World when changing Eevee Preset", default=False)
    eevee_gtao_factor: FloatProperty(name="Factor", default=1, min=0, step=0.1, update=update_eevee_gtao_factor)
    eevee_bloom_intensity: FloatProperty(name="Intensity", default=0.05, min=0, step=0.1, update=update_eevee_bloom_intensity)
    render_engine: EnumProperty(name="Render Engine", description="Render Engine", items=render_engine_items, default='BLENDER_EEVEE', update=update_render_engine)
    cycles_device: EnumProperty(name="Render Device", description="Render Device", items=cycles_device_items, default='CPU', update=update_cycles_device)
    use_compositor: EnumProperty(name="Use Viewport Compositing", description="Use Viewport Compositing", items=compositor_items, default='DISABLED', update=update_use_compositor)
    shading_light: EnumProperty(name="Lighting Method", description="Lighting Method for Solid/Texture Viewport Shading", items=shading_light_items, default='MATCAP', update=update_shading_light)
    use_flat_shadows: BoolProperty(name="Use Flat Shadows", description="Use Shadows when in Flat Lighting", default=True, update=update_use_flat_shadows)
    draw_axes_size: FloatProperty(name="Draw Axes Size", default=0.1, min=0)
    draw_axes_alpha: FloatProperty(name="Draw Axes Alpha", default=0.5, min=0, max=1)
    draw_axes_screenspace: BoolProperty(name="Draw Axes in Screen Space", default=True)
    draw_active_axes: BoolProperty(name="Draw Active Axes", description="Draw Active's Object Axes", default=False)
    draw_cursor_axes: BoolProperty(name="Draw Cursor Axes", description="Draw Cursor's Axes", default=False)
    adjust_lights_on_render: BoolProperty(name="Adjust Lights when Rendering", description="Adjust Lights Area Lights when Rendering, to better match Eevee and Cycles", default=False)
    adjust_lights_on_render_divider: FloatProperty(name="Divider used to calculate Cycles Light Strength from Eeeve Light Strength", default=4, min=1)
    adjust_lights_on_render_last: StringProperty(name="Last Light Adjustment", default='NONE')
    is_light_decreased_by_handler: BoolProperty(name="Have Lights been decreased by the init render handler?", default=False)
    enforce_hide_render: BoolProperty(name="Enforce hide_render setting when Viewport Rendering", description="Enfore hide_render setting for objects when Viewport Rendering", default=True, update=update_enforce_hide_render)
    use_bevel_shader: BoolProperty(name="Use Bevel Shader", description="Batch Apply Bevel Shader to visible Materials", default=False, update=update_use_bevel_shader)
    bevel_shader_use_dimensions: BoolProperty(name="Consider Object Dimensions for Bevel Radius Modulation", description="Consider Object Dimensions for Bevel Radius Modulation", default=True, update=update_bevel_shader)
    bevel_shader_samples: IntProperty(name="Samples", description="Bevel Shader Samples", default=16, min=2, max=32, update=update_bevel_shader)
    bevel_shader_radius: FloatProperty(name="Radius", description="Bevel Shader Global Radius", default=0.015, min=0, precision=3, step=0.01, update=update_bevel_shader)

    custom_views_local: BoolProperty(name="Custom Local Views", description="Use Custom Views, based on the active object's orientation", default=False, update=update_custom_views_local)
    custom_views_cursor: BoolProperty(name="Custom Cursor Views", description="Use Custom Views, based on the cursor's orientation", default=False, update=update_custom_views_cursor)

    align_mode: EnumProperty(name="Align Mode", items=align_mode_items, default="VIEW")

    show_smart_drive: BoolProperty(name="Show Smart Drive")

    driver_start: FloatProperty(name="Driver Start Value", precision=3)
    driver_end: FloatProperty(name="Driver End Value", precision=3)
    driver_axis: EnumProperty(name="Driver Axis", items=axis_items, default='X')
    driver_transform: EnumProperty(name="Driver Transform", items=driver_transform_items, default='LOCATION')
    driver_space: EnumProperty(name="Driver Space", items=driver_space_items, default='AUTO')
    driven_start: FloatProperty(name="Driven Start Value", precision=3)
    driven_end: FloatProperty(name="Driven End Value", precision=3)
    driven_axis: EnumProperty(name="Driven Axis", items=axis_items, default='X')
    driven_transform: EnumProperty(name="Driven Transform", items=driver_transform_items, default='LOCATION')
    driven_limit: EnumProperty(name="Driven Lmit", items=driver_limit_items, default='BOTH')

    def update_unity_export_path(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        path = self.unity_export_path

        if path:
            if not path.endswith('.fbx'):
                path += '.fbx'

            self.avoid_update = True
            self.unity_export_path = abspath(path)

    show_unity: BoolProperty(name="Show Unity")

    unity_export: BoolProperty(name="Export to Unity", description="Enable to do the actual FBX export\nLeave it off to only prepare the Model")
    unity_export_path: StringProperty(name="Unity Export Path", subtype='FILE_PATH', update=update_unity_export_path)
    unity_triangulate: BoolProperty(name="Triangulate before exporting", description="Add Triangulate Modifier to the end of every object's stack", default=False)

    def update_bcorientation(self, context):
        bcprefs = get_addon_prefs('BoxCutter')

        if self.bcorientation == 'LOCAL':
            bcprefs.behavior.orient_method = 'LOCAL'
        elif self.bcorientation == 'NEAREST':
            bcprefs.behavior.orient_method = 'NEAREST'
        elif self.bcorientation == 'LONGEST':
            bcprefs.behavior.orient_method = 'TANGENT'

    bcorientation: EnumProperty(name="BoxCutter Orientation", items=bc_orientation_items, default='LOCAL', update=update_bcorientation)

    def update_group_select(self, context):
        if not self.group_select:
            all_empties = [obj for obj in context.selected_objects if obj.M4.is_group_empty]
            top_level = [obj for obj in all_empties if obj.parent not in all_empties]

            for obj in context.selected_objects:
                if obj not in top_level:
                    obj.select_set(False)

    def update_group_recursive_select(self, context):
        if not self.group_recursive_select:
            all_empties = [obj for obj in context.selected_objects if obj.M4.is_group_empty]
            top_level = [obj for obj in all_empties if obj.parent not in all_empties]

            for obj in context.selected_objects:
                if obj not in top_level:
                    obj.select_set(False)

    def update_group_hide(self, context):
        empties = [obj for obj in context.visible_objects if obj.M4.is_group_empty]

        for e in empties:
            if e == context.active_object or not context.scene.M4.group_hide:
                e.show_name = True
                e.empty_display_size = e.M4.group_size

            else:
                e.show_name = False

                if round(e.empty_display_size, 4) != 0.0001:
                    e.M4.group_size = e.empty_display_size

                e.empty_display_size = 0.0001

    def update_affect_only_group_origin(self, context):
        if self.affect_only_group_origin:
            context.scene.tool_settings.use_transform_skip_children = True
            self.group_select = False

        else:
            context.scene.tool_settings.use_transform_skip_children = False
            self.group_select = True

    show_group: BoolProperty(name="Show Group")
    show_group_gizmos: BoolProperty(name="Show Group Gizmos", description="Toggle Group Gizmos Globally", default=True)
    group_select: BoolProperty(name="Auto Select Groups", description="Automatically select the entire Group, when its Empty is made active", default=True, update=update_group_select)
    group_recursive_select: BoolProperty(name="Recursively Select Groups", description="Recursively select entire Group Hierarchies down", default=True, update=update_group_recursive_select)
    group_hide: BoolProperty(name="Hide Group Empties in 3D View", description="Hide Group Empties in 3D View to avoid Clutter", default=True, update=update_group_hide)
    show_group_select: BoolProperty(name="Show Auto Select Toggle in main Object Context Menu", default=True)
    show_group_recursive_select: BoolProperty(name="Show Recursive Selection Toggle in main Object Context Menu", default=True)
    show_group_hide: BoolProperty(name="Show Group Hide Toggle in main Object Context Menu", default=True)
    affect_only_group_origin: BoolProperty(name="Transform only the Group Origin(Empty)", description='Transform the Group Origin(Empty) only, disable Group Auto-Select and enable "affect Parents only"', default=False, update=update_affect_only_group_origin)
    def update_group_gizmo_size(self, context):
        force_ui_update(context)

    group_gizmo_size: FloatProperty(name="Global Group Gizmo Size", description="Global Group Gizmo Size", default=1, min=0.01, update=update_group_gizmo_size)

    show_assetbrowser_tools: BoolProperty(name="Show Assetbrowser Tools")
    asset_collect_path: StringProperty(name="Collect Path", subtype="DIR_PATH", default="")

    show_extrude: BoolProperty(name="Show Extrude")

    avoid_update: BoolProperty()
    # show_meshdeform_helper: BoolProperty(name="Meshdeform Helper")
    show_align_helper: BoolProperty(name="Align Helper")
    show_wave_modifier: BoolProperty(name="Wave Modifier")
    show_control_move: BoolProperty(name="Show Control Move Panel")

class M4ObjectProperties(bpy.types.PropertyGroup):
    unity_exported: BoolProperty(name="Exported to Unity")

    pre_unity_export_mx: FloatVectorProperty(name="Pre-Unity-Export Matrix", subtype="MATRIX", size=16, default=flatten_matrix(Matrix()))
    pre_unity_export_mesh: PointerProperty(name="Pre-Unity-Export Mesh", type=bpy.types.Mesh)
    pre_unity_export_armature: PointerProperty(name="Pre-Unity-Export Armature", type=bpy.types.Armature)

    is_group_empty: BoolProperty(name="is group empty", default=False)
    is_group_object: BoolProperty(name="is group object", default=False)
    group_size: FloatProperty(name="group empty size", default=0.2, min=0)

    def update_show_group_gizmo(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.update_show_group_gizmo and not any([self.show_group_x_rotation, self.show_group_y_rotation, self.show_group_z_rotation]):
            self.show_group_x_rotation = True

        force_ui_update(context)

    def update_show_rotation(self, context):
        if any([self.show_group_x_rotation, self.show_group_y_rotation, self.show_group_z_rotation]) and not self.show_group_gizmo:
            self.avoid_update = True
            self.show_group_gizmo = True

        if not any([self.show_group_x_rotation, self.show_group_y_rotation, self.show_group_z_rotation]) and self.show_group_gizmo:
            self.avoid_update = True
            self.show_group_gizmo = False

        force_ui_update(context)

    def update_group_gizmo_size(self, context):
        force_ui_update(context)

    show_group_gizmo: BoolProperty(name="show group gizmo", default=False, update=update_show_group_gizmo)
    show_group_x_rotation: BoolProperty(name="show X rotation gizmo", default=False, update=update_show_rotation)
    show_group_y_rotation: BoolProperty(name="show Y rotation gizmo", default=False, update=update_show_rotation)
    show_group_z_rotation: BoolProperty(name="show Z rotation gizmo", default=False, update=update_show_rotation)
    group_gizmo_size: FloatProperty(name="group gizmo size", default=1, min=0.1, update=update_group_gizmo_size)

    def update_group_pose_alpha(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        empty = self.id_data

        propagate_pose_preview_alpha(empty)

    group_rest_pose: FloatVectorProperty(name="Group Rest Post Matrix", subtype="MATRIX", size=(4, 4))  # NOTE: legacy as of verison 1.7, but keep it around for legacy updates
    group_pose_COL: CollectionProperty(type=GroupPoseCollection)
    group_pose_IDX: IntProperty(name="Pose Name", description="Double Click to Rename", default=-1)
    group_pose_alpha: FloatProperty(name="Pose Preview Alpha", description="Alpha used to preview Poses across the entire Group", min=0.01, max=1, default=0.5, step=0.1, update=update_group_pose_alpha)
    draw_active_group_pose: BoolProperty(description="Draw a Preview of the Active Pose")

    smooth_angle: FloatProperty(name="Smooth Angle", default=30)
    has_smoothed: BoolProperty(name="Has been smoothed", default=False)

    draw_axes: BoolProperty(name="Draw Axes", default=False)

    def update_bevel_shader_radius_mod(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        global decalmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if decalmachine:
            obj = self.id_data

            panel_children = [obj for obj in obj.children if obj.DM.decaltype == 'PANEL']

            for c in panel_children:
                c.M4.avoid_update = True
                c.M4.bevel_shader_radius_mod = obj.M4.bevel_shader_radius_mod

                if c.M4.bevel_shader_toggle != obj.M4.bevel_shader_toggle:
                    c.M4.avoid_update = True
                    c.M4.bevel_shader_toggle = obj.M4.bevel_shader_toggle

    bevel_shader_toggle: BoolProperty(name="Active Object Bevel Toggle", description="Toggle Bevel Shader on Active Object", default=True, update=update_bevel_shader_radius_mod)
    bevel_shader_radius_mod: FloatProperty(name="Active Object Bevel Radius Modulation", description="Factor to modulate the Bevel Shader Radius on the Active Object", default=1, min=0, precision=2, step=0.1, update=update_bevel_shader_radius_mod)
    bevel_shader_dimensions_mod: FloatProperty(name="Active Object Bevel Radius Modulation", description="Factor to modulate the Bevel Shader Radius on the Active Object", default=1, min=0, precision=2, step=0.1)

    dup_hash: StringProperty(description="Hash to find associated objects")

    avoid_update: BoolProperty()


