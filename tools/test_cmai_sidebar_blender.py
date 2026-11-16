import bpy, json, sys
from pathlib import Path
root=Path(r'C:\Users\rober\CreatureMotionAI')
sys.path.insert(0,str(root))
import creature_motion_ai
try:
    creature_motion_ai.register(); registration='registered'
except ValueError as e:
    registration='already_registered'
scene=bpy.context.scene
ops=['cmai.detect_creature_automatically','cmai.analyze_video_and_rig','cmai.review_all_landmarks','cmai.reference_walk_step','cmai.compare_improve_animation','cmai.make_seamless_loop']
registered=[]
for op in ops:
    try: registered.append({'operator':op,'registered':hasattr(bpy.ops.cmai,op.split('.',1)[1])})
    except Exception as e: registered.append({'operator':op,'registered':False,'error':str(e)})
props=['cmai_walk','cmai_video','cmai_model','cmai_output','cmai_python']
report={'status':'SIDEBAR_SMOKE_TEST','registration':registration,'blender_version':bpy.app.version_string,'panel':'CMAI_PT_reference_walk','operators':registered,'scene_properties':{p:hasattr(scene,p) for p in props},'solver_backend':getattr(scene.cmai_walk,'solver_backend','NOT_AVAILABLE'),'pinocchio_auto_enabled':False,'original_file':str(bpy.data.filepath)}
out=root/'data/generated/sidebar_blender_test'; out.mkdir(parents=True,exist_ok=True); (out/'sidebar_smoke_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
