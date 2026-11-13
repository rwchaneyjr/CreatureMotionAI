"""Fit the original eight chains to a shared mesh-contact plane; unique outputs.

Runs inside Blender. No source rig/data edits. Uses the existing rest-relative
FK helper; solver correctness is checked against Blender's evaluated bones.
"""
import argparse, importlib.util, json, math, sys, time, hashlib
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from creature_motion_ai.walk_waypoints import mesh_world, fingerprint, action_curves, create_walk as shared_create_walk
spec = importlib.util.spec_from_file_location("cmai_ik_step", ROOT/"creature_motion_ai/ik_step.py")
fk = importlib.util.module_from_spec(spec); spec.loader.exec_module(fk)
LEGS = [p+"."+s for p in ["Front","MidFront","MidRear","Rear"] for s in ["L","R"]]



def helper_regression():
    hip=Vector((0,0,0)); ankle=Vector((1,1,0)); knee=Vector((1,0,0))
    result=fk.solve_rest_relative_two_link(hip,ankle,1,1,Vector((0,0,1)))
    assert (result["knee"]-knee).length<1e-6, result
    assert abs(result["knee"].z)<1e-7
    assert fk.solve_rest_relative_two_link(hip,Vector((2,0,0)),1,1,Vector((0,0,1)))["status"]=="REJECTED"
    return "PASS"


def inspect_saved_walk(out):
    """Read-only evaluation of a saved Action, including camera-space landmarks."""
    from bpy_extras.object_utils import world_to_camera_view
    s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; mesh=bpy.data.objects['CrimsonSpineBehemoth_Mesh']
    validation=json.loads((out/'walk_validation.json').read_text())
    ground=json.loads((out/'validation.json').read_text())['ground']
    cfg=validation['configuration']; cycle=cfg['cycle_frames']
    anatomy=json.loads((ROOT/'data/generated/standing_attempt2_anatomy_01/neutral_anatomy.json').read_text())
    W=s.render.resolution_x; H=s.render.resolution_y
    def project(p):
        v=world_to_camera_view(s,s.camera,p); return [float(v.x*W),float((1-v.y)*H)]
    rows=[]; first=None; edge_ref=None; mesh_check=[]; sole_slip={leg:[] for leg in LEGS}; previous={}
    edges=np.empty(len(mesh.data.edges)*2,dtype=np.int32); mesh.data.edges.foreach_get('vertices',edges); edges=edges.reshape(-1,2)
    # Select fixed neutral sole vertices, rather than chasing a different minimum each frame.
    for f in range(1,122):
        s.frame_set(f); bpy.context.view_layer.update(); verts=mesh_world(mesh)
        if first is None:
            first=verts.copy(); edge_ref=np.linalg.norm(verts[edges[:,0]]-verts[edges[:,1]],axis=1)
        root=arm.matrix_world@arm.pose.bones['Root'].head
        row={'frame':f,'legs':{},'root_world':list(root),'camera_world':list(s.camera.location),'minimum_mesh_z':float(verts[:,2].min())}
        for leg in LEGS:
            names=[f'Leg_{leg}_{i:02}' for i in (1,2,3)]
            pts=[arm.matrix_world@arm.pose.bones[n].head for n in names]+[arm.matrix_world@arm.pose.bones[names[-1]].tail]
            ids=np.array(anatomy['legs'][leg]['indices']); vv=verts[ids]
            contact=((f-1)/cycle+cfg['phase_offsets'][leg])%1<=cfg['duty_factor']
            row['legs'][leg]={'joints_px':[project(p) for p in pts],'joints_world':[list(p) for p in pts],'sole_min_z':float(vv[:,2].min()),'contact':contact,
                'mesh_displacement_from_first':float(np.linalg.norm(vv-first[ids],axis=1).max())}
            if leg in previous and contact and previous[leg][0]:
                d=np.linalg.norm(vv[:,:2]-previous[leg][1],axis=1)
                sole_slip[leg].append({'frame':f,'maximum_vertex_slip':float(d.max()),'median_vertex_slip':float(np.median(d))})
            previous[leg]=(contact,vv[:,:2].copy())
        p=Vector(row['legs']['Front.R']['joints_world'][0]); p.z=ground
        row['ground_under_front_hip_px']=project(p)
        if f in [1,11,21,31,41,61,81,101,120,121]:
            lengths=np.linalg.norm(verts[edges[:,0]]-verts[edges[:,1]],axis=1); mask=edge_ref>.0005; ratios=lengths[mask]/edge_ref[mask]
            mesh_check.append({'frame':f,'p99_edge_ratio_to_walk_frame1':float(np.quantile(ratios,.99)),'edges_over_3x':int((ratios>3).sum()),'max_edge_extension':float((lengths-edge_ref).max())})
        rows.append(row)
        if f%30==1: print('SAVED ACTION CHECK '+str(f),flush=True)
    result={'source_blend':bpy.data.filepath,'action':arm.animation_data.action.name,'action_slot':arm.animation_data.action_slot.identifier if arm.animation_data.action_slot else None,
        'image_size':[W,H],'camera':{'type':s.camera.data.type,'ortho_scale':s.camera.data.ortho_scale,'matrix_world_frame121':[list(r) for r in s.camera.matrix_world]},
        'ground':ground,'frames':rows,'mesh_edge_checks':mesh_check,'sole_vertex_slip':{leg:{'maximum_per_frame':max((v['maximum_vertex_slip'] for v in vv),default=0),'median_per_frame':float(np.median([v['median_vertex_slip'] for v in vv]))} for leg,vv in sole_slip.items()},
        'full_surface_collision':'UNVERIFIED','note':'World translation is included in mesh displacement. Deformation ratios exclude rigid translation.'}
    target=out/'saved_action_validation.json'
    if target.exists(): raise FileExistsError(target)
    target.write_text(json.dumps(result,indent=2))
    s.frame_set(1)

def create_walk(*args, **kwargs):
    kwargs.update(root_name="Root", render_stills=True, save_blend=True)
    overrides=dict(kwargs.get('overrides') or {})
    overrides.setdefault('body_bones',['Body_01','Body_02','Body_03'])
    kwargs['overrides']=overrides
    return shared_create_walk(*args, **kwargs)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--lift",type=float,default=.06)
    parser.add_argument("--inward",type=float,default=.52)
    parser.add_argument("--out")
    parser.add_argument("--walk",action="store_true")
    parser.add_argument("--render-walk",action="store_true")
    parser.add_argument("--engine",choices=["workbench","eevee"],default="eevee")
    parser.add_argument("--rear-clearance",type=float,default=.05,help="Posterior foot offset for the colliding Rear.R chain; original anatomy is retained")
    parser.add_argument("--export-anatomy",action="store_true",help="Export evaluated neutral anatomy only, without fitting or rendering")
    parser.add_argument("--anatomy-json",type=Path,help="Verified neutral geometry, used to restore bend directions in an already constrained working pose")
    parser.add_argument("--ground",type=float)
    parser.add_argument("--walk-config",type=Path)
    parser.add_argument("--inspect-saved-walk",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if args.inspect_saved_walk:
        inspect_saved_walk(Path(args.out)); return
    walk_settings=json.loads(args.walk_config.read_text()) if args.walk_config else {}
    out=Path(args.out) if args.out else ROOT/"data/generated"/("standing_fit_"+time.strftime("%Y%m%d_%H%M%S"))
    out.mkdir(parents=True,exist_ok=False)
    s=bpy.context.scene; arm=bpy.data.objects["CrimsonSpineBehemoth_Rig"]; mesh=bpy.data.objects["CrimsonSpineBehemoth_Mesh"]
    s.frame_set(1); bpy.context.view_layer.update()
    report={"source":bpy.data.filepath,"helper_regression":helper_regression(),"requested_body_lift":args.lift,"rear_right_clearance_offset":args.rear_clearance,"attempts":[],"statuses":{}}
    before=fingerprint(arm,mesh)
    baseline={p.name:p.matrix.copy() for p in arm.pose.bones}
    base_verts=mesh_world(mesh)
    report["isolated_constraints"]=[{"bone":p.name,"name":c.name,"type":c.type,"was_muted":c.mute,"influence":c.influence} for p in arm.pose.bones for c in p.constraints]
    report["source_action"]=arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None
    report["baseline_bounds"]=[base_verts.min(0).tolist(),base_verts.max(0).tolist()]
    if arm.animation_data:
        if arm.animation_data.action: arm.animation_data.action.use_fake_user=True
        arm.animation_data.action=None
        for t in arm.animation_data.nla_tracks: t.mute=True
        for d in arm.animation_data.drivers: d.mute=True
    for p in arm.pose.bones:
        for c in p.constraints: c.mute=True
    # Bake the actual evaluated starting pose into local channels after isolating
    # constraints. Its pre-constraint matrix_basis is NOT the visible source pose.
    bpy.context.view_layer.update()
    for p in sorted(arm.pose.bones,key=lambda p:len(p.parent_recursive)):
        p.matrix=baseline[p.name]
        bpy.context.view_layer.update()
    baseline_basis={p.name:p.matrix_basis.copy() for p in arm.pose.bones}
    report["isolated_source_mesh_error"]=float(np.linalg.norm(mesh_world(mesh)-base_verts,axis=1).max())
    if report["isolated_source_mesh_error"]>1e-5: raise RuntimeError("Could not preserve evaluated source pose while isolating constraints")
    anatomy=json.loads(args.anatomy_json.read_text()) if args.anatomy_json else None
    if anatomy and anatomy["geometry_sha256"]!=before: raise RuntimeError("Anatomy reference geometry/weights do not match the working rig")
    setups={}
    for leg in LEGS:
        ns=[f"Leg_{leg}_{i:02}" for i in (1,2,3)]
        ps=[arm.pose.bones[n] for n in ns]
        pts=[arm.matrix_world@ps[0].head,arm.matrix_world@ps[0].tail,arm.matrix_world@ps[1].tail,arm.matrix_world@ps[2].tail]
        source_pts=[p.copy() for p in pts]
        matrices=[arm.matrix_world@p.matrix.copy() for p in ps]
        if anatomy:
            neutral=anatomy["legs"][leg]
            parent_world=arm.matrix_world@baseline[ps[0].parent.name]
            change=parent_world@Matrix(neutral["parent_world"]).inverted()
            pts=[change@Vector(p) for p in neutral["points"]]
            matrices=[change@Matrix(m) for m in neutral["matrices"]]
        upper=(pts[1]-pts[0]).length; lower=(pts[2]-pts[1]).length
        normal=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized()
        gid=mesh.vertex_groups[ns[2]].index
        direction=(pts[3]-pts[2]).normalized()
        inds=[]
        if anatomy:
            inds=neutral["indices"]
        else:
            for v in mesh.data.vertices:
                wt=next((g.weight for g in v.groups if g.group==gid),0)
                along=(Vector(base_verts[v.index])-pts[2]).dot(direction)
                if wt>=.35 and along>0.15*(pts[3]-pts[2]).length: inds.append(v.index)
        if len(inds)<30: raise RuntimeError(f"No usable sole region for {leg}: {len(inds)}")
        setups[leg]={"names":ns,"points":pts,"lengths":[upper,lower,(pts[3]-pts[2]).length],"normal":normal,
                     "matrices":matrices,"indices":np.array(inds),"source_points":source_pts,
                     "source_sole":float(base_verts[inds,2].min()),
                     "sole":neutral["sole"]+change.translation.z if anatomy else float(base_verts[inds,2].min())}
        replay=fk.solve_rest_relative_two_link(pts[0],pts[2],upper,lower,normal,min_knee_angle=0)
        error=(replay["knee"]-pts[1]).length if replay["status"]=="PASS" else float("inf")
        report.setdefault("rest_solver_regression",{})[leg]=error
        if error>1e-5: raise RuntimeError(f"Rest knee replay failed: {leg}: {error}")
    ground=args.ground if args.ground is not None else min(x["sole"] for x in setups.values())
    if args.export_anatomy:
        export={"source":bpy.data.filepath,"geometry_sha256":before,"ground":ground,"legs":{},"regression":report["rest_solver_regression"]}
        for leg,x in setups.items():
            export["legs"][leg]={"points":[list(p) for p in x["points"]],"matrices":[[list(r) for r in m] for m in x["matrices"]],
                "indices":x["indices"].tolist(),"sole":x["sole"],"parent_world":[list(r) for r in arm.matrix_world@arm.pose.bones[x["names"][0]].parent.matrix]}
        (out/"neutral_anatomy.json").write_text(json.dumps(export))
        print("ANATOMY_EXPORTED "+str(out/"neutral_anatomy.json"),flush=True)
        return
    report["ground"]=ground
    report["baseline_feet"]={leg:{"sole_z":x["source_sole"],"vertex_count":len(x["indices"]),"ankle":list(x["source_points"][2]),"bone_tip":list(x["source_points"][3])} for leg,x in setups.items()}
    report["anatomy_reference"]=str(args.anatomy_json) if args.anatomy_json else "source_evaluated_pose"
    inv=arm.matrix_world.inverted()
    def apply_chain(leg,target,lift):
        x=setups[leg]; hip=x["points"][0]+Vector((0,0,lift))
        old_dir=(x["points"][2]-x["points"][0]).normalized()
        direction=(target-hip).normalized()
        normal=old_dir.rotation_difference(direction)@x["normal"]
        sol=fk.solve_rest_relative_two_link(hip,target,*x["lengths"][:2],normal,min_knee_angle=math.radians(8))
        if sol["status"]!="PASS": return {"status":"FAIL","reason":sol["reason"],"distance":(target-hip).length,"reach":sum(x["lengths"][:2])}
        knee=sol["knee"]
        for i,(head,tail) in enumerate([(hip,knee),(knee,target)]):
            p=arm.pose.bones[x["names"][i]]
            mat=fk.world_direction_pose_matrix(x["matrices"][i],x["points"][i],head,tail,x["points"][i+1])
            p.matrix=inv@mat
            bpy.context.view_layer.update()
        fk.restore_terminal_foot_world_orientation(arm,x["names"][2],x["matrices"][2],target)
        bpy.context.view_layer.update()
        actual=[arm.matrix_world@arm.pose.bones[n].head for n in x["names"]]+[arm.matrix_world@arm.pose.bones[x["names"][-1]].tail]
        expected=[hip,knee,target,target+(x["points"][3]-x["points"][2])]
        err=max((a-b).length for a,b in zip(actual,expected))
        return {"status":"PASS" if err<1e-4 else "FAIL","joint_error":err,"knee_flexion_deg":180-math.degrees(sol["knee_angle"]),
                "bend_dot":float((actual[1]-actual[0]).cross(actual[2]-actual[0]).normalized().dot(normal)),
                "length_error":max(abs((actual[i+1]-actual[i]).length-x["lengths"][i]) for i in range(3)),
                "foot_angle_deg":math.degrees(arm.pose.bones[x["names"][2]].matrix.to_quaternion().rotation_difference((inv@x["matrices"][2]).to_quaternion()).angle),
                "foot_world":list(actual[-1])}
    # Bounded search reduces vertical lift only when the original lengths cannot reach.
    selected=None
    for body_lift in [args.lift,args.lift*.75,args.lift*.5,0.0]:
        for p in arm.pose.bones: p.matrix_basis=baseline_basis[p.name]
        root=arm.pose.bones["Root"]
        mat=arm.matrix_world@baseline["Root"]; mat.translation+=Vector((0,0,body_lift))
        root.matrix=inv@mat; bpy.context.view_layer.update()
        targets={}
        for leg,x in setups.items():
            hip=x["points"][0]
            t=hip+(x["points"][2]-hip)*args.inward
            t.z=x["points"][2].z+ground-x["sole"]
            if leg=="Rear.R": t.y+=args.rear_clearance
            t+=Vector(walk_settings.get("stance_offsets",{}).get(leg,[0,0,0]))
            targets[leg]=t
        rows={}
        for iteration in range(8):
            rows={leg:apply_chain(leg,t,body_lift) for leg,t in targets.items()}
            if any(v["status"]!="PASS" for v in rows.values()): break
            vv=mesh_world(mesh)
            errors={leg:float(vv[x["indices"],2].min()-ground) for leg,x in setups.items()}
            if max(abs(v) for v in errors.values())<.00025: break
            for leg,e in errors.items(): targets[leg].z-=e*.9
        vv=mesh_world(mesh)
        for leg,x in setups.items():
            rows[leg]["sole_error"]=float(vv[x["indices"],2].min()-ground)
        attempt={"body_lift":body_lift,"iterations":iteration+1,"legs":rows}
        report["attempts"].append(attempt)
        print(json.dumps(attempt),flush=True)
        if all(r["status"]=="PASS" and abs(r["sole_error"])<.003 and r["bend_dot"]>.99 for r in rows.values()):
            selected=(body_lift,targets,rows); break
    report["statuses"]["standing_contacts"]="PASS" if selected else "FAIL"
    report["stance_offsets"]=walk_settings.get("stance_offsets",{})
    report["selected_body_lift"]=selected[0] if selected else report["attempts"][-1]["body_lift"]
    report["statuses"]["visual"]="UNVERIFIED"
    report["statuses"]["self_collisions"]="UNVERIFIED"
    current=mesh_world(mesh)
    edges=np.empty(len(mesh.data.edges)*2,dtype=np.int32); mesh.data.edges.foreach_get("vertices",edges); edges=edges.reshape(-1,2)
    l0=np.linalg.norm(base_verts[edges[:,0]]-base_verts[edges[:,1]],axis=1)
    l1=np.linalg.norm(current[edges[:,0]]-current[edges[:,1]],axis=1)
    ratio=l1/np.maximum(l0,1e-8)
    report["mesh"]={"max_displacement":float(np.linalg.norm(current-base_verts,axis=1).max()),"edge_ratio_p99":float(np.quantile(ratio,.99)),
                    "edges_over_3x":int((ratio>3).sum()),"min_z":float(current[:,2].min()),"penetration_any_mesh":float(max(0,ground-current[:,2].min()))}
    significant=l0>.0005
    report["mesh"].update({"significant_edges":int(significant.sum()),"significant_edge_ratio_p99":float(np.quantile(ratio[significant],.99)),
        "significant_edges_over_3x":int(((ratio>3)&significant).sum()),"max_absolute_edge_extension":float((l1-l0).max())})
    report["original_data_unchanged"]=before==fingerprint(arm,mesh)
    report["source_geometry_sha256"]=before
    report["bone_count"]=len(arm.data.bones)
    report["vertex_count"]=len(mesh.data.vertices)
    report["statuses"]["geometry_preservation"]="PASS" if report["original_data_unchanged"] and np.isfinite(current).all() else "FAIL"
    report["statuses"]["mesh_deformation"]="REVIEW_REQUIRED" if report["mesh"]["significant_edges_over_3x"] else "PASS_SAMPLED_EDGES"
    # A single static Action freezes the evaluated pose on reopen; no IK constraints.
    action=bpy.data.actions.new("CMAI_GroundFitted_Standing_"+out.name); arm.animation_data_create(); arm.animation_data.action=action
    for p in arm.pose.bones:
        p.rotation_mode="QUATERNION"
        for channel in ["location","rotation_quaternion","scale"]: p.keyframe_insert(channel,frame=1)
    s.frame_set(1); bpy.context.view_layer.update()
    report["replayed_mesh_error"]=float(np.linalg.norm(mesh_world(mesh)-current,axis=1).max())
    # Full-body framing from evaluated mesh bounds, with camera above the feet.
    for obj in s.objects:
        if obj.type=="MESH" and obj!=mesh: obj.hide_render=True
    low=current.min(0); high=current.max(0); center=Vector((0,(low[1]+high[1])/2,(low[2]+high[2])/2))
    camdata=bpy.data.cameras.new("CMAI_standing_side"); cam=bpy.data.objects.new("CMAI_standing_side",camdata); s.collection.objects.link(cam)
    cam.location=center+Vector((-8,0,.44)); cam.rotation_euler=(center-cam.location).to_track_quat("-Z","Y").to_euler()
    camdata.type="ORTHO"; camdata.ortho_scale=max((high[1]-low[1])*1.12,(high[2]-low[2])*1.9*1.15)
    s.camera=cam
    if args.walk_config:
        camera_settings=json.loads(args.walk_config.read_text()).get('camera',{})
        cam.location=center+Vector(camera_settings.get('offset',[-8,0,.44]))
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    s.render.engine="BLENDER_WORKBENCH"; sh=s.display.shading; sh.light="STUDIO"; sh.color_type="MATERIAL"; sh.show_cavity=True
    sh.background_type="WORLD"
    if s.world is None: s.world=bpy.data.worlds.new("CMAI_ground_fit_world")
    s.world.color=(.8,.8,.8); s.render.film_transparent=False
    # Add a visible ground as independent geometry.
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,ground-.0002))
    plane=bpy.context.object; plane.name="CMAI_Ground_Contact"; plane.color=(.75,.75,.75,1)
    groundmat=bpy.data.materials.new("CMAI_review_ground"); groundmat.diffuse_color=(.7,.72,.75,1); groundmat.use_nodes=True
    groundmat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value=(.7,.72,.75,1)
    groundmat.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value=.85
    plane.data.materials.append(groundmat)
    if args.engine=="eevee":
        s.render.engine="BLENDER_EEVEE"; s.eevee.taa_render_samples=32
        s.world=bpy.data.worlds.new("CMAI_review_world"); s.world.use_nodes=True
        s.world.node_tree.nodes.get("Background").inputs[0].default_value=(.7,.75,.8,1)
        s.world.node_tree.nodes.get("Background").inputs[1].default_value=.5
        for obj in s.objects:
            if obj.type=="LIGHT": obj.hide_render=True
        for name,pos,power,size in [("Key",(-2,-2,3),450,3),("Fill",(2,-1,2),250,3)]:
            ld=bpy.data.lights.new("CMAI_"+name,"AREA"); ld.energy=power; ld.shape="DISK"; ld.size=size
            lo=bpy.data.objects.new("CMAI_"+name,ld); s.collection.objects.link(lo); lo.location=pos
            lo.rotation_euler=(center-lo.location).to_track_quat("-Z","Y").to_euler()
        s.view_settings.view_transform="AgX"
    s.render.resolution_x=1280; s.render.resolution_y=720; s.render.resolution_percentage=100
    s.render.image_settings.file_format="PNG"; s.render.fps=24; s.frame_start=1; s.frame_end=1
    s.render.filepath=str(out/"standing.png")
    (out/"validation.json").write_text(json.dumps(report,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(out/"standing.blend"))
    bpy.ops.render.render(write_still=True)
    if args.walk and selected:
        create_walk(s,arm,mesh,out,report,setups,selected,baseline,apply_chain,ground,edges,l0,args.render_walk,json.loads(args.walk_config.read_text()) if args.walk_config else None)
    print("OUTPUT "+str(out),flush=True)

if __name__=="__main__": main()
