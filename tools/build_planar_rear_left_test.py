"""Build a temporary approximate planar Leg_Rear.L test from DLC 2D tracks.

This is explicitly not metric 3D reconstruction. It uses the original rest pose
and a fixed armature-local Y/Z plane, then validates the saved/reloaded Action.
"""
import argparse, json, math, shutil
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True); ap.add_argument("--tracks", required=True)
    ap.add_argument("--output", required=True); ap.add_argument("--report", required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = ap.parse_args(argv)
    import bpy
    from mathutils import Vector
    from creature_motion_ai.ik_step import solve_rest_relative_two_link, world_direction_pose_matrix, restore_terminal_foot_world_orientation
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.blend).resolve()))
    scene = bpy.context.scene
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    mesh = next(o for o in scene.objects if o.type == "MESH")
    chain = ["Leg_Rear.L_01", "Leg_Rear.L_02", "Leg_Rear.L_03"]
    if any(arm.pose.bones.get(n) is None for n in chain):
        raise RuntimeError("Leg_Rear.L chain is incomplete")
    tracks = json.loads(Path(args.tracks).read_text(encoding="utf-8"))
    rows = {int(x["frame"]): x for x in tracks["frames"] if int(x["frame"]) <= 24}
    scene.frame_set(1); bpy.context.view_layer.update()
    rest = {n: arm.matrix_world @ arm.pose.bones[n].matrix.copy() for n in chain}
    hip0 = arm.matrix_world @ arm.pose.bones[chain[0]].head
    knee0 = arm.matrix_world @ arm.pose.bones[chain[0]].tail
    ankle0 = arm.matrix_world @ arm.pose.bones[chain[1]].tail
    foot0 = arm.matrix_world @ arm.pose.bones[chain[2]].tail
    upper_len = (knee0 - hip0).length; lower_len = (ankle0 - knee0).length
    bend_normal = (knee0 - hip0).cross(ankle0 - hip0)
    if bend_normal.length < 1e-8: bend_normal = Vector((1, 0, 0))
    # side-view pixel coordinates: x -> armature-local Y, image-down y -> -Z
    baseline = rows[1]["landmarks_2d"]
    base_vec = Vector((baseline["foot"][0] - baseline["hip"][0], baseline["foot"][1] - baseline["hip"][1]))
    px_per_unit = max(base_vec.length / max((foot0 - hip0).length, 1e-6), 1e-6)
    rest_local = arm.matrix_world.inverted() @ foot0
    action = bpy.data.actions.new("CMAI_RearL_Planar_Test_24F"); action.use_fake_user = True
    arm.animation_data_create(); arm.animation_data.action = action
    accepted = []; rejected = []; keyframes = []
    last_uv = None
    for f in range(1, 25):
        row = rows.get(f)
        if row is None: rejected.append({"frame": f, "reason": "missing_track"}); continue
        uv = row["landmarks_2d"]; conf = row["confidence"]
        # Low-confidence ankle/foot values are held at the previous accepted value;
        # they are never treated as verified observations.
        if last_uv is None: last_uv = uv
        use = dict(uv)
        for k in ("ankle", "foot"):
            if conf.get(k, 0.0) < 0.6: use[k] = last_uv[k]
        last_uv = use
        dpx = Vector((use["foot"][0] - use["hip"][0] - base_vec[0], use["foot"][1] - use["hip"][1] - base_vec[1]))
        d = dpx / px_per_unit
        # fixed rest anatomical plane: local Y is image horizontal, local Z is image vertical
        # The analytical two-link target is the ankle joint, while the tracked
        # foot point is the terminal segment. Apply the observed displacement to
        # the original ankle, not to the terminal-foot tail.
        target = ankle0 + arm.matrix_world.to_3x3() @ Vector((0.0, d.x, -d.y))
        # Project out-of-workspace observations to a conservative reachable
        # shell. This preserves the observed direction but explicitly records
        # that the resulting pose is model-constrained, not a direct solve.
        vec = target - hip0; dist = vec.length
        safe_max = upper_len + lower_len - 0.02 * max(upper_len, lower_len)
        safe_min = abs(upper_len - lower_len) + 0.02 * max(upper_len, lower_len)
        clamped = False
        if dist > safe_max or dist < safe_min:
            if dist < 1e-8: vec = (ankle0 - hip0).normalized(); dist = vec.length
            target = hip0 + vec.normalized() * max(safe_min, min(safe_max, dist))
            clamped = True
        solved = solve_rest_relative_two_link(hip0, target, upper_len, lower_len, bend_normal, min_knee_angle=math.radians(8.0))
        if solved.get("status") != "PASS":
            rejected.append({"frame": f, "reason": solved.get("reason", "solve_failed")}); continue
        # Apply in hierarchy order, then restore the connected terminal foot orientation.
        b1 = arm.pose.bones[chain[0]]; b2 = arm.pose.bones[chain[1]]
        m1 = world_direction_pose_matrix(rest[chain[0]], hip0, hip0, solved["knee"], knee0)
        b1.matrix = arm.matrix_world.inverted() @ m1; bpy.context.view_layer.update()
        m2 = world_direction_pose_matrix(rest[chain[1]], knee0, solved["knee"], solved["foot"], ankle0)
        b2.matrix = arm.matrix_world.inverted() @ m2; bpy.context.view_layer.update()
        restore_terminal_foot_world_orientation(arm, chain[2], rest[chain[2]], arm.matrix_world @ b2.tail)
        bpy.context.view_layer.update()
        for b in (b1, b2, arm.pose.bones[chain[2]]):
            b.keyframe_insert("rotation_mode", frame=f)
            if b.rotation_mode == "QUATERNION": b.keyframe_insert("rotation_quaternion", frame=f)
            else: b.keyframe_insert("rotation_euler", frame=f)
        keyframes.append(f); accepted.append({"frame": f, "confidence": conf, "workspace_clamped": clamped, "used_hold_for_low_confidence": [k for k in ("ankle", "foot") if conf.get(k, 0.0) < 0.6]})
    scene.frame_start = 1; scene.frame_end = 24; scene.render.fps = 24
    scene.render.engine = "BLENDER_WORKBENCH"; scene.display.shading.color_type = "TEXTURE"; scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=50
    scene.frame_set(1); bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.output).resolve()))
    report = {"status": "GENERATED_PLANAR_APPROXIMATION", "action": action.name, "chain": chain, "keyframes": keyframes, "accepted": accepted, "rejected": rejected, "low_confidence_policy": "ankle/foot held at last accepted value below 0.6", "projection": "fixed armature-local Y/Z plane; depth held at rest", "metric_3d_claim": False}
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__": main()
