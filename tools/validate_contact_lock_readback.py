"""Re-measure baseline and saved contact Action from Blender's evaluated poses."""
import bpy, json, math, sys
from pathlib import Path
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import creature_motion_ai as package
package.__path__.insert(0, str(ROOT / "creature_motion_ai"))
from creature_motion_ai import collision_proxies

OUT = ROOT / "data/generated/balisk_camera_fullbody_walk_02/contact_lock_v1"
SOURCE = ROOT / "data/generated/balisk_camera_fullbody_walk_02/balisk_seamless_loop.blend"
CANDIDATE = OUT / "balisk_contact_locked.blend"
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


def find_arm():
    return next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")


def proxy_stats(arm):
    segments = collision_proxies.segments_for_chains(arm, CHAINS, [])
    count, overlap_sum, maximum = 0, 0.0, 0.0
    for i, a in enumerate(segments):
        for b in segments[i + 1:]:
            if a["region"] == b["region"]:
                continue
            overlap = a["r"] + b["r"] - collision_proxies._segdist(a["a"], a["b"], b["a"], b["b"])
            if overlap > 0:
                count += 1
                overlap_sum += float(overlap)
                maximum = max(maximum, float(overlap))
    return {"count": count, "overlap_sum": overlap_sum, "maximum_overlap": maximum}


def capture_current():
    scene, arm = bpy.context.scene, find_arm()
    result = {"action": arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None,
              "frames": []}
    for frame in range(1, 122):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        row = {"frame": frame, "legs": {}, "proxy": proxy_stats(arm)}
        for leg, names in CHAINS.items():
            bones = [arm.pose.bones[n] for n in names]
            pts = [arm.matrix_world @ b.head for b in bones] + [arm.matrix_world @ bones[-1].tail]
            bend = (pts[1] - pts[0]).cross(pts[2] - pts[0])
            row["legs"][leg] = {
                "points": [list(v) for v in pts],
                "segment_lengths": [(pts[i + 1] - pts[i]).length for i in range(3)],
                "bend_normal": list(bend.normalized()) if bend.length > 1e-9 else None,
                "knee_flexion_deg": 180.0 - math.degrees((pts[0] - pts[1]).angle(pts[2] - pts[1])),
            }
        result["frames"].append(row)
    return result


def slip_summary(points, states):
    deltas = []
    for i in range(1, min(len(points), len(states))):
        if states[i - 1] == "STANCE" and states[i] == "STANCE":
            deltas.append(float(np.linalg.norm((np.asarray(points[i]) - np.asarray(points[i - 1]))[:2])))
    return {"stance_pairs": len(deltas), "planar_path_length": float(sum(deltas)),
            "mean_per_frame_slip": float(np.mean(deltas)) if deltas else None,
            "max_per_frame_slip": float(max(deltas, default=0.0))}


def main():
    # Start with the baseline scene already opened by command line.
    baseline = capture_current()
    baseline_path = OUT / "baseline_physics_readback.json"
    baseline_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    bpy.ops.wm.open_mainfile(filepath=str(CANDIDATE))
    candidate = capture_current()
    contact_obs = json.loads((OUT / "contact_observations.json").read_text(encoding="utf-8"))
    candidate_audit = json.loads((OUT / "candidate_anchor_audit.json").read_text(encoding="utf-8"))
    original_report = json.loads((OUT / "contact_lock_comparison.json").read_text(encoding="utf-8"))
    before_legs, after_legs, slip_comparison = {}, {}, {}
    bend_dots, length_deltas = [], []
    for leg in CHAINS:
        states = [r["state"] for r in contact_obs["frames"][leg]]
        before_pts = [r["sole"] for r in contact_obs["frames"][leg]]
        after_pts = [r["centroid"] for r in candidate_audit[leg]["rows"]]
        bslip, aslip = slip_summary(before_pts, states), slip_summary(after_pts, states)
        before_legs[leg] = {**original_report["before"]["legs"][leg], "contact_pairs": bslip}
        after_clearance = [r["clearance"] for r in candidate_audit[leg]["rows"]]
        stance_clearance = [r["clearance"] for r, s in zip(candidate_audit[leg]["rows"], states) if s == "STANCE"]
        swing_clearance = [r["clearance"] for r, s in zip(candidate_audit[leg]["rows"], states) if s == "SWING"]
        flexes, per_frame_length_error, per_frame_bend_dot = [], [], []
        for b_row, c_row in zip(baseline["frames"], candidate["frames"]):
            bp, cp = b_row["legs"][leg], c_row["legs"][leg]
            flexes.append(cp["knee_flexion_deg"])
            per_frame_length_error.append(max(abs(a - b) for a, b in zip(bp["segment_lengths"], cp["segment_lengths"])))
            if bp["bend_normal"] and cp["bend_normal"]:
                d = float(np.dot(bp["bend_normal"], cp["bend_normal"]))
                per_frame_bend_dot.append(d)
                bend_dots.append(d)
            length_deltas.extend(per_frame_length_error[-1:])
        counts = {state: states.count(state) for state in ("STANCE", "SWING", "UNCERTAIN")}
        after_legs[leg] = {
            "sole_patch_vertices": int(original_report["geometry_verification"][leg]["vertices"]),
            "contact_pairs": aslip,
            "stance_min_clearance": min(stance_clearance) if stance_clearance else None,
            "stance_max_clearance": max(stance_clearance) if stance_clearance else None,
            "swing_min_clearance": min(swing_clearance) if swing_clearance else None,
            "all_frame_min_clearance": min(after_clearance),
            "max_knee_flexion_deg": max(flexes), "min_knee_flexion_deg": min(flexes),
            "min_bend_normal_dot_vs_baseline": min(per_frame_bend_dot) if per_frame_bend_dot else None,
            "max_segment_length_delta_vs_baseline": max(per_frame_length_error),
            "anchor_residual_xy_mean": candidate_audit[leg]["mean_anchor_residual_xy"],
            "anchor_residual_xy_max": candidate_audit[leg]["max_anchor_residual_xy"],
            "state_counts": counts,
            "correction": original_report["after"]["legs"][leg]["correction"],
        }
        bv, av = bslip["mean_per_frame_slip"], aslip["mean_per_frame_slip"]
        slip_comparison[leg] = {"before_mean_slip": bv, "after_mean_slip": av,
                                "relative_change": (av - bv) / bv if bv and av is not None else None,
                                "status": "UNVERIFIED" if bv is None or av is None else ("PASS" if av < bv else "FAIL")}
    proxy_before = [r["proxy"] for r in baseline["frames"]]
    proxy_after = [r["proxy"] for r in candidate["frames"]]
    def proxy_summary(rows):
        return {"frames_with_hits": sum(r["count"] > 0 for r in rows),
                "max_hits_in_frame": max(r["count"] for r in rows),
                "max_overlap_sum": max(r["overlap_sum"] for r in rows),
                "max_single_overlap": max(r["maximum_overlap"] for r in rows)}
    supports = [sum(r["state"] == "STANCE" for r in contact_obs["frames"][leg]) for leg in CHAINS]
    support_by_frame = [sum(contact_obs["frames"][leg][i]["state"] == "STANCE" for leg in CHAINS) for i in range(121)]
    endpoint = max(float(np.linalg.norm(np.asarray(candidate_audit[leg]["rows"][0]["centroid"]) -
                                        np.asarray(candidate_audit[leg]["rows"][-1]["centroid"]))) for leg in CHAINS)
    criterion = {
        "foot_sliding": {leg: slip_comparison[leg]["status"] for leg in CHAINS},
        "ground_penetration": "PASS" if min(v["all_frame_min_clearance"] for v in after_legs.values()) >= -0.003 else "FAIL",
        "swing_clearance": "UNVERIFIED: contact-state detector produces sparse swing samples and sub-millimeter lift on this baseline",
        "knee_direction": "PASS" if min(bend_dots, default=-1) >= 0.95 else "FAIL",
        "bone_lengths": "PASS" if max(length_deltas, default=0) <= 1e-4 else "FAIL",
        "leg_collisions": "UNVERIFIED: capsule proxy checks do not test exact evaluated-mesh self-intersection",
        "proxy_collision_checks": "PASS" if proxy_summary(proxy_after)["max_overlap_sum"] <= proxy_summary(proxy_before)["max_overlap_sum"] + 1e-5 else "FAIL",
        "body_support_stability": "UNVERIFIED: no mass/center-of-mass model; contact support count recorded",
        "loop_continuity": "PASS" if endpoint <= 0.003 else "FAIL",
    }
    updated = {
        **original_report,
        "measurement_source": "fresh read-back from baseline and saved candidate .blend, 121 evaluated samples, fixed same sole patch IDs and baseline contact-state windows",
        "before": {**original_report["before"], "legs": before_legs,
                   "proxy_collisions": proxy_summary(proxy_before)},
        "after": {**original_report["after"], "legs": after_legs,
                  "proxy_collisions": proxy_summary(proxy_after),
                  "support": {"minimum_stance_legs": min(support_by_frame),
                              "mean_stance_legs": float(np.mean(support_by_frame))},
                  "loop": {"sampled_frames_including_endpoint": 121,
                           "endpoint_sole_error_max": endpoint}},
        "per_leg_slip_comparison": slip_comparison,
        "criteria": criterion,
        "artifact_status": "VALIDATED_CANDIDATE" if all(v == "PASS" for v in criterion.values()) else "CANDIDATE_WITH_LIMITATIONS",
    }
    (OUT / "contact_lock_comparison.json").write_text(json.dumps(updated, indent=2), encoding="utf-8")
    print("READBACK_VALIDATION " + json.dumps({"status": updated["artifact_status"],
          "criteria": criterion, "slip": slip_comparison,
          "proxy_before": updated["before"]["proxy_collisions"],
          "proxy_after": updated["after"]["proxy_collisions"]}), flush=True)


if __name__ == "__main__":
    main()
