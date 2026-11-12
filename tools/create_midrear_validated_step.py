import bpy,json,sys
from pathlib import Path
from mathutils import Vector,Quaternion
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
blend,reach,outblend,outjson=args[:4]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; s=bpy.context.scene
names=['Leg_MidRear.L_01','Leg_MidRear.L_02','Leg_MidRear.L_03']
s.frame_set(1); bpy.context.view_layer.update(); base={n:arm.pose.bones[n].rotation_quaternion.copy() for n in names}
d=json.loads(Path(reach).read_text()); tests={x['name']:x for x in d['tests']}
grid=d['reach_grid']
lift=next(x['q'] for x in grid if x['lift_height']==0.009 and x['forward_fraction']==0.25 and x['pass'])
fwd=next(x['q'] for x in grid if x['lift_height']==0.009 and x['forward_fraction']==1.0 and x['pass'])
# Waypoint-only visual test: expand the validated solver waypoint rotations
# conservatively; Blender interpolates between them. This is not a replacement
# for reach validation and remains a diagnostic animation.
lift=[v*1.75 for v in lift]
fwd=[v*1.75 for v in fwd]
act=bpy.data.actions.new('CMAI_MidRearL_NaturalStep'); arm.animation_data_create(); arm.animation_data.action=act
def pose(qs,frame):
    for n,qv in zip(names,qs):
        p=arm.pose.bones[n]; p.rotation_mode='QUATERNION'; p.rotation_quaternion=Quaternion((1,0,0),float(qv))@base[n]; p.keyframe_insert('rotation_quaternion',frame=frame)
keys=[(1,[0,0,0]),(20,[0,0,0]),(32,lift),(48,lift),(64,fwd),(78,fwd),(92,[0,0,0]),(120,[0,0,0])]
for fr,q in keys: pose(q,fr)
s.frame_start=1; s.frame_end=120; s.render.fps=24
s['CMAI_MidRearL_Step_Status']='DIAGNOSTIC_NATURAL_STEP'
bpy.ops.wm.save_as_mainfile(filepath=str(Path(outblend).resolve()))
rows=[]
for fr in [1,20,32,48,64,78,92,120]:
    s.frame_set(fr); bpy.context.view_layer.update(); p=arm.pose.bones[names[-1]]; rows.append({'frame':fr,'foot_world':list(arm.matrix_world@p.tail)})
Path(outjson).write_text(json.dumps({'status':'MIDREARL_NATURAL_STEP_CREATED','action':act.name,'frames':rows,'note':'Other legs untouched; visual review required.'},indent=2))
print(outblend)
