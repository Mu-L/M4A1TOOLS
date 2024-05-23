def old_modifier(self, context):
    layout = self.layout

    layout.operator_menu_enum("object.modifier_add", "type")
    layout.template_modifiers()