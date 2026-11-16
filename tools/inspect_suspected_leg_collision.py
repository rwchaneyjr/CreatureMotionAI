import json
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BLEND = r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\collision_candidates\candidate_-4.blend'
OUT = Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\suspected_collision')
OUT.mkdir(parents=True, exist_ok=True)
FRAMES = [27, 28, 29, 67, 68, 69, 107, 108, 109]
CHAIN_A = ['Leg_Rear.R_01', 'Leg_Rear.R_02', 'Leg_Rear.R_03']
CHAIN_B = ['Leg_MidRear.R_01', 'Leg_MidRear.R_02', 'Leg_MidRear.R_03']

bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
mesh = next(o for o in scene.objects if o.type == 'MESH')
arm = next(o for o in scene.objects if o.type == 'ARMATURE')
groups_a = {mesh.vertex_groups[n].index for n in CHAIN_A if mesh.vertex_groups.get(n)}
groups_b = {mesh.vertex_groups[n].index for n in CHAIN_B if mesh.vertex_groups.get(n)}
def segdist(p,a,b):
    d=b-a
    t=max(0.0,min(1.0,(p-a).dot(d)/(d.dot(d) or 1.0)))
    return (p-(a+d*t)).length
def dominant_vertices(groups, chain_names):
    scene.frame_set(1); bpy.context.view_layer.update()
    pseg=[]
    for name in chain_names:
        bone=arm.pose.bones[name]
        pseg.append((arm.matrix_world@bone.head, arm.matrix_world@bone.tail))
    selected=set()
    for v in mesh.data.vertices:
        chain=sum(g.weight for g in v.groups if g.group in groups)
        maximum=max((g.weight for g in v.groups), default=0.0)
        point=mesh.matrix_world@v.co
        near=min(segdist(point,a,b) for a,b in pseg)
        if chain >= .35 and chain >= maximum*.75 and near <= .12:
            selected.add(v.index)
    return selected
ids_a = dominant_vertices(groups_a, CHAIN_A)
ids_b = dominant_vertices(groups_b, CHAIN_B)
mesh.data.calc_loop_triangles()
source_tris = [tuple(t.vertices) for t in mesh.data.loop_triangles]

def triangle_set(data, allowed):
    return [tri for tri in data.loop_triangles if len(set(tri.vertices).intersection(allowed)) >= 2]

rows = []
for frame in FRAMES:
    scene.frame_set(frame); bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(deps); data = ev.to_mesh(); data.calc_loop_triangles()
    verts = [ev.matrix_world @ v.co for v in data.vertices]
    tris_a = triangle_set(data, ids_a); tris_b = triangle_set(data, ids_b)
    # Do not compare triangles that share source vertices; those are connected
    # or blended boundary geometry, not independent surface penetration.
    bvh_a = BVHTree.FromPolygons(verts, [tuple(t.vertices) for t in tris_a], all_triangles=True)
    bvh_b = BVHTree.FromPolygons(verts, [tuple(t.vertices) for t in tris_b], all_triangles=True)
    overlaps = bvh_a.overlap(bvh_b)
    filtered = []
    for ia, ib in overlaps:
        ta = set(tris_a[ia].vertices); tb = set(tris_b[ib].vertices)
        if ta.intersection(tb):
            continue
        filtered.append({'a': list(tris_a[ia].vertices), 'b': list(tris_b[ib].vertices)})
    def bbox(ids):
        p = [verts[i] for i in ids]
        return {'min': list(map(float, (min(x.x for x in p), min(x.y for x in p), min(x.z for x in p)))),
                'max': list(map(float, (max(x.x for x in p), max(x.y for x in p), max(x.z for x in p))))}
    rows.append({'frame': frame, 'region_a_vertices': len(ids_a), 'region_b_vertices': len(ids_b),
                 'region_a_triangles': len(tris_a), 'region_b_triangles': len(tris_b),
                 'raw_bvh_overlaps': len(overlaps), 'filtered_surface_overlaps': len(filtered),
                 'surface_intersection': bool(filtered), 'bbox_a': bbox(ids_a), 'bbox_b': bbox(ids_b),
                 'overlap_examples': filtered[:20]})
    ev.to_mesh_clear()

result = {'status': 'ACTUAL_MESH_INTERSECTION' if any(r['surface_intersection'] for r in rows) else 'NO_ACTUAL_MESH_INTERSECTION',
          'blend': BLEND, 'regions': {'A': CHAIN_A, 'B': CHAIN_B},
          'vertex_weight_threshold': .35, 'dominant_chain_weight_ratio': .75, 'rest_distance_to_chain_max': .12, 'frames': rows,
          'note': 'Separate weighted-region BVHs; shared-boundary triangles excluded. This tests actual evaluated geometry, not capsule proxies.'}
(OUT / 'bvh_region_collision_report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({'status': result['status'], 'frames': {r['frame']: r['filtered_surface_overlaps'] for r in rows}}))
