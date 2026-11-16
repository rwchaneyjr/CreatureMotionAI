import bpy, json
from pathlib import Path
from mathutils import Quaternion

src=r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\seamless\seamless_loop.blend'
root=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\bending_diagnosis')
root.mkdir(parents=True,exist_ok=True); outblend=root/'bending_corrected.blend'
def curves(action):
    if hasattr(action,'layers'):
        for l in action.layers:
            for st in l.strips:
                for b in st.channelbags: return list(b.fcurves)
    return list(action.fcurves)
bpy.ops.wm.open_mainfile(filepath=src)
s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE')
source=arm.animation_data.action; corrected=source.copy(); corrected.name=source.name+'_MidRearR_AnkleDamped'; arm.animation_data.action=corrected
target='pose.bones["Leg_MidRear.R_03"].rotation_quaternion'
fcs={fc.array_index:fc for fc in curves(corrected) if fc.data_path==target}
if len(fcs)!=4: raise RuntimeError(f'Missing terminal quaternion curves: {len(fcs)}')
rest=Quaternion(tuple(fcs[i].evaluate(1.0) for i in range(4))).normalized(); factor=.35
for frame in range(1,42):
    q=Quaternion(tuple(fcs[i].evaluate(frame) for i in range(4))).normalized(); nq=rest.slerp(q,factor)
    for i in range(4):
        fcs[i].keyframe_points.insert(frame,float(nq[i])); fcs[i].update()
s.frame_start=1; s.frame_end=120; s.render.fps=24
report={'source_action':source.name,'corrected_action':corrected.name,'changed_bone':'Leg_MidRear.R_03','terminal_rotation_damping_factor':factor,'hip_and_knee_preserved':True,'original_preserved':source.name in bpy.data.actions}
(root/'bending_correction_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(outblend),copy=True)
print(json.dumps(report))
