"""Gate 2D proposals using projected endpoints of the original rig."""
import argparse,json,math
from pathlib import Path
import bpy
from bpy_extras.object_utils import world_to_camera_view

def main():
    p=argparse.ArgumentParser(); p.add_argument('--proposals',required=True); p.add_argument('--output',required=True); p.add_argument('--threshold',type=float,default=90.0); a=p.parse_args()
    data=json.loads(Path(a.proposals).read_text(encoding='utf-8')); scene=bpy.context.scene; rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    cams={'camera_A':bpy.data.objects.get('CMAI_Calibrated_Front_Camera'),'camera_B':bpy.data.objects.get('CMAI_Calibrated_Side_Camera')}; width,height=640,720
    result=[]; accepted=rejected=0
    for row in data.get('frames',[]):
        frame_result={'frame':row['frame']}
        for cam_name in ('camera_A','camera_B'):
            cam=cams[cam_name]; out={}
            if not cam: frame_result[cam_name]={'landmarks':out}; continue
            for name,item in row.get(cam_name,{}).get('landmarks',{}).items():
                endpoint='head' if name.endswith('_head') else 'tail'; bone_name=name.rsplit('_',1)[0]; bone=rig.data.bones.get(bone_name)
                new=dict(item); new['rig_gate']='uncertain_no_bone'
                if bone:
                    co=rig.matrix_world @ (bone.head_local if endpoint=='head' else bone.tail_local); uv=world_to_camera_view(scene,cam,co); px,py=float(uv.x*width),float((1-uv.y)*height); d=math.hypot(float(item['x'])-px,float(item['y'])-py); new['rig_projected_xy']=[round(px,2),round(py,2)]; new['rig_distance_px']=round(d,2)
                    if d<=a.threshold and item.get('state') not in ('uncertain_outside_foreground',): new['rig_gate']='accepted'; accepted+=1
                    else: new['state']='uncertain_rig_gate'; new['confidence']=0.0; rejected+=1
                out[name]=new
            frame_result[cam_name]={'landmarks':out}
        result.append(frame_result)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps({'frames':result,'status':'projected_rig_gated','threshold_px':a.threshold,'accepted_points':accepted,'rejected_points':rejected,'note':'Rest-pose projection is a gate, not a final moving-pose label.'},indent=2),encoding='utf-8'); print(json.dumps({'output':str(out),'accepted':accepted,'rejected':rejected}))
if __name__=='__main__': main()
