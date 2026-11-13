# Reference Walk Builder — first integrated workflow

This is part of the existing Creature Motion AI add-on. It creates a working
scene copy and unique output folders. The original scene, rig data, animation
Actions and previously generated files are retained.

The current builder reuses the **executed rest-relative two-link waypoint
backend** that produced the latest Balisk eight-leg review. It does not pretend
that the historical Front.L IKPy or MidRear.L Pinocchio experiments validate
every external-solver mapping for every leg. Those adapters remain available.

## Running it

1. Install the new versioned add-on ZIP using Blender Preferences, then enable
   Creature Motion AI. Restart Blender if an older version is already loaded.
2. Open the natural standing baseline and select its armature.
3. Open **N → Creature Motion AI → Reference Walk Builder**.
4. For the Balisk, click **Load Balisk Review Settings**. For another creature,
   provide an explicit rig-profile JSON. The builder will not guess an unknown
   bone hierarchy from a video.
5. Select an output directory and the existing external Python environment with
   OpenCV and imageio-ffmpeg. No dependencies are installed into Blender.
6. Run Analyze Creature Rig → Fit Standing Pose → Preview Standing Pose →
   Generate Walking Waypoints → Build Eight-Leg Walk → Validate Animation →
   Render Five-Second Preview.

The builder requires Blender 4.4+ Action slots; execution is tested on Blender
5.2.2. Existing legacy operators retain their names and behavior.

## Stage meanings and current scope

| Control | Implementation |
|---|---|
| Analyze Creature Rig | Detect familiar names or read explicit chains; verify hierarchy and weights; export actual rest/pose matrices and local axes. |
| Analyze Reference Video | Not connected to this builder yet. Existing OpenCV, DLC and landmark review tools remain available in the original panel. |
| Calibrate Camera | Independent calibration is incomplete. Standing fit creates automatic approximate side framing, which is not labeled calibrated. |
| Fit Standing Pose | Copy scene, isolate Action/NLA/constraints in the copy, preserve actual baseline pose, fit mesh soles to shared ground, create a new standing Action. |
| Preview Standing Pose | Render the current standing Action without overwriting a previous preview. |
| Generate Walking Waypoints | Solve sparse reachable leg poses and store complete local pose matrices; restore the standing Action afterward. |
| Build Eight-Leg Walk | Consume the stored poses, use Bezier interpolation, correct intermediate contact errors, add root travel and a following camera. |
| Validate Animation | Evaluate all 120 frames and loop endpoint; check real mesh movement, contacts, sole sliding, bend direction, lengths, proxy intersections and framing. |
| Render Five-Second Preview | Render frames 1–120 at 24 FPS; encode externally; decode the MP4 and check temporal change in every second. |
| Export Animation | Final FBX/export-reimport and visual approval gating remain incomplete. Working Blender files and Actions are saved already. |

PASS means that stage executed its stated numerical or file checks. It does
**not** mean the walk is visually approved, that tracking identities are
verified, or that the motion exactly matches the reference. Visual approval and
exact mesh collision status remain separate fields in the reports.

## Reused code and preserved evidence

- `creature_motion_ai/ik_step.py`: corrected rest-relative knee-plane solver,
  rest-to-target direction mapping and terminal orientation preservation.
- `creature_motion_ai/walk_waypoints.py`: shared generation/keyframing and
  intermediate checks extracted from the executed standing-fit tool. The old
  command-line tool now delegates to this module.
- `creature_motion_ai/reference_walk.py`: profile inspection, standing fitting,
  per-joint basis tests, camera framing and actual playback validation.
- `creature_motion_ai/collision_proxies.py`: existing segment/radius checks,
  extended with profile-supplied chain names without changing legacy entry points.
- `tools/apply_ikpy_frontl_poc.py` and
  `data/generated/ikpy_frontL_ikpy_diagnostic_v13_report.json`: successful
  evaluated terminal-direction correction for the original Front.L target.
- `tools/apply_pinocchio_chain_blender_poc.py` and
  `data/generated/pinocchio_midrearL_validated_report.json`: MidRear.L local-X
  correction in its exported joint-rest basis, not a universal world-X rule.
- `data/generated/reference_walk_refinement_04/`: prior eight-leg review,
  contacts, comparison and limitations. Preserved as evidence, not automatic
  visual acceptance of this new implementation.

## Profiles and recovery

Balisk-specific phase offsets, foot placement offsets, body height and naming
live in `creature_motion_ai/profiles/balisk_reference_walk.json`. The generic
modules contain no Balisk bone-name or object-name lookup. Explicit profiles
may supply different three-bone chain names and a different top-level root.

Current scope: one skinned mesh, a common top-level root, connected three-bone
legs and a horizontal forward direction on a world-Z ground plane. Other
creatures are not visually validated merely because their profiles load.
Unsupported chains produce an explicit error instead of changing anatomy.

Changing motion settings invalidates downstream PASS statuses. Changing the
rig/profile invalidates the rig analysis too. Refit/rebuild to produce a fresh
version. Outputs include rig profile/anatomy, standing validation, local-axis
tests, waypoint poses, Action reports, whole-preview validation, Blender copies,
120 source PNGs, MP4, decoded contact sheet and workflow state.

The external solver helper accepts explicitly bone-local axes. It preserves
bone roll and uses Blender's rest/parent conversion. An external solver must
still provide predicted joint positions for its own conversion regression;
the local-basis test is not proof that an arbitrary Pinocchio model is correct.

## Known remaining work

- Connect existing tracking review/approval to reference timing and identities.
- Add independent camera correspondence validation and measured motion fitting.
- Complete external Pinocchio/IKPy backend selection and per-leg regression.
- Add multiple skinned meshes and test additional creature anatomies.
- Validate exact mesh collisions, localized stretching and final gait quality.
- Add approved FBX export/reimport validation.

`tools/test_reference_walk_builder.py` executes the registered operators in
Blender, exercises register/unregister/re-register, and compares the original
scene's evaluated mesh and Action after the complete workflow.
