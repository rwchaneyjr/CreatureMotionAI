import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector, Quaternion

blend, out = sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']
pin_report=json.loads(Path('data/generated/pinocchio_frontL_poc_report.json').read_text())
pin_axis=Vector(pin_report['bend_axis']).normalized()
bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
baseline={n:(arm.pose.bones[n].rotation_mode,arm.pose.bones[n].rotation_quaternion.copy()) for n in names}
def restore():
    for n,(m,q) in baseline.items():
        p=arm.pose.bones[n]; p.rotation_mode='QUATERNION'; p.rotation_quaternion=q.copy()
    bpy.context.view_layer.update()
def pos(n):
    p=arm.pose.bones[n]
    return {'head':list(arm.matrix_world@p.head),'tail':list(arm.matrix_world@p.tail)}
rows=[]
for n in names:
    db=arm.data.bones[n]; p=arm.pose.bones[n]; rest=db.matrix_local.to_3x3()
    axes={a:list((arm.matrix_world.to_3x3()@rest@Vector(v)).normalized()) for a,v in [('X',(1,0,0)),('Y',(0,1,0)),('Z',(0,0,1))]}
    tests=[]
    for a,v in [('X',(1,0,0)),('Y',(0,1,0)),('Z',(0,0,1))]:
        for sign in (-1,1):
            restore(); delta=Quaternion(Vector(v), sign*0.1); p.rotation_quaternion=delta@baseline[n][1]; bpy.context.view_layer.update()
            tests.append({'axis':a,'sign':sign,'head':pos(n)['head'],'tail':pos(n)['tail'],'child_head':pos(names[names.index(n)+1])['head'] if n!=names[-1] else None})
    restore()
    rows.append({'bone':n,'parent':db.parent.name if db.parent else None,'length':db.length,'local_axes_world':axes,'pinocchio_axis_world':list(pin_axis),'tests':tests})
restore()
Path(out).write_text(json.dumps({'status':'PINOCCHIO_AXIS_DIAGNOSTIC','pinocchio_axis_world':list(pin_axis),'bones':rows,'note':'Independent +/-0.1 rad tests on a fresh baseline; no animation created.'},indent=2),encoding='utf-8')
print(json.dumps({'output':out,'bones':len(rows)}))
