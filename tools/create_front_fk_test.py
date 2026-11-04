import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--source',required=True); p.add_argument('--output',required=True); a=p.parse_args(); out=str(Path(a.output).resolve()).replace('\\','/')
 expr=f'''import bpy,math
from mathutils import Euler
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.source).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); s.frame_start=1; s.frame_end=24; s.render.fps=24
for pb in arm.pose.bones:
 for c in list(pb.constraints): pb.constraints.remove(c)
arm.animation_data_clear(); act=bpy.data.actions.new('CMAI_FrontL_FK_Test_24F'); act.use_fake_user=True; slot=act.slots.new('OBJECT',arm.name); arm.animation_data_create(); arm.animation_data.action=act; arm.animation_data.action_slot=slot
names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']
for n in names: arm.pose.bones[n].rotation_mode='XYZ'
base={{n:arm.pose.bones[n].rotation_euler.copy() for n in names}}
for f in range(1,25):
 q=(f-1)/23; swing=math.sin(math.pi*q); advance=math.sin(math.pi*q)
 for n in names: arm.pose.bones[n].rotation_euler=base[n]
 arm.pose.bones[names[0]].rotation_euler[0]=base[names[0]].x-0.18*swing
 arm.pose.bones[names[1]].rotation_euler[0]=base[names[1]].x+0.28*swing
 arm.pose.bones[names[2]].rotation_euler[0]=base[names[2]].x-0.10*swing
 for n in names: arm.pose.bones[n].keyframe_insert('rotation_euler',frame=f)
s.frame_set(1); bpy.ops.wm.save_as_mainfile(filepath=r'{out}')'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
