import os

import bpy
from bpy.props import StringProperty

from .skeleton import write_profile


class CMAI_OT_inspect_armature(bpy.types.Operator):
    bl_idname = "cmai.inspect_armature"
    bl_label = "Inspect Armature"
    bl_description = "Write a creature-independent skeleton profile for the selected armature"

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != "ARMATURE":
            obj = next((item for item in context.scene.objects if item.type == "ARMATURE"), None)
        if not obj:
            self.report({'ERROR'}, "Select or open an armature first")
            return {'CANCELLED'}
        output = bpy.path.abspath(context.scene.cmai_profile_output)
        if not output:
            self.report({'ERROR'}, "Choose a profile output path")
            return {'CANCELLED'}
        try:
            path = write_profile(obj, output)
        except OSError as exc:
            self.report({'ERROR'}, f"Could not write profile: {exc}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Wrote {len(obj.data.bones)} bones to {os.path.basename(path)}")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(CMAI_OT_inspect_armature)
    bpy.types.Scene.cmai_profile_output = StringProperty(
        name="Skeleton Profile", subtype='FILE_PATH', default="//data/profiles/skeleton.json"
    )


def unregister():
    del bpy.types.Scene.cmai_profile_output
    bpy.utils.unregister_class(CMAI_OT_inspect_armature)
