import argparse, subprocess, json
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--source',required=True); p.add_argument('--output',required=True); p.add_argument('--report',required=True); a=p.parse_args()
 out=str(Path(a.output).resolve()).replace('\\','/'); rep=str(Path(a.report).resolve()).replace('\\','/')
 expr=f'''import bpy,json,math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.source).resolve()}"); s=bpy.context.scene; s.frame_start=1; s.frame_end=24; s.render.fps=24
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); leg='Leg_Front.L'
for pb in arm.pose.bones:
 for c in list(pb.constraints): pb.constraints.remove(c)
upper=arm.pose.bones[leg+'_01']; lower=arm.pose.bones[leg+'_02']; foot=arm.pose.bones[leg+'_03']
def w(x,tail=False): return arm.matrix_world@(x.tail if tail else x.head)
hip=w(upper); knee=w(upper,True); ankle=w(lower,True); base=w(foot,True); L=(knee-hip).length+(ankle-knee).length+(base-ankle).length
plane=(knee-hip).normalized().cross((base-knee).normalized()).normalized(); pole_dir=plane.cross((knee-hip).normalized()).normalized()
t=bpy.data.objects.new('CMAI_FrontL_Step_Target',None); t.location=base; s.collection.objects.link(t); p=bpy.data.objects.new('CMAI_FrontL_Step_Pole',None); p.location=knee+pole_dir*.22; s.collection.objects.link(p)
c=foot.constraints.new('IK'); c.name='CMAI_FrontL_Step_IK'; c.target=t; c.pole_target=p; c.chain_count=3; c.influence=1
rows=[]
for f in range(1,25):
 q=(f-1)/23
 if q < 0.5:
  advance=0.0; lift=0.0
 else:
  sw=(q-0.5)*4.0*math.pi; swing=max(0,math.sin(sw)); advance=(1-math.cos(sw))*0.03*L; lift=swing*swing*.08*L
 desired=base+Vector((0,advance,lift)); t.location=desired; t.keyframe_insert('location',frame=f)
 s.frame_set(f); bpy.context.view_layer.update(); pos=w(foot,True); rows.append({{'frame':f,'target_error':(t.matrix_world.translation-pos).length,'foot':list(pos),'bend_alignment':(pos-knee).normalized().dot(plane)}})
open(r'{rep}','w').write(json.dumps({{'status':'front_leg_step_created','leg':leg,'leg_length':L,'bend_plane':list(plane),'rows':rows}},indent=2)); bpy.ops.wm.save_as_mainfile(filepath=r'{out}')'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
