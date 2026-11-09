import sys, json, bpy
from pathlib import Path
from mathutils import Vector
argv=sys.argv[sys.argv.index('--')+1:]
blend=argv[0]; report=argv[1]
bpy.ops.wm.open_mainfile(filepath=blend); s=bpy.context.scene; s.frame_set(1)
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; p=[arm.pose.bones[f'Leg_Front.L_{i:02d}'] for i in (1,2,3)]
inv=arm.matrix_world.inverted()
def wp(b,end=False): return arm.matrix_world @ (b.tail if end else b.head)
rest_tail=wp(p[2],True); rest_head=wp(p[2],False); rows=[]
for endpoint_name, endpoint in [('head',rest_head),('tail',rest_tail)]:
    t=bpy.data.objects.new('CMAI_FinalIK_Target_'+endpoint_name,None); s.collection.objects.link(t); t.location=inv@endpoint
    c=p[0].constraints.new('IK'); c.name='CMAI Final IK '+endpoint_name; c.target=t; c.chain_count=3
    vals=[]
    for f,off in [(1,Vector((0,0,0))),(12,Vector((0.01,0,0))),(24,Vector((0,0,0)))]:
        s.frame_set(f); t.location=inv@(endpoint+off); bpy.context.view_layer.update(); cur=wp(p[2],True); vals.append({'frame':f,'target':list(endpoint+off),'tail':list(cur),'tail_error':(cur-(endpoint+off)).length,'head_error':(wp(p[2])-endpoint).length})
    rows.append({'endpoint':endpoint_name,'results':vals}); p[0].constraints.remove(c); bpy.data.objects.remove(t,do_unlink=True)
Path(report).write_text(json.dumps({'status':'FINAL_IK_DIAGNOSTIC','armature':arm.name,'leg':'Leg_Front.L','rows':rows,'coordinate_space':'armature_local_target_with_world_evaluation'},indent=2),encoding='utf-8')
print(json.dumps({'report':report}))
