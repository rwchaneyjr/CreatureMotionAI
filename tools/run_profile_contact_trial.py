"""Profile-driven contact-lock trial for an isolated creature copy.

The runner consumes a user-confirmed anatomy JSON, preserves its source Action,
uses only the configured terminal bone's weighted underside mesh patch, and
writes a separate candidate .blend/report/render sequence. Ground height may be
provided explicitly; otherwise it is conservatively inferred from foot-surface
observations and marked as inferred in the report.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from creature_motion_ai.contact_lock import (centroid_world, make_tracker, patch_clearance,
                                               select_sole_patch, stance_slip)
from creature_motion_ai import ik_step, collision_proxies


def evaluated_world_mesh(mesh):
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    xyz = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", xyz)
    xyz = xyz.reshape(-1, 3)
    matrix = np.asarray(ev.matrix_world, dtype=np.float64)
    world = xyz @ matrix[:3, :3].T + matrix[:3, 3]
    normal = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("normal", normal)
    normal = normal.reshape(-1, 3) @ np.linalg.inv(matrix[:3, :3])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)
    ev.to_mesh_clear()
    return world, normal


def weight_array(mesh, group_name):
    group = mesh.vertex_groups.get(group_name)
    if group is None:
        raise ValueError(f"No mesh vertex group for configured terminal bone {group_name!r}")
    values = np.zeros(len(mesh.data.vertices), dtype=np.float32)
    for vertex in mesh.data.vertices:
        for membership in vertex.groups:
            if membership.group == group.index:
                values[vertex.index] = membership.weight
    return values


def validate_profile(arm, mesh, profile):
    if profile.get("armature") != arm.name or not profile.get("confirmed"):
        raise ValueError("Anatomy profile is not user-confirmed for this armature")
    chains = {}
    for item in profile.get("legs", []):
        name, chain = item["name"], item["bones"]
        if len(chain) != 3:
            raise ValueError(f"{name}: current two-link contact solver requires a 3-bone chain")
        for i, bone_name in enumerate(chain):
            if bone_name not in arm.pose.bones:
                raise ValueError(f"{name}: missing bone {bone_name}")
            if i and arm.data.bones[bone_name].parent.name != chain[i - 1]:
                raise ValueError(f"{name}: chain parent mismatch at {bone_name}")
        if item.get("contact_bone") != chain[-1]:
            raise ValueError(f"{name}: configured contact bone must be chain terminal for this solver")
        weight_array(mesh, item["contact_bone"])
        chains[name] = chain
    if not chains:
        raise ValueError("Profile contains no leg chains")
    return chains


def collect_surface_candidates(scene, arm, mesh, chains, weights, frames):
    candidates = {name: [] for name in chains}
    lows = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        world, normals = evaluated_world_mesh(mesh)
        for name, chain in chains.items():
            bones = [arm.pose.bones[n] for n in chain]
            points = [arm.matrix_world @ bone.head for bone in bones] + [arm.matrix_world @ bones[-1].tail]
            length = max((points[3] - points[2]).length, 1e-8)
            direction = np.asarray((points[3] - points[2]).normalized(), dtype=np.float64)
            along = (world - np.asarray(points[2], dtype=np.float64)) @ direction
            eligible = (weights[name] >= 0.35) & (along >= 0.15 * length) & (normals[:, 2] < -0.25)
            ids = np.flatnonzero(eligible)
            if len(ids) < 12:
                continue
            z = world[ids, 2]
            low = ids[z <= z.min() + 0.003]
            pts = world[low]
            if len(low) < 12:
                continue
            min_z = float(pts[:, 2].min())
            lows.append(min_z)
            candidates[name].append({"frame": frame, "vertex_indices": low,
                                     "world_positions": pts, "clearance": min_z,
                                     "underside_fraction": float(np.mean(normals[low, 2] < -0.25))})
    if not lows:
        raise ValueError("No terminal weighted underside regions found; cannot infer ground/contact")
    # The low tail is based on sole-like weighted regions only, not the full mesh bounds.
    floor = float(np.percentile(np.asarray(lows), 2.0))
    return candidates, floor, {"min": min(lows), "p02": floor, "p50": float(np.median(lows)),
                               "max": max(lows), "observations": len(lows)}


def derive_patches(candidates, ground_z):
    patches, report = {}, {}
    for name, rows in candidates.items():
        calibrated = []
        for row in rows:
            item = dict(row)
            item["clearance"] = float(item["clearance"] - ground_z)
            if item["clearance"] <= 0.03:
                calibrated.append(item)
        try:
            patch = select_sole_patch(calibrated)
        except ValueError as exc:
            report[name] = {"status": "UNVERIFIED", "candidate_frames": len(calibrated), "reason": str(exc)}
            continue
        patches[name] = patch
        report[name] = {"status": "PASS_CANDIDATE_PATCH", "sample_frame": patch.sample_frame,
                         "vertex_count": int(len(patch.vertex_indices)), "quality": patch.quality,
                         "sample_clearance": patch.min_clearance,
                         "extent_xyz": list(patch.extent_xyz)}
    return patches, report


def capture_baseline(scene, arm, mesh, chains, patches, ground_z, frames):
    poses, observations = {}, {name: [] for name in patches}
    trackers = {name: make_tracker() for name in patches}
    lengths = {name: sum(arm.data.bones[b].length for b in chains[name][:2]) for name in patches}
    for frame in frames:
        scene.frame_set(frame); bpy.context.view_layer.update()
        poses[frame] = {bone.name: bone.matrix_basis.copy() for bone in arm.pose.bones}
        world, _ = evaluated_world_mesh(mesh)
        for name, patch in patches.items():
            point = centroid_world(world, patch)
            clearance = patch_clearance(world, patch, ground_z)
            decision = trackers[name].update(frame, point, clearance, lengths[name], anatomy_quality=patch.quality)
            observations[name].append({"frame": frame, "sole": point.tolist(), "clearance": clearance,
                                       "state": decision.state.value, "confidence": decision.confidence,
                                       "anchor": list(decision.anchor_world) if decision.anchor_world else None,
                                       "lock": decision.lock_enabled, "reason": decision.reason})
    return poses, observations, lengths


def set_pose_matrix(arm, bone, matrix):
    bone.matrix = arm.matrix_world.inverted() @ matrix
    bpy.context.view_layer.update()


def lock_leg(arm, mesh, chain, patch, anchor, shift_limit):
    bones = [arm.pose.bones[n] for n in chain]
    bpy.context.view_layer.update()
    points = [arm.matrix_world @ b.head for b in bones] + [arm.matrix_world @ bones[-1].tail]
    world_vertices, _ = evaluated_world_mesh(mesh)
    sole = world_vertices[patch.vertex_indices].mean(axis=0)
    target = points[2] + Vector(anchor) - Vector(sole)
    shift = (target - points[2]).length
    if shift > shift_limit:
        return {"status": "REJECTED", "reason": "reach_budget", "shift": float(shift)}
    world_matrices = [arm.matrix_world @ b.matrix for b in bones]
    bend_normal = (points[1] - points[0]).cross(points[2] - points[0])
    if bend_normal.length < 1e-8:
        return {"status": "REJECTED", "reason": "degenerate_bend_plane", "shift": float(shift)}
    bend_normal.normalize()
    result = ik_step.solve_rest_relative_two_link(points[0], target,
        (points[1]-points[0]).length, (points[2]-points[1]).length,
        bend_normal, min_knee_angle=math.radians(8.0))
    if result.get("status") != "PASS":
        return {"status": "REJECTED", "reason": result.get("reason", "ik_rejected"), "shift": float(shift)}
    flex = 180.0 - math.degrees(result["knee_angle"])
    if flex > 135.0:
        return {"status": "REJECTED", "reason": "knee_flex_limit", "flex_deg": flex, "shift": float(shift)}
    inverse = arm.matrix_world.inverted()
    desired = [(points[0], result["knee"]), (result["knee"], target)]
    for index, (head, tail) in enumerate(desired):
        matrix = ik_step.world_direction_pose_matrix(world_matrices[index], points[index], head, tail, points[index+1])
        bones[index].matrix = inverse @ matrix
        bpy.context.view_layer.update()
    ik_step.restore_terminal_foot_world_orientation(arm, chain[2], world_matrices[2], target)
    bpy.context.view_layer.update()
    actual = [arm.matrix_world @ b.head for b in bones] + [arm.matrix_world @ bones[-1].tail]
    new_normal = (actual[1]-actual[0]).cross(actual[2]-actual[0])
    bend_dot = float(new_normal.normalized().dot(bend_normal)) if new_normal.length else -1.0
    length_error = max(abs((actual[i+1]-actual[i]).length-(points[i+1]-points[i]).length) for i in range(3))
    if bend_dot < .95 or length_error > 1e-4:
        for bone, matrix in zip(bones, world_matrices):
            set_pose_matrix(arm, bone, matrix)
        return {"status":"REJECTED","reason":"bend_or_length_validation","bend_dot":bend_dot,
                "length_error":length_error,"shift":float(shift)}
    return {"status":"PASS","shift":float(shift),"knee_flexion_deg":flex,
            "bend_dot":bend_dot,"length_error":length_error}


def segments_and_overlaps(arm, chains, body_bones):
    segments = collision_proxies.segments_for_chains(arm, chains, body_bones)
    hits=[]; overlap_sum=0.0
    for i, a in enumerate(segments):
        for b in segments[i+1:]:
            if a["region"] == b["region"]:
                continue
            overlap=a["r"]+b["r"]-collision_proxies._segdist(a["a"],a["b"],b["a"],b["b"])
            if overlap>0:
                hits.append({"bone_a":a["bone"],"bone_b":b["bone"],"overlap":float(overlap)})
                overlap_sum+=float(overlap)
    return hits, overlap_sum


def insert_pose_keys(action_arm, frame):
    for pose_bone in action_arm.pose.bones:
        pose_bone.keyframe_insert("location", frame=frame, group=pose_bone.name)
        if pose_bone.rotation_mode == 'QUATERNION':
            pose_bone.keyframe_insert("rotation_quaternion", frame=frame, group=pose_bone.name)
        elif pose_bone.rotation_mode == 'AXIS_ANGLE':
            pose_bone.keyframe_insert("rotation_axis_angle", frame=frame, group=pose_bone.name)
        else:
            pose_bone.keyframe_insert("rotation_euler", frame=frame, group=pose_bone.name)
        pose_bone.keyframe_insert("scale", frame=frame, group=pose_bone.name)


def action_fcurves(action):
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    return list(bag.fcurves)
    return list(getattr(action, "fcurves", []))


def measure_variant(scene, arm, mesh, chains, patches, ground_z, frames, baseline_poses, observations, body_bones,
                    action_name):
    action=bpy.data.actions.new(action_name); action.use_fake_user=True
    slot=action.slots.new(arm.id_type,arm.name)
    arm.animation_data_create(); arm.animation_data.action=action
    if hasattr(arm.animation_data,"action_slot"): arm.animation_data.action_slot=slot
    per_leg={name:{"attempted":0,"accepted":0,"rejected":0,"reasons":{}} for name in chains}
    rows=[]
    obs_lookup={name:{row["frame"]:row for row in values} for name,values in observations.items()}
    for frame in frames:
        scene.frame_set(frame)
        for bone in arm.pose.bones:
            bone.matrix_basis=baseline_poses[frame][bone.name]
        bpy.context.view_layer.update()
        before_geometry={}
        for name,chain in chains.items():
            bones=[arm.pose.bones[n] for n in chain]
            pts=[arm.matrix_world@b.head for b in bones]+[arm.matrix_world@bones[-1].tail]
            normal=(pts[1]-pts[0]).cross(pts[2]-pts[0])
            before_geometry[name]={"points":pts,"normal":normal.normalized() if normal.length else Vector((0,0,0)),
                "lengths":[(pts[i+1]-pts[i]).length for i in range(3)]}
        corrections={}
        for name,patch in patches.items():
            obs=obs_lookup[name][frame]
            if obs["lock"] and obs["anchor"] is not None:
                per_leg[name]["attempted"]+=1
                result=lock_leg(arm,mesh,chains[name],patch,obs["anchor"],
                                .10*sum(arm.data.bones[b].length for b in chains[name][:2]))
                corrections[name]=result
                if result["status"]=="PASS": per_leg[name]["accepted"]+=1
                else:
                    per_leg[name]["rejected"]+=1
                    reason=result.get("reason","unknown"); per_leg[name]["reasons"][reason]=per_leg[name]["reasons"].get(reason,0)+1
        bpy.context.view_layer.update()
        insert_pose_keys(arm,frame)
        bpy.context.view_layer.update()
        world,_=evaluated_world_mesh(mesh)
        leg_results={}
        for name,patch in patches.items():
            chain=chains[name]; bones=[arm.pose.bones[n] for n in chain]
            pts=[arm.matrix_world@b.head for b in bones]+[arm.matrix_world@bones[-1].tail]
            knee_angle=(pts[0]-pts[1]).angle(pts[2]-pts[1])
            bend=(pts[1]-pts[0]).cross(pts[2]-pts[0])
            ref=before_geometry[name]["normal"]
            leg_results[name]={"state":obs_lookup[name][frame]["state"],
                "confidence":obs_lookup[name][frame]["confidence"],
                "sole":centroid_world(world,patch).tolist(),
                "clearance":patch_clearance(world,patch,ground_z),
                "knee_flexion_deg":180.0-math.degrees(knee_angle),
                "bend_dot":float(bend.normalized().dot(ref)) if bend.length else -1.0,
                "correction":corrections.get(name)}
        hits,overlap=segments_and_overlaps(arm,chains,body_bones)
        rows.append({"frame":frame,"legs":leg_results,"proxy_collision_count":len(hits),
                     "proxy_overlap_sum":overlap,"proxy_collisions":hits})
    for curve in action_fcurves(action):
        for key in curve.keyframe_points:
            key.interpolation='LINEAR'
    return action,rows,per_leg


def summarize(rows, names):
    leg_summary={}
    for name in names:
        values=[r["legs"][name] for r in rows]
        states=[v["state"] for v in values]
        leg_summary[name]={
            "stance_slip":stance_slip([v["sole"] for v in values],states),
            "stance_clearance_min":min((v["clearance"] for v in values if v["state"]=="STANCE"),default=None),
            "stance_clearance_max":max((v["clearance"] for v in values if v["state"]=="STANCE"),default=None),
            "min_swing_clearance":min((v["clearance"] for v in values if v["state"]=="SWING"),default=None),
            "state_counts":{s:states.count(s) for s in ("STANCE","SWING","UNCERTAIN")},
            "max_abs_bend_dot_error":max((abs(1-v["bend_dot"]) for v in values),default=0.0)}
    stance_count=[sum(v["state"]=="STANCE" for v in r["legs"].values()) for r in rows]
    return {"legs":leg_summary,
        "support":{"minimum_stance_legs":min(stance_count,default=0),"mean_stance_legs":float(np.mean(stance_count)) if stance_count else 0.0},
        "proxy_collisions":{"frames_with_proxy_hits":sum(r["proxy_collision_count"]>0 for r in rows),
                             "max_hits":max((r["proxy_collision_count"] for r in rows),default=0),
                             "max_overlap_sum":max((r["proxy_overlap_sum"] for r in rows),default=0.0)},
        "frame_count":len(rows)}


def render_sequence(scene, output, frames):
    output.mkdir(parents=True,exist_ok=True)
    old_path=scene.render.filepath; old_fmt=scene.render.image_settings.file_format
    old_percentage=scene.render.resolution_percentage
    scene.render.resolution_percentage=65
    scene.render.image_settings.file_format='PNG'
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath=str(output/f"frame_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    scene.render.filepath=old_path; scene.render.image_settings.file_format=old_fmt
    scene.render.resolution_percentage=old_percentage


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--profile",required=True); parser.add_argument("--action",default="Move_Scissor_Offset")
    parser.add_argument("--output-dir",required=True); parser.add_argument("--ground-z",type=float,default=None)
    parser.add_argument("--render",action="store_true")
    args,_=parser.parse_known_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    profile=json.loads(Path(args.profile).read_text(encoding="utf-8"))
    scene=bpy.context.scene
    arm=bpy.data.objects.get(profile.get("armature"))
    if arm is None: raise RuntimeError("Profile armature not found in isolated test file")
    meshes=[o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers)]
    if len(meshes)!=1: raise RuntimeError(f"Expected one mesh bound to selected armature; found {len(meshes)}")
    mesh=meshes[0]; chains=validate_profile(arm,mesh,profile)
    source=bpy.data.actions.get(args.action)
    if source is None: raise RuntimeError(f"Starting Action not found: {args.action}")
    arm.animation_data_create(); arm.animation_data.action=source
    if source.slots and hasattr(arm.animation_data,"action_slot"): arm.animation_data.action_slot=source.slots[0]
    start,end=(int(round(v)) for v in source.frame_range)
    if end<=start: raise RuntimeError("Action has no usable frame range")
    frames=list(range(start,end+1))
    weights={name:weight_array(mesh,chain[-1]) for name,chain in chains.items()}
    candidates,inferred_ground,ground_stats=collect_surface_candidates(scene,arm,mesh,chains,weights,frames)
    ground_z=args.ground_z if args.ground_z is not None else inferred_ground
    patches,patch_report=derive_patches(candidates,ground_z)
    out=Path(args.output_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
    if len(patches)!=len(chains):
        report={"status":"FAIL_PATCH_COVERAGE","source_action":source.name,"frame_range":[start,end],
                "ground_z":ground_z,"ground_source":"USER" if args.ground_z is not None else "INFERRED_FROM_ANIMATED_TERMINAL_UNDERSIDE",
                "ground_inference_stats":ground_stats,"profile":str(Path(args.profile).resolve()),
                "patches":patch_report,"note":"No animation candidate was generated because every configured foot lacks a verified weighted sole patch."}
        (out/"contact_lock_validation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        print("CONTACT_TRIAL_RESULT "+json.dumps({"status":report["status"],"report":str(out/"contact_lock_validation.json")}),flush=True)
        return
    base_poses,observations,lengths=capture_baseline(scene,arm,mesh,chains,patches,ground_z,frames)
    source_slot=getattr(arm.animation_data,"action_slot",None)
    candidate,after_rows,counts=measure_variant(scene,arm,mesh,chains,patches,ground_z,frames,base_poses,observations,
                                                 profile.get("body_bones",[]),"CMAI_ContactLocked_"+Path(args.profile).stem)
    after=summarize(after_rows,chains)
    # Re-measure baseline through the same patches/state labels and collision proxy logic.
    arm.animation_data.action=source
    if source_slot and hasattr(arm.animation_data,"action_slot"): arm.animation_data.action_slot=source_slot
    baseline_rows=[]
    for frame in frames:
        scene.frame_set(frame)
        for bone in arm.pose.bones: bone.matrix_basis=base_poses[frame][bone.name]
        bpy.context.view_layer.update()
        world,_=evaluated_world_mesh(mesh); legs={}
        for name,patch in patches.items():
            obs=next(row for row in observations[name] if row["frame"]==frame)
            chain=chains[name]; bones=[arm.pose.bones[n] for n in chain]
            pts=[arm.matrix_world@b.head for b in bones]+[arm.matrix_world@bones[-1].tail]
            bend=(pts[1]-pts[0]).cross(pts[2]-pts[0])
            legs[name]={"state":obs["state"],"confidence":obs["confidence"],
                        "sole":centroid_world(world,patch).tolist(),"clearance":patch_clearance(world,patch,ground_z),
                        "knee_flexion_deg":180-math.degrees((pts[0]-pts[1]).angle(pts[2]-pts[1])),
                        "bend_dot":1.0 if bend.length else -1.0}
        hits,overlap=segments_and_overlaps(arm,chains,profile.get("body_bones",[]))
        baseline_rows.append({"frame":frame,"legs":legs,"proxy_collision_count":len(hits),"proxy_overlap_sum":overlap})
    before=summarize(baseline_rows,chains)
    slip_compare={}
    for name in chains:
        b=before["legs"][name]["stance_slip"]; a=after["legs"][name]["stance_slip"]
        bv=b["mean_per_frame_slip"]; av=a["mean_per_frame_slip"]
        slip_compare[name]={"before":b,"after":a,"relative_change":None if bv in (None,0) or av is None else (av-bv)/bv,
                            "status":"UNVERIFIED" if bv is None or av is None else ("PASS" if av<bv else "NO_IMPROVEMENT")}
    max_correction=max((c.get("length_error",0.0) for row in after_rows for c in row["legs"].values() if c.get("correction")),default=0.0)
    all_collisions=[row["proxy_collision_count"] for row in after_rows]
    endpoint_error=max((np.linalg.norm(np.asarray(after_rows[0]["legs"][n]["sole"])-np.asarray(after_rows[-1]["legs"][n]["sole"])) for n in patches),default=0.0)
    report={"schema_version":1,"status":"CONTACT_LOCK_TRIAL_COMPLETE","source_blend":bpy.data.filepath,
        "source_action":source.name,"candidate_action":candidate.name,"frame_range":[start,end],"fps":scene.render.fps,
        "profile":str(Path(args.profile).resolve()),"leg_count":len(chains),"ground_z":ground_z,
        "ground_source":"USER_PROVIDED" if args.ground_z is not None else "INFERRED_FROM_LOW_TAIL_OF_TERMINAL_WEIGHTED_UNDERSIDE_SAMPLES",
        "ground_inference_stats":ground_stats,"patches":patch_report,"before":before,"after":after,
        "foot_slip_comparison":slip_compare,"correction_counts":counts,
        "criteria":{"patch_coverage":"PASS" if len(patches)==len(chains) else "FAIL",
            "foot_slip":"PASS" if all(x["status"]=="PASS" for x in slip_compare.values()) else "FAIL_OR_UNVERIFIED",
            "ground_penetration":"PASS" if min(v["clearance"] for r in after_rows for v in r["legs"].values())>=-0.003 else "FAIL",
            "bone_lengths":"PASS" if max_correction<=1e-4 else "FAIL",
            "support_stability":"PASS" if after["support"]["minimum_stance_legs"]>=2 else "FAIL",
            "proxy_collisions":"PASS" if max(all_collisions,default=0)==0 else "FAIL_PROXY_ONLY",
            "loop_continuity":"PASS" if endpoint_error<=0.003 else "FAIL",
            "full_mesh_self_collision":"UNVERIFIED"},
        "limitations":["Ground height was inferred because this file contains no named ground object.",
            "Distal weighted underside patches are model-derived contact candidates, not artist-authored sole labels.",
            "Collision output uses segment capsule proxies; it does not prove full mesh self-intersection absence.",
            "Existing-action contact locking is evaluated on the configured three-bone quadruped legs only; wings and tail are preserved from source Action."]}
    report_path=out/"contact_lock_validation.json"
    report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    (out/"contact_lock_frames.json").write_text(json.dumps({"observations":observations,"candidate_frames":after_rows},indent=2),encoding="utf-8")
    # Keep source and candidate Actions; candidate remains active in this separate deliverable.
    arm.animation_data.action=candidate
    if candidate.slots and hasattr(arm.animation_data,"action_slot"): arm.animation_data.action_slot=candidate.slots[0]
    scene.frame_set(start); bpy.context.view_layer.update()
    blend_path=out/"CrimsonWingedDragon_contact_lock_candidate.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path),copy=False)
    (out/"source_action_preview").mkdir(exist_ok=True)
    (out/"contact_lock_preview").mkdir(exist_ok=True)
    if args.render:
        arm.animation_data.action=source
        if source.slots and hasattr(arm.animation_data,"action_slot"): arm.animation_data.action_slot=source.slots[0]
        render_sequence(scene,out/"source_action_preview",frames)
        arm.animation_data.action=candidate
        if candidate.slots and hasattr(arm.animation_data,"action_slot"): arm.animation_data.action_slot=candidate.slots[0]
        render_sequence(scene,out/"contact_lock_preview",frames)
    print("CONTACT_TRIAL_RESULT "+json.dumps({"blend":str(blend_path),"report":str(report_path),
        "candidate_action":candidate.name,"criteria":report["criteria"]}),flush=True)


if __name__=="__main__":
    main()
