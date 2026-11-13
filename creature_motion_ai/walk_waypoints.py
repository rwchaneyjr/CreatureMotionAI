"""Shared waypoint generation extracted from the executed standing-fit tool.

No creature names, fixed joint axes, or repository data paths are required.
"""
import json, math, hashlib
import bpy
import numpy as np
from mathutils import Vector, Matrix

def mesh_world(mesh):
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    a = np.empty(len(me.vertices)*3, dtype=np.float64)
    me.vertices.foreach_get("co", a); a=a.reshape(-1,3)
    mat=np.array(ev.matrix_world)
    out=a@mat[:3,:3].T+mat[:3,3]
    ev.to_mesh_clear()
    return out


def fingerprint(arm, mesh):
    h=hashlib.sha256()
    a=np.empty(len(mesh.data.vertices)*3,dtype=np.float32)
    mesh.data.vertices.foreach_get("co",a); h.update(a.tobytes())
    for v in mesh.data.vertices:
        h.update(str([(g.group,round(g.weight,8)) for g in v.groups]).encode())
    for b in arm.data.bones:
        h.update(str((b.name,b.parent.name if b.parent else None,list(b.head_local),list(b.tail_local),[list(r) for r in b.matrix_local])).encode())
    return h.hexdigest()


def action_curves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def create_walk(scene,arm,mesh,out,standing,setups,selected,baseline,apply_chain,ground,edges,rest_edge_lengths,render_walk=False,overrides=None,*,root_name=None,plan_only=False,prepared=None,render_stills=False,save_blend=False):
    """Sparse FK waypoints on the original rig, then evaluate every interpolated frame.

    The corrected analytical solver is used only for waypoint placement. Optional
    root travel cancels stance travel; evaluated world-space slip is measured.
    """
    legs=list(setups)
    if not root_name or root_name not in arm.pose.bones: raise ValueError("Specify the profile root bone")
    leg_bones={n for x in setups.values() for n in x["names"]}
    body_lift,standing_targets,_=selected
    cycle=40; duty=.65; forward=Vector((0,-1,0)); inv=arm.matrix_world.inverted()
    phases={leg:i/max(1,len(legs)) for i,leg in enumerate(legs)}
    config={"cycle_frames":cycle,"fps":24,"duty_factor":duty,"forward_world":list(forward),"body_bob":.002,"shared_stride":.075,
        "phase_offsets":phases,"phase_evidence":"Rear-to-front recovery suggested by SIDEbalaskWALK frames; precise per-leg timing and hidden-side identity UNVERIFIED.",
        "reference_matching":"APPROXIMATE_STYLE_ONLY","foot_contact_mode":"TREADMILL: stance feet move backward relative to stationary body; raw and belt-compensated slip are reported separately.",
        "keyframe_phases":[0,.3,.60,.65,.72,.825,.93,1],"minimum_knee_flexion_degrees":8,"maximum_knee_flexion_degrees":135,
        "ground_penetration_limit":.003,"contact_height_tolerance":.003,"legs":{}}
    if overrides: config.update(overrides)
    cycle=int(config["cycle_frames"]); duty=config["duty_factor"]; phases=config["phase_offsets"]
    forward=Vector(config["forward_world"]).normalized()
    if abs(forward.z)>1e-5: raise ValueError("Walking forward must be horizontal in world space")
    if 120%cycle: raise ValueError("Cycle frames must divide 120 for the five-second loop")
    stand_pose={p.name:p.matrix_basis.copy() for p in arm.pose.bones}
    stand_mesh=mesh_world(mesh)
    stand_mat={p.name:p.matrix.copy() for p in arm.pose.bones}
    def body_at(frame):
        return body_lift+config["body_bob"]*(1-math.cos(4*math.pi*(frame-1)/cycle))*.5
    def phase_at(frame,leg): return ((frame-1)/cycle+phases[leg])%1
    def desired(frame,leg):
        p=phase_at(frame,leg); cfg=config["legs"][leg]; target=standing_targets[leg].copy()
        if p<=duty:
            x=.5-p/duty; z=0
        else:
            t=(p-duty)/(1-duty); x=-.5+t*t*(3-2*t); z=math.sin(math.pi*t)**1.5
        target+=forward*(x*cfg["stride"]); target.z+=cfg["lift"]*z
        return target,z*cfg["lift"]
    def reset_pose(frame):
        whole=math.floor(frame); scene.frame_set(whole,subframe=frame-whole)
        for p in arm.pose.bones: p.matrix_basis=stand_pose[p.name]
        mat=arm.matrix_world@baseline[root_name]; mat.translation+=Vector((0,0,body_at(frame)))
        arm.pose.bones[root_name].matrix=inv@mat
        bpy.context.view_layer.update()
    source_action=arm.animation_data.action
    source_slot=arm.animation_data.action_slot
    action=bpy.data.actions.new("CMAI_EightLeg_GroundFitted_"+out.name)
    action.use_fake_user=True; arm.animation_data.action=action
    # Freeze non-leg channels in this Action; all original rest geometry remains untouched.
    for p in arm.pose.bones:
        if not p.name in leg_bones:
            for ch in ["location","rotation_quaternion","scale"]: p.keyframe_insert(ch,frame=1)
    for frame in range(1,cycle+2,5):
        reset_pose(frame); arm.pose.bones[root_name].keyframe_insert("location",frame=frame,group="A - Body")
    targets_report={}; failed=[]; planned={}
    for leg,x in setups.items():
        length=sum(x["lengths"][:2])
        lift_fraction=config.get("lift_fraction",.20)
        cfg={"stride":config["shared_stride"],"lift":length*lift_fraction,"length":sum(x["lengths"]),"amplitude_scale":1.0}
        config["legs"][leg]=cfg
        times={1.0,float(cycle+1)}
        for phase in config["keyframe_phases"]:
            times.add(round(1+((phase-phases[leg])%1)*cycle,5))
        if prepared is not None:
            cfg.update(prepared["configuration"]["legs"][leg])
            poses=[(v["frame"],{n:Matrix(m) for n,m in v["basis"].items()},v["result"]) for v in prepared["poses"][leg]]
            valid=True
        else:
            poses=[]
            for scale in [1.0,.85,.7,.55]:
                cfg.update(stride=config["shared_stride"]*scale,lift=length*lift_fraction*scale,amplitude_scale=scale)
                poses=[]; valid=True
                for frame in sorted(times):
                    reset_pose(frame); target,clearance=desired(frame,leg)
                    for iteration in range(5):
                        result=apply_chain(leg,target,body_at(frame))
                        if result["status"]!="PASS" or result["knee_flexion_deg"]>135:
                            valid=False; break
                        verts=mesh_world(mesh); sole=float(verts[x["indices"],2].min())
                        error=sole-ground-clearance
                        if abs(error)<.0003: break
                        target.z-=error*.9
                    if not valid: break
                    poses.append((frame,{n:arm.pose.bones[n].matrix_basis.copy() for n in x["names"]},dict(result,sole_clearance=sole-ground,target=list(target))))
                if valid: break
        if not valid:
            failed.append({"leg":leg,"frame":frame,"result":result}); continue
        planned[leg]=[{"frame":f,"basis":{n:[list(row) for row in m] for n,m in pose.items()},"result":r} for f,pose,r in poses]
        previous={}
        targets_report[leg]=[]
        for frame,pose,result in poses:
            reset_pose(frame)
            for n,matrix in pose.items():
                p=arm.pose.bones[n]; p.matrix_basis=matrix
                p.rotation_mode="QUATERNION"
                if n in previous and p.rotation_quaternion.dot(previous[n])<0: p.rotation_quaternion.negate()
                previous[n]=p.rotation_quaternion.copy()
                p.keyframe_insert("rotation_quaternion",frame=frame,group="B - "+leg)
                # Location/scale are fixed. Connected bones must not be stretched.
                if frame==1:
                    p.keyframe_insert("location",frame=1,group="B - "+leg); p.keyframe_insert("scale",frame=1,group="B - "+leg)
            targets_report[leg].append(dict(result,frame=frame))
        print("KEYED "+leg+" "+json.dumps(cfg),flush=True)
    for curve in action_curves(action):
        for k in curve.keyframe_points:
            k.interpolation="BEZIER"; k.handle_left_type="AUTO_CLAMPED"; k.handle_right_type="AUTO_CLAMPED"
        if len(curve.keyframe_points)>1: curve.modifiers.new("CYCLES")
    (out/"walk_configuration.json").write_text(json.dumps(config,indent=2))
    if failed:
        (out/"walk_failed_waypoints.json").write_text(json.dumps(failed,indent=2))
        raise RuntimeError("Walking waypoints rejected; see walk_failed_waypoints.json")
    if plan_only:
        payload={"configuration":config,"poses":planned,"status":"PASS","backend":"existing_rest_relative_two_link"}
        (out/"waypoints.json").write_text(json.dumps(payload,indent=2))
        arm.animation_data.action=source_action
        if source_slot: arm.animation_data.action_slot=source_slot
        scene.frame_set(1); bpy.context.view_layer.update()
        action.use_fake_user=False
        bpy.data.actions.remove(action)
        return payload
    # Correct only actual intermediate contact errors, never stretch the chains.
    corrections=[]
    for round_number in range(2):
        fixes=[]
        for frame in range(1,cycle+1):
            scene.frame_set(frame); bpy.context.view_layer.update(); verts=mesh_world(mesh)
            for leg,x in setups.items():
                sole=float(verts[x["indices"],2].min()-ground)
                contact=phase_at(frame,leg)<=duty
                target=arm.matrix_world@arm.pose.bones[x["names"][2]].head
                expected,_=desired(frame,leg)
                lateral_error=Vector((target.x-expected.x,target.y-expected.y,0)).length
                if sole<-.0005 or (contact and (sole>.001 or lateral_error>config.get("contact_xy_tolerance",1e3))):
                    target.z-=sole-.00015
                    if contact: target.x=expected.x; target.y=expected.y
                    fixes.append((frame,leg,target,sole))
        if not fixes: break
        for frame,leg,target,old in fixes:
            scene.frame_set(frame); bpy.context.view_layer.update()
            r=apply_chain(leg,target,body_at(frame))
            if r["status"]!="PASS": continue
            for n in setups[leg]["names"]:
                p=arm.pose.bones[n]
                # choose the quaternion hemisphere of the preexisting curve sample
                if p.rotation_quaternion.w<0: p.rotation_quaternion.negate()
                p.keyframe_insert("rotation_quaternion",frame=frame,group="B - "+leg)
            corrections.append({"round":round_number+1,"frame":frame,"leg":leg,"previous_clearance":old})
        for c in action_curves(action):
            for k in c.keyframe_points:
                k.interpolation="BEZIER"; k.handle_left_type="AUTO_CLAMPED"; k.handle_right_type="AUTO_CLAMPED"
    # Enforce an identical evaluated loop endpoint after corrections at frame 1.
    scene.frame_set(1); bpy.context.view_layer.update()
    for p in arm.pose.bones:
        if p.name in leg_bones or p.name==root_name:
            for ch in ["location","rotation_quaternion","scale"]: p.keyframe_insert(ch,frame=cycle+1)
    from . import collision_proxies as proxy
    def proxy_pairs():
        segments=proxy.segments_for_chains(arm,{leg:x["names"] for leg,x in setups.items()},config.get('body_bones',[])); hits=[]
        for i,a in enumerate(segments):
            for b in segments[i+1:]:
                if a["region"]==b["region"]: continue
                overlap=a["r"]+b["r"]-proxy._segdist(a["a"],a["b"],b["a"],b["b"])
                if overlap>0: hits.append({"a":a["bone"],"b":b["bone"],"overlap":overlap})
        return hits
    rows=[]; positions={leg:[] for leg in legs}; firstmesh=None; firstbones=None; edge_stats=[]
    for frame in range(1,cycle+2):
        scene.frame_set(frame); bpy.context.view_layer.update(); verts=mesh_world(mesh)
        if firstmesh is None:
            firstmesh=verts.copy(); firstbones={p.name:np.array(p.matrix) for p in arm.pose.bones}
        frame_legs={}
        for leg,x in setups.items():
            pts=[arm.matrix_world@arm.pose.bones[n].head for n in x["names"]]+[arm.matrix_world@arm.pose.bones[x["names"][-1]].tail]
            direction=(pts[2]-pts[0]).normalized(); old=(x["points"][2]-x["points"][0]).normalized()
            normal=old.rotation_difference(direction)@x["normal"]
            bend=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized().dot(normal)
            flex=180-math.degrees((pts[0]-pts[1]).angle(pts[2]-pts[1]))
            angle=math.degrees((arm.matrix_world@arm.pose.bones[x["names"][2]].matrix).to_quaternion().rotation_difference(x["matrices"][2].to_quaternion()).angle)
            clearance=float(verts[x["indices"],2].min()-ground)
            delta=float(np.linalg.norm(verts[x["indices"]]-firstmesh[x["indices"]],axis=1).max())
            frame_legs[leg]={"clearance":clearance,"contact":phase_at(frame,leg)<=duty,"foot":list(pts[3]),"knee":list(pts[1]),
                "knee_flexion":flex,"bend_dot":bend,"foot_orientation_degrees":angle,"weighted_mesh_displacement":delta,
                "length_error":max(abs((pts[i+1]-pts[i]).length-x["lengths"][i]) for i in range(3))}
            positions[leg].append(frame_legs[leg])
        if frame in [1,11,21,31,41]:
            lens=np.linalg.norm(verts[edges[:,0]]-verts[edges[:,1]],axis=1); ratio=lens/np.maximum(rest_edge_lengths,1e-8); mask=rest_edge_lengths>.0005
            edge_stats.append({"frame":frame,"significant_edge_ratio_p99":float(np.quantile(ratio[mask],.99)),"significant_edges_over_3x":int(((ratio>3)&mask).sum()),"max_extension":float((lens-rest_edge_lengths).max())})
        rows.append({"frame":frame,"legs":frame_legs,"mesh_min_z":float(verts[:,2].min()),"proxy_collisions":proxy_pairs()})
        if frame%10==1: print("VALIDATED FRAME "+str(frame),flush=True)
    loop_mesh=float(np.linalg.norm(verts-firstmesh,axis=1).max())
    loop_bone=max(float(np.abs(np.array(p.matrix)-firstbones[p.name]).max()) for p in arm.pose.bones)
    summary={}
    for leg,pp in positions.items():
        feet=np.array([r["foot"] for r in pp]); contacts=[r for r in pp[:-1] if r["contact"]]
        raw=[]; compensated=[]
        belt=forward*(-config["legs"][leg]["stride"]/(duty*cycle))
        for a,b in zip(pp[:-2],pp[1:-1]):
            if a["contact"] and b["contact"]:
                delta=Vector(b["foot"])-Vector(a["foot"]); raw.append(Vector((delta.x,delta.y,0)).length)
                compensated.append(Vector((delta.x-belt.x,delta.y-belt.y,0)).length)
        summary[leg]={"foot_travel_xyz":np.ptp(feet,axis=0).tolist(),"max_mesh_displacement":max(r["weighted_mesh_displacement"] for r in pp),
            "max_clearance":max(r["clearance"] for r in pp),"max_penetration":max(0,-min(r["clearance"] for r in pp)),
            "max_contact_float":max(0,max(r["clearance"] for r in contacts)),"knee_flexion_range":[min(r["knee_flexion"] for r in pp),max(r["knee_flexion"] for r in pp)],
            "min_bend_dot":min(r["bend_dot"] for r in pp),"max_foot_orientation_change":max(r["foot_orientation_degrees"] for r in pp),
            "max_stance_motion_per_frame":max(raw,default=0),"max_belt_compensated_slip_per_frame":max(compensated,default=0),
            "max_length_error":max(r["length_error"] for r in pp)}
        r=summary[leg]; r["numerical_status"]="PASS" if r["max_penetration"]<.003 and r["max_contact_float"]<.004 and r["min_bend_dot"]>.95 and r["max_length_error"]<1e-5 and r["max_mesh_displacement"]>.02 else "FAIL"
    result={"configuration":config,"action":action.name,"legs":summary,"loop_mesh_error":loop_mesh,"loop_bone_error":loop_bone,
        "corrections":corrections,"waypoints":targets_report,"frames":rows,"mesh_edge_checks":edge_stats,
        "exact_surface_collisions":"UNVERIFIED","visual_status":"UNVERIFIED","reference_match":"UNVERIFIED_APPROXIMATE_STYLE_ONLY"}
    if config.get("world_planted_support"):
        # Translate root, camera and lights together. Rotation waypoints stay
        # unchanged; stance feet now hold approximately fixed WORLD positions.
        speed=config["shared_stride"]/(duty*cycle)
        local_direction=arm.pose.bones[root_name].bone.matrix_local.to_3x3().inverted()@inv.to_3x3()@forward
        root_path=arm.pose.bones[root_name].path_from_id('location')
        translated_channels=0
        for c in action_curves(action):
            if c.data_path==root_path and abs(local_direction[c.array_index])>1e-6:
                translated_channels+=1
                for k in c.keyframe_points:
                    delta=local_direction[c.array_index]*speed*(k.co.x-1)
                    k.co.y+=delta; k.handle_left.y+=delta; k.handle_right.y+=delta; k.interpolation='LINEAR'
                for mod in c.modifiers:
                    if mod.type=='CYCLES': mod.mode_before='REPEAT_OFFSET'; mod.mode_after='REPEAT_OFFSET'
        if translated_channels==0: raise RuntimeError('Root translation channel was not found; camera tracking was not applied.')
        for obj in [scene.camera]+[o for o in scene.objects if o.type=='LIGHT' and not o.hide_render]:
            start=obj.location.copy(); obj.keyframe_insert('location',frame=1)
            obj.location=start+forward*speed*cycle; obj.keyframe_insert('location',frame=cycle+1)
            for c in action_curves(obj.animation_data.action):
                for k in c.keyframe_points: k.interpolation='LINEAR'
                mod=c.modifiers.new('CYCLES'); mod.mode_before='REPEAT_OFFSET'; mod.mode_after='REPEAT_OFFSET'
        world_rows=[]
        for f in range(1,121):
            scene.frame_set(f); bpy.context.view_layer.update()
            world_rows.append({'frame':f,'feet':{leg:list(arm.matrix_world@arm.pose.bones[x['names'][-1]].tail) for leg,x in setups.items()}})
        result['world_motion']={'root_speed_BU_per_frame':speed,'camera_tracks_root':True,'loop_convention':'Pose and camera-relative image loop; root advances continuously in world space','frames':world_rows,'stance_slip':{}}
        for leg in legs:
            slips=[]
            for a,b in zip(world_rows,world_rows[1:]):
                if phase_at(a['frame'],leg)<=duty and phase_at(b['frame'],leg)<=duty:
                    d=Vector(b['feet'][leg])-Vector(a['feet'][leg]); slips.append(Vector((d.x,d.y,0)).length)
            result['world_motion']['stance_slip'][leg]={'maximum_per_frame':max(slips,default=0),'mean_per_frame':float(np.mean(slips))}
    (out/"walk_validation.json").write_text(json.dumps(result,indent=2))
    scene.frame_start=1; scene.frame_end=120; scene.frame_set(1); scene.render.fps=24
    if save_blend: bpy.ops.wm.save_as_mainfile(filepath=str(out/"eight_leg_walk.blend"),copy=True)
    for frame in ([1,11,21,31] if render_stills else []):
        scene.frame_set(frame); scene.render.filepath=str(out/f"walk_pose_{frame:03}.png"); bpy.ops.render.render(write_still=True)
    if render_walk and all(x["numerical_status"]=="PASS" for x in summary.values()) and loop_mesh<1e-5:
        (out/"frames").mkdir(exist_ok=False)
        scene.render.filepath=str(out/"frames"/"walk_"); bpy.ops.render.render(animation=True)
    print("WALK SUMMARY "+json.dumps(summary),flush=True)
    return result
