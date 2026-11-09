import bpy, json, sys
from pathlib import Path
from mathutils import Matrix, Vector

blend, report_path, out_blend, out_report = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']
mesh=bpy.data.objects['CrimsonSpineBehemoth_Mesh']
data=json.loads(Path(report_path).read_text())
names=data['bones']; root=Vector(data['chain_root_armature'])
bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
baseline_pose={p.name:p.matrix.copy() for p in arm.pose.bones}
rest_mats={n:bpy.data.armatures[arm.data.name].bones[n].matrix_local.copy() for n in names}
rest_verts=[arm.matrix_world @ mesh.matrix_world.inverted() @ v.co for v in mesh.data.vertices]

def apply_pose(mats):
    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    # Clear the previous test pose before assigning absolute armature-space
    # matrices; otherwise parent-relative evaluation compounds the prior pose.
    for n,p in baseline_pose.items():
        arm.pose.bones[n].matrix = p.copy()
    bpy.context.view_layer.update()
    pending=[]
    use_chain_orientation = bool(data.get('orientation_constrained'))
    neutral_fk = [Matrix(m) for m in data.get('neutral_joint_matrices', [])]
    for i,n in enumerate(names):
        pb=arm.pose.bones[n]; db=arm.data.bones[n]
        fk=Matrix(mats[i])
        desired_head=root+Vector((fk[0][3],fk[1][3],fk[2][3]))
        if i+1 < len(names):
            next_fk=Matrix(mats[i+1]); desired_tail=root+Vector((next_fk[0][3],next_fk[1][3],next_fk[2][3]))
        else:
            end=Matrix(mats[-1])
            desired_tail=root+Vector((end[0][3],end[1][3],end[2][3]))
        # Use the bone matrix's actual local +Y axis.  Blender's bone data
        # head/tail vectors are not a safe substitute for the rolled pose
        # matrix when deriving a parent-relative rotation.
        rest_dir=(rest_mats[n].to_3x3() @ Vector((0.0,1.0,0.0))).normalized()
        desired_dir=(desired_tail-desired_head).normalized()
        if use_chain_orientation and i + 1 < len(neutral_fk):
            # Preserve IKPy's cumulative orientation change. The previous
            # adapter reconstructed orientation only from endpoint vectors,
            # which discarded proximal joint rotation when a link endpoint
            # remained fixed.
            chain_rest_rot = neutral_fk[i + 1].to_3x3()
            chain_pose_rot = Matrix(mats[i + 1]).to_3x3()
            delta_rot = chain_rest_rot.inverted() @ chain_pose_rot
            target_rot = baseline_pose[n].to_3x3() @ delta_rot
            target_matrix = Matrix.Translation(desired_head) @ target_rot.to_4x4()
            pending.append((pb, target_matrix))
            continue
        if i == len(names) - 1:
            # The IKPy terminal translation is the endpoint of the actual
            # Blender terminal bone. Preserve the bone's rest roll and apply
            # only the rest-relative direction change, exactly as for the
            # validated upstream links. A world-space orientation here loses
            # Blender's terminal rest-axis relationship.
            align=rest_dir.rotation_difference(desired_dir).to_matrix().to_4x4()
            rot=rest_mats[n].to_3x3().to_4x4()
        else:
            align=rest_dir.rotation_difference(desired_dir).to_matrix().to_4x4()
            rot=rest_mats[n].to_3x3().to_4x4()
        pending.append((pb, Matrix.Translation(desired_head) @ align @ rot))
    # Assign parents first and children last.  PoseBone.matrix is an absolute
    # armature-space matrix, but Blender updates descendants when a parent is
    # assigned; the child must therefore receive its final matrix afterward.
    for pb, target_matrix in pending:
        pb.matrix=target_matrix
    # Feedback correction for the terminal bone only.  Once the parent chain
    # has been evaluated, use Blender's actual current L03 direction and the
    # desired endpoint direction to derive the shortest corrective rotation.
    # This deliberately avoids a hard-coded angle and leaves L01/L02 intact.
    bpy.context.view_layer.update()
    if not use_chain_orientation:
        terminal=arm.pose.bones[names[-1]]
        actual_dir=(terminal.tail-terminal.head).normalized()
        desired_dir=(pending[-1][1].to_3x3() @ Vector((0.0,1.0,0.0))).normalized()
        correction=actual_dir.rotation_difference(desired_dir)
        terminal.matrix=Matrix.Translation(terminal.head) @ correction.to_matrix().to_4x4() @ terminal.matrix
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()

def measure(mats):
    pb=arm.pose.bones[names[-1]]
    foot=arm.matrix_world @ pb.tail
    joints=[]
    for i,n in enumerate(names):
        pb=arm.pose.bones[n]
        fk=Matrix(mats[i]); exp_head=root+Vector((fk[0][3],fk[1][3],fk[2][3]))
        if i+1 < len(mats):
            nf=Matrix(mats[i+1]); exp_tail=root+Vector((nf[0][3],nf[1][3],nf[2][3]))
        else: exp_tail=exp_head
        ah=arm.matrix_world @ pb.head; at=arm.matrix_world @ pb.tail
        joints.append({'bone':n,'expected_head':list(exp_head),'actual_head':list(ah),'head_error':float((ah-exp_head).length),'expected_tail':list(exp_tail),'actual_tail':list(at),'tail_error':float((at-exp_tail).length),'pose_matrix':[[float(pb.matrix[r][c]) for c in range(4)] for r in range(4)]})
    deps=bpy.context.evaluated_depsgraph_get(); em=mesh.evaluated_get(deps); me=em.to_mesh()
    verts=[arm.matrix_world @ mesh.matrix_world.inverted() @ v.co for v in me.vertices]
    disp=max((a-b).length for a,b in zip(verts,rest_verts))
    em.to_mesh_clear()
    return {'foot_world':list(foot),'max_mesh_displacement':float(disp),'joints':joints}

if 'step_joint_matrices' in data:
    if 'step_pose_frames' in data:
        base=data['step_joint_matrices']
        if len(base) == 5 and data.get('step_mode') == 'orientation_step':
            poses=[('rest',base[0]),('support',base[1]),('forward_up',base[2]),('plant',base[3]),('rest_return',base[4])]
        else:
            poses=[('rest',base[0]),('support',base[0]),('lift',base[1]),('forward_up',base[2]),('plant',base[3]),('plant_support',base[3]),('rest_return',base[4])]
        pose_frames=data.get('step_pose_frames',[1,20,21,45,75,95,120])
    else:
        poses=[('rest',data['step_joint_matrices'][0]),('lift',data['step_joint_matrices'][1]),('forward_up',data['step_joint_matrices'][2]),('plant',data['step_joint_matrices'][3]),('rest_return',data['step_joint_matrices'][4])]
        pose_frames=[1,25,55,85,120]
else:
    poses=[('rest',data['neutral_joint_matrices']),('lift',data['moved_joint_matrices']),('rest_return',data['neutral_joint_matrices'])]
    pose_frames=[1,41,81]
results=[]
anim_data=arm.animation_data
preexisting_action=anim_data.action if anim_data else None
preexisting_nla=[(s,s.mute) for t in (anim_data.nla_tracks if anim_data else []) for s in t.strips]
for s,_ in preexisting_nla: s.mute=True
if anim_data: anim_data.action=None
test_action=None
for pose_index,(label,mats) in enumerate(poses):
    apply_pose(mats)
    frame=pose_frames[pose_index]
    bpy.context.scene.frame_set(frame)
    measured=measure(mats)
    expected=(root+Vector((mats[-1][0][3],mats[-1][1][3],mats[-1][2][3])))
    measured['target_error_armature']=float((Vector(measured['foot_world'])-expected).length)
    results.append({'pose':label,'expected_foot_armature':list(expected),**measured})
    # Keyframe only after measuring the pose. Reattach the test Action for
    # insertion, but detach it before selecting the next test frame so its
    # interpolation cannot overwrite the pose being diagnosed.
    if anim_data:
        if test_action is not None: anim_data.action=test_action
        for n in baseline_pose:
            p=arm.pose.bones[n]
            p.keyframe_insert(data_path='rotation_mode',frame=frame)
            if p.rotation_mode=='QUATERNION': p.keyframe_insert(data_path='rotation_quaternion',frame=frame)
            else: p.keyframe_insert(data_path='rotation_euler',frame=frame)
        test_action=anim_data.action
        anim_data.action=None
if anim_data: anim_data.action=test_action
bpy.context.view_layer.update()
# Re-evaluate the saved keyframes after the measurements, restoring the test
# Action and checking that Blender can reproduce the recorded pose.
replay=[]
if anim_data and test_action:
    anim_data.action=test_action
    for pose_index,(label,mats) in enumerate(poses):
        frame=pose_frames[pose_index]
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        replayed=measure(mats)
        expected=(root+Vector((mats[-1][0][3],mats[-1][1][3],mats[-1][2][3])))
        replay.append({'pose':label,'target_error_armature':float((Vector(replayed['foot_world'])-expected).length),'foot_world':replayed['foot_world']})
    anim_data.action=test_action
for s,m in preexisting_nla: s.mute=m
bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=120; bpy.context.scene.render.fps=24
bpy.context.scene.camera=bpy.data.objects.get('CMAI_Static_ThreeQuarter_Camera') or bpy.context.scene.camera
bpy.context.scene.render.engine='BLENDER_WORKBENCH'
bpy.context.scene.render.image_settings.file_format='PNG'
frames_dir=(Path(out_blend).resolve().parent/'ikpy_frontl_diagnostic_frames').resolve()
frames_dir.mkdir(parents=True,exist_ok=True)
bpy.context.scene.render.filepath=str(frames_dir/'frame_')
bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_blend).resolve()))
bpy.ops.render.render(animation=True)
Path(out_report).write_text(json.dumps({'status':'BLENDER_IKPY_APPLICATION_TEST','results':results,'replay':replay,'note':'Pose matrices are converted from chain-root FK directions; mesh displacement is measured on evaluated geometry.'},indent=2),encoding='utf-8')
print(json.dumps({'blend':out_blend,'report':out_report,'results':results}))
