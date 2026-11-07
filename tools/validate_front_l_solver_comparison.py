"""Validate saved Front.L solver comparison files using evaluated Blender geometry."""
import argparse, json, math, sys
from pathlib import Path

import bpy
from mathutils import Vector

CHAIN = ["Leg_Front.L_01", "Leg_Front.L_02", "Leg_Front.L_03"]
FRAMES = [1, 6, 12, 18, 24]

def qangle(a, b):
    return math.degrees(a.rotation_difference(b).angle)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True)
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    args = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.blend).resolve()))
    scene = bpy.context.scene
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm or o.type == 'MESH')
    deps = bpy.context.evaluated_depsgraph_get()
    groups = {mesh.vertex_groups[n].index for n in CHAIN if mesh.vertex_groups.get(n)}
    ids = [v.index for v in mesh.data.vertices if any(g.group in groups and g.weight > .25 for g in v.groups)]
    if not ids:
        raise RuntimeError("No weighted Front.L vertices found")
    scene.frame_set(1); bpy.context.view_layer.update()
    ev = mesh.evaluated_get(deps); me = ev.to_mesh()
    rest_pts = [ev.matrix_world @ me.vertices[i].co for i in ids]
    ground_z = min(p.z for p in rest_pts)
    rest_bones = {n: (arm.pose.bones[n].matrix.to_4x4(), arm.pose.bones[n].matrix.to_quaternion()) for n in CHAIN}
    rest_foot = arm.pose.bones[CHAIN[-1]].tail.copy()
    rest_knee = arm.pose.bones[CHAIN[0]].tail.copy()
    ev.to_mesh_clear()
    rows=[]; max_disp=0.0; max_pen=0.0; max_orient=0.0; max_rot=0.0
    for f in range(1, 25):
        scene.frame_set(f); bpy.context.view_layer.update()
        bones={n: arm.pose.bones[n] for n in CHAIN}
        ev=mesh.evaluated_get(deps); me=ev.to_mesh()
        pts=[ev.matrix_world @ me.vertices[i].co for i in ids]
        min_z=min(p.z for p in pts); pen=max(0.0, ground_z-min_z)
        foot=bones[CHAIN[-1]].tail.copy()
        disp=(foot-rest_foot).length
        orient=qangle(rest_bones[CHAIN[-1]][1], bones[CHAIN[-1]].matrix.to_quaternion())
        rot=max(qangle(rest_bones[n][1], bones[n].matrix.to_quaternion()) for n in CHAIN)
        mesh_disp=max((p-r).length for p,r in zip(pts,rest_pts))
        max_disp=max(max_disp,disp); max_pen=max(max_pen,pen); max_orient=max(max_orient,orient); max_rot=max(max_rot,rot)
        rows.append({'frame':f,'foot_displacement':disp,'min_weighted_mesh_z':min_z,'ground_penetration':pen,'foot_orientation_deviation_deg':orient,'max_chain_rotation_deg':rot,'max_weighted_mesh_displacement':mesh_disp})
        ev.to_mesh_clear()
    target_err=max(float(r.get('target_error',0.0)) for r in json.loads(Path(args.blend).with_name(f'front_l_{args.method}_report.json').read_text()).get('frames',[])) if False else None
    result={'status':'UNVERIFIED','method':args.method,'blend':str(Path(args.blend).resolve()),'chain':CHAIN,'tested_frames':FRAMES,'all_frames_evaluated':24,'weighted_vertex_count':len(ids),'ground_reference_z':ground_z,'max_foot_displacement':max_disp,'max_ground_penetration':max_pen,'max_foot_orientation_deviation_deg':max_orient,'max_chain_rotation_deg':max_rot,'rows':rows,'checks':{'evaluated_bone_motion':'PASS' if max_rot>1e-5 else 'FAIL','evaluated_mesh_deformation':'PASS' if max_disp>1e-5 and max(r['max_weighted_mesh_displacement'] for r in rows)>1e-5 else 'FAIL','ground_clearance':'PASS' if max_pen<=1e-5 else 'FAIL','foot_orientation':'UNVERIFIED','knee_direction':'UNVERIFIED','proxy_collision':'UNVERIFIED','targeted_mesh_collision':'UNVERIFIED'},'note':'Ground is baseline-relative to the Front.L weighted mesh at frame 1. Collision checks require the regional proxy/BVH stage and are intentionally not inferred from deformation.'}
    # Return-to-rest check is explicit and based on evaluated geometry.
    result['checks']['return_to_rest']='PASS' if rows[-1]['foot_displacement'] <= 1e-5 else 'FAIL'
    Path(args.out).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'method':args.method,'max_penetration':max_pen,'max_foot_displacement':max_disp,'max_orientation_deg':max_orient,'mesh_vertices':len(ids)}))

if __name__ == '__main__': main()
