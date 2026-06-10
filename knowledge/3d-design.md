# 3D Design & Rendering — Complete Guide

## Table of Contents

1. [Introduction to 3D](#introduction-to-3d)
2. [Blender](#blender)
3. [Autodesk Maya](#autodesk-maya)
4. [3ds Max](#3ds-max)
5. [Cinema 4D](#cinema-4d)
6. [ZBrush](#zbrush)
7. [Houdini](#houdini)
8. [SketchUp](#sketchup)
9. [SolidWorks](#solidworks)
10. [3D File Formats](#3d-file-formats)
11. [Rendering Engines](#rendering-engines)
12. [Materials & PBR](#materials--pbr)
13. [Lighting & HDRIs](#lighting--hdris)
14. [Compositing](#compositing)
15. [Python Scripting for Blender (bpy)](#python-scripting-for-blender-bpy)
16. [Texturing Tools](#texturing-tools)
17. [Photogrammetry](#photogrammetry)
18. [Workflow & Pipeline](#workflow--pipeline)

---

## Introduction to 3D

The 3D pipeline consists of several interconnected stages:

# 3D Design & Rendering -- Complete Guide

## Table of Contents

1. [Introduction to 3D](#introduction-to-3d)
2. [Blender](#blender)
3. [Autodesk Maya](#autodesk-maya)
4. [3ds Max](#3ds-max)
5. [Cinema 4D](#cinema-4d)
6. [ZBrush](#zbrush)
7. [Houdini](#houdini)
8. [SketchUp](#sketchup)
9. [SolidWorks](#solidworks)
10. [3D File Formats](#3d-file-formats)
11. [Rendering Engines](#rendering-engines)
12. [Materials & PBR](#materials--pbr)
13. [Lighting & HDRIs](#lighting--hdris)
14. [Compositing](#compositing)
15. [Python Scripting for Blender (bpy)](#python-scripting-for-blender-bpy)
16. [Texturing Tools](#texturing-tools)
17. [Photogrammetry](#photogrammetry)
18. [Workflow & Pipeline](#workflow--pipeline)


---

## Introduction to 3D

The 3D pipeline consists of several interconnected stages:

```
Modeling -> UV Mapping -> Texturing -> Rigging -> Animation -> Lighting -> Rendering -> Compositing
```

---

## Introduction to 3D

The 3D pipeline: Modeling -> UV Mapping -> Texturing -> Rigging -> Animation -> Lighting -> Rendering -> Compositing

**Key concepts:** Vertices/Edges/Faces, NURBS, Subdivision Surface, Displacement, Normal Mapping, PBR

### Coordinate Systems

| Software | Up Axis | Forward Axis |
|----------|---------|--------------|
| Blender | Z | -Y |
| Maya | Y | Z |
| 3ds Max | Z | Y |
| Cinema 4D | Y | Z |

---

## Blender

### Box Modeling

`python
import bpy
bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
obj = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=2)
bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0,0,1)})
bpy.ops.mesh.loop_cut(number_cuts=1, location=(0,0,0), edge_percent=0.5)
bpy.ops.mesh.bevel(offset=0.1, segments=3, affect='EDGES')
bpy.ops.object.mode_set(mode='OBJECT')
`

### Modifiers

`python
obj = bpy.context.active_object
subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
subdiv.levels = 2; subdiv.render_levels = 3
mirror = obj.modifiers.new(name="Mirror", type='MIRROR')
mirror.use_axis[0] = True; mirror.use_clip = True
bool_mod = obj.modifiers.new(name="Boolean", type='BOOLEAN')
bool_mod.operation = 'DIFFERENCE'
array = obj.modifiers.new(name="Array", type='ARRAY')
array.count = 10
bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
bevel.width = 0.02; bevel.segments = 3
`

### Sculpting

`python
obj = bpy.context.active_object
multires = obj.modifiers.new(name="Multires", type='MULTIRES')
for i in range(6): bpy.ops.object.multires_subdivide(modifier="Multires")
bpy.ops.object.mode_set(mode='SCULPT')
# Brushes: Clay Strips, Crease, Flatten, Grab, Inflate, Pinch, Smooth, Snake Hook
bpy.context.scene.tool_settings.sculpt.detail_type_method = 'CONSTANT_DETAIL'
bpy.ops.sculpt.dynamic_topology_toggle()
`

### UV Mapping

`python
obj = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
bpy.ops.uv.pack_islands(margin=0.001, rotate=True, scale=True)
`

### Texturing with Nodes

`python
mat = bpy.data.materials.new(name="CustomMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes; links = mat.node_tree.links
for node in nodes: nodes.remove(node)
bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
tex_image = nodes.new(type='ShaderNodeTexImage')
tex_coord = nodes.new(type='ShaderNodeTexCoord')
mapping = nodes.new(type='ShaderNodeMapping')
output = nodes.new(type='ShaderNodeOutputMaterial')
tex_image.image = bpy.data.images.load("C:/textures/albedo.png")
links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])
links.new(mapping.outputs['Vector'], tex_image.inputs['Vector'])
links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
`

### PBR Material Function

`python
def create_pbr_material(name, textures):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True; nodes = mat.node_tree.nodes; links = mat.node_tree.links; nodes.clear()
    output = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    if 'base_color' in textures:
        tex = nodes.new(type='ShaderNodeTexImage')
        tex.image = bpy.data.images.load(textures['base_color'])
        links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    if 'roughness' in textures:
        tex = nodes.new(type='ShaderNodeTexImage')
        tex.image = bpy.data.images.load(textures['roughness'])
        tex.image.colorspace_settings.name = 'Non-Color'
        links.new(tex.outputs['Color'], bsdf.inputs['Roughness'])
    if 'metallic' in textures:
        tex = nodes.new(type='ShaderNodeTexImage')
        tex.image = bpy.data.images.load(textures['metallic'])
        links.new(tex.outputs['Color'], bsdf.inputs['Metallic'])
    if 'normal' in textures:
        nm = nodes.new(type='ShaderNodeNormalMap')
        tex = nodes.new(type='ShaderNodeTexImage')
        tex.image = bpy.data.images.load(textures['normal'])
        tex.image.colorspace_settings.name = 'Non-Color'
        links.new(tex.outputs['Color'], nm.inputs['Color'])
        links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat
`

### Rigging

`python
armature = bpy.data.armatures.new("Armature")
arm_obj = bpy.data.objects.new("Armature", armature)
bpy.context.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='EDIT')
bone = armature.edit_bones.new('Root')
bone.head = (0,0,0); bone.tail = (0,0,1)
leg = armature.edit_bones.new('Leg.L')
leg.parent = bone; leg.head = (0.5,0,0); leg.tail = (0.5,0,-1)
bpy.ops.object.mode_set(mode='OBJECT')
mesh_obj = bpy.data.objects.get("Character")
mesh_obj.parent = arm_obj
mesh_obj.modifiers.new("Armature", 'ARMATURE').object = arm_obj
bpy.ops.object.mode_set(mode='POSE')
leg_bone = arm_obj.pose.bones.get("ForeLeg.L")
ik = leg_bone.constraints.new('IK')
ik.target = arm_obj; ik.subtarget = 'IK_Target.L'; ik.chain_count = 2
bpy.ops.object.mode_set(mode='OBJECT')
`

### Animation

`python
import math
obj = bpy.context.active_object
obj.animation_data_create()
action = bpy.data.actions.new("CubeAction")
obj.animation_data.action = action
obj.location = (0,0,0); obj.keyframe_insert(data_path="location", frame=1)
obj.location = (5,0,3); obj.keyframe_insert(data_path="location", frame=50)
obj.rotation_euler = (0,0,math.radians(360))
obj.keyframe_insert(data_path="rotation_euler", frame=100)
for fc in action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
    noise = fc.modifiers.new('NOISE'); noise.scale = 10; noise.strength = 0.5
`

### Cycles Rendering

`python
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'
bpy.context.scene.cycles.samples = 1024
bpy.context.scene.cycles.use_denoising = True
bpy.context.scene.cycles.denoiser = 'OPENIMAGEDENOISE'
bpy.context.scene.cycles.max_bounces = 12
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.filepath = "C:/renders/frame_"
bpy.ops.render.render(write_still=True)
`

### Eevee Rendering

`python
bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
bpy.context.scene.eevee.use_gtao = True
bpy.context.scene.eevee.use_bloom = True
bpy.context.scene.eevee.use_volumetric = True
bpy.context.scene.eevee.use_ssr = True
bpy.context.scene.eevee.use_soft_shadows = True
bpy.context.scene.eevee.use_taa = True
bpy.context.scene.eevee.taa_render_samples = 64
`

### Shader Nodes (Custom Glass)

`python
def create_glass_node_group():
    group = bpy.data.node_groups.new("CustomGlass", 'ShaderNodeTree')
    gi = group.nodes.new('NodeGroupInput')
    go = group.nodes.new('NodeGroupOutput')
    group.inputs.new('NodeSocketColor', 'Color')
    group.inputs.new('NodeSocketFloat', 'Roughness')
    group.inputs.new('NodeSocketFloat', 'IOR')
    glass = group.nodes.new('ShaderNodeBsdfGlass')
    mix = group.nodes.new('ShaderNodeMixShader')
    lp = group.nodes.new('ShaderNodeLightPath')
    tr = group.nodes.new('ShaderNodeBsdfTransparent')
    links = group.links
    links.new(gi.outputs['Color'], glass.inputs['Color'])
    links.new(gi.outputs['Roughness'], glass.inputs['Roughness'])
    links.new(gi.outputs['IOR'], glass.inputs['IOR'])
    links.new(lp.outputs['Is Shadow Ray'], mix.inputs['Fac'])
    links.new(tr.outputs['BSDF'], mix.inputs[1])
    links.new(glass.outputs['BSDF'], mix.inputs[2])
    links.new(mix.outputs['Shader'], go.inputs[0])
    return group
`

### Geometry Nodes

`python
obj = bpy.context.active_object
mod = obj.modifiers.new("GeoNodes", 'NODES')
group = bpy.data.node_groups.new("ScatterPoints", 'GeometryNodeTree')
gi = group.nodes.new('NodeGroupInput')
go = group.nodes.new('NodeGroupOutput')
group.inputs.new('NodeSocketGeometry', 'Geometry')
group.outputs.new('NodeSocketGeometry', 'Geometry')
points = group.nodes.new('GeometryNodeDistributePointsOnFaces')
points.distribute_method = 'POISSON'
instance = group.nodes.new('GeometryNodeInstanceOnPoints')
cube = group.nodes.new('GeometryNodeMeshCube')
realize = group.nodes.new('GeometryNodeRealizeInstances')
links = group.links
links.new(gi.outputs['Geometry'], points.inputs['Mesh'])
links.new(points.outputs['Points'], instance.inputs['Points'])
links.new(cube.outputs['Mesh'], instance.inputs['Instance'])
links.new(instance.outputs['Instances'], realize.inputs['Geometry'])
links.new(realize.outputs['Geometry'], go.inputs['Geometry'])
`

---

## Autodesk Maya

`python
import maya.cmds as cmds
cube = cmds.polyCube(name="MyCube", width=2, height=2, depth=2)
cmds.move(5, 0, 0, cube[0])
cmds.rotate(45, 0, 0, cube[0])
cmds.polyExtrudeFacet(cube[0], translateZ=1, divisions=3)
cmds.polyBevel(cube[0], offset=0.1, segments=3)
cmds.nonLinear(cube[0], type='bend', curvature=45)
lambert = cmds.shadingNode('lambert', asShader=True)
cmds.setAttr(lambert + '.color', 1, 0, 0, type='double3')
cmds.hyperShade(assign=lambert)
cmds.setKeyframe(cube[0], attribute='translateX', t=1, v=0)
cmds.setKeyframe(cube[0], attribute='translateX', t=24, v=10)
cmds.setAttr('defaultRenderGlobals.currentRenderer', 'arnold')
`

### Rigging

`python
cmds.joint(name='hip', position=(0,0,0))
cmds.joint(name='knee', position=(0,-40,0))
cmds.joint(name='ankle', position=(0,-80,0))
cmds.ikHandle(name='legIK', startJoint='hip', endEffector='ankle')
cmds.skinCluster('CharacterMesh', toSelectedBones=True)
`

---

## 3ds Max (MaxScript)

`maxscript
b = Box length:50 width:50 height:50 pos:[0,0,0]
addModifier b (TurboSmooth iterations:2)
addModifier b (Bend angle:45 bendAxis:0)
convertToPoly b
mat = StandardMaterial(); mat.diffuse = color 255 0 0
b.material = mat
with animate on (
    at time 0 ( b.pos = [0,0,0] )
    at time 100 ( b.pos = [100,0,50] )
)
render outputFile:"C:/renders/scene.png" vfb:off
exportFile "C:/exports/model.fbx" #noPrompt
`

---

## Cinema 4D (Python)

`python
import c4d
doc = c4d.documents.GetActiveDocument()
cube = c4d.BaseObject(c4d.Ocube)
cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(200,200,200)
doc.InsertObject(cube)
sphere = c4d.BaseObject(c4d.Osphere)
sphere[c4d.PRIM_SPHERE_RAD] = 100
doc.InsertObject(sphere)
mat = c4d.BaseMaterial(c4d.Mmaterial)
mat[c4d.MATERIAL_USE_COLOR] = True
mat[c4d.MATERIAL_COLOR_COLOR] = c4d.Vector(1,0,0)
doc.InsertMaterial(mat)
cloner = c4d.BaseObject(c4d.Omgcloner)
doc.InsertObject(cloner)
sphere.InsertUnder(cloner)
effector = c4d.BaseObject(c4d.Omgreffector)
effector[c4d.ID_MG_BASEEFFECTOR_POSITION_ACTIVE] = True
effector[c4d.ID_MG_BASEEFFECTOR_POSITION] = c4d.Vector(0,200,0)
doc.InsertObject(effector); effector.InsertUnder(cloner)
`

---

## ZBrush

Key workflows:
1. ZSphere -> Adaptive Skin -> DynaMesh -> Sculpt -> Subdivide -> Detail
2. Import Base Mesh -> Subdivide -> Sculpt -> Polypaint -> UV Master

Brushes: ClayBuildup, DamStandard, Move, Inflate, Pinch, TrimDynamic

Displacement: ZPlugin -> Multi Map Exporter -> Displacement -> 32-bit TIF -> Level 5+

---

## Houdini

`python
import hou
geo = hou.node("/obj").createNode("geo", "ProcBuilding")
box = geo.createNode("box", "BaseBox"); box.parm("sizey").set(10)
scatter = geo.createNode("scatter", "ScatterPoints")
scatter.setInput(0, box); scatter.parm("npts").set(500)
copy = geo.createNode("copytopoints", "CopyToPoints")
copy.setInput(0, scatter); copy.setInput(1, box)
wrangle = geo.createNode("attribwrangle", "RandomScale")
wrangle.setInput(0, copy)
wrangle.parm("snippet").set('@pscale = fit01(rand(@ptnum), 0.1, 0.5);')
geo.layoutChildren()
`

### VEX

`ex
@Cd = set(0, @P.y/10, 1-@P.y/10);
@up = {0,1,0};
matrix3 m = maketransform(@N, @up);
@orient = quaternion(m);
vector noise = curlnoise(@P*0.1 + @Time*0.01);
@P += noise * 0.1;
`

### Simulation Types: Pyro FX (fire), FLIP (fluids), Grains (sand), RBD (rigid body), Vellum (cloth)

---

## SketchUp (Ruby)

`uby
model = Sketchup.active_model
entities = model.active_entities
face = entities.add_face([Geom::Point3d.new(0,0,0), Geom::Point3d.new(100,0,0), Geom::Point3d.new(100,100,0), Geom::Point3d.new(0,100,0)])
face.pushpull(-200)
`

---

## SolidWorks (VBA)

`bnet
Dim swApp As SldWorks.SldWorks
Set swApp = Application.SldWorks
Dim swPart As SldWorks.PartDoc
Set swPart = swApp.NewDocument("C:\template.prtdot", 0, 0, 0)
swPart.SketchManager.InsertSketch True
swPart.SketchManager.CreateCornerRectangle 0, 0, 0, 0.1, 0.05, 0
swPart.FeatureManager.FeatureExtrusion2 True, False, False, 6, 0, 0.02
swPart.Extension.SaveAs "C:/exports/part.STEP"
swPart.Extension.SaveAs "C:/exports/part.STL"
`

---

## 3D File Formats

| Format | Type | Anim | Textures | Use |
|--------|------|------|----------|-----|
| OBJ | Mesh | No | MTL | Universal |
| FBX | Scene | Yes | Yes | Game engines |
| glTF/GLB | Scene | Yes | Embedded | Web |
| USD | Scene | Yes | Yes | Pixar |
| STL | Mesh | No | No | 3D printing |
| STEP | CAD | No | No | Engineering |
| PLY | Mesh | No | No | Scanning |
| ABC | Cache | Yes | No | Simulation |
| VDB | Vol | No | No | Smoke |

### Conversion

`python
import subprocess
subprocess.run(["assimp", "export", "input.fbx", "output.gltf", "--format=gltf2"])

def convert_with_blender(input_path, output_path, fmt='FBX'):
    import bpy; bpy.ops.wm.clear_recent_files()
    ext = input_path.split('.')[-1].lower()
    if ext == 'obj': bpy.ops.wm.obj_import(filepath=input_path)
    elif ext == 'fbx': bpy.ops.import_scene.fbx(filepath=input_path)
    if fmt.lower() == 'fbx': bpy.ops.export_scene.fbx(filepath=output_path)
    elif fmt.lower() in ['glb','gltf']: bpy.ops.export_scene.gltf(filepath=output_path)
`

---

## Rendering Engines

### Arnold (Maya): cmds.setAttr('defaultRenderGlobals.currentRenderer', 'arnold'); aiStandardSurface; aiAreaLight

### V-Ray (MaxScript): VRayMtl; VRayLight; subdivs=8; giOn=True

### Redshift (Maya): unifiedMinSamples=64; RedshiftMaterial; SSS support

### RenderMan (Maya): PxrSurface; PxrDomeLight for HDRI; EXR output

### Octane (C4D): Octane material 1036222; transmission, scattering, IOR control

---

## Materials & PBR

### PBR Maps: Base Color (sRGB), Roughness (Non-Color), Metalness (Non-Color), Normal (Non-Color), Displacement (Non-Color), AO (Non-Color)

### Substance Painter API

`python
import substance_painter as sp
sp.project.open("C:/projects/helmet.spp")
sp.export.export_project_textures(
    export_path="C:/exports/textures/",
    export_list=[{"exportPreset": "PBR (Metallic)", "outputSize": "2048"}],
    export_bit_depth=16
)
`

### Substance Designer: Nodes -> Perlin Noise, Voronoi, Tile Sampler, Histogram Scan, Slope Blur, PBR Output

---

## Lighting

### Three-Point: Key (main), Fill (shadows), Rim (separation)

### HDRI: Environment texture with ShaderNodeTexEnvironment, set as Background

### Light Types: Point, Sun, Spot, Area, Dome/HDRI, IES

---

## Compositing

### Blender Compositor: Render Layers -> Denoise -> Glare -> Color Balance -> Composite

### AOVs: Combined, Z, Normal, Diffuse, Glossy, Shadow, AO, Cryptomatte

---

## Photogrammetry

Pipeline: Capture -> Align -> Dense Cloud -> Mesh -> Texture

Software: RealityCapture, Metashape, Meshroom, COLMAP

COLMAP:
`ash
colmap feature_extractor --database_path db.db --image_path ./images
colmap exhaustive_matcher --database_path db.db
colmap mapper --database_path db.db --image_path ./images --output_path ./sparse
colmap patch_match_stereo --workspace_path ./dense
colmap stereo_fusion --workspace_path ./dense --output_path ./dense/fused.ply
`

---

## Pipeline

Production: Concept -> Modeling -> UV -> Texturing -> Rigging -> Animation -> Lighting -> Rendering -> Compositing

Game Asset: High Poly (ZBrush) -> Retopo -> UV -> Bake -> Low Poly + Textures -> Engine

### Render Farm

`python
import subprocess
def submit_render(blend_path, start, end, out_dir):
    cmd = ["blender", "-b", blend_path, "-E", "CYCLES", "-o", f"{out_dir}/frame_####", "-s", str(start), "-e", str(end), "-a"]
    return subprocess.run(cmd).returncode
`

### bpy Reference: objects, meshes, materials, images, armatures, actions, worlds, node_groups, collections, lights, cameras

---

## Python Scripting Quick Reference

### bpy Data Access

`python
# Object operations
bpy.data.objects["Cube"]  # access by name
bpy.context.selected_objects  # currently selected
bpy.context.active_object  # active object
bpy.context.scene.objects  # all objects in scene

# Mesh data
obj.data.vertices  # vertex array
obj.data.edges  # edge array
obj.data.polygons  # face array
obj.data.uv_layers  # UV maps
obj.data.vertex_colors  # vertex colors

# Material operations
bpy.data.materials.new("MaterialName")
bpy.data.materials.remove(material)
obj.data.materials.append(mat)  # assign material
obj.active_material  # current material

# Animation
bpy.context.scene.frame_current = 1  # set current frame
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 250

# Rendering
bpy.ops.render.render(write_still=True)  # render single frame
bpy.ops.render.render(animation=True)  # render animation
bpy.context.scene.render.filepath = "//render/frame_####"  # output path

# Import/Export
bpy.ops.import_scene.obj(filepath="model.obj")
bpy.ops.import_scene.fbx(filepath="model.fbx")
bpy.ops.export_scene.fbx(filepath="export.fbx")
bpy.ops.wm.stl_export(filepath="model.stl")
bpy.ops.wm.usd_export(filepath="model.usdc")

# Modifiers
mod = obj.modifiers.new(name="Name", type='SUBSURF')
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.object.modifier_move_up(modifier=mod.name)
`

### Common bpy Operators

| Operator | Description |
|----------|-------------|
| bpy.ops.object.join() | Join selected meshes |
| bpy.ops.object.duplicate() | Duplicate selection |
| bpy.ops.object.delete() | Delete selection |
| bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY') | Set origin |
| bpy.ops.object.transform_apply() | Apply transforms |
| bpy.ops.object.shade_smooth() | Smooth shading |
| bpy.ops.object.shade_flat() | Flat shading |
| bpy.ops.object.parent_set() | Parent objects |
| bpy.ops.object.select_all(action='DESELECT') | Deselect all |
| bpy.ops.mesh.primitive_cube_add() | Add cube |
| bpy.ops.mesh.primitive_uv_sphere_add() | Add UV sphere |
| bpy.ops.mesh.primitive_cylinder_add() | Add cylinder |
| bpy.ops.mesh.primitive_torus_add() | Add torus |

### bpy.types Reference

`python
# Core types
bpy.types.Object  # 3D object
bpy.types.Mesh  # mesh geometry data
bpy.types.Material  # material definition
bpy.types.Image  # image texture
bpy.types.World  # environment
bpy.types.Collection  # group of objects
bpy.types.Scene  # scene data
bpy.types.Camera  # camera
bpy.types.Light  # lighting
bpy.types.Armature  # rigging bones
bpy.types.Action  # animation data
bpy.types.ParticleSettings  # particles
bpy.types.Tex  # texture data
bpy.types.Brush  # sculpting/painting brush
bpy.types.NodeTree  # shader/compositor node tree
bpy.types.Modifier  # object modifier
bpy.types.Constraint  # object constraint
bpy.types.Key  # shape key
bpy.types.GPencil  # grease pencil (2D animation)
bpy.types.MovieClip  # video clip
bpy.types.Sound  # audio data
bpy.types.Library  # linked data
bpy.types.Text  # text data block
`

### Texturing Tools Comparison

| Tool | Type | Best For |
|------|------|----------|
| Substance Painter | 3D painting | Real-time texturing, PBR |
| Substance Designer | Procedural | Material generation |
| Mari | 3D painting | Film VFX, large UDIMs |
| ArmorPaint | 3D painting | Open source alternative |
| Quixel Mixer | 3D painting | Megascans integration |
| 3D-Coat | 3D painting + voxel | All-in-one |
| Blender Texture Paint | Built-in | Basic texturing |

### Photogrammetry Best Practices

**Capture tips:**
- 60% overlap minimum between adjacent photos
- Consistent lighting (avoid harsh shadows)
- Use a tripod for sharp images
- Avoid reflective/transparent surfaces
- 50-200 images depending on subject complexity
- Shoot raw for maximum flexibility
- Include color checker for accurate color

**Processing tips:**
- Mask out background for cleaner models
- Use control points for scale reference
- Generate low-res preview first to verify alignment
- Clean dense point cloud before meshing
- Decimate mesh for manageable file sizes
- Unwrap UVs before texturing
- Retopologize for animation-ready assets
