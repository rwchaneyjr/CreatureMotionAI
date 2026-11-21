"""Build a sparse, smoothly interpolated Action from user-selected pose extrema.

The user chooses frames after reviewing a reference video beside the current
animation. This module samples the existing rig Action at those frames; it does
not infer 3D joints or claim that image-space points have been solved.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import bpy
from bpy.props import StringProperty


def _all_fcurves(action):
    """Support both legacy Actions and Blender 4.4+ layered Actions."""
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    yield from bag.fcurves
    else:
        yield from action.fcurves


def _unique_action_name(name):
    base = name.strip() or "CMAI_ExtremaWaypoints"
    if base not in bpy.data.actions:
        return base
    index = 1
    while f"{base}_{index:03d}" in bpy.data.actions:
        index += 1
    return f"{base}_{index:03d}"


def create_extrema_action(scene, armature, frame_text, requested_name):
    """Sample the active Action at extrema frames and make a new sparse Action.

    Start/end frames are always included. Quaternion curves interpolate
    linearly (then Blender normalizes the rotation); other channels use
    auto-clamped Bezier interpolation to avoid overshoot.
    """
    if armature is None or armature.type != "ARMATURE":
        raise ValueError("Select an armature first")
    animation_data = armature.animation_data
    source = animation_data.action if animation_data else None
    if source is None:
        raise ValueError("The selected armature has no active Action")

    start = int(round(source.frame_range[0]))
    end = int(round(source.frame_range[1]))
    if end <= start:
        raise ValueError("The active Action has no usable frame range")

    frames = {start, end}
    for token in re.split(r"[,;\s]+", frame_text.strip()):
        if not token:
            continue
        try:
            frame = int(token)
        except ValueError as exc:
            raise ValueError(f"Invalid waypoint frame: {token!r}") from exc
        if frame < start or frame > end:
            raise ValueError(f"Waypoint {frame} is outside the Action range {start}–{end}")
        frames.add(frame)
    frames = sorted(frames)
    if len(frames) < 3:
        raise ValueError("Choose at least one interior minimum/maximum frame")

    old_frame = scene.frame_current
    old_action = source
    old_slot = getattr(animation_data, "action_slot", None)
    snapshots = {}
    try:
        for frame in frames:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            snapshots[frame] = {
                pose_bone.name: {
                    "location": pose_bone.location.copy(),
                    "rotation_mode": pose_bone.rotation_mode,
                    "rotation_euler": pose_bone.rotation_euler.copy(),
                    "rotation_quaternion": pose_bone.rotation_quaternion.copy(),
                    "rotation_axis_angle": tuple(pose_bone.rotation_axis_angle),
                    "scale": pose_bone.scale.copy(),
                }
                for pose_bone in armature.pose.bones
            }

        action = bpy.data.actions.new(_unique_action_name(requested_name))
        animation_data.action = action
        if getattr(action, "slots", None) and hasattr(animation_data, "action_slot"):
            animation_data.action_slot = action.slots[0]

        for frame in frames:
            scene.frame_set(frame)
            for pose_bone in armature.pose.bones:
                values = snapshots[frame][pose_bone.name]
                pose_bone.location = values["location"]
                pose_bone.rotation_mode = values["rotation_mode"]
                pose_bone.rotation_euler = values["rotation_euler"]
                pose_bone.rotation_quaternion = values["rotation_quaternion"]
                pose_bone.rotation_axis_angle = values["rotation_axis_angle"]
                pose_bone.scale = values["scale"]
                pose_bone.keyframe_insert("location", frame=frame, group=pose_bone.name)
                if pose_bone.rotation_mode == "QUATERNION":
                    pose_bone.keyframe_insert("rotation_quaternion", frame=frame, group=pose_bone.name)
                elif pose_bone.rotation_mode == "AXIS_ANGLE":
                    pose_bone.keyframe_insert("rotation_axis_angle", frame=frame, group=pose_bone.name)
                else:
                    pose_bone.keyframe_insert("rotation_euler", frame=frame, group=pose_bone.name)
                pose_bone.keyframe_insert("scale", frame=frame, group=pose_bone.name)

        curves = list(_all_fcurves(action))
        for curve in curves:
            quaternion_curve = "rotation_quaternion" in curve.data_path
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR" if quaternion_curve else "BEZIER"
                if not quaternion_curve:
                    point.handle_left_type = "AUTO_CLAMPED"
                    point.handle_right_type = "AUTO_CLAMPED"
            curve.update()

        scene.frame_set(old_frame)
        bpy.context.view_layer.update()
        report = {
            "status": "CREATED",
            "armature": armature.name,
            "source_action": old_action.name,
            "new_action": action.name,
            "source_action_preserved": old_action.name in bpy.data.actions,
            "source_frame_range": [start, end],
            "waypoint_frames": frames,
            "pose_bone_count": len(armature.pose.bones),
            "fcurve_count": len(curves),
            "interpolation": {
                "quaternion": "LINEAR",
                "other_channels": "BEZIER_AUTO_CLAMPED",
            },
            "scope_note": "Samples an existing Action at user-selected extrema frames. It does not automatically detect or fit video landmarks.",
        }
        return report
    except Exception:
        animation_data.action = old_action
        if old_slot is not None and hasattr(animation_data, "action_slot"):
            animation_data.action_slot = old_slot
        scene.frame_set(old_frame)
        bpy.context.view_layer.update()
        raise


class CMAI_OT_create_extrema_action(bpy.types.Operator):
    bl_idname = "cmai.create_extrema_waypoint_action"
    bl_label = "Create Smoothed Action from Extrema"
    bl_description = "Sample the current Action at selected minimum/maximum pose frames and create a new smoothly interpolated Action"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        armature = context.active_object
        try:
            report = create_extrema_action(
                scene,
                armature,
                scene.cmai_extrema_frames,
                scene.cmai_extrema_action_name,
            )
            report_path = bpy.path.abspath(scene.cmai_extrema_report)
            if report_path:
                path = Path(report_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            self.report({"INFO"}, f"Created {report['new_action']} with {len(report['waypoint_frames'])} pose keys")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


_CLASSES = (CMAI_OT_create_extrema_action,)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cmai_extrema_frames = StringProperty(
        name="Extrema frames",
        description="Comma-separated minimum/maximum pose frames; Action endpoints are included automatically",
        default="25, 49, 73",
    )
    bpy.types.Scene.cmai_extrema_action_name = StringProperty(
        name="New Action name", default="CMAI_ExtremaWaypoints"
    )
    bpy.types.Scene.cmai_extrema_report = StringProperty(
        name="Report path", subtype="FILE_PATH", default="//cmai_extrema_waypoint_report.json"
    )


def unregister():
    for name in ("cmai_extrema_report", "cmai_extrema_action_name", "cmai_extrema_frames"):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
