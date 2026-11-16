import bpy, json
from pathlib import Path

src=r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\seamless\seamless_loop.blend'
root=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\collision_candidates'); root.mkdir(parents=True,exist_ok=True)
def curves(action):
    if hasattr(action,'layers'):
        for l in action.layers:
            for st in l.strips:
                for b in st.channelbags: return list(b.fcurves)
    return list(action.fcurves)
for shift in (-4,4):
    bpy.ops.wm.open_mainfile(filepath=src); s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE')
    old=arm.animation_data.action; act=old.copy(); act.name=old.name+f'_RearRPhase{shift:+d}'; arm.animation_data.action=act
    for fc in curves(act):
        if 'Leg_Rear.R_' not in fc.data_path: continue
        points=[(float(k.co.x),float(k.co.y)) for k in fc.keyframe_points]
        for k,(x,y) in zip(fc.keyframe_points,points):
            k.co.x=1.0+((x-1.0+shift)%40.0)
        fc.update()
    out=root/f'candidate_{shift:+d}.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(out),copy=True)
    print('SAVED',out)
