import json, sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.modules.pop('creature_motion_ai', None)
import creature_motion_ai
from creature_motion_ai import auto_anatomy, reference_walk
scene=bpy.context.scene
arm,mesh=reference_walk.bind_creature(scene)
report=auto_anatomy.detect_anatomy(arm)
out=ROOT/'data/generated/auto_anatomy_tests'
out.mkdir(parents=True,exist_ok=True)
(out/'balisk_auto_anatomy.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'status':report['status'],'selected_leg_count':report['selected_leg_count'],'confidence':report['mapping_confidence'],'chains':[x['bones'] for x in report['selected_chains']]},indent=2))
assert report['selected_leg_count']==8
assert report['confirmed'] is False
assert all(len(x['bones'])==3 for x in report['selected_chains'])
