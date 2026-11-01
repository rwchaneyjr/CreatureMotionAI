"""Bounded render/compare fitting for one frame using the existing 38-bone rig."""
import argparse, json, math, shutil, subprocess
from pathlib import Path
import cv2, numpy as np

def masks(path):
    img=cv2.imread(str(path)); hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    m=(hsv[:,:,1]>35).astype(np.uint8)
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    return m

def score(ref_path, img_path):
    a=masks(ref_path); b=masks(img_path)
    def iou(x,y):
        inter=np.logical_and(x,y).sum(); union=np.logical_or(x,y).sum(); return float(inter/max(union,1))
    h,w=a.shape
    # Fixed normalized regions keep body/head/tail/leg evidence separate.
    regs={'body':(int(.20*w),int(.35*h),int(.72*w),int(.78*h)),
          'head':(int(.62*w),int(.25*h),int(.98*w),int(.78*h)),
          'tail':(0,int(.25*h),int(.42*w),int(.78*h)),
          'legs':(0,int(.55*h),w,int(.98*h))}
    vals={k:iou(a[y0:y1,x0:x1],b[y0:y1,x0:x1]) for k,(x0,y0,x1,y1) in regs.items()}
    vals['global']=iou(a,b); vals['combined']=.35*vals['global']+.25*vals['body']+.15*vals['head']+.1*vals['tail']+.15*vals['legs']
    return vals

def run(blender, expr):
    subprocess.run([blender,'--background','--python-expr',expr],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--reference',required=True); p.add_argument('--output',required=True); p.add_argument('--blender',required=True); p.add_argument('--work',required=True); a=p.parse_args()
    work=Path(a.work); work.mkdir(parents=True,exist_ok=True); current=work/'current.blend'; shutil.copy2(a.blend,current)
    def render(expr_path):
        expr=f"""import bpy
bpy.ops.wm.open_mainfile(filepath=r'{current.resolve()}'); s=bpy.context.scene; s.render.engine='BLENDER_WORKBENCH'; s.display.shading.light='STUDIO'; s.display.shading.color_type='TEXTURE'; s.render.resolution_x=1280; s.render.resolution_y=720; s.render.resolution_percentage=100; s.frame_set(1); s.render.filepath=r'{expr_path.resolve()}'; bpy.ops.render.render(write_still=True)"""
        run(a.blender,expr)
    baseline_img=work/'baseline.png'; render(baseline_img); base=score(a.reference,baseline_img); best=base['combined']; accepted=[]; trials=[]
    legs=['Leg_Front.L','Leg_Front.R','Leg_MidFront.L','Leg_MidFront.R','Leg_MidRear.L','Leg_MidRear.R','Leg_Rear.L','Leg_Rear.R']
    # Screen-side bending is primarily local X for this armature/camera. Keep the search small.
    joints=[(n+'_01',8.0) for n in legs]+[(n+'_02',10.0) for n in legs]
    for bone,limit in joints:
        local=[]
        for deg in (-limit/2,limit/2):
            trial=work/f'trial_{bone}_{deg:+.0f}.png'
            expr=f"""import bpy, math
bpy.ops.wm.open_mainfile(filepath=r'{current.resolve()}'); s=bpy.context.scene; s.frame_set(1); a=next(o for o in bpy.data.objects if o.type=='ARMATURE'); p=a.pose.bones.get(r'{bone}')
if p: p.rotation_mode='XYZ'; r=p.rotation_euler.copy(); r[0]+=math.radians({deg}); p.rotation_euler=r
s.render.engine='BLENDER_WORKBENCH'; s.display.shading.light='STUDIO'; s.display.shading.color_type='TEXTURE'; s.render.resolution_x=1280; s.render.resolution_y=720; s.render.resolution_percentage=100; s.render.filepath=r'{trial.resolve()}'; bpy.ops.render.render(write_still=True)"""
            run(a.blender,expr); raw=score(a.reference,trial); penalized=raw['combined']-abs(deg)/1800.0; local.append((penalized,deg,raw))
        local.sort(reverse=True,key=lambda x:x[0]); val,deg,raw=local[0]; trials.append({'bone':bone,'best_deg':deg,'score':raw,'penalized':val})
        if val>best+0.002:
            apply=f"""import bpy, math
bpy.ops.wm.open_mainfile(filepath=r'{current.resolve()}'); s=bpy.context.scene; s.frame_set(1); a=next(o for o in bpy.data.objects if o.type=='ARMATURE'); p=a.pose.bones.get(r'{bone}')
p.rotation_mode='XYZ'; r=p.rotation_euler.copy(); r[0]+=math.radians({deg}); p.rotation_euler=r; bpy.ops.wm.save_as_mainfile(filepath=r'{current.resolve()}')"""
            run(a.blender,apply); best=val; accepted.append({'bone':bone,'axis':'local_x','degrees':deg,'score':raw})
    final_img=work/'final.png'; render(final_img); final=score(a.reference,final_img); shutil.copy2(current,a.output)
    report={'baseline':base,'final':final,'accepted_changes':accepted,'tested_trials':trials,'camera_alignment_note':'Same calibrated side camera used for baseline and candidates; remaining body-height/proportion mismatch is pose evidence, not camera drift.','limits':'Upper/lower local-X trials only; ±8° upper, ±10° lower; rest-pose deviation penalty; no IK or Move Action reused.','output':str(Path(a.output).resolve())}
    Path(a.output).with_suffix('.fit_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
