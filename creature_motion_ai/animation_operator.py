"""Apply portable solver pose targets as a new Blender Action."""
import json
from pathlib import Path

import bpy
from bpy.props import StringProperty


class CMAI_OT_apply_pose_targets(bpy.types.Operator):
    bl_idname = "cmai.apply_pose_targets"
    bl_label = "Generate Animation Action"
    bl_description = "Create a new Action from normalized solver pose targets"

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != "ARMATURE":
            self.report({'ERROR'}, "Select an armature first")
            return {'CANCELLED'}
        path = Path(bpy.path.abspath(context.scene.cmai_motion_targets))
        if not path.is_file():
            self.report({'ERROR'}, "Pose-target JSON was not found")
            return {'CANCELLED'}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            frames = data.get("frames", [])
            action_name = data.get("action", "CreatureMotionAI_Action")
        except (OSError, ValueError) as exc:
            self.report({'ERROR'}, f"Invalid pose-target JSON: {exc}")
            return {'CANCELLED'}
        if not frames:
            self.report({'ERROR'}, "Pose-target JSON contains no frames")
            return {'CANCELLED'}
        action = bpy.data.actions.get(action_name) or bpy.data.actions.new(action_name)
        action.use_fake_user = True
        obj.animation_data_create()
        obj.animation_data.action = action
        keyed = 0
        for frame_data in frames:
            frame = int(frame_data["frame"])
            for target in frame_data.get("targets", []):
                bone = obj.pose.bones.get(target.get("bone", ""))
                if not bone:
                    continue
                bone.rotation_mode = "XYZ"
                if "rotation_z" in target:
                    bone.rotation_euler.z = float(target["rotation_z"])
                if "rotation_x" in target:
                    bone.rotation_euler.x = float(target["rotation_x"])
                if "rotation_y" in target:
                    bone.rotation_euler.y = float(target["rotation_y"])
                bone.keyframe_insert("rotation_euler", frame=frame)
                keyed += 1
        context.scene.frame_start = min(int(item["frame"]) for item in frames)
        context.scene.frame_end = max(int(item["frame"]) for item in frames)
        self.report({'INFO'}, f"Created {action.name} with {keyed} pose targets")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(CMAI_OT_apply_pose_targets)
    bpy.types.Scene.cmai_motion_targets = StringProperty(
        name="Pose Targets", subtype='FILE_PATH', default="//data/motion/pose_targets.json"
    )


def unregister():
    del bpy.types.Scene.cmai_motion_targets
    bpy.utils.unregister_class(CMAI_OT_apply_pose_targets)
