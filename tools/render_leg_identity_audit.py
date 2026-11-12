import bpy, json, sys, math
from mathutils import Vector
from pathlib import Path

args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
blend_path, out_dir = args[:2]
out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene
scene.frame_set(1)
deps = bpy.context.evaluated_depsgraph_get()
arm = bpy.data.objects.get('CrimsonSpineBehemoth_Rig')
mesh = bpy.data.objects.get('CrimsonSpineBehemoth_Mesh')
if not arm or not mesh:
    raise RuntimeError('Expected Balisk rig/mesh not found')

legs = ['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
chains = {}
for leg in legs:
    prefix = 'Leg_' + leg + '_'
    names = [prefix + f'{i:02d}' for i in (1,2,3)]
    chains[leg] = [n for n in names if arm.pose.bones.get(n)]

audit = {'source_blend': blend_path, 'frame': 1, 'mesh': mesh.name, 'armature': arm.name,
         'bone_count': len(arm.data.bones), 'leg_chains': chains, 'actions': [], 'nla_tracks': [],
         'constraints': [], 'drivers': bool(arm.animation_data and arm.animation_data.drivers),
         'mesh_vertex_count': len(mesh.data.vertices), 'mesh_modifiers': [m.type for m in mesh.modifiers]}
if arm.animation_data:
    if arm.animation_data.action: audit['actions'].append(arm.animation_data.action.name)
    for tr in arm.animation_data.nla_tracks:
        audit['nla_tracks'].append({'name': tr.name, 'strips': [s.name for s in tr.strips]})
for pb in arm.pose.bones:
    for c in pb.constraints:
        audit['constraints'].append({'bone': pb.name, 'type': c.type, 'name': c.name})

scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 900, 600, 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
if not scene.world: scene.world = bpy.data.worlds.new('CMAI_Diagnostic_World')
scene.world.color = (0.035,0.035,0.035)

cam = bpy.data.objects.get('CMAI_LegIdentity_Camera')
if not cam:
    cam = bpy.data.objects.new('CMAI_LegIdentity_Camera', bpy.data.cameras.new('CMAI_LegIdentity_Camera'))
    scene.collection.objects.link(cam)
if cam.type != 'CAMERA': raise RuntimeError('Diagnostic camera object has wrong type')
cam.location = (-3.0, 0.0, 0.02)
target = Vector((0.0, 0.0, 0.0))
direction = target - cam.location
cam.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'; cam.data.ortho_scale=1.8
scene.camera = cam

created=[]
colors=[(1,0.15,0.1,1),(0.1,1,0.2,1),(0.1,0.5,1,1),(1,0.7,0.1,1),(0.8,0.2,1,1),(0.1,1,1,1),(1,0.3,0.7,1),(0.7,1,0.2,1)]
for idx,leg in enumerate(legs):
    mat=bpy.data.materials.new('CMAI_'+leg+'_Marker'); mat.diffuse_color=colors[idx]
    for j,bn in enumerate(chains[leg]):
        pb=arm.pose.bones[bn]; p=arm.matrix_world @ pb.head
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.018, location=p)
        ob=bpy.context.object; ob.name='CMAI_MARKER_'+leg+'_'+str(j+1); ob.data.materials.append(mat); created.append(ob)
        bpy.ops.object.text_add(location=p + Vector((0,0,0.025)))
        txt=bpy.context.object; txt.name='CMAI_LABEL_'+leg+'_'+str(j+1); txt.data.body=leg+' '+str(j+1); txt.data.size=0.035; txt.data.align_x='CENTER'; txt.data.materials.append(mat); txt.rotation_euler=cam.rotation_euler; created.append(txt)

scene.render.filepath=str(out/'leg_identity_side_minus_x.png')
bpy.ops.render.render(write_still=True)
scene['cmai_camera_search']={'direction':'-X','orthographic_scale':1.8,'height_offset':-0.08}
scene['cmai_diagnostic']='Leg identity audit; temporary markers only'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'leg_identity_audit.blend'))
Path(out/'standing_pose_audit.json').write_text(json.dumps(audit, indent=2))
print(json.dumps({'render':str(out/'leg_identity_side_minus_x.png'),'blend':str(out/'leg_identity_audit.blend'),'report':str(out/'standing_pose_audit.json'),'chains':chains}, indent=2))
