"""Create a fixed-camera reference/model landmark comparison."""
import json, sys
from pathlib import Path
import bpy
from bpy_extras.object_utils import world_to_camera_view

run=Path(sys.argv[-1]).resolve(); req=json.loads((run/"request.json").read_text())
source=Path(req["source"]).resolve(); video=Path(req["video"]).resolve(); frame=int(req["blender_frame"])
bpy.ops.wm.open_mainfile(filepath=str(source)); scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=="ARMATURE")
skinned=next(o for o in scene.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object==arm for m in o.modifiers))
for obj in scene.objects:
    if obj.type=="MESH": obj.hide_render=(obj!=skinned)
profile=next(x for x in json.loads(Path(req["camera_profiles"]).read_text())["profiles"] if x["view"]=="side")
data=bpy.data.cameras.new("CMAI_ImageLandmark_Camera"); cam=bpy.data.objects.new(data.name,data); scene.collection.objects.link(cam)
cam.location=profile["location"]; cam.rotation_euler=profile["rotation_euler"]; data.type=profile["projection"]; data.ortho_scale=profile["ortho_scale"]; data.lens=profile["focal_length"]; data.sensor_width=36; data.shift_x=profile["shift_x"]; data.shift_y=profile["shift_y"]; scene.camera=cam
scene.render.engine="BLENDER_WORKBENCH"; scene.render.resolution_x=640; scene.render.resolution_y=360; scene.render.resolution_percentage=100; scene.render.image_settings.file_format="PNG"; scene.display.shading.color_type="SINGLE"; scene.display.shading.single_color=(1,1,1); scene.display.shading.light="FLAT"; scene.display.shading.background_type="WORLD"; scene.display.shading.show_shadows=False; scene.display.shading.show_cavity=False; scene.world=bpy.data.worlds.new("CMAI_ImageLandmark_World"); scene.world.color=(0,0,0)
scene.frame_set(frame); bpy.context.view_layer.update()
if (run/"camera_adjustment.json").exists():
    adjustment=json.loads((run/"camera_adjustment.json").read_text())
    data.shift_x+=adjustment["shift_x_delta"]; data.shift_y+=adjustment["shift_y_delta"]
    if data.type=="PERSP": data.lens*=adjustment["zoom"]
    else: data.ortho_scale/=adjustment["zoom"]
    output="model_aligned.png"
else: output="model_baseline.png"
scene.render.filepath=str(run/output); bpy.ops.render.render(write_still=True)
if output=="model_aligned.png":
    scene.display.shading.light="STUDIO"
    scene.display.shading.single_color=(0.65,0.75,0.82)
    scene.display.shading.show_cavity=True
    scene.render.filepath=str(run/"model_visual.png")
    bpy.ops.render.render(write_still=True)
proxies=[]
projected=[]
bone_map={"torso":"Body_02","head":"Head_02","tail":"Tail_01",
          "Front.R hip":"Leg_Front.R_01","Front.R knee":"Leg_Front.R_02",
          "Front.R ankle":"Leg_Front.R_03","Front.R foot":"Leg_Front.R_03"}
for side in ("L", "R"):
    for leg in ("Front", "MidFront", "MidRear", "Rear"):
        for role, suffix in (("hip", "01"), ("knee", "02"), ("ankle", "03")):
            bone_map[f"{leg}.{side} {role}"] = f"Leg_{leg}.{side}_{suffix}"
        bone_map[f"{leg}.{side} foot"] = f"Leg_{leg}.{side}_03"
for label,bone_name in bone_map.items():
    bone=arm.pose.bones.get(bone_name)
    if bone is not None:
        point=bone.tail if label.endswith("foot") else bone.head
        uv=world_to_camera_view(scene,cam,arm.matrix_world@point)
        projected.append({"name":label,"bone":bone_name,"xy":[float(uv.x*640),float((1-uv.y)*360)],"status":"UNVERIFIED_CORRESPONDENCE"})
report={"status":"BLOCKED_NO_VERIFIED_LANDMARKS","source":str(source),"video":str(video),"frame":frame,"reference_frame":int(req["frame"]),"camera_profile":profile,"reference_landmarks":{"verified":[],"provisional":proxies},"projected_model_landmarks":projected,"errors_px":[],"optimization":{"status":"NOT_RUN","reason":"No exact-video/frame verified anatomical correspondences; no bone rotations changed."},"validation":{"source_action_unchanged":True,"camera_fixed_during_comparison":True,"knee_contact_collision":"NOT RUN; no candidate pose"},"comparison":str(run/"image_landmark_comparison.png"),"recommendation":"Verify at least one body or leg correspondence for this exact video/frame before bounded bone optimization."}
(run/"image_landmark_report.json").write_text(json.dumps(report,indent=2)); print(json.dumps(report))
