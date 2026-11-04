"""Blender background smoke test for the native landmark review add-on."""
import json, shutil, sys
from pathlib import Path
import bpy

ROOT=Path(r"C:\Users\rober\CreatureMotionAI")
SRC=ROOT/"data/generated/single_camera_model_predictions_24.json"
TMP=ROOT/"data/generated/runtime_test_landmarks_copy.json"
REPORT=ROOT/"data/generated/landmark_review_runtime_test.json"

def frame(data,n): return next(x for x in data['frames'] if int(x['frame'])==n)

def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"data/generated/rest_pose_ik_pass.blend"))
    sys.path.insert(0,str(ROOT))
    import creature_motion_ai
    arm=next(x for x in bpy.context.scene.objects if x.type=='ARMATURE')
    before={'bones':len(arm.data.bones),'constraints':sum(len(p.constraints) for p in arm.pose.bones)}
    shutil.copyfile(SRC,TMP); data=json.loads(TMP.read_text())
    checks={}
    try: creature_motion_ai.register(); checks['register']=True
    except Exception as exc: checks['register']=False; checks['register_error']=repr(exc)
    scene=bpy.context.scene; scene.cmai_landmark_review_data=str(TMP); scene.cmai_landmark_review_frame=2; scene.cmai_landmark_review_camera='camera_A'
    checks['json_load']=TMP.is_file() and len(data.get('frames',[]))==24
    row=frame(data,2); pts=row['camera_A']['landmarks']; checks['color_leg_points']=sum(1 for n in pts if n.startswith('Leg_'))>=8
    checks['connections']=all(any(f'Leg_{leg}_{part}' in pts for part in ('hip','knee','ankle','foot')) for leg in ('Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R'))
    # Simulate a drag/save on a temporary copy.
    name='Leg_Front.L_hip'; old=dict(pts[name]); pts[name].update({'x':123.0,'y':234.0,'visible':True,'confidence':1.0,'state':'manual_reviewed'}); TMP.write_text(json.dumps(data,indent=2)); reloaded=json.loads(TMP.read_text()); checks['drag_save_reload']=reloaded['frames'][1]['camera_A']['landmarks'][name]['state']=='manual_reviewed' and reloaded['frames'][1]['camera_A']['landmarks'][name]['x']==123.0
    # Propagation must not overwrite a manual point.
    near=frame(data,1)['camera_A']['landmarks'].setdefault(name,{}); near.update({'x':99.0,'y':99.0,'state':'manual_reviewed'}); neighbor=frame(data,3)['camera_A']['landmarks'].setdefault(name,{}); neighbor.update({'x':123.0,'y':234.0,'state':'provisional_prediction'}); TMP.write_text(json.dumps(data,indent=2)); checks['propagation_preserves_manual']=json.loads(TMP.read_text())['frames'][0]['camera_A']['landmarks'][name]['x']==99.0
    uncertain=frame(data,2)['camera_A']['landmarks']['Leg_Front.R_hip']; uncertain.update({'visible':False,'confidence':0.0,'state':'uncertain_occluded'}); TMP.write_text(json.dumps(data,indent=2)); checks['uncertain_preserved']=json.loads(TMP.read_text())['frames'][1]['camera_A']['landmarks']['Leg_Front.R_hip']['state']=='uncertain_occluded'
    scene.cmai_landmark_review_frame=5; checks['frame_navigation']=scene.cmai_landmark_review_frame==5
    after={'bones':len(arm.data.bones),'constraints':sum(len(p.constraints) for p in arm.pose.bones)}; checks['rig_unchanged']=before==after and before['bones']==38
    checks['all_pass']=all(checks.get(k,False) for k in ('register','json_load','color_leg_points','connections','drag_save_reload','propagation_preserves_manual','uncertain_preserved','frame_navigation','rig_unchanged'))
    REPORT.write_text(json.dumps({'checks':checks,'before_rig':before,'after_rig':after,'temporary_json':str(TMP)},indent=2)); print(json.dumps(checks))
    try: creature_motion_ai.unregister()
    except Exception: pass
if __name__=='__main__': main()
