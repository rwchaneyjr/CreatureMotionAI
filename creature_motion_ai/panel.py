import bpy


class CMAI_PT_main(bpy.types.Panel):
    bl_label = "Creature Motion AI"
    bl_idname = "CMAI_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Creature Motion AI"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        box = layout.box()
        box.label(text="Milestone 1: Video Preparation")
        box.prop(scene, "cmai_video")
        box.prop(scene, "cmai_output")
        box.prop(scene, "cmai_python")
        row = box.row(align=True)
        row.prop(scene, "cmai_start")
        row.prop(scene, "cmai_end")
        box.operator("cmai.extract_frames", icon='RENDER_ANIMATION')
        layout.separator()
        layout.label(text="Later milestones", icon='INFO')
        for label in ("Run AI Tracking", "Map Bones", "Generate Animation", "Export FBX", "Export GLB"):
            op = layout.operator("cmai.not_ready", text=label)
            op.message = f"{label} is planned for a later milestone."


def register():
    bpy.utils.register_class(CMAI_PT_main)


def unregister():
    bpy.utils.unregister_class(CMAI_PT_main)

