"""Run isolated anatomical foot-contact experiment in Blender background.

Usage: blender --background BASELINE.blend --python tools/run_contact_lock_experiment.py
Outputs are written to the adjacent contact_lock_v1 directory; baseline is read-only.
"""
import bpy
import json
import math
import sys
from pathlib import Path

import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import creature_motion_ai as _cmai_package  # noqa: E402
# Blender may preload the installed add-on package from AppData before this
# script runs. Put the checked-out repository first for this isolated process.
_cmai_package.__path__.insert(0, str(ROOT / "creature_motion_ai"))
from creature_motion_ai.contact_lock import (  # noqa: E402
    centroid_world, make_tracker, patch_clearance, select_sole_patch, stance_slip,
)
from creature_motion_ai import ik_step, collision_proxies  # noqa: E402
from creature_motion_ai.walk_waypoints import action_curves  # noqa: E402

BASE = ROOT / "data/generated/balisk_camera_fullbody_walk_02"
SOURCE = BASE / "balisk_seamless_loop.blend"
OUT = BASE / "contact_lock_v1"
OUT.mkdir(parents=True, exist_ok=True)
SAMPLES = range(1, 121)
END_FRAME = 121
GROUND_NAME = "CMAI_Ground_Contact"
CHAINS = {
    "Front.L": ["Leg_Front.L_01", "Leg_Front.L_02", "Leg_Front.L_03"],
    "Front.R": ["Leg_Front.R_01", "Leg_Front.R_02", "Leg_Front.R_03"],
    "MidFront.L": ["Leg_MidFront.L_01", "Leg_MidFront.L_02", "Leg_MidFront.L_03"],
    "MidFront.R": ["Leg_MidFront.R_01", "Leg_MidFront.R_02", "Leg_MidFront.R_03"],
    "MidRear.L": ["Leg_MidRear.L_01", "Leg_MidRear.L_02", "Leg_MidRear.L_03"],
    "MidRear.R": ["Leg_MidRear.R_01", "Leg_MidRear.R_02", "Leg_MidRear.R_03"],
    "Rear.L": ["Leg_Rear.L_01", "Leg_Rear.L_02", "Leg_Rear.L_03"],
    "Rear.R": ["Leg_Rear.R_01", "Leg_Rear.R_02", "Leg_Rear.R_03"],
}


def evaluated_world_mesh(mesh):
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    xyz = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", xyz)
    xyz = xyz.reshape(-1, 3)
    m = np.asarray(ev.matrix_world, dtype=np.float64)
    world = xyz @ m[:3, :3].T + m[:3, 3]
    normal = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("normal", normal)
    normal = normal.reshape(-1, 3) @ np.linalg.inv(m[:3, :3])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)
    ev.to_mesh_clear()
    return world, normal


def setup_scene():
    scene = bpy.context.scene
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    meshes = [o for o in scene.objects if o.type == "MESH" and any(
        mod.type == "ARMATURE" and mod.object == arm for mod in o.modifiers)]
    if len(meshes) != 1:
        raise RuntimeError(f"expected one skinned mesh, found {len(meshes)}")
    mesh = meshes[0]
    if len(arm.data.bones) != 38:
        raise RuntimeError(f"expected original 38-bone rig, found {len(arm.data.bones)}")
    if not arm.animation_data or not arm.animation_data.action:
        raise RuntimeError("baseline armature Action missing")
    if not scene.objects.get(GROUND_NAME):
        raise RuntimeError("saved ground plane missing; refusing guessed ground height")
    ground_z = float(scene.objects[GROUND_NAME].location.z)
    return scene, arm, mesh, ground_z


def collect_weight_arrays(mesh):
    arrays = {}
    for leg, names in CHAINS.items():
        group = mesh.vertex_groups.get(names[-1])
        if group is None:
            raise RuntimeError(f"{leg}: terminal mesh weight group missing")
        weights = np.zeros(len(mesh.data.vertices), dtype=np.float32)
        for v in mesh.data.vertices:
            for membership in v.groups:
                if membership.group == group.index:
                    weights[v.index] = membership.weight
        arrays[leg] = weights
    return arrays


def derive_patches(scene, arm, mesh, ground_z, weights):
    candidate_rows = {leg: [] for leg in CHAINS}
    for frame in range(1, 41):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        coords, normals = evaluated_world_mesh(mesh)
        for leg, names in CHAINS.items():
            bones = [arm.pose.bones[n] for n in names]
            p = [arm.matrix_world @ b.head for b in bones] + [arm.matrix_world @ bones[-1].tail]
            foot_length = max((p[3] - p[2]).length, 1e-8)
            direction = np.asarray((p[3] - p[2]).normalized(), dtype=np.float64)
            along = (coords - np.asarray(p[2], dtype=np.float64)) @ direction
            eligible = (weights[leg] >= 0.35) & (along >= 0.15 * foot_length) & (normals[:, 2] < -0.25)
            ids = np.flatnonzero(eligible)
            if len(ids) < 12:
                continue
            z = coords[ids, 2]
            low = ids[z <= z.min() + 0.003]
            pts = coords[low]
            candidate_rows[leg].append({
                "frame": frame, "vertex_indices": low, "world_positions": pts,
                "clearance": float(pts[:, 2].min() - ground_z),
                "underside_fraction": float(np.mean(normals[low, 2] < -0.25)),
            })
    patches, audit = {}, {}
    for leg, candidates in candidate_rows.items():
        try:
            patch = select_sole_patch(candidates)
        except ValueError as exc:
            audit[leg] = {"status": "UNVERIFIED", "reason": str(exc)}
            continue
        patches[leg] = patch
        audit[leg] = {"status": "PASS", "sample_frame": patch.sample_frame,
                      "vertices": int(len(patch.vertex_indices)),
                      "sample_clearance": patch.min_clearance,
                      "quality": patch.quality,
                      "extent_xyz": patch.extent_xyz}
    return patches, audit


def capture_motion(scene, arm, mesh, ground_z, patches):
    """Capture baseline basis and fixed-sole measurements before editing curves."""
    frames, observations = {}, {leg: [] for leg in patches}
    trackers = {leg: make_tracker() for leg in patches}
    limb_lengths = {leg: sum(arm.data.bones[n].length for n in CHAINS[leg][:2])
                    for leg in patches}
    for frame in range(1, END_FRAME + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        frames[frame] = {p.name: p.matrix_basis.copy() for p in arm.pose.bones}
        world, _ = evaluated_world_mesh(mesh)
        for leg, patch in patches.items():
            sole = centroid_world(world, patch)
            clearance = patch_clearance(world, patch, ground_z)
            quality = patch.quality
            decision = trackers[leg].update(frame, sole, clearance, limb_lengths[leg],
                                            anatomy_quality=quality)
            observations[leg].append({"frame": frame, "sole": sole.tolist(),
                                      "clearance": clearance,
                                      "state": decision.state.value,
                                      "confidence": decision.confidence,
                                      "anchor": list(decision.anchor_world) if decision.anchor_world else None,
                                      "lock": decision.lock_enabled,
                                      "reason": decision.reason})
    return frames, observations, limb_lengths


def apply_contact_lock(arm, mesh, leg, anchor, maximum_shift):
    """Solve a bounded current-pose two-link correction; reject rather than stretch."""
    names = CHAINS[leg]
    bpy.context.view_layer.update()
    bones = [arm.pose.bones[n] for n in names]
    points = [arm.matrix_world @ b.head for b in bones] + [arm.matrix_world @ bones[-1].tail]
    current_sole, _ = evaluated_world_mesh(mesh)
    # The caller's fixed anatomical patch is attached for the duration of this function.
    patch = mesh.get("_cmai_active_patch")
    if patch is None:
        return {"status": "REJECTED", "reason": "missing_sole_patch"}
    ids = np.asarray(json.loads(patch), dtype=np.int64)
    sole = current_sole[ids].mean(axis=0)
    target = points[2] + Vector(anchor) - Vector(sole)
    shift = (target - points[2]).length
    if shift > maximum_shift:
        return {"status": "REJECTED", "reason": "correction_exceeds_reach_budget", "shift": shift}
    world_mats = [arm.matrix_world @ b.matrix for b in bones]
    bend_normal = (points[1] - points[0]).cross(points[2] - points[0])
    if bend_normal.length < 1e-8:
        return {"status": "REJECTED", "reason": "straight_or_degenerate_knee"}
    bend_normal.normalize()
    result = ik_step.solve_rest_relative_two_link(
        points[0], target, (points[1] - points[0]).length,
        (points[2] - points[1]).length, bend_normal,
        min_knee_angle=math.radians(8.0))
    if result["status"] != "PASS":
        return {"status": "REJECTED", "reason": result.get("reason", "ik_rejected"), "shift": shift}
    flex = 180.0 - math.degrees(result["knee_angle"])
    if flex > 135.0:
        return {"status": "REJECTED", "reason": "knee_flex_limit", "knee_flexion_deg": flex}
    normal_before = bend_normal.copy()
    inv = arm.matrix_world.inverted()
    desired = [(points[0], result["knee"]), (result["knee"], target)]
    for i, (head, tail) in enumerate(desired):
        matrix = ik_step.world_direction_pose_matrix(
            world_mats[i], points[i], head, tail, points[i + 1])
        bones[i].matrix = inv @ matrix
        bpy.context.view_layer.update()
    ik_step.restore_terminal_foot_world_orientation(arm, names[2], world_mats[2], target)
    bpy.context.view_layer.update()
    actual = [arm.matrix_world @ b.head for b in bones] + [arm.matrix_world @ bones[-1].tail]
    bend_after = (actual[1] - actual[0]).cross(actual[2] - actual[0]).normalized()
    bend_dot = float(bend_after.dot(normal_before))
    length_error = max(abs((actual[i + 1] - actual[i]).length - (points[i + 1] - points[i]).length)
                       for i in range(3))
    if bend_dot < 0.95 or length_error > 1e-4:
        # Restore the sampled matrices before returning a failed candidate.
        for b, m in zip(bones, world_mats):
            b.matrix = inv @ m
            bpy.context.view_layer.update()
        return {"status": "REJECTED", "reason": "bend_or_bone_length_validation",
                "bend_dot": bend_dot, "length_error": length_error, "shift": shift}
    return {"status": "PASS", "shift": shift, "knee_flexion_deg": flex,
            "bend_dot": bend_dot, "length_error": length_error}


def proxy_overlaps(arm):
    segments = collision_proxies.segments_for_chains(arm, CHAINS, [])
    hits, total = [], 0.0
    for i, a in enumerate(segments):
        for b in segments[i + 1:]:
            if a["region"] == b["region"]:
                continue
            overlap = a["r"] + b["r"] - collision_proxies._segdist(a["a"], a["b"], b["a"], b["b"])
            if overlap > 0:
                total += overlap
                hits.append({"a": a["bone"], "b": b["bone"], "overlap": float(overlap)})
    return hits, total


def run_variant(scene, arm, mesh, ground_z, patches, base_poses, observations,
                variant_name, active_legs):
    # A new Action is built from sampled baseline poses; source Action remains untouched.
    new_action = bpy.data.actions.new("CMAI_ContactLock_" + variant_name)
    new_action.use_fake_user = True
    slot = new_action.slots.new(arm.id_type, arm.name)
    arm.animation_data_create()
    arm.animation_data.action = new_action
    if hasattr(arm.animation_data, "action_slot"):
        arm.animation_data.action_slot = slot
    lookup = {leg: {int(row["frame"]): row for row in rows}
              for leg, rows in observations.items()}
    per_leg = {leg: {"attempted": 0, "accepted": 0, "rejected": 0, "reject_reasons": {}}
               for leg in active_legs}
    correction_rows = []
    rows = []
    for frame in range(1, END_FRAME + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for p in arm.pose.bones:
            p.matrix_basis = base_poses[frame][p.name]
        bpy.context.view_layer.update()
        frame_result = {"frame": frame, "legs": {}}
        base_geometry = {}
        for leg, names in CHAINS.items():
            b = [arm.pose.bones[n] for n in names]
            q = [arm.matrix_world @ x.head for x in b] + [arm.matrix_world @ b[-1].tail]
            normal = (q[1] - q[0]).cross(q[2] - q[0])
            base_geometry[leg] = {"points": q, "normal": normal.normalized() if normal.length else Vector((0, 0, 0)),
                                  "lengths": [(q[i + 1] - q[i]).length for i in range(3)]}
        for leg, patch in patches.items():
            obs = lookup[leg][frame]
            accepted = None
            if leg in active_legs and obs["lock"] and obs["anchor"] is not None:
                per_leg[leg]["attempted"] += 1
                mesh["_cmai_active_patch"] = json.dumps(patch.vertex_indices.tolist())
                limb_length = sum(arm.data.bones[n].length for n in CHAINS[leg][:2])
                accepted = apply_contact_lock(arm, mesh, leg, obs["anchor"], 0.10 * limb_length)
                if accepted["status"] == "PASS":
                    per_leg[leg]["accepted"] += 1
                    correction_rows.append({"frame": frame, "leg": leg, **accepted})
                else:
                    per_leg[leg]["rejected"] += 1
                    reason = accepted.get("reason", "unknown")
                    per_leg[leg]["reject_reasons"][reason] = per_leg[leg]["reject_reasons"].get(reason, 0) + 1
        # Record once per frame after all leg corrections, avoiding duplicate keys.
        bpy.context.view_layer.update()
        for p in arm.pose.bones:
            p.rotation_mode = "QUATERNION"
            loc, quat, scale = p.matrix_basis.decompose()
            p.location = loc
            p.rotation_quaternion = quat
            p.scale = scale
            p.keyframe_insert("location", frame=frame, group=p.name)
            p.keyframe_insert("rotation_quaternion", frame=frame, group=p.name)
            p.keyframe_insert("scale", frame=frame, group=p.name)
        bpy.context.view_layer.update()
        world, _ = evaluated_world_mesh(mesh)
        for leg, patch in patches.items():
            centroid = centroid_world(world, patch)
            clearance = patch_clearance(world, patch, ground_z)
            points = [arm.matrix_world @ arm.pose.bones[n].head for n in CHAINS[leg]]
            tail = arm.matrix_world @ arm.pose.bones[CHAINS[leg][-1]].tail
            flex = 180.0 - math.degrees((points[0] - points[1]).angle(points[2] - points[1]))
            bend = (points[1] - points[0]).cross(points[2] - points[0])
            bend_dot = float(bend.normalized().dot(base_geometry[leg]["normal"])) if bend.length else -1.0
            lengths = [(arm.matrix_world @ arm.pose.bones[CHAINS[leg][i + 1]].head -
                        arm.matrix_world @ arm.pose.bones[CHAINS[leg][i]].head).length
                       for i in range(2)]
            length_error = max(abs(lengths[i] - base_geometry[leg]["lengths"][i]) for i in range(2))
            frame_result["legs"][leg] = {
                "state": obs["state"], "confidence": obs["confidence"],
                "sole_centroid": centroid.tolist(), "clearance": clearance,
                "knee_flexion_deg": flex, "bend_dot_vs_baseline": bend_dot,
                "length_error_vs_baseline": length_error, "correction": accepted,
                "foot_world": list(tail),
            }
        hits, overlap = proxy_overlaps(arm)
        frame_result["proxy_collision_count"] = len(hits)
        frame_result["proxy_overlap_sum"] = overlap
        rows.append(frame_result)
        if frame % 20 == 0:
            print(f"{variant_name}: sampled frame {frame}/{END_FRAME}", flush=True)
    # Dense sampled action: linear rotations avoid invented between-frame knee flips.
    for curve in action_curves(new_action):
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    return new_action, rows, per_leg, correction_rows


def summarize(rows, patches, observations, per_leg):
    legs = {}
    for leg, patch in patches.items():
        vals = [row["legs"][leg] for row in rows]
        states = [row["state"] for row in vals]
        pts = [row["sole_centroid"] for row in vals]
        contacts = [v for v in vals if v["state"] == "STANCE"]
        swings = [v for v in vals if v["state"] == "SWING"]
        legs[leg] = {
            "sole_patch_vertices": int(len(patch.vertex_indices)),
            "contact_pairs": stance_slip(pts, states),
            "stance_min_clearance": min((v["clearance"] for v in contacts), default=None),
            "stance_max_clearance": max((v["clearance"] for v in contacts), default=None),
            "swing_min_clearance": min((v["clearance"] for v in swings), default=None),
            "max_knee_flexion_deg": max(v["knee_flexion_deg"] for v in vals),
            "min_knee_flexion_deg": min(v["knee_flexion_deg"] for v in vals),
            "state_counts": {state: states.count(state) for state in ("STANCE", "SWING", "UNCERTAIN")},
            "correction": per_leg.get(leg),
        }
    collisions = [row["proxy_collision_count"] for row in rows]
    overlap = [row["proxy_overlap_sum"] for row in rows]
    support_counts = [sum(leg["state"] == "STANCE" for leg in row["legs"].values()) for row in rows]
    return {"legs": legs,
            "proxy_collisions": {"frames_with_hits": sum(v > 0 for v in collisions),
                                 "max_hits_in_frame": max(collisions, default=0),
                                 "max_overlap_sum": max(overlap, default=0.0)},
            "support": {"minimum_stance_legs": min(support_counts, default=0),
                        "mean_stance_legs": float(np.mean(support_counts)) if support_counts else 0.0},
            "loop": {"sampled_frames_including_endpoint": len(rows),
                     "endpoint_sole_error_max": max((np.linalg.norm(np.array(rows[0]["legs"][leg]["sole_centroid"]) -
                                                  np.array(rows[-1]["legs"][leg]["sole_centroid"]))
                                                     for leg in patches), default=0.0)}}


def main():
    scene, arm, mesh, ground_z = setup_scene()
    weights = collect_weight_arrays(mesh)
    patches, patch_report = derive_patches(scene, arm, mesh, ground_z, weights)
    if len(patches) != 8:
        raise RuntimeError(f"Only {len(patches)}/8 anatomical sole patches verified; refusing all-leg run")
    print("SOLE_PATCHES " + json.dumps(patch_report), flush=True)
    baseline_action = arm.animation_data.action
    baseline_slot = getattr(arm.animation_data, "action_slot", None)
    base_poses, observations, lengths = capture_motion(scene, arm, mesh, ground_z, patches)

    # Isolated one-leg experiment first, then independent all-leg candidate from same baseline.
    one_action, one_rows, one_counts, one_fixes = run_variant(
        scene, arm, mesh, ground_z, patches, base_poses, observations,
        "RearL_Test", {"Rear.L"})
    one_summary = summarize(one_rows, patches, observations, one_counts)
    one_action.use_fake_user = False
    bpy.data.actions.remove(one_action)

    # Restore the source Action and create the full candidate only after the isolated run completes.
    arm.animation_data.action = baseline_action
    if baseline_slot and hasattr(arm.animation_data, "action_slot"):
        arm.animation_data.action_slot = baseline_slot
    all_action, all_rows, all_counts, all_fixes = run_variant(
        scene, arm, mesh, ground_z, patches, base_poses, observations,
        "EightLeg", set(patches))
    all_summary = summarize(all_rows, patches, observations, all_counts)

    # Candidate Action selected for saving; original Action remains in the .blend.
    scene.frame_set(1)
    bpy.context.view_layer.update()
    destination = OUT / "balisk_contact_locked.blend"
    baseline = {leg: [] for leg in patches}
    for leg, rows in observations.items():
        for row in rows:
            baseline[leg].append({"state": row["state"], "sole_centroid": row["sole"],
                                  "clearance": row["clearance"], "confidence": row["confidence"]})
    baseline_rows = []
    for frame in range(1, END_FRAME + 1):
        baseline_rows.append({"frame": frame, "legs": {
            leg: {"state": baseline[leg][frame - 1]["state"],
                  "sole_centroid": baseline[leg][frame - 1]["sole_centroid"],
                  "clearance": baseline[leg][frame - 1]["clearance"],
                  "knee_flexion_deg": 0.0}
            for leg in patches}, "proxy_collision_count": 0, "proxy_overlap_sum": 0.0})

    # Re-measure proxy overlaps on baseline using captured pose samples, same proxy method.
    original_active = all_action
    baseline_collision_counts, baseline_overlap = [], []
    for frame in range(1, END_FRAME + 1):
        scene.frame_set(frame)
        for p in arm.pose.bones:
            p.matrix_basis = base_poses[frame][p.name]
        bpy.context.view_layer.update()
        hits, overlap = proxy_overlaps(arm)
        baseline_collision_counts.append(len(hits)); baseline_overlap.append(overlap)
        if frame <= 120:
            for leg, names in CHAINS.items():
                pts = [arm.matrix_world @ arm.pose.bones[n].head for n in names]
                tail = arm.matrix_world @ arm.pose.bones[names[-1]].tail
                baseline_rows[frame - 1]["legs"][leg]["knee_flexion_deg"] = 180.0 - math.degrees((pts[0]-pts[1]).angle(pts[2]-pts[1]))
                baseline_rows[frame - 1]["legs"][leg]["foot_world"] = list(tail)
    for i, row in enumerate(baseline_rows):
        row["proxy_collision_count"] = baseline_collision_counts[i]
        row["proxy_overlap_sum"] = baseline_overlap[i]
    before = summarize(baseline_rows, patches, observations, {})
    after = all_summary
    comparison = {}
    for leg in patches:
        b, a = before["legs"][leg], after["legs"][leg]
        bs = b["contact_pairs"]["mean_per_frame_slip"]
        as_ = a["contact_pairs"]["mean_per_frame_slip"]
        comparison[leg] = {"before_mean_slip": bs, "after_mean_slip": as_,
                           "relative_change": None if bs in (None, 0) or as_ is None else (as_ - bs) / bs,
                           "status": "UNVERIFIED" if bs is None or as_ is None else
                                    ("PASS" if as_ < bs else "FAIL")}
    report = {
        "schema_version": 1,
        "source_blend": str(SOURCE),
        "source_action": baseline_action.name,
        "modified_blend": str(destination),
        "modified_action": all_action.name,
        "fps": scene.render.fps,
        "measured_frames": 120,
        "loop_endpoint_frame": END_FRAME,
        "method": "fixed weighted distal underside mesh vertex patches; per-leg STANCE/SWING/UNCERTAIN hysteresis; bounded current-pose two-link IK; world-space sole-centroid anchor; no root correction",
        "geometry_verification": patch_report,
        "single_leg_first": {"leg": "Rear.L", "summary": one_summary,
                              "corrections": one_fixes},
        "before": before,
        "after": after,
        "per_leg_slip_comparison": comparison,
        "criteria": {
            "foot_sliding": {leg: comparison[leg]["status"] for leg in patches},
            "ground_penetration": "PASS" if min(v["clearance"] for row in all_rows for v in row["legs"].values()) >= -0.003 else "FAIL",
            "swing_clearance": "PASS" if all((v["swing_min_clearance"] is None or v["swing_min_clearance"] >= -0.003) for v in after["legs"].values()) else "FAIL",
            "knee_direction": "PASS" if min(v["bend_dot_vs_baseline"] for row in all_rows for v in row["legs"].values()) >= 0.95 else "FAIL",
            "bone_lengths": "PASS" if max(v["length_error_vs_baseline"] for row in all_rows for v in row["legs"].values()) <= 1e-4 else "FAIL",
            "leg_collisions": "UNVERIFIED: coarse existing capsule proxies only; original mesh self-collision not evaluated",
            "body_support_stability": "UNVERIFIED: contact-count proxy only; mass/center-of-mass data unavailable",
            "loop_continuity": "PASS" if after["loop"]["endpoint_sole_error_max"] <= 0.003 else "FAIL",
        },
        "limitations": [
            "Mesh underside patches are anatomy/weight-derived surface regions, not authored anatomical sole labels.",
            "A single fixed polygon set may include toe tips; patch audit records sample extent and quality.",
            "Contact correction is bounded and only applies where the baseline motion provides confident contact.",
            "Collision proxies are approximate and do not prove absence of mesh self-intersection.",
        ],
    }
    report_path = OUT / "contact_lock_comparison.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "contact_observations.json").write_text(json.dumps({
        "patches": {leg: {"indices": patch.vertex_indices.tolist(),
                          "sample_frame": patch.sample_frame,
                          "quality": patch.quality} for leg, patch in patches.items()},
        "frames": observations,
        "corrections": all_fixes,
        "per_leg": all_counts,
    }, indent=2), encoding="utf-8")
    # Save candidate action active in the deliverable; state/metrics report is external.
    arm.animation_data.action = all_action
    scene.frame_set(1)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(destination), copy=False)
    print("CONTACT_LOCK_REPORT " + json.dumps({"blend": str(destination), "report": str(report_path),
          "patches": patch_report, "criteria": report["criteria"]}), flush=True)


if __name__ == "__main__":
    main()
