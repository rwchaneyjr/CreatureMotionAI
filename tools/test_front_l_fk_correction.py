import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--source',required=True); p.add_argument('--output',required=True); p.add_argument('--delta-deg',type=float,required=True); a=p.parse_args(); out=str(Path(a.output).resolve()).replace('\\','/')
 expr=f'''import bpy,math
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.source).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); pb=arm.pose.bones['Leg_Front.L_02']
delta=math.radians({a.delta_deg})
for f in range(2,24):
 s.frame_set(f); bpy.context.view_layer.update(); base=pb.rotation_euler[0]; pb.rotation_euler[0]=base+delta; pb.keyframe_insert('rotation_euler',index=0,frame=f)
s.frame_set(1); bpy.ops.wm.save_as_mainfile(filepath=r'{out}')'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
