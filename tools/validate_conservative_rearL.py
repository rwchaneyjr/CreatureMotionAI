"""Bounded validation for the conservative rest-relative Rear.L test."""
import argparse, json, math, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--blend', required=True); ap.add_argument('--report', required=True)
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    a = ap.parse_args(argv)
    import bpy
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    scene = bpy.context.scene
    arm = next(o for o in scene.objects if o.type == 'ARMATURE')
    mesh = next(o for o in scene.objects if o.type == 'MESH')
    chain = ['Leg_Rear.L_01', 'Leg_Rear.L_02', 'Leg_Rear.L_03']
    groups = {mesh.vertex_groups[n].index for n in chain if mesh.vertex_groups.get(n)}
    ids = [v.index for v in mesh.data.vertices if any(g.group in groups and g.weight > 0.05 for g in v.groups)]
    deps = bpy.context.evaluated_depsgraph_get()
    def sample():
        ev = mesh.evaluated_get(deps); me = ev.to_mesh()
        pts = [ev.matrix_world @ me.vertices[i].co for i in ids]
        ev.to_mesh_clear()
        p = {n: {'head': list(arm.matrix_world @ arm.pose.bones[n].head), 'tail': list(arm.matrix_world @ arm.pose.bones[n].tail)} for n in chain}
        return p, pts
    scene.frame_set(1); bpy.context.view_layer.update(); rest, rest_pts = sample()
    rest_foot = Vector(rest[chain[2]]['tail']); rest_hip = Vector(rest[chain[0]]['head']); rest_knee = Vector(rest[chain[0]]['tail'])
    rest_normal = (rest_knee-rest_hip).cross(rest_foot-rest_hip).normalized()
    ground = min(p.z for p in rest_pts)
    rows=[]; max_disp=0.; max_pen=0.; max_ori=0.; min_bend=1.
    rest_q=(arm.matrix_world @ arm.pose.bones[chain[2]].matrix).to_quaternion()
    for f in range(1,25):
        scene.frame_set(f); bpy.context.view_layer.update(); pose, pts = sample()
        disp=max((p-q).length for p,q in zip(pts,rest_pts)); minz=min(p.z for p in pts); pen=max(0., ground-minz)
        q=(arm.matrix_world @ arm.pose.bones[chain[2]].matrix).to_quaternion(); ori=math.degrees(q.rotation_difference(rest_q).angle)
        hip=Vector(pose[chain[0]]['head']); knee=Vector(pose[chain[0]]['tail']); foot=Vector(pose[chain[2]]['tail'])
        bend=(knee-hip).cross(foot-hip); dot=float(bend.normalized().dot(rest_normal)) if bend.length>1e-9 else 0.
        max_disp=max(max_disp,disp); max_pen=max(max_pen,pen); max_ori=max(max_ori,ori); min_bend=min(min_bend,dot)
        rows.append({'frame':f,'max_weighted_vertex_displacement':disp,'min_weighted_vertex_z':minz,'ground_penetration':pen,'foot_orientation_deviation_deg':ori,'bend_alignment_dot':dot,'foot_endpoint':list(foot)})
    action=arm.animation_data.action if arm.animation_data else None
    out={'status':'PASS_WITH_LIMITATIONS' if max_pen<=0.005 and max_disp>1e-4 and min_bend>0 else 'FAIL','action_evaluated':bool(action),'action_name':action.name if action else None,'chain':chain,'weighted_vertex_count':len(ids),'ground_reference_z':ground,'max_ground_penetration':max_pen,'max_weighted_mesh_displacement':max_disp,'max_foot_orientation_deviation_deg':max_ori,'minimum_bend_alignment_dot':min_bend,'self_collision':'UNVERIFIED','frames':rows,'visual_review':'REQUIRED_BECAUSE_CLOSEUP_RENDER_HAS_NO_RENDERED_ARMATURE_OVERLAY','other_legs_animated':False}
    Path(a.report).write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps(out,indent=2))
if __name__ == '__main__': main()
