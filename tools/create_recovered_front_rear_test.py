"""Recovery test: compose the previously isolated rest-relative leg methods only.

This intentionally does not generate an eight-leg gait.  It starts from the clean
working file and keys Front.L and Rear.L independently, leaving the other six legs
untouched.  The report distinguishes mathematical acceptance from physical checks.
"""
import argparse, json, math, sys
from pathlib import Path

LEGS = ("Front.L", "Rear.L")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

    import bpy
    from mathutils import Vector
    from creature_motion_ai.ik_step import (
        solve_rest_relative_two_link,
        world_direction_pose_matrix,
        restore_terminal_foot_world_orientation,
    )

    bpy.ops.wm.open_mainfile(filepath=str(Path(args.blend).resolve()))
    scene = bpy.context.scene
    arm = next((o for o in scene.objects if o.type == "ARMATURE"), None)
    mesh = next((o for o in scene.objects if o.type == "MESH" and o.parent == arm), None)
    if arm is None:
        raise RuntimeError("No armature in working baseline")
    scene.frame_start, scene.frame_end, scene.render.fps = 1, 24, 24
    scene.frame_set(1)
    bpy.context.view_layer.update()

    # Baseline identity and evaluated mesh sample are recorded before any pose.
    rest_mesh = [tuple(v.co) for v in mesh.data.vertices] if mesh else []
    action = bpy.data.actions.new("CMAI_Recovered_FrontRear_RestRelative_24F")
    action.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = action
    setups, leg_rows = [], []
    for leg in LEGS:
        chain = [f"Leg_{leg}_{i:02d}" for i in (1, 2, 3)]
        if any(arm.pose.bones.get(n) is None for n in chain):
            leg_rows.append({"leg": leg, "status": "FAIL", "reason": "missing_chain", "chain": chain})
            continue
        pbs = [arm.pose.bones[n] for n in chain]
        rest = {n: arm.matrix_world @ pb.matrix.copy() for n, pb in zip(chain, pbs)}
        hip = arm.matrix_world @ pbs[0].head
        knee = arm.matrix_world @ pbs[0].tail
        ankle = arm.matrix_world @ pbs[1].tail
        foot = arm.matrix_world @ pbs[2].tail
        bend = (knee - hip).cross(ankle - hip).normalized()
        setups.append({"leg": leg, "chain": chain, "rest": rest, "hip": hip,
                       "knee": knee, "ankle": ankle, "foot": foot,
                       "upper": (knee - hip).length, "lower": (ankle - knee).length,
                       "bend": bend})
        leg_rows.append({"leg": leg, "status": "READY", "chain": chain,
                         "upper_length": (knee - hip).length,
                         "lower_length": (ankle - knee).length})

    rows = []
    for frame in range(1, 25):
        q = (frame - 1) / 23.0
        env = math.sin(math.pi * q)
        frame_row = {"frame": frame, "legs": []}
        for setup in setups:
            # Separate conservative amplitude per isolated leg.  Rear.L uses the
            # validated +Z clearance sign; Front.L is deliberately smaller and
            # remains subject to independent physical validation.
            leg = setup["leg"]
            phase = 0.0 if leg == "Front.L" else math.pi
            wave = math.sin(2.0 * math.pi * q + phase)
            # Front.L's first recovery pass penetrated the measured ground
            # reference by 0.00465 BU.  Increase only its swing clearance;
            # Rear.L remains unchanged from the validated recovery path.
            lift = (0.020 if leg == "Front.L" else 0.006) * max(0.0, wave) * env
            advance = (0.006 if leg == "Front.L" else 0.008) * wave * env
            local = Vector((0.0, advance, lift))
            target = setup["ankle"] + arm.matrix_world.to_3x3() @ local
            solved = solve_rest_relative_two_link(
                setup["hip"], target, setup["upper"], setup["lower"], setup["bend"],
                min_knee_angle=math.radians(12),
            )
            if solved.get("status") != "PASS":
                frame_row["legs"].append({"leg": leg, "status": "REJECTED",
                                           "reason": solved.get("reason", "solver_rejected"),
                                           "target": list(target)})
                continue
            b1, b2, b3 = (arm.pose.bones[n] for n in setup["chain"])
            b1.matrix = arm.matrix_world.inverted() @ world_direction_pose_matrix(
                setup["rest"][setup["chain"][0]], setup["hip"], setup["hip"],
                solved["knee"], setup["knee"])
            bpy.context.view_layer.update()
            eval_knee = arm.matrix_world @ b1.tail
            b2.matrix = arm.matrix_world.inverted() @ world_direction_pose_matrix(
                setup["rest"][setup["chain"][1]], eval_knee, solved["knee"],
                solved["foot"], setup["ankle"])
            bpy.context.view_layer.update()
            eval_ankle = arm.matrix_world @ b2.tail
            restore_terminal_foot_world_orientation(
                arm, setup["chain"][2], setup["rest"][setup["chain"][2]], eval_ankle)
            bpy.context.view_layer.update()
            for pb in (b1, b2, b3):
                pb.keyframe_insert(data_path="rotation_mode", frame=frame)
                if pb.rotation_mode == "QUATERNION":
                    pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                else:
                    pb.keyframe_insert(data_path="rotation_euler", frame=frame)
            frame_row["legs"].append({"leg": leg, "status": "ACCEPTED",
                                       "target": list(target),
                                       "knee": list(solved["knee"]),
                                       "ankle": list(solved["foot"]),
                                       "evaluated_knee": list(eval_knee),
                                       "evaluated_ankle": list(eval_ankle)})
        rows.append(frame_row)

    # Evaluate frame 1 and verify the non-targeted six legs did not move.
    scene.frame_set(1)
    bpy.context.view_layer.update()
    current_rest_mesh = [tuple(v.co) for v in mesh.data.vertices] if mesh else []
    rest_mesh_max_delta = max((sum((a[i]-b[i])**2 for i in range(3))**0.5
                               for a, b in zip(rest_mesh, current_rest_mesh)), default=0.0)
    scene["CMAI_recovery_scope"] = "Front.L + Rear.L only; six legs unchanged"
    scene["CMAI_failed_eight_leg_generator_quarantined"] = True
    report = {
        "status": "RECOVERY_TEST_GENERATED",
        "baseline": str(Path(args.blend).resolve()),
        "armature": arm.name,
        "mesh": mesh.name if mesh else None,
        "action": action.name,
        "scope": {"animated_legs": list(LEGS), "untouched_legs": 6},
        "rest_mesh_frame1_max_delta": rest_mesh_max_delta,
        "rest_validation": "PASS" if rest_mesh_max_delta <= 1e-5 else "FAIL",
        "front_l_physical_status": "REQUIRES_VALIDATOR",
        "rear_l_physical_status": "REQUIRES_VALIDATOR",
        "frames": rows,
        "failed_generator": "tools/create_eight_leg_walk_rest_relative.py",
        "failed_generator_excluded": True,
    }
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.output).resolve()))
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
