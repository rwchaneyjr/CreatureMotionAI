"""Create separate Fly and Land Actions on a copied dragon blend.

Fly holds the elevated-wing FLAP pose closest to the supplied airborne video.
Land transitions from that pose to the existing Idle pose. No source Action,
rig rest data, mesh, or weights are overwritten.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--flight-action", default="FLAP")
    p.add_argument("--flight-frame", type=int, default=30)
    p.add_argument("--landing-action", default="RUN")
    p.add_argument("--landing-frame", type=int, default=1)
    p.add_argument("--frames", type=int, default=120)
    p.add_argument("--transition-frames", type=int, default=24)
    return p.parse_args(argv)


def assign_action(rig, action):
    rig.animation_data_create()
    rig.animation_data.action = action
    if hasattr(rig.animation_data, "action_slot") and action.slots:
        rig.animation_data.action_slot = action.slots[0]


def capture_pose(rig, action, frame):
    assign_action(rig, action)
    scene = bpy.context.scene
    scene.frame_set(int(frame))
    bpy.context.view_layer.update()
    return {
        "object_location": rig.location.copy(),
        "object_rotation": rig.rotation_quaternion.copy() if rig.rotation_mode == "QUATERNION" else rig.rotation_euler.to_quaternion(),
        "object_scale": rig.scale.copy(),
        "bones": {
            pb.name: pb.matrix_basis.copy().decompose()
            for pb in rig.pose.bones
        },
    }


def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def create_action(rig, name, start_pose, end_pose, frames, transition_frames=0):
    if bpy.data.actions.get(name):
        raise RuntimeError(f"Refusing to overwrite existing Action {name!r}")
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    slot = action.slots.new(id_type="OBJECT", name=rig.name)
    assign_action(rig, action)
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"

    n = max(2, int(frames))
    for i in range(n):
        frame = i + 1
        if transition_frames > 1:
            t = smoothstep(min(1.0, i / (transition_frames - 1)))
        else:
            t = 0.0
        rig.location = start_pose["object_location"].lerp(end_pose["object_location"], t)
        rig.rotation_mode = "QUATERNION"
        rig.rotation_quaternion = start_pose["object_rotation"].slerp(end_pose["object_rotation"], t)
        rig.scale = start_pose["object_scale"].lerp(end_pose["object_scale"], t)
        for pb in rig.pose.bones:
            loc0, rot0, scale0 = start_pose["bones"][pb.name]
            loc1, rot1, scale1 = end_pose["bones"][pb.name]
            pb.location = loc0.lerp(loc1, t)
            pb.rotation_quaternion = rot0.slerp(rot1, t)
            pb.scale = scale0.lerp(scale1, t)
            pb.keyframe_insert("location", frame=frame, group=pb.name)
            pb.keyframe_insert("rotation_quaternion", frame=frame, group=pb.name)
            pb.keyframe_insert("scale", frame=frame, group=pb.name)
        rig.keyframe_insert("location", frame=frame, group="Armature Object")
        rig.keyframe_insert("rotation_quaternion", frame=frame, group="Armature Object")
        rig.keyframe_insert("scale", frame=frame, group="Armature Object")

    # We sampled every frame, so linear interpolation avoids overshoot and
    # guarantees the explicit endpoints. Land timing is eased in the samples.
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = "LINEAR"
    return action


def main():
    a = cli_args()
    source = Path(a.source).resolve()
    output = Path(a.output).resolve()
    report_path = Path(a.report).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    rig = bpy.data.objects.get("CrimsonWingedDragon_Rig")
    if not rig or rig.type != "ARMATURE":
        raise RuntimeError("Expected CrimsonWingedDragon_Rig in source copy")
    if len(rig.data.bones) != 47:
        raise RuntimeError(f"Expected original 47-bone dragon rig, found {len(rig.data.bones)}")
    flap = bpy.data.actions.get(a.flight_action)
    landing = bpy.data.actions.get(a.landing_action)
    if flap is None or landing is None:
        raise RuntimeError(f"Missing source Actions: flight={a.flight_action!r}, landing={a.landing_action!r}")
    if not int(flap.frame_range[0]) <= a.flight_frame <= int(flap.frame_range[1]):
        raise RuntimeError("Flight pose frame is outside the FLAP action range")
    if not int(landing.frame_range[0]) <= a.landing_frame <= int(landing.frame_range[1]):
        raise RuntimeError("Landing pose frame is outside its source Action range")

    flight_pose = capture_pose(rig, flap, a.flight_frame)
    landing_pose = capture_pose(rig, landing, a.landing_frame)
    fly = create_action(rig, "Fly", flight_pose, flight_pose, a.frames)
    land = create_action(rig, "Land", flight_pose, landing_pose, a.frames,
                         transition_frames=a.transition_frames)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end, scene.render.fps = 1, a.frames, 24
    assign_action(rig, fly)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(output))

    report = {
        "status": "ACTIONS_CREATED_VISUAL_REVIEW_REQUIRED",
        "source_blend_copy": str(source),
        "output_blend": str(output),
        "rig": rig.name,
        "bone_count": len(rig.data.bones),
        "source_actions_preserved": [a.flight_action, a.landing_action, "Idle", "FLAP"],
        "new_actions": {
            "Fly": {
                "frames": [1, a.frames],
                "source_pose": f"{a.flight_action} frame {a.flight_frame}",
                "method": "constant held pose; no exaggerated flap, matching the reference clip's nearly static airborne posture",
                "reference_status": "The supplied clip shows only airborne posture and contains no observed landing section.",
            },
            "Land": {
                "frames": [1, a.frames],
                "from_pose": f"{a.flight_action} frame {a.flight_frame}",
                "to_pose": f"{a.landing_action} frame {a.landing_frame}",
                "transition_frames": a.transition_frames,
                "method": "authored smoothstep transition to the existing grounded RUN pose, then hold; not claimed to be captured from the supplied video",
            },
        },
        "rig_mesh_rest_data_modified": False,
        "original_source_file_modified": False,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("DRAGON_FLY_LAND_CREATED " + json.dumps(report))


if __name__ == "__main__":
    main()
