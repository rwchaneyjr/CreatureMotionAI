"""Inspect original leg hierarchy, transforms, scales, and evaluated endpoints."""
import argparse, json, sys
from pathlib import Path
import bpy

LEGS=["Leg_Front.L","Leg_Front.R","Leg_MidFront.L","Leg_MidFront.R","Leg_MidRear.L","Leg_MidRear.R","Leg_Rear.L","Leg_Rear.R"]

def mat(m): return [[round(float(x),8) for x in row] for row in m]
def vec(v): return [round(float(x),8) for x in v]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=p.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve())); scene=bpy.context.scene; scene.frame_set(1); arm=next(o for o in scene.objects if o.type=='ARMATURE'); bpy.context.view_layer.update()
    result={'blend':str(Path(a.blend).resolve()),'bone_count':len(arm.data.bones),'object_scale':vec(arm.scale),'object_matrix_world':mat(arm.matrix_world),'scene_frame':scene.frame_current,'legs':[]}
    for root in LEGS:
        chain=[]; name=root+'_01'; seen=set()
        while name and name not in seen:
            seen.add(name); b=arm.data.bones.get(name); pbone=arm.pose.bones.get(name)
            if not b: chain.append({'name':name,'missing':True}); break
            chain.append({'name':b.name,'parent':b.parent.name if b.parent else None,'children':[c.name for c in b.children],'use_connect':b.use_connect,'length':b.length,'head_local':vec(b.head_local),'tail_local':vec(b.tail_local),'matrix_local':mat(b.matrix_local),'matrix':mat(b.matrix),'roll':None,'head_world':vec(arm.matrix_world @ pbone.head),'tail_world':vec(arm.matrix_world @ pbone.tail),'pose_matrix':mat(pbone.matrix),'matrix_basis':mat(pbone.matrix_basis),'rotation_mode':pbone.rotation_mode,'constraints':[{'type':c.type,'name':c.name,'chain_count':getattr(c,'chain_count',None),'space':getattr(c,'owner_space',None)} for c in pbone.constraints]}); name=b.children[0].name if b.children else None
        result['legs'].append({'root':root,'chain':chain,'expected_names':[root+'_01',root+'_02',root+'_03'],'actual_chain_length':len(chain)})
    Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'output':a.output,'bones':result['bone_count'],'legs':len(result['legs'])}))
if __name__=='__main__': main()
