import argparse, json, math, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--blend', required=True); ap.add_argument('--report', required=True)
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    import bpy
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    s = bpy.context.scene; arm = next(o for o in s.objects if o.type == 'ARMATURE'); mesh = next(o for o in s.objects if o.type == 'MESH')
    deps = bpy.context.evaluated_depsgraph_get(); out = {'blend': str(Path(a.blend).resolve()), 'legs': {}, 'action': arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None}
    for leg in ('Front.L', 'Rear.L'):
        chain = [f'Leg_{leg}_{i:02d}' for i in (1, 2, 3)]
        groups = {mesh.vertex_groups[n].index for n in chain if mesh.vertex_groups.get(n)}
        ids = [v.index for v in mesh.data.vertices if any(g.group in groups and g.weight > .05 for g in v.groups)]
        def snap():
            ev = mesh.evaluated_get(deps); me = ev.to_mesh(); pts = [ev.matrix_world @ me.vertices[i].co for i in ids]; ev.to_mesh_clear()
            pbs = [arm.pose.bones[n] for n in chain]; return pts, [arm.matrix_world @ pb.head for pb in pbs], [arm.matrix_world @ pb.tail for pb in pbs]
        s.frame_set(1); bpy.context.view_layer.update(); rest_pts, rest_heads, rest_tails = snap(); ground = min((p.z for p in rest_pts), default=0.0); rest_q = (arm.matrix_world @ arm.pose.bones[chain[2]].matrix).to_quaternion(); rows=[]
        for f in range(1,25):
            s.frame_set(f); bpy.context.view_layer.update(); pts, heads, tails = snap(); q=(arm.matrix_world @ arm.pose.bones[chain[2]].matrix).to_quaternion(); rows.append({'frame':f,'weighted_displacement':max(((p-r).length for p,r in zip(pts,rest_pts)),default=0.0),'ground_penetration':max(0.0,ground-min((p.z for p in pts),default=ground)),'foot_orientation_deviation_deg':math.degrees(q.rotation_difference(rest_q).angle),'foot_endpoint_displacement':(tails[2]-rest_tails[2]).length})
        out['legs'][leg] = {'weighted_vertices':len(ids),'max_weighted_displacement':max(r['weighted_displacement'] for r in rows),'max_ground_penetration':max(r['ground_penetration'] for r in rows),'max_foot_orientation_deviation_deg':max(r['foot_orientation_deviation_deg'] for r in rows),'max_foot_endpoint_displacement':max(r['foot_endpoint_displacement'] for r in rows),'rows':rows}
    Path(a.report).write_text(json.dumps(out, indent=2), encoding='utf-8'); print(json.dumps(out, indent=2))
if __name__ == '__main__': main()
