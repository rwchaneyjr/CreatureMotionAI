"""Import an FBX and create a non-destructive eight-leg material-ID diagnostic."""
import argparse, json
from pathlib import Path
import bpy

LEGS=("Leg_Front.L","Leg_Front.R","Leg_MidFront.L","Leg_MidFront.R","Leg_MidRear.L","Leg_MidRear.R","Leg_Rear.L","Leg_Rear.R")
COLORS=((1,.05,.05,1),(1,.35,.02,1),(1,.9,.02,1),(.1,.9,.1,1),(.05,.8,1,1),(.1,.25,1,1),(.45,.08,1,1),(1,.05,.7,1))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    bpy.ops.import_scene.fbx(filepath=str(Path(a.source).resolve()))
    mesh=next((o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.vertex_groups)>0),None)
    if not mesh: raise RuntimeError('FBX contains no mesh')
    dup=mesh.copy(); dup.data=mesh.data.copy(); dup.name='CMAI_FBX_Leg_Color_Test'; bpy.context.collection.objects.link(dup)
    for i,c in enumerate(COLORS,1):
        m=bpy.data.materials.new(f'CMAI_FBX_Leg_{i}'); m.diffuse_color=c; m.use_nodes=True; bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=c; bs.inputs['Emission Color'].default_value=c; bs.inputs['Emission Strength'].default_value=1.2; dup.data.materials.append(m)
    neutral=bpy.data.materials.new('CMAI_FBX_Body_Neutral'); neutral.diffuse_color=(.18,.18,.18,1); neutral.use_nodes=True; neutral.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.18,.18,.18,1); dup.data.materials.append(neutral)
    groups={n:[dup.vertex_groups.get(f'{n}_{s:02d}') for s in (1,2,3) if dup.vertex_groups.get(f'{n}_{s:02d}')] for n in LEGS}
    for poly in dup.data.polygons:
        votes=[]
        for chain in groups.values():
            vals=[]
            for g in chain:
                for vi in poly.vertices:
                    try: vals.append(g.weight(vi))
                    except RuntimeError: pass
            votes.append(max(vals) if vals else 0.0)
        best=max(range(8),key=votes.__getitem__); poly.material_index=best if votes[best]>.20 else 8
    mesh.hide_render=True; mesh.hide_viewport=True; dup['cmai_source_fbx']=str(Path(a.source).resolve()); dup['cmai_original_preserved']=True
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve()))
    print(json.dumps({'output':str(Path(a.output).resolve()),'mesh':mesh.name,'colored_mesh':dup.name,'leg_groups':sum(bool(v) for v in groups.values())}))
if __name__=='__main__': main()
