import bpy, importlib.util, sys
from pathlib import Path
root=Path(r'C:\Users\rober\CreatureMotionAI')
spec=importlib.util.spec_from_file_location('cmai_collision',root/'creature_motion_ai/collision_proxies.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
for name in ['..\\seamless\\seamless_loop.blend','candidate_-4.blend','candidate_+4.blend']:
    bpy.ops.wm.open_mainfile(filepath=str(root/'data/generated/e2e_balisk_test/builder/collision_candidates'/name))
    status,path=mod.check_animation(list(range(1,121)))
    import json
    report=json.loads(Path(path).read_text())
    print(name,status,'max_new',report['max_new_collision_count'],'frames_with_new',sum(1 for r in report['frames'] if r['new_collision_count']))
