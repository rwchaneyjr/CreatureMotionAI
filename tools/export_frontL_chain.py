import bpy,sys,json
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:]
blend,out=args[:2]
leg=args[2] if len(args)>2 else 'Front.L'
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig')
names=[f'Leg_{leg}_{i:02d}' for i in (1,2,3)]
rows=[]
arm_inv=arm.matrix_world.inverted()
for n in names:
 b=arm.pose.bones[n]; m=arm.data.bones[n].matrix_local
 hw=arm.matrix_world@b.head; tw=arm.matrix_world@b.tail
 parent=arm.data.bones[n].parent
 local=(parent.matrix_local.inverted()@m) if parent else m
 rows.append({'name':n,'parent':parent.name if parent else None,'head_world':[float(x) for x in hw],'tail_world':[float(x) for x in tw],'head_armature':[float(x) for x in (arm_inv@hw)],'tail_armature':[float(x) for x in (arm_inv@tw)],'length':float(b.length),'rotation_mode':b.rotation_mode,'rest_matrix':[[float(m[r][c]) for c in range(4)] for r in range(4)],'parent_relative_rest':[[float(local[r][c]) for c in range(4)] for r in range(4)]})
root=Vector(rows[0]['head_armature'])
Path(out).write_text(json.dumps({'status':'CHAIN_EXPORTED_PARENT_RELATIVE','leg':leg,'armature':arm.name,'chain_root_armature':list(root),'bones':rows},indent=2),encoding='utf-8')
print(json.dumps({'output':out,'bones':len(rows)}))
