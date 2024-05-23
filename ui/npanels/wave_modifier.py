import bpy
from bpy.types import (PropertyGroup,
                       Panel)
class WavePanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WaveHelper'

    @classmethod
    def poll(cls, context) -> bool:
        obj = context.object
        mod = obj and obj.modifiers.active
        wave = mod and (mod.type == 'WAVE')
        return wave

    @property
    def is_out(self) -> bool:
        """是向外扩散模式的布尔值

        Returns:
            bool: _description_
        """
        return self.prop.direction == 'out'

    @property
    def prop(self):
        """物体自定义属性

        Returns:
            _type_: _description_
        """
        obj = bpy.context.object
        return obj.wave_modifiers_helper

    @property
    def mod(self) -> 'bpy.types.WaveModifier':
        """活动波修改器

        Returns:
            bpy.types.WaveModifier: _description_
        """
        obj = bpy.context.object
        return obj.modifiers.active


class WaveSet(WavePanel, Panel):
    bl_idname = 'M4N1_PT_wave_set_modifier'
    bl_label = """WaveHelper"""

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        mod = self.mod
        prop = self.prop

        col = layout.column()

        row = col.row(align=True, heading='Motion')
        row.prop(mod, 'use_x', expand=True, toggle=1)
        row.prop(mod, 'use_y', expand=True, toggle=1)

        col.prop(mod, 'use_cyclic')

        row = col.row(align=False, heading='Along Normals')
        row.prop(mod, 'use_normal', text='')

        row.prop(mod, 'use_normal_x', expand=True, toggle=1, text='X')
        row.prop(mod, 'use_normal_y', expand=True, toggle=1, text='Y')
        row.prop(mod, 'use_normal_z', expand=True, toggle=1, text='Z')

        col.prop(mod, 'falloff_radius', text='Falloff')
        col.prop(mod, 'height')

        row = col.row(align=True)
        row.prop(prop, 'width')
        row.prop(prop, 'width_use_high_precision',
                 icon='PREFERENCES',
                 icon_only=True)

        col.prop(prop, 'space')

        row = col.row()
        row.prop(prop, 'direction', expand=True)

        col.separator()

        col.prop_search(mod,
                        "vertex_group",
                        context.object,
                        "vertex_groups",
                        text="Vertex Groups")


class WaveAnimation(WavePanel, Panel):
    bl_idname = 'M4N1_PT_wave_animation'
    bl_label = 'Animation'
    bl_parent_id = WaveSet.bl_idname

    @property
    def stop_frame(self) -> int:
        """停止帧

        Returns:
            int: _description_
        """
        mod = self.mod
        return mod.time_offset + mod.damping_time + mod.lifetime

    @property
    def sum_frame(self) -> int:
        """总帧数，修改器运行时间

        Returns:
            int: _description_
        """
        mod = self.mod
        a = int((mod.lifetime + mod.damping_time) - mod.time_offset)

        if self.is_out:
            return a
        else:
            return self.prop.frame_stop

    @property
    def frame_end(self) -> int:
        """帧结束时间

        Returns:
            int: _description_
        """
        if self.is_out:
            return self.prop.frame_end
        else:
            return self.prop.frame_stop

    @property
    def frame_start(self) -> int:
        """帧开始时间

        Returns:
            int: _description_
        """
        if self.is_out:
            return self.prop.frame_start
        else:
            return self.prop.frame_zero

    def draw_text(self, layout: bpy.types.UILayout):
        """绘制时间帧相关信息

        Args:
            layout (bpy.types.UILayout): _description_
        """
        scene = bpy.context.scene

        if self.prop.cycle:
            layout.label(
                text=f'Total frame count for looping:  {scene.frame_end - scene.frame_start}')
        else:
            layout.label(text=f'Total frame count for motion:{round(self.sum_frame, 2)}')

            layout.label(
                text=f'{"Frame Start" if self.is_out else "Frame Zero"}:{self.frame_start}')
            layout.label(
                text=f'{"Frame End" if self.is_out else "Frame Stop"}:{self.frame_end}')

            layout.label(text=f'Full stop frame:{round(self.stop_frame, 2)}')

    def draw(self, context):
        """主绘制

        Args:
            context (_type_): _description_
        """
        layout = self.layout
        layout.use_property_split = True
        mod = self.mod
        prop = self.prop

        row = layout.row(align=True)

        row.prop(prop, 'frequency',
                 )
        row.prop(prop, 'cycle',
                 icon='FILE_REFRESH',
                 icon_only=True
                 )
        if prop.cycle:
            layout.prop(prop, 'offset',
                        )
            layout.separator()
            col = layout
        else:
            layout.separator()
            col = layout.column(align=True)
            if self.is_out:
                col.prop(prop, 'frame_start')
                col.prop(prop, 'frame_end')
            else:
                col.prop(prop, 'frame_zero')
                col.prop(prop, 'frame_stop')
            col.prop(mod, 'damping_time', text='Damping')
            col.separator()

        self.draw_text(col)
