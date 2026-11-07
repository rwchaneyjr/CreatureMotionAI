"""Fast bone-segment collision proxies for visual and bounded animation checks.

These proxies are an approximation. They never replace the original mesh and are
excluded from render/export by default.
"""
import json, math
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError:  # allows source inspection outside Blender
    bpy = None

LEGS = ('Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R')
BODY = ('Body_01','Body_02','Body_03')

def _armature():
    return next((o for o in bpy.context.scene.objects if o.type == 'ARMATURE'), None)

def _chain(arm, prefix):
    return [f'Leg_{prefix}_{i:02d}' for i in (1,2,3) if arm.pose.bones.get(f'Leg_{prefix}_{i:02d}')]

def _proxy_collection():
    c = bpy.data.collections.get('CMAI_Collision_Proxies') or bpy.data.collections.new('CMAI_Collision_Proxies')
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c

def _radius_for_bone(arm, bone_name):
    # Conservative radius based on nearby bone length; never uses oversized body bounds.
    b = arm.data.bones[bone_name]
    # Keep the proxy close to the deforming segment. The previous 16% radius
    # produced false contacts where neighboring leg roots naturally overlap.
    return max(0.003, min(b.length * 0.10, 0.022))

def build_proxies():
    arm = _armature(); col = _proxy_collection()
    old = [o for o in list(col.objects) if o.get('cmai_proxy')]
    for o in old: bpy.data.objects.remove(o, do_unlink=True)
    specs=[]
    for leg in LEGS:
        specs += [(f'Leg_{leg}_{i:02d}', f'{leg}_{i:02d}') for i in (1,2,3)]
    specs += [(n, 'BODY') for n in BODY if arm and arm.pose.bones.get(n)]
    for bone_name, region in specs:
        if bone_name not in arm.pose.bones: continue
        b=arm.data.bones[bone_name]; length=b.length; r=_radius_for_bone(arm,bone_name) if region != 'BODY' else min(length*.14,.05)
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=r, depth=length)
        o=bpy.context.object; o.name=f'CMAI_PROXY_{bone_name}'; o.data.name=f'CMAI_PROXY_MESH_{bone_name}'; o['cmai_proxy']=True; o['cmai_region']=region; o['cmai_bone']=bone_name; o.hide_render=True; o.display_type='WIRE'; o.color=(0.1,0.8,1.0,0.35)
        # Cylinder is local Z; align to the rest bone, then follow the pose bone.
        o.location=arm.matrix_world @ ((b.head+b.tail)*0.5)
        o.rotation_mode='QUATERNION'; o.rotation_quaternion=(arm.matrix_world.to_3x3() @ b.vector).to_track_quat('Z','Y')
        o.parent=arm; o.parent_type='BONE'; o.parent_bone=bone_name; o.matrix_parent_inverse=arm.matrix_world.inverted()
        for cc in list(o.users_collection): cc.objects.unlink(o)
        col.objects.link(o)
    return len([o for o in col.objects if o.get('cmai_proxy')])

def _segments(arm):
    out=[]
    for leg in LEGS:
        ch=_chain(arm,leg)
        for n in ch:
            b=arm.pose.bones[n]; out.append({'bone':n,'region':leg,'a':arm.matrix_world@b.head,'b':arm.matrix_world@b.tail,'r':_radius_for_bone(arm,n)})
    for n in BODY:
        if arm.pose.bones.get(n):
            b=arm.pose.bones[n]; out.append({'bone':n,'region':'BODY','a':arm.matrix_world@b.head,'b':arm.matrix_world@b.tail,'r':min(b.length*.14,.05)})
    return out

def _segdist(a,b,c,d):
    # Closest distance between two 3D segments, robust enough for proxy gating.
    u=b-a; v=d-c; w=a-c; A=u.dot(u); B=u.dot(v); C=v.dot(v); D=u.dot(w); E=v.dot(w); den=A*C-B*B
    if den < 1e-12: s=0.; t=max(0.,min(1.,E/C if C else 0.))
    else:
        s=max(0.,min(1.,(B*E-C*D)/den)); t=max(0.,min(1.,(A*E-B*D)/den))
    return ((a+u*s)-(c+v*t)).length

def check_animation(frames=None):
    scene=bpy.context.scene; arm=_armature(); frames=frames or list(range(scene.frame_start,scene.frame_end+1)); rows=[]; max_hits=0
    scene.frame_set(1); bpy.context.view_layer.update(); base_seg=_segments(arm); baseline=set()
    for i,x in enumerate(base_seg):
        for y in base_seg[i+1:]:
            if x['region']==y['region'] and abs(int(x['bone'][-2:])-int(y['bone'][-2:]))==1: continue
            if x['region']=='BODY' and y['region']=='BODY': continue
            if x['r']+y['r']-_segdist(x['a'],x['b'],y['a'],y['b'])>0: baseline.add((x['bone'],y['bone']))
    for f in frames:
        scene.frame_set(f); bpy.context.view_layer.update(); seg=_segments(arm); hits=[]
        for i,x in enumerate(seg):
            for y in seg[i+1:]:
                if x['region']==y['region'] and x['bone'][-3:-1] != y['bone'][-3:-1]: continue
                if x['region']=='BODY' and y['region']=='BODY': continue
                # Adjacent links in one chain are legitimate joint contact.
                if x['region']==y['region'] and abs(int(x['bone'][-2:])-int(y['bone'][-2:]))==1: continue
                overlap=x['r']+y['r']-_segdist(x['a'],x['b'],y['a'],y['b'])
                if overlap>0: hits.append({'region_a':x['region'],'bone_a':x['bone'],'region_b':y['region'],'bone_b':y['bone'],'overlap':overlap})
        new=[h for h in hits if (h['bone_a'],h['bone_b']) not in baseline and (h['bone_b'],h['bone_a']) not in baseline]
        rows.append({'frame':f,'baseline_collision_count':len(baseline),'collision_count':len(hits),'new_collision_count':len(new),'collisions':hits,'new_collisions':new}); max_hits=max(max_hits,len(new))
    status='PASS_PROXY_ONLY' if max_hits==0 else 'FAIL_PROXY_COLLISION'
    root=Path(__file__).resolve().parent.parent/'data'/'generated'; root.mkdir(parents=True,exist_ok=True); out=root/'cmai_collision_proxy_report.json'; out.write_text(json.dumps({'status':status,'proxy_type':'bone_segment_capsule_approximation','baseline_pairs':sorted([list(x) for x in baseline]),'frames':rows,'max_new_collision_count':max_hits,'full_mesh_validation':'NOT_PERFORMED','note':'Proxy results do not prove exact mesh collision clearance; standing-pose overlaps are reported separately.'},indent=2),encoding='utf-8')
    return status, str(out)

class CMAI_OT_build_collision_proxies(bpy.types.Operator):
    bl_idname='cmai.build_collision_proxies'; bl_label='Build Collision Proxies'
    def execute(self, context): self.report({'INFO'},f'Built {build_proxies()} proxies'); return {'FINISHED'}
class CMAI_OT_show_collision_proxies(bpy.types.Operator):
    bl_idname='cmai.show_collision_proxies'; bl_label='Show Collision Proxies'
    def execute(self, context):
        c=bpy.data.collections.get('CMAI_Collision_Proxies'); c.hide_viewport=not c.hide_viewport if c else False; return {'FINISHED'}
class CMAI_OT_check_animation_collisions(bpy.types.Operator):
    bl_idname='cmai.check_animation_collisions'; bl_label='Check Animation Collisions'
    def execute(self, context):
        status,path=check_animation(); self.report({'INFO'},f'{status}: {path}'); return {'FINISHED'}

CLASSES=(CMAI_OT_build_collision_proxies,CMAI_OT_show_collision_proxies,CMAI_OT_check_animation_collisions)
def register():
    for c in CLASSES: bpy.utils.register_class(c)
def unregister():
    for c in reversed(CLASSES): bpy.utils.unregister_class(c)
