"""Create a safe one-second reference-driven body pass from the clean static rig.

Only the existing Root bone is keyed from measured video centroid motion. The
original leg pose remains the contact baseline; no IK or Move Action is reused.
This is an intermediate grounded pass, not the final leg solver.
"""
import argparse, json, subprocess
from pathlib import Path
import cv2

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--video',required=True); p.add_argument('--output',required=True); p.add_argument('--blender',required=True); p.add_argument('--report',required=True); a=p.parse_args()
    cap=cv2.VideoCapture(a.video); centers=[]
    for _ in range(24):
        ok,img=cap.read()
        if not ok: break
        hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV); mask=((hsv[:,:,1]>35)&(hsv[:,:,2]>35)).astype('uint8')
        n,lab,stats,cents=cv2.connectedComponentsWithStats(mask,8); best=None
        for j in range(1,n):
            x,y,w,h,area=stats[j]
            if area>1000 and (best is None or area>best[0]): best=(area,cents[j])
        centers.append((float(best[1][0]/img.shape[1]) if best else .5, float(best[1][1]/img.shape[0]) if best else .5))
    cap.release()
    if not centers: centers=[(.5,.5)]*24
    expr=f"""
import bpy, json, math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{Path(a.blend).resolve()}')
scene=bpy.context.scene; scene.frame_start=1; scene.frame_end=24; scene.render.fps=24
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); root=arm.pose.bones.get('Root')
for act in list(bpy.data.actions):
    if act.name != 'CMAI_Static_Original_Standing': bpy.data.actions.remove(act)
action=bpy.data.actions.new('CMAI_Reference_Grounded_Body_1s'); arm.animation_data_create(); arm.animation_data.action=action
centers={repr(centers)}
baseline=root.location.copy(); arm.animation_data.action=None; root.location=baseline; root.keyframe_insert('location',frame=1,group='Root')
arm.animation_data.action=action
for i,(cx,cy) in enumerate(centers[:24],1):
    # Screen-horizontal reference motion maps to local Y; vertical drift maps conservatively to Z.
    root.location=baseline+Vector((0.0,(cx-centers[0][0])*0.35,(centers[0][1]-cy)*0.12))
    root.keyframe_insert('location',frame=i,group='Root')
scene.frame_set(1); bpy.ops.wm.save_as_mainfile(filepath=r'{Path(a.output).resolve()}')
print(json.dumps({{'frames':len(centers[:24]),'action':action.name,'leg_bones_keyed':False,'ik_constraints':0}}))
"""
    r=subprocess.run([a.blender,'--background','--python-expr',expr],capture_output=True,text=True,check=True)
    data={}
    for line in reversed(r.stdout.splitlines()):
        if line.strip().startswith('{'):
            data=json.loads(line); break
    if not data:
        raise RuntimeError('Blender did not emit pass JSON. STDERR: '+r.stderr[-2000:])
    data.update({'input_blend':str(Path(a.blend).resolve()),'video':str(Path(a.video).resolve()),'output':str(Path(a.output).resolve()),'status':'grounded_body_pass_only','warning':'Leg motion remains static until per-leg tracking and contact fitting are solved.'})
    Path(a.report).write_text(json.dumps(data,indent=2),encoding='utf-8'); print(json.dumps(data,indent=2))
if __name__=='__main__': main()
