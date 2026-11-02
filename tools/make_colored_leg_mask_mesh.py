"""Duplicate the original mesh and color vertices by dominant leg weight."""
import argparse,json
from pathlib import Path
import bpy

LEGS=("Leg_Front.L","Leg_Front.R","Leg_MidFront.L","Leg_MidFront.R","Leg_MidRear.L","Leg_MidRear.R","Leg_Rear.L","Leg_Rear.R")
COLORS=[(1,.05,.05,1),(1,.35,.02,1),(1,.9,.02,1),(.1,.9,.1,1),(.05,.8,1,1),(.1,.25,1,1),(.45,.08,1,1),(1,.05,.7,1)]
NEUTRAL=(.18,.18,.18,1)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
    src=next(o for o in bpy.data.objects if o.type=='MESH'); dup=src.copy(); dup.data=src.data.copy(); dup.name='CMAI_Temporary_Leg_Color_Mask'; bpy.context.collection.objects.link(dup)
    for i,c in enumerate(COLORS):
        m=bpy.data.materials.new('CMAI_LegID_'+str(i+1)); m.diffuse_color=c; m.use_nodes=True; bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=c; bs.inputs['Emission Color'].default_value=c; bs.inputs['Emission Strength'].default_value=1.5; dup.data.materials.append(m)
    neutral=bpy.data.materials.new('CMAI_Neutral_Body'); neutral.diffuse_color=NEUTRAL; neutral.use_nodes=True
    bs=neutral.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=NEUTRAL
    dup.data.materials.append(neutral)
    groups={name:[dup.vertex_groups.get(name+'_'+suffix) for suffix in ('01','02','03') if dup.vertex_groups.get(name+'_'+suffix)] for name in LEGS}
    for poly in dup.data.polygons:
        votes=[]
        for name,chain in groups.items():
            vals=[]
            for group in chain:
                for vi in poly.vertices:
                    try: vals.append(group.weight(vi))
                    except RuntimeError: pass
            votes.append(max(vals) if vals else 0.0)
        best=max(range(len(votes)),key=votes.__getitem__)
        poly.material_index=best if votes[best] > 0.20 else len(COLORS)
    src.hide_render=True; src.hide_viewport=True
    dup['cmai_mask_source']=src.name; dup['cmai_original_preserved']=True
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve()))
    print(json.dumps({'output':str(a.output),'mesh':dup.name,'legs':len(LEGS)}))
if __name__=='__main__': main()
