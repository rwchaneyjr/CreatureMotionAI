import bpy,json,sys
from pathlib import Path
from mathutils import Matrix
blend,out=sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; arm.data.pose_position='POSE'; bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
names=[]; b=arm.data.bones['Leg_Front.L_01']
while b:
    names.append(b.name); b=b.parent
names=list(reversed(names))
rows=[]
for n in names:
    db=arm.data.bones[n]; pb=arm.pose.bones[n]
    rows.append({'name':n,'parent':db.parent.name if db.parent else None,'head_armature':list(pb.head),'tail_armature':list(pb.tail),'rest_matrix':[[float(db.matrix_local[r][c]) for c in range(4)] for r in range(4)],'pose_matrix':[[float(pb.matrix[r][c]) for c in range(4)] for r in range(4)]})
Path(out).write_text(json.dumps({'status':'FRONT_L_ROOT_HIERARCHY','armature_object_matrix':[[float(arm.matrix_world[r][c]) for c in range(4)] for r in range(4)],'hierarchy':rows},indent=2),encoding='utf-8')
print(json.dumps({'output':out,'hierarchy':names}))
