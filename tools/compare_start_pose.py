import bpy,sys,json
from pathlib import Path
from mathutils import Vector

def snap(path):
    bpy.ops.wm.open_mainfile(filepath=str(Path(path).resolve()))
    s=bpy.context.scene; s.frame_set(1); bpy.context.view_layer.update()
    mesh=bpy.data.objects.get('CrimsonSpineBehemoth_Mesh') or next(o for o in bpy.data.objects if o.type=='MESH')
    arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig') or next(o for o in bpy.data.objects if o.type=='ARMATURE')
    ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=ev.to_mesh()
    pts=[tuple(mesh.matrix_world@v.co) for v in me.vertices]
    bones={b.name:(list(b.matrix),list(b.head),list(b.tail)) for b in arm.pose.bones}
    me.calc_loop_triangles(); ev.to_mesh_clear()
    return {'points':pts,'bones':bones,'mesh':mesh.name,'arm':arm.name,'mesh_world':list(mesh.matrix_world),'arm_world':list(arm.matrix_world)}

def main():
    orig,new,out=sys.argv[sys.argv.index('--')+1:]
    a=snap(orig); b=snap(new)
    n=min(len(a['points']),len(b['points'])); ds=[(Vector(a['points'][i])-Vector(b['points'][i])).length for i in range(n)]
    common=set(a['bones'])&set(b['bones']); bd={name:max(abs(a['bones'][name][0][r][c]-b['bones'][name][0][r][c]) for r in range(4) for c in range(4)) for name in common}
    report={'status':'START_POSE_COMPARISON','original':str(Path(orig).resolve()),'animated':str(Path(new).resolve()),'mesh_vertices_compared':n,'mesh_max_world_error':max(ds) if ds else None,'mesh_mean_world_error':sum(ds)/len(ds) if ds else None,'bone_count_common':len(common),'bone_max_matrix_error':max(bd.values()) if bd else None,'bone_matrix_errors':bd,'object_names_match':a['mesh']==b['mesh'] and a['arm']==b['arm'],'note':'World-space comparison at frame 1; camera differences are not included.'}
    Path(out).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report))
if __name__=='__main__': main()
