import bpy, json, sys
from pathlib import Path

blend, out = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']
names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']
result=[]
baseline={}
for f in (1,12,25):
    s.frame_set(f); bpy.context.view_layer.update()
    row={'frame':f,'bones':[]}
    for n in names:
        p=arm.pose.bones[n]
        if f == 1:
            baseline[n] = p.matrix.copy()
        delta = (baseline[n].inverted() @ p.matrix).to_quaternion().angle
        row['bones'].append({'name':n,'rotation_mode':p.rotation_mode,'rotation_euler':list(p.rotation_euler),'rotation_quaternion':list(p.rotation_quaternion),'matrix':[[float(v) for v in r] for r in p.matrix]})
        row['bones'][-1]['delta_angle_degrees'] = float(delta * 180.0 / 3.141592653589793)
    result.append(row)
Path(out).write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
