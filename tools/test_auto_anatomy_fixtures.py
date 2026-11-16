import json, sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.modules.pop('creature_motion_ai',None)
from creature_motion_ai.auto_anatomy import detect_anatomy

fixtures={
 'balisk': ROOT/'data/generated/cmai_exact_standing_baseline_24f.blend',
 'quadruped_crab': Path('C:/Users/rober/Desktop/Blender Models/WoodlandCoralCrab_RigOnly.blend'),
 'biped_golem': Path('C:/Users/rober/Desktop/Blender Models/StoneGolem_RigOnly.blend'),
}
out=ROOT/'data/generated/auto_anatomy_tests'; out.mkdir(parents=True,exist_ok=True)
results={}
for label,path in fixtures.items():
    if not path.is_file():
        results[label]={'status':'NOT AVAILABLE','path':str(path)}; continue
    bpy.ops.wm.open_mainfile(filepath=str(path))
    arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    if len(arms)!=1:
        results[label]={'status':'FAIL','reason':f'expected one armature, found {len(arms)}'}; continue
    report=detect_anatomy(arms[0]); results[label]={
        'status':report['status'],'armature':report['armature'],
        'selected_leg_count':report['selected_leg_count'],
        'mapping_confidence':report['mapping_confidence'],
        'chains':report['selected_chains'],
        'warnings':report['warnings'],
    }
    (out/f'{label}_auto_anatomy.json').write_text(json.dumps(report,indent=2))
(out/'fixture_summary.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
