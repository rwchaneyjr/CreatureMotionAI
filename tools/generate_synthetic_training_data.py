"""Generate a small, deterministic two-camera synthetic keypoint dataset."""
import argparse, json, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); p.add_argument('--blender',required=True); p.add_argument('--count',type=int,default=100); a=p.parse_args()
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True); (out/'camera_A').mkdir(exist_ok=True); (out/'camera_B').mkdir(exist_ok=True)
    expr=f"""
import bpy, json, math, random
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
bpy.ops.wm.open_mainfile(filepath=r'{Path(a.blend).resolve()}')
s=bpy.context.scene; s.frame_start=1; s.frame_end=1; s.render.engine='BLENDER_WORKBENCH'; s.display.shading.light='STUDIO'; s.display.shading.color_type='TEXTURE'; s.render.resolution_x=256; s.render.resolution_y=144; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); s.frame_set(1)
base={{p.name:(p.rotation_mode,p.rotation_euler.copy(),p.location.copy()) for p in arm.pose.bones}}; arm.animation_data.action=None
cameras=[('camera_A',bpy.data.objects['CMAI_Studio_Camera_A_Side']),('camera_B',bpy.data.objects['CMAI_Studio_Camera_B_Front'])]
legs=['Leg_Front.L','Leg_Front.R','Leg_MidFront.L','Leg_MidFront.R','Leg_MidRear.L','Leg_MidRear.R','Leg_Rear.L','Leg_Rear.R']
parts=['Root','Body_01','Body_02','Body_03','Head_01','Head_02']+[f'Tail_{{i}}' for i in range(1,9)]
for n in legs:
    parts += [n+'_01',n+'_02',n+'_03']
def reset():
    for n,(mode,rot,loc) in base.items():
        p=arm.pose.bones[n]; p.rotation_mode=mode; p.rotation_euler=rot; p.location=loc
def joints():
    out={{}}
    for n in parts:
        p=arm.pose.bones.get(n)
        if not p: continue
        out[n+'_head']=list(arm.matrix_world @ p.head); out[n+'_tail']=list(arm.matrix_world @ p.tail)
    return out
def project(cam,pt):
    q=world_to_camera_view(s,cam,Vector(pt)); in_frame=bool(0<=q.x<=1 and 0<=q.y<=1 and q.z>=0); visible=False
    if in_frame:
        origin=cam.matrix_world.translation.copy(); ray=Vector(pt)-origin; dist=ray.length
        hit,loc,normal,*_=s.ray_cast(bpy.context.evaluated_depsgraph_get(),origin,ray.normalized(),distance=dist+0.25)
        # A joint is visible when the first mesh surface is at or behind the joint.
        visible=bool(hit and (loc-origin).length >= dist-0.025)
    return [round(q.x*256,3),round((1-q.y)*144,3),in_frame,visible]
rng=random.Random(8301); labels=[]
for i in range({int(a.count)}):
    reset(); s.frame_set(1)
    # Bounded local rotations preserve the original pose and avoid the failed IK path.
    for n in legs:
        for suffix,limit in (('_01',0.22),('_02',0.28)):
            p=arm.pose.bones[n+suffix]; p.rotation_mode='XYZ'; p.rotation_euler.x += rng.uniform(-limit,limit); p.rotation_euler.y += rng.uniform(-0.08,0.08)
    for n,limit in [('Body_02',0.08),('Head_01',0.12),('Head_02',0.12)]:
        p=arm.pose.bones[n]; p.rotation_mode='XYZ'; p.rotation_euler.z += rng.uniform(-limit,limit)
    for n in ('Tail_03','Tail_05','Tail_07'):
        p=arm.pose.bones[n]; p.rotation_mode='XYZ'; p.rotation_euler.z += rng.uniform(-0.10,0.10)
    truth=joints(); pose={{n:list(arm.pose.bones[n].rotation_euler) for n in parts if arm.pose.bones.get(n)}}
    rec={{'sample':i,'seed':8301,'pose_rotations':pose,'joints_3d':truth,'cameras':{{}}}}
    for label,cam in cameras:
        rec['cameras'][label]={{'joints_2d':{{k:project(cam,v) for k,v in truth.items()}}}}
        s.camera=cam; s.render.filepath=str(Path(r'{out.resolve()}')/label/f'pose_{{i:04d}}.png'); bpy.ops.render.render(write_still=True)
    labels.append(rec)
Path(r'{(out/'labels.jsonl').resolve()}').write_text(''.join(json.dumps(x)+'\\n' for x in labels),encoding='utf-8')
Path(r'{(out/'dataset_meta.json').resolve()}').write_text(json.dumps({{'count':len(labels),'resolution':[256,144],'cameras':['camera_A','camera_B'],'joint_count':len(labels[0]['joints_3d']),'synthetic_only':True,'weights_or_training':False}},indent=2),encoding='utf-8')
print(json.dumps({{'count':len(labels),'output':r'{out.resolve()}','joint_count':len(labels[0]['joints_3d'])}}))
"""
    r=subprocess.run([a.blender,'--background','--python-expr',expr],capture_output=True,text=True,check=True)
    print(r.stdout[-2000:]); print(r.stderr[-1000:])
if __name__=='__main__': main()
