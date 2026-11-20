"""Create a separate tucked-leg flight Action while retaining FLAP wings."""
import argparse
import bpy
import math
import os
import sys
from mathutils import Quaternion, Vector


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-blend", required=True)
    parser.add_argument("--action-name", default="CMAI_Flight_Tucked")
    parser.add_argument("--front-hip-deg", type=float, default=18.0)
    parser.add_argument("--front-knee-deg", type=float, default=62.0)
    parser.add_argument("--rear-hip-deg", type=float, default=22.0)
    parser.add_argument("--rear-knee-deg", type=float, default=58.0)
    parser.add_argument("--ankle-deg", type=float, default=0.0)
    return parser.parse_args(args)


def main():
    args = cli_args()
    rig = bpy.data.objects.get("CrimsonWingedDragon_Rig")
    if not rig or not rig.animation_data:
        raise RuntimeError("Expected animated CrimsonWingedDragon_Rig")
    flap = bpy.data.actions.get("FLAP")
    if not flap:
        raise RuntimeError("Existing FLAP action not found")
    if args.action_name in bpy.data.actions:
        raise RuntimeError(f"Refusing to replace existing action: {args.action_name}")

    # Duplicate the proven wing action and add only leg pose channels to the copy.
    action = flap.copy()
    action.name = args.action_name
    rig.animation_data.action = action
    if hasattr(rig.animation_data, "action_slot") and len(action.slots):
        try:
            rig.animation_data.action_slot = action.slots[0]
        except Exception:
            pass

    first = int(round(flap.frame_range[0]))
    last = int(round(flap.frame_range[1]))
    angles = {}
    for side in ("L", "R"):
        angles[f"Leg_Front.{side}_01"] = args.front_hip_deg
        angles[f"Leg_Front.{side}_02"] = args.front_knee_deg
        angles[f"Leg_Front.{side}_03"] = args.ankle_deg
        angles[f"Leg_Rear.{side}_01"] = args.rear_hip_deg
        angles[f"Leg_Rear.{side}_02"] = args.rear_knee_deg
        angles[f"Leg_Rear.{side}_03"] = args.ankle_deg

    missing = [name for name in angles if rig.pose.bones.get(name) is None]
    if missing:
        raise RuntimeError("Missing expected leg bones: " + ", ".join(missing))

    for frame in range(first, last + 1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name, degrees in angles.items():
            pb = rig.pose.bones[name]
            base = pb.rotation_quaternion.copy()
            # Add a small cyclic flex to keep the tucked pose alive during flight.
            # Zero at both loop endpoints keeps the repeated Action continuous.
            phase = 2.0 * math.pi * (frame - first) / max(1, last - first)
            pulse = 2.0 * math.sin(phase)
            joint = "_02" in name
            joint_pulse = pulse if joint else pulse * 0.35
            q_delta = Quaternion((1.0, 0.0, 0.0), math.radians(degrees + joint_pulse))
            pb.rotation_quaternion = base @ q_delta
            pb.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=name)

    bpy.context.scene.frame_start = first
    bpy.context.scene.frame_end = last
    bpy.context.scene.frame_set(first)
    os.makedirs(os.path.dirname(os.path.abspath(args.output_blend)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.output_blend))
    print("TUCKED_FLIGHT_ACTION_CREATED=" + repr({
        "action": args.action_name,
        "source_action": flap.name,
        "frames": [first, last],
        "leg_rotation_offsets_degrees": angles,
        "saved_blend": os.path.abspath(args.output_blend),
    }))


if __name__ == "__main__":
    main()
