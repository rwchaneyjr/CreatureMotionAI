"""Estimate per-camera 2D affine correction between detector and Blender projections."""
import argparse,json
from pathlib import Path
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

def solve(rows):
    # Translation + independent scale is intentionally conservative.
    if len(rows)<2: return {'scale_x':1.0,'scale_y':1.0,'offset_x':0.0,'offset_y':0.0,'samples':len(rows)}
    xs=[r[0] for r in rows]; ys=[r[1] for r in rows]; us=[r[2] for r in rows]; vs=[r[3] for r in rows]
    sx=(max(us)-min(us))/max(max(xs)-min(xs),1e-6); sy=(max(vs)-min(vs))/max(max(ys)-min(ys),1e-6)
    ox=sum(u-sx*x for x,u in zip(xs,us))/len(rows); oy=sum(v-sy*y for y,v in zip(ys,vs))/len(rows)
    residual=sum(((sx*x+ox-u)**2+(sy*y+oy-v)**2)**.5 for x,y,u,v in rows)/len(rows)
    return {'scale_x':sx,'scale_y':sy,'offset_x':ox,'offset_y':oy,'samples':len(rows),'mean_residual_px':residual}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--proposals',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    data=json.loads(Path(a.proposals).read_text(encoding='utf-8')); bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve())); frame=data.get('frames',[{}])[0]; scene=bpy.context.scene; rig=next(o for o in bpy.data.objects if o.type=='ARMATURE'); cams={'camera_A':bpy.data.objects.get('CMAI_Calibrated_Side_Camera'),'camera_B':bpy.data.objects.get('CMAI_Calibrated_Front_Camera')}; result={}
    for label,cam in cams.items():
        rows=[]
        for name,item in frame.get(label,{}).get('landmarks',{}).items():
            bone_name=name.rsplit('_',1)[0]; bone=rig.data.bones.get(bone_name)
            if not bone or not item.get('visible'): continue
            co=rig.matrix_world @ (bone.head_local if name.endswith('_head') else bone.tail_local); uv=world_to_camera_view(scene,cam,co); rows.append((float(uv.x*640),float((1-uv.y)*720),float(item['x']),float(item['y'])))
        result[label]=solve(rows)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps({'status':'panel_affine_calibration','cameras':result,'note':'Calibration is provisional and must be checked visually before triangulation.'},indent=2),encoding='utf-8'); print(json.dumps(result))
if __name__=='__main__': main()
