"""Read-only comparison of an original FBX and a generated Blender asset."""
import argparse, json
from pathlib import Path
import bpy

def snapshot(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if str(path).lower().endswith('.fbx'): bpy.ops.import_scene.fbx(filepath=str(path))
    else: bpy.ops.wm.open_mainfile(filepath=str(path))
    meshes=[]; arms=[]
    for o in bpy.context.scene.objects:
        if o.type=='MESH':
            corners=[o.matrix_world @ __import__('mathutils').Vector(c) for c in o.bound_box]
            meshes.append({'name':o.name,'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'dimensions':list(o.dimensions),'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale),'bounds_min':[min(v[i] for v in corners) for i in range(3)],'bounds_max':[max(v[i] for v in corners) for i in range(3)],'materials':[m.name if m else None for m in o.data.materials],'modifiers':[(m.type,m.object.name if getattr(m,'object',None) else None) for m in o.modifiers]})
        if o.type=='ARMATURE':
            arms.append({'name':o.name,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale),'bones':[{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local),'matrix':sum(([list(row) for row in b.matrix_local],[]),[])} for b in o.data.bones]})
    return {'path':str(path),'meshes':meshes,'armatures':arms,'actions':[a.name for a in bpy.data.actions]}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--original',required=True); p.add_argument('--generated',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    original=snapshot(a.original); generated=snapshot(a.generated)
    report={'original':original,'generated':generated,'differences':{}}
    for key in ('meshes','armatures'):
        report['differences'][key+'_count']=(len(original[key]),len(generated[key]))
    if original['meshes'] and generated['meshes']:
        om,gm=original['meshes'][0],generated['meshes'][0]
        report['differences']['mesh_topology']={'vertices':(om['vertices'],gm['vertices']),'polygons':(om['polygons'],gm['polygons']),'dimensions':(om['dimensions'],gm['dimensions']),'materials':(om['materials'],gm['materials']),'modifiers':(om['modifiers'],gm['modifiers'])}
        report['differences']['mesh_transform']={'location':(om['location'],gm['location']),'rotation':(om['rotation'],gm['rotation']),'scale':(om['scale'],gm['scale']),'bounds':(om['bounds_min']+om['bounds_max'],gm['bounds_min']+gm['bounds_max'])}
    if original['armatures'] and generated['armatures']:
        ob,gb=original['armatures'][0]['bones'],generated['armatures'][0]['bones']; om={b['name']:b for b in ob}; gm={b['name']:b for b in gb}; common=sorted(set(om)&set(gm)); report['differences']['bone_names']={'original':len(ob),'generated':len(gb),'common':len(common),'missing_in_generated':sorted(set(om)-set(gm)),'extra_in_generated':sorted(set(gm)-set(om))}; report['differences']['rest_bones']=[{'bone':n,'head_delta':[gm[n]['head'][i]-om[n]['head'][i] for i in range(3)],'tail_delta':[gm[n]['tail'][i]-om[n]['tail'][i] for i in range(3)],'parent_changed':om[n]['parent']!=gm[n]['parent']} for n in common if om[n]['head']!=gm[n]['head'] or om[n]['tail']!=gm[n]['tail'] or om[n]['parent']!=gm[n]['parent']]
    Path(a.output).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps({'output':a.output,'mesh_count':report['differences']['meshes_count'],'armature_count':report['differences']['armatures_count']}))
if __name__=='__main__': main()
