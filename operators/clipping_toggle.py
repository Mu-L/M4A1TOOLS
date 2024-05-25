import bpy
from bpy.props import FloatProperty, BoolProperty, EnumProperty
from .. utils.draw import draw_fading_label, get_text_dimensions
from .. utils.property import step_enum
from .. utils.registration import get_prefs
from .. colors import white, yellow, green, red

state_items = [("MIN", "Minimum", ""),
               ("MED", "Medium", ""),
               ("MAX", "Maximum", "")]

class ClippingToggle(bpy.types.Operator):
    bl_idname = "m4a1.clipping_toggle"
    bl_label = "M4A1: Clipping Toggle"
    bl_options = {'REGISTER', 'UNDO'}

    def update_clip_start_maximum(self, context):
        if self.avoid_item_update:
            self.avoid_item_update = False
            return

        bpy.context.space_data.clip_start = self.maximum
        self.avoid_state_update = True
        self.state = "MAX"
        self.avoid_execute = True

    def update_clip_start_medium(self, context):
        if self.avoid_item_update:
            self.avoid_item_update = False
            return

        bpy.context.space_data.clip_start = self.medium
        self.avoid_state_update = True
        self.state = "MED"
        self.avoid_execute = True

    def update_clip_start_minimum(self, context):
        if self.avoid_item_update:
            self.avoid_item_update = False
            return

        bpy.context.space_data.clip_start = self.minimum
        self.avoid_state_update = True
        self.state = "MIN"
        self.avoid_execute = True

    def update_state(self, context):
        if self.avoid_execute:
            self.avoid_execute = False
            return

        if self.avoid_state_update:
            self.avoid_state_update = False
            return

        view = bpy.context.space_data

        if self.state == "MIN":
            view.clip_start = self.minimum

        elif self.state == "MED":
            view.clip_start = self.medium

        elif self.state == "MAX":
            view.clip_start = self.maximum

        self.avoid_execute = True

    def update_reset(self, context):
        if not self.reset:
            return

        self.avoid_item_update = True
        self.maximum = 1
        self.avoid_item_update = True
        self.medium = 0.05
        self.avoid_item_update = True
        self.minimum = 0.001

        view = bpy.context.space_data

        if self.state == "MIN":
            view.clip_start = self.minimum

        elif self.state == "MED":
            view.clip_start = self.medium

        elif self.state == "MAX":
            view.clip_start = self.maximum

        self.reset = False
        self.avoid_execute = True

    minimum: FloatProperty(name="Minimum", default=0.001, min=0, precision=5, step=0.001, update=update_clip_start_minimum)
    medium: FloatProperty(name="Medium", default=0.05, min=0, precision=3, step=1, update=update_clip_start_medium)
    maximum: FloatProperty(name="Maximum", default=1, min=0, precision=2, step=10, update=update_clip_start_maximum)
    state: EnumProperty(name="Current State", items=state_items, default="MED", update=update_state)
    reset: BoolProperty(default=False, update=update_reset)
    avoid_execute: BoolProperty(default=False)
    avoid_state_update: BoolProperty(default=False)
    avoid_item_update: BoolProperty(default=False)
    def draw(self, context):
        layout = self.layout
        col = layout.column()

        view = bpy.context.space_data

        row = col.row(align=True)
        row.prop(self, "state", expand=True)
        row.prop(self, "reset", text="", icon="BLANK1", emboss=False)

        row = col.row(align=True)
        row.prop(self, "minimum", text="")
        row.prop(self, "medium", text="")
        row.prop(self, "maximum", text="")
        row.prop(self, "reset", text="", icon="LOOP_BACK")

        row = col.row(align=True)
        row.label(text="Current")
        row.label(text=str(round(view.clip_start, 6)))

    def execute(self, context):
        if self.avoid_execute:
            self.avoid_execute = False

        else:
            self.avoid_execute = True
            self.state = step_enum(self.state, state_items, 1, loop=True)

            view = bpy.context.space_data

            if self.state == "MIN":
                view.clip_start = self.minimum
                text, color = f"Minimum: {round(self.minimum, 6)} ", yellow
                x = (context.region.width / 2) - get_text_dimensions(context, text)[0] - (get_text_dimensions(context, f"Medium: {round(self.medium, 6)}")[0] / 2)

            elif self.state == "MED":
                view.clip_start = self.medium
                text, color = f"Medium: {round(self.medium, 6)}", green
                x = None

            elif self.state == "MAX":
                view.clip_start = self.maximum
                text, color = f" Maximum: {round(self.maximum, 6)}", red
                x = (context.region.width / 2) + (get_text_dimensions(context, f"Medium: {round(self.medium, 6)}")[0] / 2)

            draw_fading_label(context, text="Clip Start", y=125, center=True, color=white, alpha=0.5, time=get_prefs().HUD_fade_clipping_toggle * 0.8)
            draw_fading_label(context, text=text, x=x, center=self.state=='MED', color=color, time=get_prefs().HUD_fade_clipping_toggle)

        return {'FINISHED'}
