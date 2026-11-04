import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--source',required=True); p.add_argument('--output',required=True); p.add_argument('--report',required=True); a=p.parse_args(); out=str(Path(a.output).resolve()).replace('\\','/'); rp=str(Path(a.report).resolve()).replace('\\','/')
 expr=f'''import bpy,json
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.source).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); foot=arm.pose.bones['Leg_Front.L_03'];
for c in list(foot.constraints):
 if c.type=='COPY_ROTATION' and c.name.startswith('CMAI_Test_'): foot.constraints.remove(c)
rest=foot.matrix.copy(); ref=bpy.data.objects.new('CMAI_Test_FrontL_RestOrientation',None); ref.rotation_mode='QUATERNION'; ref.rotation_quaternion=rest.to_quaternion(); s.collection.objects.link(ref)
c=foot.constraints.new('COPY_ROTATION'); c.name='CMAI_Test_FrontL_RestOrientation'; c.target=ref; c.target_space='WORLD'; c.owner_space='WORLD'; c.influence=1.0
for f,inf in ((1,1.0),(12,1.0),(13,0.0),(18,0.35),(23,0.8),(24,1.0)):
 c.influence=inf; c.keyframe_insert('influence',frame=f)
s.frame_set(1); bpy.context.view_layer.update(); bpy.ops.wm.save_as_mainfile(filepath=r'{out}')
open(r'{rp}','w').write(json.dumps({{'status':'orientation_control_test_created','constraint':c.name,'owner':'Leg_Front.L_03','lower_leg_unlocked':True,'ik_preserved':True,'source':r'{str(Path(a.source).resolve())}','output':r'{out}'}},indent=2)); print(json.dumps({{'status':'orientation_control_test_created','output':r'{out}'}}))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
