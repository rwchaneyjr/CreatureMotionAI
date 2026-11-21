"""Capture manually matched rig poses against actual reference-video frames.

This is a sparse, user-guided workflow: it does not claim to infer 3D motion
from pixels. The user displays a real video frame, adjusts the rig, and captures
the resulting pose at that frame number. A separate Action interpolates captures.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import bpy
from bpy.props import StringProperty


def _video_path(scene):
    raw = str(getattr(scene, "cmai_video", "") or "")
    return Path(bpy.path.abspath(raw)).resolve() if raw else None


def _video_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_name(video, armature):
    identity = f"{video.resolve()}|{armature.name}|{_video_sha256(video)}"
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    safe_rig = re.sub(r"[^A-Za-z0-9_]+", "_", armature.name)[:24]
    return f"CMAI_VideoPose_{safe_rig}_{suffix}"


def _read_waypoints(video, armature):
    text = bpy.data.texts.get(_text_name(video, armature))
    if not text:
        return {"schema": 1, "waypoints": [], "source_video": str(video), "armature": armature.name}
    try:
        data = json.loads(text.as_string())
        if data.get("schema") != 1 or not isinstance(data.get("waypoints"), list):
            raise ValueError("Unsupported video-pose waypoint data")
        return data
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Cannot read video-pose waypoint record: {exc}") from exc


def _write_waypoints(data, video, armature):
    name = _text_name(video, armature)
    text = bpy.data.texts.get(name) or bpy.data.texts.new(name)
    text.clear()
    text.write(json.dumps(data, indent=2))


def _pose_snapshot(armature):
    snapshot = {}
    for bone in armature.pose.bones:
        snapshot[bone.name] = {
            "location": list(bone.location),
            "rotation_mode": bone.rotation_mode,
            "rotation_euler": list(bone.rotation_euler),
            "rotation_quaternion": list(bone.rotation_quaternion),
            "rotation_axis_angle": list(bone.rotation_axis_angle),
            "scale": list(bone.scale),
        }
    return snapshot


def _unique_action_name(name):
    base = name.strip() or "CMAI_VideoGuided"
    if base not in bpy.data.actions:
        return base
    suffix = 1
    while f"{base}_{suffix:03d}" in bpy.data.actions:
        suffix += 1
    return f"{base}_{suffix:03d}"


def _all_fcurves(action):
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    yield from bag.fcurves
    else:
        yield from action.fcurves


def create_video_guided_action(scene, armature, name):
    if armature is None or armature.type != "ARMATURE":
        raise ValueError("Select the original creature armature first")
    video = _video_path(scene)
    if video is None or not video.is_file():
        raise ValueError("Set the source MP4 before building a video-guided Action")
    data = _read_waypoints(video, armature)
    points = sorted(data["waypoints"], key=lambda point: int(point["frame"]))
    if len(points) < 2:
        raise ValueError("Capture at least two video-matched poses before building an Action")
    frames = [int(point["frame"]) for point in points]
    if len(set(frames)) != len(frames):
        raise ValueError("Waypoint frame numbers must be unique")

    anim = armature.animation_data_create()
    old_action = anim.action
    old_slot = getattr(anim, "action_slot", None)
    old_frame = scene.frame_current
    action = bpy.data.actions.new(_unique_action_name(name))
    try:
        anim.action = action
        if getattr(action, "slots", None) and hasattr(anim, "action_slot"):
            anim.action_slot = action.slots[0]
        for point in points:
            frame = int(point["frame"])
            for bone in armature.pose.bones:
                values = point["pose"].get(bone.name)
                if values is None:
                    continue
                bone.location = values["location"]
                bone.rotation_mode = values["rotation_mode"]
                bone.rotation_euler = values["rotation_euler"]
                bone.rotation_quaternion = values["rotation_quaternion"]
                bone.rotation_axis_angle = values["rotation_axis_angle"]
                bone.scale = values["scale"]
                bone.keyframe_insert("location", frame=frame, group=bone.name)
                path = {"QUATERNION": "rotation_quaternion", "AXIS_ANGLE": "rotation_axis_angle"}.get(bone.rotation_mode, "rotation_euler")
                bone.keyframe_insert(path, frame=frame, group=bone.name)
                bone.keyframe_insert("scale", frame=frame, group=bone.name)
        curves = list(_all_fcurves(action))
        for curve in curves:
            quaternion_curve = "rotation_quaternion" in curve.data_path
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR" if quaternion_curve else "BEZIER"
                if not quaternion_curve:
                    key.handle_left_type = "AUTO_CLAMPED"
                    key.handle_right_type = "AUTO_CLAMPED"
            curve.update()
        scene.frame_set(old_frame)
        bpy.context.view_layer.update()
        return {
            "status": "CREATED_FROM_CAPTURED_POSES",
            "new_action": action.name,
            "source_action_preserved": old_action is None or old_action.name in bpy.data.actions,
            "armature": armature.name,
            "reference_video": data.get("source_video"),
            "reference_video_sha256": data.get("source_video_sha256"),
            "waypoint_record": _text_name(video, armature),
            "waypoint_frames": frames,
            "waypoint_count": len(points),
            "pose_bone_count": len(armature.pose.bones),
            "fcurve_count": len(curves),
            "interpolation": "quaternion linear; other channels auto-clamped Bezier",
            "matching_method": "User-captured armature poses after manual comparison with reference images; pose adjustments are not machine-verified.",
            "limitations": ["No automatic pixel-to-3D pose fitting is performed.", "The add-on cannot verify that a pose was actually adjusted to match the image.", "Unobserved anatomy should not be reported as video-observed."],
        }
    except Exception:
        anim.action = old_action
        if old_slot is not None and hasattr(anim, "action_slot"):
            anim.action_slot = old_slot
        scene.frame_set(old_frame)
        bpy.data.actions.remove(action)
        raise


class CMAI_OT_load_video_pose_reference(bpy.types.Operator):
    bl_idname = "cmai.load_video_pose_reference"
    bl_label = "Load Reference Image in Image Editor"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        path = Path(bpy.path.abspath(context.scene.cmai_video_pose_image))
        if not path.is_file():
            self.report({"ERROR"}, "Choose an extracted still from the reference MP4 first")
            return {"CANCELLED"}
        areas = [area for area in context.screen.areas if area.type == "IMAGE_EDITOR"]
        if not areas:
            self.report({"ERROR"}, "Split the workspace and change one area to Image Editor, then click again")
            return {"CANCELLED"}
        image = bpy.data.images.load(str(path), check_existing=True)
        areas[0].spaces.active.image = image
        self.report({"INFO"}, f"Loaded reference still: {path.name}")
        return {"FINISHED"}


class CMAI_OT_capture_video_pose(bpy.types.Operator):
    bl_idname = "cmai.capture_video_pose"
    bl_label = "Capture Pose at Current Video Frame"
    bl_description = "Save the current manually adjusted armature pose as a reference-guided waypoint"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene, armature = context.scene, context.active_object
        video = _video_path(scene)
        if video is None or not video.is_file():
            self.report({"ERROR"}, "Set the source MP4 in Milestone 1 before capturing video poses")
            return {"CANCELLED"}
        if armature is None or armature.type != "ARMATURE":
            self.report({"ERROR"}, "Select the creature armature as the active object")
            return {"CANCELLED"}
        frame = int(scene.frame_current)
        try:
            data = _read_waypoints(video, armature)
            data.update({
                "schema": 1,
                "source_video": str(video),
                "source_video_sha256": _video_sha256(video),
                "armature": armature.name,
                "coordinate_note": "Pose transforms captured from the selected Blender armature at the matching video frame.",
            })
            waypoint = {
                "frame": frame,
                "evidence": "USER_CAPTURED_AFTER_REFERENCE_REVIEW",
                "reference_image": bpy.path.abspath(scene.cmai_video_pose_image) if scene.cmai_video_pose_image else None,
                "pose": _pose_snapshot(armature),
            }
            data["waypoints"] = [point for point in data["waypoints"] if int(point["frame"]) != frame] + [waypoint]
            data["waypoints"].sort(key=lambda point: int(point["frame"]))
            _write_waypoints(data, video, armature)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Captured video-guided pose at frame {frame}; {len(data['waypoints'])} waypoint(s) saved")
        return {"FINISHED"}


class CMAI_OT_build_video_guided_action(bpy.types.Operator):
    bl_idname = "cmai.build_video_guided_action"
    bl_label = "Build Interpolated Video-Guided Action"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            report = create_video_guided_action(context.scene, context.active_object, context.scene.cmai_video_pose_action)
            report_path = Path(bpy.path.abspath(context.scene.cmai_video_pose_report))
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Built {report['new_action']} from {report['waypoint_count']} captured video poses")
        return {"FINISHED"}


_CLASSES = (CMAI_OT_load_video_pose_reference, CMAI_OT_capture_video_pose,
            CMAI_OT_build_video_guided_action)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cmai_video_pose_image = StringProperty(name="Reference still", subtype="FILE_PATH")
    bpy.types.Scene.cmai_video_pose_action = StringProperty(name="New Action", default="CMAI_VideoGuided")
    bpy.types.Scene.cmai_video_pose_report = StringProperty(name="Report", subtype="FILE_PATH", default="//data/generated/video_guided_pose_report.json")


def unregister():
    for name in ("cmai_video_pose_report", "cmai_video_pose_action", "cmai_video_pose_image"):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
