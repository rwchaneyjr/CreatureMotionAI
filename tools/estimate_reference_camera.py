"""Search camera candidates against reference silhouettes; never saves the Blender file."""
import argparse, json, subprocess, tempfile
from pathlib import Path
import cv2, numpy as np

def mask(im, ref=False):
    gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    _,m=cv2.threshold(gray,150 if ref else 20,255,cv2.THRESH_BINARY_INV if ref else cv2.THRESH_BINARY)
    return cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))

def score(a,b):
    a,b=mask(a,True),mask(b,False); a=cv2.resize(a,(b.shape[1],b.shape[0]))
    i=np.logical_and(a>0,b>0).sum(); u=np.logical_or(a>0,b>0).sum()
    return float(i/max(u,1))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--blend',required=True); ap.add_argument('--video',required=True); ap.add_argument('--blender',required=True); ap.add_argument('--output',required=True); ap.add_argument('--panel',choices=('full','left','right'),default='full'); a=ap.parse_args()
    out=Path(a.output).resolve(); out.mkdir(parents=True,exist_ok=True)
    cap=cv2.VideoCapture(a.video); refs=[]
    for f in (1,12,24):
        cap.set(cv2.CAP_PROP_POS_FRAMES,f-1); ok,im=cap.read()
        if ok:
            # Use left half for the two-view reference; fall back to full frame if needed.
            if a.panel=='left': im=im[:,:im.shape[1]//2]
            elif a.panel=='right': im=im[:,im.shape[1]//2:]
            refs.append((f,im))
    cap.release()
    dirs=[('plus_x',(1,0,0)),('minus_x',(-1,0,0)),('plus_y',(0,1,0)),('minus_y',(0,-1,0))]
    candidates=[]
    for name,d in dirs:
        for elev in (-0.12,0.0,0.12):
            for scale in (1.2,1.8,2.4): candidates.append({'name':name,'direction':d,'elevation':elev,'scale':scale,'projection':'ORTHO'})
            for lens in (35,50,75): candidates.append({'name':name,'direction':d,'elevation':elev,'lens':lens,'projection':'PERSP'})
    manifest=out/'candidates.json'; manifest.write_text(json.dumps({'blend':str(Path(a.blend).resolve()),'candidates':candidates},indent=2),encoding='utf-8')
    expr="""import bpy,json,math
from mathutils import Vector
cfg=json.load(open(r'%s')); sc=bpy.context.scene; sc.render.engine='BLENDER_WORKBENCH'; sc.render.resolution_x=640; sc.render.resolution_y=360; sc.render.resolution_percentage=100
meshes=[o for o in sc.objects if o.type=='MESH']; pts=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
if not pts: raise RuntimeError('No mesh geometry found')
center=sum(pts,Vector())/len(pts)
for i,c in enumerate(cfg['candidates']):
 cam=bpy.data.objects.get('CMAI_TEMP_CAMERA') or bpy.data.cameras.new('CMAI_TEMP_CAMERA'); obj=bpy.data.objects.get('CMAI_TEMP_CAMERA')
 if obj is None: obj=bpy.data.objects.new('CMAI_TEMP_CAMERA',cam); sc.collection.objects.link(obj)
 sc.camera=obj; obj.data.type=c['projection']; d=Vector(c['direction']); d.z += c['elevation']; d.normalize(); obj.location=center-d*10; obj.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
 if c['projection']=='ORTHO': obj.data.ortho_scale=c['scale']
 else: obj.data.lens=c['lens']
 for f in (1,12,24):
  sc.frame_set(f); sc.render.filepath=r'%s/cand_%%03d_f%%03d.png'%%(i,f); bpy.ops.render.render(write_still=True)
"""%(str(manifest).replace('\\','/'),str(out).replace('\\','/'))
    script=out/'render_candidates.py'; script.write_text(expr,encoding='utf-8')
    subprocess.run([a.blender,'-b','--python',str(script)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    rows=[]
    for i,c in enumerate(candidates):
        vals=[]
        for f,ref in refs:
            im=cv2.imread(str(out/f'cand_{i:03d}_f{f:03d}.png'))
            if im is not None: vals.append(score(ref,im))
        rows.append({**c,'scores':vals,'mean_iou':float(np.mean(vals)) if vals else 0.0})
    rows.sort(key=lambda x:x['mean_iou'],reverse=True); best=rows[0] if rows else None
    confidence='LOW' if not best or best['mean_iou']<.35 else ('MEDIUM' if best['mean_iou']<.55 else 'HIGH')
    # Make visual evidence for the winning candidate on every tested frame.
    if best:
        bi=candidates.index({k:best[k] for k in candidates[0].keys() if k in best}) if False else next(i for i,c in enumerate(candidates) if c=={k:best[k] for k in c.keys()})
        panels=[]
        for f,ref in refs:
            render=cv2.imread(str(out/f'cand_{bi:03d}_f{f:03d}.png'))
            if render is None: continue
            ref=cv2.resize(ref,(render.shape[1],render.shape[0])); overlay=cv2.addWeighted(ref,0.5,render,0.5,0)
            cv2.putText(overlay,f'frame {f} | IoU {score(ref,render):.3f}',(12,28),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,255),2); panels.append(overlay)
        if panels:
            while len(panels)<3: panels.append(panels[-1].copy())
            cv2.imwrite(str(out/'best_camera_overlay.png'),np.vstack(panels[:3]))
    report={'status':'CANDIDATE_SEARCH_COMPLETE','best':best,'top_candidates':rows[:8],'confidence':confidence,'frames_tested':[f for f,_ in refs],'panel':a.panel,'previous_baseline_iou':0.602,'held_out_improvement_over_baseline':(best['mean_iou']-0.602) if best else None,'projection_warning':'This is silhouette matching, not unique metric camera calibration. Perspective/depth and hidden limbs remain ambiguous.','visual_overlay':str(out/'best_camera_overlay.png'),'profile_saved':str(out/'camera_profile.json')}
    (out/'camera_search_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); (out/'camera_profile.json').write_text(json.dumps({'projection':best,'source_video':str(Path(a.video).resolve()),'validated':False},indent=2),encoding='utf-8'); print(json.dumps({'best':best,'confidence':confidence,'report':str(out/'camera_search_report.json')}))
if __name__=='__main__': main()
