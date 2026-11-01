"""Small model-guided single-frame pose fitting pass.

The clean static blend is the baseline. This performs real render/compare trials
on the existing armature only, accepting a pose change only when the silhouette
score improves. It never creates an armature and never edits mesh geometry.
"""
import argparse, json, subprocess, shutil
from pathlib import Path
import cv2, numpy as np


def score(ref_path, render_path):
    ref = cv2.imread(str(ref_path)); img = cv2.imread(str(render_path))
    ref = cv2.resize(ref, (img.shape[1], img.shape[0]))
    # Saturation masks are deliberately coarse: they guide the search, not replace visual review.
    rs = cv2.cvtColor(ref, cv2.COLOR_BGR2HSV)[:,:,1] > 35
    bs = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:,:,1] > 35
    inter = np.logical_and(rs, bs).sum(); union = np.logical_or(rs, bs).sum()
    return float(inter / max(union, 1))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--blend',required=True); p.add_argument('--reference',required=True)
    p.add_argument('--output',required=True); p.add_argument('--blender',required=True)
    p.add_argument('--work',required=True); args=p.parse_args()
    work=Path(args.work); work.mkdir(parents=True,exist_ok=True)
    render=work/'candidate.png'; out=Path(args.output)
    current=work/'current.blend'; shutil.copy2(args.blend,current)
    # Existing rig naming convention: eight *_01 leg roots.
    expr=f"""
import bpy, json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{current.resolve()}')
scene=bpy.context.scene; scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.light='STUDIO'; scene.display.shading.color_type='TEXTURE'; scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
if scene.world is None: scene.world=bpy.data.worlds.new('CMAI_Fit_World')
scene.world.color=(0.42,0.42,0.42)
cam=bpy.data.objects.get('CMAI_Calibrated_Side_Camera')
if cam is None:
 d=bpy.data.cameras.new('CMAI_Calibrated_Side_Camera'); cam=bpy.data.objects.new('CMAI_Calibrated_Side_Camera',d); bpy.context.collection.objects.link(cam)
cam.location=(-3.35,0,0.42); cam.data.lens=52.0
cam.rotation_euler=(Vector((0,0,0.22))-cam.location).to_track_quat('-Z','Y').to_euler(); scene.camera=cam
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
roots=[b for b in arm.pose.bones if (b.name.endswith('_01') or b.name.endswith('_upper')) and any(k in b.name.lower() for k in ('leg','front','mid','rear'))]
roots=sorted(roots,key=lambda b:b.name)[:8]
for pb in roots: pb.rotation_mode='XYZ'
scene.render.filepath=r'{render.resolve()}'; scene.frame_set(1); bpy.ops.render.render(write_still=True)
print('ROOTS',json.dumps([b.name for b in roots]))
"""
    subprocess.run([args.blender,'--background','--python-expr',expr],check=True)
    baseline=score(args.reference,render)
    current_score=baseline; accepted=[]; roots=[]
    # Query the exact roots once, then try bounded local-Y/local-Z rotations.
    query=f"import bpy, json; bpy.ops.wm.open_mainfile(filepath=r'{current.resolve()}'); a=next(o for o in bpy.data.objects if o.type=='ARMATURE'); print(json.dumps(sorted([b.name for b in a.pose.bones if b.name.endswith('_01') and 'Leg_' in b.name])[:8]))"
    q=subprocess.run([args.blender,'--background','--python-expr',query],capture_output=True,text=True,check=True)
    for line in reversed(q.stdout.splitlines()):
        if line.strip().startswith('['):
            try: roots=json.loads(line.strip()); break
            except Exception: pass
    for bone in roots:
        best_for_bone=None
        for axis in (2,):
            for deg in (-8.0,-4.0,4.0,8.0):
                trial=work/f'trial_{bone}_{axis}_{deg:+.0f}.png'
                expr2=f"""
import bpy
bpy.ops.wm.open_mainfile(filepath=r'{current.resolve()}')
scene=bpy.context.scene; scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.light='STUDIO'; scene.display.shading.color_type='TEXTURE'; scene.frame_set(1); a=next(o for o in bpy.data.objects if o.type=='ARMATURE')
pb=a.pose.bones.get(r'{bone}')
if pb:
    pb.rotation_mode='XYZ'; r=pb.rotation_euler.copy(); r[{axis}]+=__import__('math').radians({deg}); pb.rotation_euler=r
scene.render.filepath=r'{trial.resolve()}'; bpy.ops.render.render(write_still=True)
"""
                subprocess.run([args.blender,'--background','--python-expr',expr2],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
                s=score(args.reference,trial)
                if best_for_bone is None or s>best_for_bone[0]: best_for_bone=(s,axis,deg,trial)
        if best_for_bone and best_for_bone[0] > current_score + 0.001:
            s,axis,deg,trial=best_for_bone
            apply=f"""
import bpy
bpy.ops.wm.open_mainfile(filepath=r'{current.resolve()}'); scene=bpy.context.scene; scene.frame_set(1)
a=next(o for o in bpy.data.objects if o.type=='ARMATURE'); pb=a.pose.bones.get(r'{bone}')
pb.rotation_mode='XYZ'; r=pb.rotation_euler.copy(); r[{axis}]+=__import__('math').radians({deg}); pb.rotation_euler=r
bpy.ops.wm.save_as_mainfile(filepath=r'{current.resolve()}')
"""
            subprocess.run([args.blender,'--background','--python-expr',apply],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
            current_score=s; accepted.append({'bone':bone,'axis':axis,'degrees':deg,'score':s})
    shutil.copy2(current,out)
    report={'baseline_silhouette_iou':baseline,'final_silhouette_iou':current_score,
            'accepted_pose_changes':accepted,'tested_roots':roots,
            'status':'bounded_single_frame_render_compare_fit',
            'limits':'±8 degrees, 4-degree increments, root bones only; no lower-leg direct keys.',
            'output':str(out.resolve()),'render':str(render.resolve())}
    out.with_suffix('.fit_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
