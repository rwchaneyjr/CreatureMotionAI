import bpy, json, math, os, sys
from mathutils import Vector, Quaternion

src = bpy.data.filepath
out_dir = os.path.abspath('data/generated/frontL_three_pose_explicit_reversed')
os.makedirs(out_dir, exist_ok=True)
arm = bpy.data.objects.get('CrimsonSpineBehemoth_Rig')
mesh = bpy.data.objects.get('CrimsonSpineBehemoth_Mesh')
names = ['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 800; scene.render.resolution_y = 800; scene.render.resolution_percentage = 100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False

# Capture the exact evaluated standing pose from the v13 baseline.
scene.frame_set(1); bpy.context.view_layer.update()
base = {n: arm.pose.bones[n].rotation_quaternion.copy() for n in names}

def qx(a): return Quaternion((1,0,0), a)
def pose(frame, angles):
    scene.frame_set(frame)
    for n in names:
        arm.pose.bones[n].rotation_mode='QUATERNION'
        arm.pose.bones[n].rotation_quaternion = qx(angles.get(n,0.0)) @ base[n]
        arm.pose.bones[n].keyframe_insert('rotation_quaternion', frame=frame)

act = bpy.data.actions.new('CMAI_FrontL_ThreePose_Proof_ReversedBend')
arm.animation_data_create(); arm.animation_data.action = act
# Explicit, large, visually testable waypoints. Values are local-X bend rotations,
# chosen as a diagnostic range; the baseline is restored exactly at endpoints.
pose(1, {})
pose(12, {'Leg_Front.L_01':-0.42, 'Leg_Front.L_02':0.82, 'Leg_Front.L_03':-0.12})
pose(20, {'Leg_Front.L_01':0.52, 'Leg_Front.L_02':-0.74, 'Leg_Front.L_03':0.08})
pose(30, {})
# Blender 4+ stores F-curves in Action slots/layers; default interpolation is
# sufficient for this still-image proof, and the explicit poses remain keyed.
scene.frame_start=1; scene.frame_end=30; scene.render.fps=24

# Fixed side camera looking along -X; screen horizontal is creature Y.
def look(obj, target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
cam_data=bpy.data.cameras.new('CMAI_FrontL_Proof_Camera_Data')
cam=bpy.data.objects.new('CMAI_FrontL_Proof_Camera', cam_data); bpy.context.collection.objects.link(cam)
cam.location=(-2.8,-0.80,-0.12); cam_data.type='ORTHO'; cam_data.ortho_scale=0.48; look(cam,(0.12,-0.80,-0.12)); scene.camera=cam

# Diagnostic local mesh: retain only faces close to the Front.L chain, avoiding body-wide
# vertex-group selection. This is a temporary copy; original mesh is not modified.
scene.frame_set(1); bpy.context.view_layer.update()
pb=[arm.pose.bones[n] for n in names]
segs=[(arm.matrix_world@p.head, arm.matrix_world@p.tail) for p in pb]
def dist_seg(p,a,b):
    ab=b-a; t=max(0,min(1,(p-a).dot(ab)/(ab.length_squared if ab.length_squared else 1))); return (p-(a+t*ab)).length
sel=[]
for v in mesh.data.vertices:
    pw=mesh.matrix_world @ v.co
    weighted=any((mesh.vertex_groups.get(n) and any(g.group==mesh.vertex_groups[n].index and g.weight>0.2 for g in v.groups)) for n in names)
    sel.append(weighted and min(dist_seg(pw,a,b) for a,b in segs)<0.18)
faces=[]; used=set()
for poly in mesh.data.polygons:
    if all(sel[i] for i in poly.vertices): faces.append(tuple(poly.vertices)); used.update(poly.vertices)
if len(faces)<10:
    # fallback still keeps the diagnostic local and avoids an empty render
    for poly in mesh.data.polygons:
        if any(sel[i] for i in poly.vertices): faces.append(tuple(poly.vertices)); used.update(poly.vertices)
idx={old:i for i,old in enumerate(sorted(used))}
verts=[mesh.data.vertices[i].co[:] for i in sorted(used)]
faces2=[tuple(idx[i] for i in f) for f in faces]
md=bpy.data.meshes.new('CMAI_FrontL_Diagnostic_Mesh'); md.from_pydata(verts,[],faces2); md.update()
reg=bpy.data.objects.new('CMAI_FrontL_Diagnostic_Region',md); bpy.context.collection.objects.link(reg)
reg.matrix_world=mesh.matrix_world.copy()
for vg in mesh.vertex_groups:
    nvg=reg.vertex_groups.new(name=vg.name)
for old,newi in idx.items():
    for g in mesh.data.vertices[old].groups:
        try: reg.vertex_groups[g.group].add([newi],g.weight,'REPLACE')
        except: pass
mod=reg.modifiers.new('CMAI diagnostic armature','ARMATURE'); mod.object=arm
mat=bpy.data.materials.new('CMAI FrontL diagnostic bright'); mat.diffuse_color=(1.0,0.06,0.02,1.0); reg.data.materials.append(mat)
mesh.hide_render=True

def measure(f):
    scene.frame_set(f); bpy.context.view_layer.update(); p=arm.pose.bones[names[-1]]
    foot=arm.matrix_world@p.tail
    knee=arm.matrix_world@arm.pose.bones[names[1]].head
    return {'frame':f,'foot_world':list(foot),'knee_world':list(knee)}
measurements=[measure(f) for f in (1,12,20,30)]

for f,label in [(1,'standing'),(12,'high_lift'),(20,'forward_swing')]:
    scene.frame_set(f); bpy.context.view_layer.update(); scene.render.filepath=os.path.join(out_dir,label+'.png'); bpy.ops.render.render(write_still=True)
scene.frame_set(1); bpy.context.view_layer.update()
json.dump({'source':src,'action':act.name,'diagnostic_region_vertices':len(verts),'diagnostic_region_faces':len(faces2),'measurements':measurements,'waypoints':{'high_lift':12,'forward_swing':20}},open(os.path.join(out_dir,'report.json'),'w'),indent=2)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath('data/generated/frontL_three_pose_explicit_reversed.blend'))
