"""Locate missing joint motion between MoCapAnything pose, rotation, and BVH outputs.

This is a read-only diagnostic. It never changes the model cache, predicted arrays,
or the original Blender rig. Run it with the isolated MoCapAnything Python environment.
"""

import argparse
import json
from pathlib import Path

import numpy as np


def bvh_rotation_ranges(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    motion = lines.index("MOTION")
    columns = {}
    current = None
    offset = 0
    for line in lines[:motion]:
        parts = line.strip().split()
        if not parts:
            continue
        if parts[0] in ("ROOT", "JOINT"):
            current = parts[1]
        elif parts[0] == "CHANNELS":
            columns[current] = list(range(offset, offset + int(parts[1])))
            offset += int(parts[1])
    data = np.array([list(map(float, line.split())) for line in lines[motion + 3:] if line.strip()])
    if data.ndim != 2 or data.shape[1] != offset:
        raise ValueError("BVH frame/channel count does not match its hierarchy")
    return {name: float(np.ptp(data[:, indices[-3:]], axis=0).max()) for name, indices in columns.items()}, len(data)


def diagnose(pose_path, rotation_path, species_info_path, bvh_path, species):
    pose = np.load(pose_path)
    rotation = np.load(rotation_path)
    info = np.load(species_info_path, allow_pickle=True).item()[species]
    names = list(info["joints_name"])
    if pose.shape != (rotation.shape[0], rotation.shape[1], 3):
        raise ValueError(f"Unexpected pose/rotation shapes: {pose.shape}, {rotation.shape}")
    if rotation.shape[2] != 6 or len(names) > pose.shape[1]:
        raise ValueError("Expected padded 6D rotations with the species joints first")
    bvh_ranges, bvh_frames = bvh_rotation_ranges(bvh_path)
    if bvh_frames != len(pose):
        raise ValueError("BVH and prediction frame counts differ")
    static_rotation_mask = set(map(int, info["static_rot_joints"]))
    joints = {}
    for index, name in enumerate(names):
        displacement = np.linalg.norm(pose[:, index] - pose[0, index], axis=1)
        rot_difference = np.linalg.norm(rotation[:, index] - rotation[0, index], axis=1)
        joints[name] = {
            "index": index,
            "pose_max_displacement_in_prediction_units": float(displacement.max()),
            "rot6d_max_change": float(rot_difference.max()),
            "bvh_max_channel_range_degrees": bvh_ranges.get(name),
            "forced_static_by_species_mask": index in static_rotation_mask,
        }
    segments = {}
    for name in names:
        if not name.startswith("Leg_") or not name.endswith(("_02", "_03")):
            continue
        parent = name[:-2] + ("01" if name.endswith("02") else "02")
        if parent not in joints:
            continue
        a, b = joints[parent]["index"], joints[name]["index"]
        lengths = np.linalg.norm(pose[:, a] - pose[:, b], axis=1)
        initial = float(lengths[0])
        segments[parent + " -> " + name] = {
            "initial_prediction_length": initial,
            "minimum_prediction_length": float(lengths.min()),
            "maximum_prediction_length": float(lengths.max()),
            "maximum_relative_length_change": float(np.max(np.abs(lengths - initial)) / max(initial, 1e-9)),
        }
    leg_names = [name for name in names if name.startswith("Leg_")]
    masked = [name for name in leg_names if joints[name]["forced_static_by_species_mask"]]
    return {
        "species": species,
        "frames": len(pose),
        "joints_in_rig": len(names),
        "array_joints_including_padding": pose.shape[1],
        "static_leg_rotations_in_bvh": sum((joints[n]["bvh_max_channel_range_degrees"] or 0) < 1e-5 for n in leg_names),
        "masked_leg_rotations": masked,
        "diagnosis": (
            "The species static-rotation mask forces listed joints to their reference rotations "
            "in the pose-to-rotation model before BVH export. Pose predictions retain movement, "
            "but their variable segment lengths rule out direct use as a physically valid rig pose."
        ),
        "joint_motion": joints,
        "predicted_leg_segment_lengths": segments,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pose", required=True)
    parser.add_argument("--rot6d", required=True)
    parser.add_argument("--species-info", required=True)
    parser.add_argument("--bvh", required=True)
    parser.add_argument("--species", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = diagnose(args.pose, args.rot6d, args.species_info, args.bvh, args.species)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "frames": report["frames"],
                      "masked_leg_rotations": len(report["masked_leg_rotations"]),
                      "static_leg_rotations_in_bvh": report["static_leg_rotations_in_bvh"]}, indent=2))


if __name__ == "__main__":
    main()
