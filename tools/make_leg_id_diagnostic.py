"""Create a non-destructive color-coded eight-leg identity diagnostic scene."""
import argparse, json
from pathlib import Path
import bpy
from mathutils import Vector

COLORS=[(1,0.05,0.05,1),(1,0.35,0.02,1),(1,0.9,0.02,1),(0.1,0.9,0.1,1),(0.05,0.8,1,1),(0.1,0.25,1,1),(0.45,0.08,1,1),(1,0.05,0.7,1)]
LEGS=("Leg_Front.L","Leg_Front.R","Leg_MidFront.L","Leg_MidFront.R","Leg_MidRear.L","Leg_MidRear.R","Leg_Rear.L","Leg_Rear.R")

def mat(name,color):
    m=bpy.data.materials.new(name); m.diffuse_color=color; m.use_nodes=True; bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=color; bs.inputs['Emission Color'].default_value=color; bs.inputs['Emission Strength'].default_value=2.0; return m

def marker(name,loc,material,size=0.045):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=size, location=loc); o=bpy.context.object; o.name=name; o.data.materials.append(material); return o

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE'); bpy.context.scene.frame_set(1)
    for i,leg in enumerate(LEGS):
        material=mat('CMAI_ID_'+leg.replace('.','_'),COLORS[i])
        for suffix,size in (('_01',0.055),('_02',0.05),('_03',0.045)):
            b=rig.pose.bones.get(leg+suffix)
            if b:
                marker('CMAI_ID_'+leg+suffix+'_head',rig.matrix_world@b.head,material,size)
                marker('CMAI_ID_'+leg+suffix+'_tail',rig.matrix_world@b.tail,material,size)
    rig['cmai_id_diagnostic']='temporary colored leg identity markers'; rig['cmai_source_preserved']=True
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve()))
    print(json.dumps({'output':str(a.output),'legs':len(LEGS),'note':'Markers only; source mesh and materials unchanged.'}))
if __name__=='__main__': main()
