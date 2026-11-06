import argparse, json, subprocess
from pathlib import Path
import cv2, numpy as np

def ref_mask(path):
    im=cv2.imread(str(path)); hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
    # Balisk is saturated blue/red against a pale background.
    m=((hsv[:,:,1]>35)&(hsv[:,:,2]<250)).astype(np.uint8)*255
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((7,7),np.uint8))
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    return m

def score(a,b):
    aa=a>0; bb=b>0
    inter=np.count_nonzero(aa&bb); union=np.count_nonzero(aa|bb)
    ys,xs=np.where(aa); yt,xt=np.where(bb)
    if not len(xs) or not len(xt): return 999.0,0.0
    ca=np.array([xs.mean(),ys.mean()]); cb=np.array([xt.mean(),yt.mean()])
    iou=inter/max(1,union)
    return float((1-iou)+0.002*np.linalg.norm(ca-cb)),float(iou)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--reference',required=True); p.add_argument('--blender',required=True); p.add_argument('--outdir',required=True); args=p.parse_args()
    root=Path(args.outdir); root.mkdir(parents=True,exist_ok=True)
    ref=ref_mask(args.reference); cv2.imwrite(str(root/'reference_body_mask.png'),ref)
    candidates=[]
    for scale in [0.72,0.82,0.92,1.02,1.12,1.22]:
      for ty in [-0.10,-0.04,0.02,0.08,0.14]:
       for tz in [-0.08,-0.02,0.04,0.10]: candidates.append((scale,ty,tz))
    manifest=root/'candidates.json'; manifest.write_text(json.dumps({'candidates':candidates}),encoding='utf-8')
    expr=f"""
import bpy,json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{Path(args.blend).resolve()}')
s=bpy.context.scene; s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=640; s.render.resolution_y=720; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.render.film_transparent=False
s.display.shading.light='STUDIO'; s.display.shading.color_type='SINGLE'; s.display.shading.single_color=(0.92,0.92,0.92); s.display.shading.show_shadows=False; s.display.shading.show_cavity=True
if s.world is None: s.world=bpy.data.worlds.new('CMAI_CameraWorld')
s.world.color=(0.0,0.0,0.0)
for o in bpy.data.objects:
    if o.type=='MESH': o.hide_render=False; o.hide_viewport=False
for o in bpy.data.objects:
    if o.type=='ARMATURE': o.hide_render=True
camd=bpy.data.cameras.get('CMAI_Frame26_Ortho') or bpy.data.cameras.new('CMAI_Frame26_Ortho')
cam=bpy.data.objects.get('CMAI_Frame26_Ortho') or bpy.data.objects.new('CMAI_Frame26_Ortho',camd)
if cam.name not in s.collection.objects: s.collection.objects.link(cam)
camd.type='ORTHO'; camd.ortho_scale=1.0
cam.location=(-3.0,0,0.0); cam.rotation_euler=(Vector((0,0,0.0))-cam.location).to_track_quat('-Z','Y').to_euler(); s.camera=cam
for i,(sc,ty,tz) in enumerate(json.load(open(r'{manifest}'))['candidates']):
    camd.ortho_scale=sc; cam.location=(-3.0,ty,tz); cam.rotation_euler=(Vector((0,0,0.0))-cam.location).to_track_quat('-Z','Y').to_euler(); s.render.filepath=r'{root.resolve()}\\cand_{{:03d}}.png'.format(i); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=r'{(root/'camera_calibrated_static.blend').resolve()}')
"""
    subprocess.run([args.blender,'--background','--python-expr',expr],check=True)
    best=None; rows=[]
    for i,(sc,ty,tz) in enumerate(candidates):
        im=cv2.imread(str(root/f'cand_{i:03d}.png'),cv2.IMREAD_GRAYSCALE); _,m=cv2.threshold(im,10,255,cv2.THRESH_BINARY)
        val,iou=score(ref,m); row={'index':i,'ortho_scale':sc,'target_y':ty,'target_z':tz,'score':val,'iou':iou}; rows.append(row)
        if best is None or val<best['score']: best=row
    rows.sort(key=lambda x:x['score']); best=rows[0]
    im=cv2.imread(str(args.reference)); render=cv2.imread(str(root/f"cand_{best['index']:03d}.png"));
    render=cv2.resize(render,(im.shape[1],im.shape[0])); overlay=cv2.addWeighted(im,0.55,render,0.45,0); cv2.imwrite(str(root/'camera_overlay.png'),overlay)
    # Re-render the selected candidate and save that exact camera state.
    sc,ty,tz=best['ortho_scale'],best['target_y'],best['target_z']
    best_expr=f"""
import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{Path(args.blend).resolve()}')
s=bpy.context.scene; s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=640; s.render.resolution_y=720; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.display.shading.light='STUDIO'; s.display.shading.color_type='SINGLE'; s.display.shading.single_color=(0.92,0.92,0.92); s.display.shading.show_shadows=False; s.display.shading.show_cavity=True
if s.world is None: s.world=bpy.data.worlds.new('CMAI_CameraWorld')
s.world.color=(0,0,0)
for o in bpy.data.objects:
    if o.type=='MESH': o.hide_render=False
    if o.type=='ARMATURE': o.hide_render=True
cd=bpy.data.cameras.new('CMAI_Frame26_Ortho'); cam=bpy.data.objects.new('CMAI_Frame26_Ortho',cd); s.collection.objects.link(cam); cd.type='ORTHO'; cd.ortho_scale={sc}; cam.location=(-3.0,{ty},{tz}); cam.rotation_euler=(Vector((0,0,0.0))-cam.location).to_track_quat('-Z','Y').to_euler(); s.camera=cam; s.render.filepath=r'{(root/'best_camera_render.png').resolve()}'; bpy.ops.render.render(write_still=True); bpy.ops.wm.save_as_mainfile(filepath=r'{(root/'camera_calibrated_static.blend').resolve()}')
"""
    subprocess.run([args.blender,'--background','--python-expr',best_expr],check=True)
    report={'status':'DIAGNOSTIC','reference':str(Path(args.reference).resolve()),'blend':str((root/'camera_calibrated_static.blend').resolve()),'render':str((root/'best_camera_render.png').resolve()),'best':best,'top_candidates':rows[:10],'candidate_count':len(candidates),'note':'Orthographic body-silhouette search only; no leg fitting or metric 3D calibration performed. Camera uncertainty remains due to unknown depth and reference segmentation.'}
    (root/'camera_calibration.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
