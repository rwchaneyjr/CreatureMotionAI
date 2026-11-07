import bpy,json
from pathlib import Path
fbx=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\CrimsonSpineBehemoth_CMAI_RestRelative_24f.fbx')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(fbx),automatic_bone_orientation=False)
scene=bpy.context.scene
mesh=next((o for o in bpy.data.objects if o.type=='MESH'),None)
arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if not mesh or not arm: raise RuntimeError('Reimport missing mesh or armature')
def pts():
    dg=bpy.context.evaluated_depsgraph_get(); ev=mesh.evaluated_get(dg); me=ev.to_mesh(); p=[ev.matrix_world@v.co for v in me.vertices]; ev.to_mesh_clear(); return p
rows=[]
scene.frame_set(1); a=pts()
for f in (1,6,12,18,24):
    scene.frame_set(f); b=pts(); ds=[(x-y).length for x,y in zip(a,b)]; rows.append({'frame':f,'max_vertex_displacement':max(ds),'mean_vertex_displacement':sum(ds)/len(ds)})
out=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\CrimsonSpineBehemoth_CMAI_RestRelative_24f_reimport_validation.json')
out.write_text(json.dumps({'status':'REIMPORT_VERTEX_CHECK','mesh':mesh.name,'armature':arm.name,'frames':rows,'actions':[a.name for a in bpy.data.actions]},indent=2),encoding='utf-8')
print(json.dumps(rows))
