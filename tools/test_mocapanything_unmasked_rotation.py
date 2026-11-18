"""Run only MoCapAnything's pose-to-rotation stage with leg masks disabled.

Reads saved pose predictions and official weights. Never edits MoCapAnything's
species cache, checkpoint, original FBX, or any existing Blender file.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pose", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    vendor = Path(__file__).resolve().parents[1] / "external" / "MocapAnything"
    sys.path.insert(0, str(vendor))
    import torch
    from inference.video2pose2rot import build_inference_batch
    from utils.config_utils import load_yaml_config, instantiate_from_config

    torch.set_num_threads(min(4, max(1, os.cpu_count() or 1)))
    cfg = load_yaml_config(str(Path(args.config).resolve()))
    cfg["data"]["base_dir"] = str(vendor / "zoo")
    cfg["data"]["memory_pkl_path"] = ""
    cfg["data"]["retarget"]["ref_seq"] = "Balisk#Balisk-Move/y0"
    cfg["data"]["wild_flag"] = True
    pose = np.load(args.pose)
    if pose.ndim != 3 or pose.shape[1:] != (150, 3):
        raise ValueError(f"Expected [frames, 150, 3] pose array, got {pose.shape}")
    batch = build_inference_batch(cfg, np.zeros((len(pose), 1024), dtype=np.float32))
    info = np.load(vendor / "zoo" / "species_info_dict.npy", allow_pickle=True).item()["Balisk"]
    names = list(info["joints_name"])
    unmasked_indices = [i for i, name in enumerate(names) if name.startswith("Leg_") and bool(batch["static_rot_joint_mask"][0, i])]
    if not unmasked_indices:
        raise RuntimeError("No masked leg joints were found; check the source species metadata")
    batch["static_rot_joint_mask"][0, unmasked_indices] = False

    model = instantiate_from_config(cfg["model"]).float().cpu().eval()
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    weights = next((checkpoint[key] for key in ("model_state", "model", "model_state_dict", "state_dict")
                    if isinstance(checkpoint, dict) and key in checkpoint), checkpoint)
    weights = {(key[7:] if key.startswith("module.") else key): value for key, value in weights.items()}
    model.load_state_dict(weights)
    with torch.no_grad():
        result = model.pos2rot(batch=batch, pose_override=torch.from_numpy(pose[None]).float())
    rotation = result["pred_rot6d"].squeeze(0).cpu().numpy()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite prior isolated prediction: {output}")
    np.save(output, rotation)
    joint_changes = {}
    for i, name in enumerate(names):
        change = np.linalg.norm(rotation[:, i] - rotation[0, i], axis=1)
        joint_changes[name] = float(change.max())
    report = {
        "status": "ROTATION_DIAGNOSTIC_ONLY",
        "frames": len(pose),
        "unmasked_leg_joints": [names[i] for i in unmasked_indices],
        "joint_rot6d_max_change": joint_changes,
        "output": str(output.resolve()),
        "note": "Unmasked rotations are model predictions, not physically validated animation.",
    }
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "unmasked_leg_joints": len(unmasked_indices),
                      "moving_unmasked_legs": sum(joint_changes[names[i]] > 1e-4 for i in unmasked_indices)}, indent=2))


if __name__ == "__main__":
    main()
