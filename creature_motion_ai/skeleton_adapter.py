import subprocess
from pathlib import Path
def extract_profile(blend_path, output_path, blender):
    expr=f'''import bpy,json
bpy.ops.wm.open_mainfile(filepath=r"{Path(blend_path).resolve()}"); arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); bones=[]
for b in arm.data.bones: bones.append({{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head),'tail':list(b.tail),'length':b.length,'matrix_local':[list(r) for r in b.matrix_local]}})
legs={{}}
for n in ['Front','MidFront','MidRear','Rear']:
 for side in ['L','R']:
  key=f'Leg_{{n}}.{{side}}'; chain=[key+'_01',key+'_02',key+'_03']; legs[key]=chain if all(x in arm.data.bones for x in chain) else []
out={{'armature':arm.name,'bone_count':len(bones),'bones':bones,'leg_chains':legs,'coordinate_note':'Blender armature-local rest coordinates'}}; open(r"{str(Path(output_path).resolve()).replace(chr(92),chr(47))}",'w').write(json.dumps(out,indent=2))'''
    subprocess.run([blender,'--background','--python-expr',expr],check=True)
