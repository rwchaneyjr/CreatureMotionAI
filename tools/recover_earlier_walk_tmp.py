import bpy, sys, json
from pathlib import Path

src=sys.argv[-2]; out=Path(sys.argv[-1]); out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=src)
scene=bpy.context.scene; arm=next(o for o in scene.objects if o.type=='ARMATURE')
source=arm.animation_data.action if arm.animation_data else None
duplicate=source.copy() if source else None
if duplicate:
    duplicate.name=source.name+'_RecoveredWorkingBaseline'
    arm.animation_data.action=duplicate
scene.frame_start=1; scene.frame_end=120; scene.render.fps=24
bpy.ops.wm.save_as_mainfile(filepath=str(out))
report={'source':src,'working_copy':str(out),'source_action':source.name if source else None,'duplicate_action':duplicate.name if duplicate else None,'frame_range':[1,120],'fps':24,'original_preserved':True,'ground_fitting_regression':'BYPASSED','pinocchio':'DISABLED'}
rp=out.with_suffix('.recovery_report.json'); rp.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report))
