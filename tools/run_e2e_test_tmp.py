import sys, json, time
from pathlib import Path
import bpy

ROOT=Path(r'C:\Users\rober\CreatureMotionAI')
VIDEO=Path(r'C:\Users\rober\Downloads\2VIEWSBALISK SYNCWALK.mp4')
OUT=ROOT/'data/generated/e2e_balisk_test'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'data/generated/original_static_standing.blend'))
import importlib.util
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
auto=load('cmai_auto',ROOT/'creature_motion_ai/auto_anatomy.py')
analysis=load('cmai_analysis',ROOT/'creature_motion_ai/video_rig_analysis.py')
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH')
det=auto.detect_anatomy(arm)
(OUT/'anatomy_detection.json').write_text(json.dumps(det,indent=2),encoding='utf-8')
profile=auto.profile_from_detection(det,next(b.name for b in arm.data.bones if b.parent is None))
profile['confirmed']=True; profile['mapping_status']='E2E_TEST_MANUALLY_CONFIRMED_BY_TEST_HARNESS'
(OUT/'confirmed_profile.json').write_text(json.dumps(profile,indent=2),encoding='utf-8')
analysis_result=analysis.analyze(VIDEO,OUT/'anatomy_detection.json',OUT/'video_analysis',None,None)
(OUT/'video_analysis_summary.json').write_text(json.dumps(analysis_result,indent=2),encoding='utf-8')
print('DETECTION',det['selected_leg_count'],det['mapping_confidence'])
print('VIDEO',analysis_result.get('status'))
