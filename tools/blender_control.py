"""
TOM Blender Control — Automates Blender 3D modeling via Python API.
Generates and executes Blender Python scripts for 3D creation.
"""
import os
import json
import subprocess
import sys
from typing import Any, Dict, List, Optional
from tools.project_paths import project_path_str

class BlenderControl:
    def __init__(self):
        self.blender_path = self._find_blender()
        self._bpy = None
        self._has_bpy = False
        self._try_import_bpy()

    def _try_import_bpy(self):
        try:
            import bpy
            self._bpy = bpy
            self._has_bpy = True
        except ImportError:
            self._has_bpy = False
            self._bpy = None

    def _find_blender(self) -> Optional[str]:
        candidates = [
            r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.5\blender.exe",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        try:
            result = subprocess.run(["where", "blender"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().splitlines()[0]
        except Exception:
            pass
        return None

    def is_available(self) -> bool:
        return self._has_bpy or self.blender_path is not None

    def get_blender_path(self) -> str:
        return self.blender_path or "Not found"

    def generate_script(self, task: str) -> str:
        task_lower = task.lower()
        scene_name = "TOM_Generated_Scene"
        if "cube" in task_lower:
            code = self._cube_script()
        elif "sphere" in task_lower or "ball" in task_lower:
            code = self._sphere_script()
        elif "cylinder" in task_lower:
            code = self._cylinder_script()
        elif "torus" in task_lower or "donut" in task_lower:
            code = self._torus_script()
        elif "terrain" in task_lower or "landscape" in task_lower or "ground" in task_lower:
            code = self._terrain_script()
        elif "light" in task_lower:
            code = self._light_setup_script()
        elif "material" in task_lower or "texture" in task_lower:
            code = self._material_script()
        elif "animation" in task_lower or "animate" in task_lower:
            code = self._animation_script()
        elif "array" in task_lower or "pattern" in task_lower or "multiple" in task_lower:
            code = self._array_script()
        elif "smooth" in task_lower or "subdivide" in task_lower:
            code = self._subdivision_script()
        elif "curve" in task_lower or "path" in task_lower:
            code = self._curve_script()
        elif "text" in task_lower:
            code = self._text_script()
        elif "rig" in task_lower or "skeleton" in task_lower or "armature" in task_lower:
            code = self._rigging_script()
        elif "render" in task_lower:
            code = self._render_script()
        elif "house" in task_lower or "building" in task_lower:
            code = self._house_script()
        else:
            code = self._general_script(task)
        return code

    def _general_script(self, task: str) -> str:
        return f'''import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# TOM Blender Script
# Task: {task}

# Create a collection for organized scene
col = bpy.data.collections.new("TOM_Scene")
bpy.context.scene.collection.children.link(col)

# Create a basic object
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "TOM_Main"

# Smooth shading
bpy.ops.object.shade_smooth()

# Add material
mat = bpy.data.materials.new(name="TOM_Material")
mat.use_nodes = True
obj.data.materials.append(mat)

print("TOM Blender script executed successfully")
'''

    def _cube_script(self) -> str:
        return '''import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "TOM_Cube"
bpy.ops.object.shade_smooth()

# Subdivision surface for smooth cube
bpy.ops.object.modifier_add(type='SUBSURF')
bpy.context.object.modifiers["Subdivision"].levels = 2
bpy.context.object.modifiers["Subdivision"].render_levels = 3

mat = bpy.data.materials.new(name="Cube_Mat")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.2, 0.4, 0.8, 1.0)
obj.data.materials.append(mat)
print("TOM Cube created")
'''

    def _sphere_script(self) -> str:
        return '''import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_uv_sphere_add(radius=1.5, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "TOM_Sphere"
bpy.ops.object.shade_smooth()

mat = bpy.data.materials.new(name="Sphere_Mat")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.1, 0.8, 0.3, 1.0)
mat.node_tree.nodes["Principled BSDF"].inputs[4].default_value = 0.7
obj.data.materials.append(mat)
print("TOM Sphere created")
'''

    def _cylinder_script(self) -> str:
        return '''import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=2, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "TOM_Cylinder"
bpy.ops.object.shade_smooth()
print("TOM Cylinder created")
'''

    def _torus_script(self) -> str:
        return '''import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_torus_add(major_radius=1.5, minor_radius=0.5, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "TOM_Torus"
bpy.ops.object.shade_smooth()

mat = bpy.data.materials.new(name="Torus_Mat")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.9, 0.3, 0.1, 1.0)
mat.node_tree.nodes["Principled BSDF"].inputs[4].default_value = 0.3
obj.data.materials.append(mat)
print("TOM Torus created")
'''

    def _terrain_script(self) -> str:
        return '''import bpy
import random
import math
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_grid_add(size=20, subdivisions=50, location=(0, 0, -1))
terrain = bpy.context.active_object
terrain.name = "TOM_Terrain"

bpy.ops.object.modifier_add(type='DISPLACE')
tex = bpy.data.textures.new(name="TerrainTex", type='CLOUDS')
tex.noise_scale = 2.0
tex.noise_depth = 6
bpy.context.object.modifiers["Displace"].texture = tex
bpy.context.object.modifiers["Displace"].strength = 1.5
bpy.ops.object.modifier_apply(modifier="Displace")
bpy.ops.object.shade_smooth()

mat = bpy.data.materials.new(name="Terrain_Mat")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.3, 0.6, 0.2, 1.0)
terrain.data.materials.append(mat)
print("TOM Terrain generated")
'''

    def _light_setup_script(self) -> str:
        return '''import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 3-point lighting setup
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "TOM_Subject"

# Key light
bpy.ops.object.light_add(type='AREA', location=(5, -3, 6))
key = bpy.context.active_object
key.data.energy = 800
key.data.color = (1.0, 0.95, 0.85)

# Fill light
bpy.ops.object.light_add(type='AREA', location=(-4, 2, 3))
fill = bpy.context.active_object
fill.data.energy = 300
fill.data.color = (0.8, 0.85, 1.0)

# Back light
bpy.ops.object.light_add(type='AREA', location=(0, 4, 4))
back = bpy.context.active_object
back.data.energy = 200
back.data.color = (1.0, 1.0, 1.0)

# Set up viewport
bpy.context.scene.render.engine = 'CYCLES'
print("TOM 3-point lighting setup complete")
'''

    def _material_script(self) -> str:
        return '''import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_uv_sphere_add(radius=1.5, location=(0, 0, 0))
obj = bpy.context.active_object

mat = bpy.data.materials.new(name="Procedural_Mat")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

output = nodes.new(type='ShaderNodeOutputMaterial')
principled = nodes.new(type='ShaderNodeBsdfPrincipled')
noise = nodes.new(type='ShaderNodeTexNoise')
color_ramp = nodes.new(type='ShaderNodeValToRGB')
bump = nodes.new(type='ShaderNodeBump')

noise.inputs[2].default_value = 5.0
color_ramp.color_ramp.elements[0].color = (0.1, 0.2, 0.6, 1.0)
color_ramp.color_ramp.elements[1].color = (0.8, 0.2, 0.1, 1.0)
bump.inputs[0].default_value = 0.3

links.new(noise.outputs[1], color_ramp.inputs[0])
links.new(color_ramp.outputs[0], principled.inputs[0])
links.new(noise.outputs[0], bump.inputs[2])
links.new(bump.outputs[0], principled.inputs[19])
links.new(principled.outputs[0], output.inputs[0])

obj.data.materials.append(mat)
obj.name = "TOM_ProceduralSphere"
bpy.ops.object.shade_smooth()
print("TOM procedural material created")
'''

    def _animation_script(self) -> str:
        return '''import bpy
import math
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "TOM_AnimatedSphere"

# Keyframe animation: bounce + rotate
frames = 60
for i in range(frames):
    t = i / frames * 2 * math.pi
    obj.location.x = 4 * math.sin(t)
    obj.location.z = 2 * abs(math.sin(t * 2))
    obj.rotation_euler.z = t * 2
    obj.keyframe_insert(data_path="location", frame=i)
    obj.keyframe_insert(data_path="rotation_euler", frame=i)

bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = frames
bpy.context.scene.render.fps = 30
print("TOM animation keyframes created")
'''

    def _array_script(self) -> str:
        return '''import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "TOM_Base"

for x in range(5):
    for y in range(5):
        for z in range(3):
            if x == 0 and y == 0 and z == 0:
                continue
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.ops.object.duplicate(linked=False)
            dup = bpy.context.active_object
            dup.location = (x * 1.2, y * 1.2, z * 1.2)
print("TOM array pattern created")
'''

    def _subdivision_script(self) -> str:
        return '''import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "TOM_Subdivided"

bpy.ops.object.modifier_add(type='SUBSURF')
bpy.context.object.modifiers["Subdivision"].levels = 3
bpy.context.object.modifiers["Subdivision"].render_levels = 4
bpy.ops.object.shade_smooth()

mat = bpy.data.materials.new(name="Smooth_Mat")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.2, 0.2, 0.2, 1.0)
mat.node_tree.nodes["Principled BSDF"].inputs[4].default_value = 0.8
obj.data.materials.append(mat)
print("TOM subdivision surface created")
'''

    def _curve_script(self) -> str:
        return '''import bpy
import math
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.curve.primitive_bezier_curve_add()
curve = bpy.context.active_object
curve.name = "TOM_Curve"
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.curve.select_all(action='SELECT')
bpy.ops.curve.delete(type='VERT')
bpy.ops.object.mode_set(mode='OBJECT')

import mathutils
spline = curve.data.splines.new('BEZIER')
spline.bezier_points.add(4)
for i, (x, y) in enumerate([(0, 0), (3, 2), (6, -1), (9, 3), (12, 0)]):
    p = spline.bezier_points[i]
    p.co = mathutils.Vector((x, y, 0))
    p.handle_right_type = 'AUTO'
    p.handle_left_type = 'AUTO'

# Add a sphere following the curve
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(0, 0, 0))
obj = bpy.context.active_object
mod = obj.modifiers.new(name="CurveFollow", type='CURVE')
mod.object = curve
mod.deform_axis = 'POS_X'

print("TOM curve path created")
'''

    def _text_script(self) -> str:
        return '''import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.object.text_add(location=(0, 0, 0))
text = bpy.context.active_object
text.name = "TOM_Text"
text.data.body = "TOM"
text.data.size = 2.5
text.data.extrude = 0.2
text.data.bevel_depth = 0.05
text.data.align_x = 'CENTER'

mat = bpy.data.materials.new(name="Text_Mat")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.9, 0.6, 0.1, 1.0)
mat.node_tree.nodes["Principled BSDF"].inputs[4].default_value = 0.5
text.data.materials.append(mat)
print("TOM 3D text created")
'''

    def _rigging_script(self) -> str:
        return '''import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create a simple armature
bpy.ops.object.armature_add(location=(0, 0, 0))
armature = bpy.context.active_object
armature.name = "TOM_Armature"

bpy.ops.object.mode_set(mode='EDIT')
# Add bones
for y in range(5):
    bpy.ops.armature.bone_primitive_add()
    bone = armature.data.edit_bones[-1]
    bone.head = (0, y * 0.4, 0)
    bone.tail = (0, (y + 1) * 0.4, 0)
    bone.name = f"Bone_{y}"

bpy.ops.object.mode_set(mode='OBJECT')
print("TOM armature rig created")
'''

    def _render_script(self) -> str:
        return '''import bpy
import os

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Scene setup
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.5, location=(0, 0, 0.5))
bpy.ops.object.shade_smooth()
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))

# Camera
bpy.ops.object.camera_add(location=(5, -5, 4))
cam = bpy.context.active_object
cam.rotation_euler = (1.1, 0, 0.8)
bpy.context.scene.camera = cam

# Lighting
bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
bpy.context.active_object.data.energy = 3

# Render settings
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.filepath = os.path.join(os.path.expanduser("~"), "Desktop", "TOM_Render.png")
bpy.context.scene.render.image_settings.file_format = 'PNG'

bpy.ops.render.render(write_still=True)
print(f"Render saved to {{bpy.context.scene.render.filepath}}")
'''

    def _house_script(self) -> str:
        return '''import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Walls
bpy.ops.mesh.primitive_cube_add(size=4, location=(0, 0, 1.5))
walls = bpy.context.active_object
walls.scale = (2, 1.5, 0.75)
bpy.ops.object.transform_apply(scale=True)
walls.name = "TOM_House"

# Roof
bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=3, depth=1.5, location=(0, 0, 3))
roof = bpy.context.active_object
roof.rotation_euler.x = 0
roof.name = "TOM_Roof"
mat_roof = bpy.data.materials.new(name="Roof_Mat")
mat_roof.use_nodes = True
mat_roof.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.6, 0.2, 0.1, 1.0)
roof.data.materials.append(mat_roof)

# Ground
bpy.ops.mesh.primitive_plane_add(size=15, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "TOM_Ground"
mat_ground = bpy.data.materials.new(name="Ground_Mat")
mat_ground.use_nodes = True
mat_ground.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.2, 0.5, 0.1, 1.0)
ground.data.materials.append(mat_ground)

# Door
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(1.5, -0.1, 0.5))
door = bpy.context.active_object
door.scale = (0.3, 0.1, 0.8)
bpy.ops.object.transform_apply(scale=True)
door.name = "TOM_Door"
print("TOM house model created")
'''

    def execute_script(self, script: str, background: bool = True) -> Dict[str, Any]:
        if not self.blender_path and not self._has_bpy:
            return {"status": "error", "message": "Blender not found. Install Blender or run in direct mode."}

        script_path = project_path_str("tom_brain", "_blender_script.py")
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        with open(script_path, "w") as f:
            f.write(script)

        if self._has_bpy:
            try:
                exec(script, {"__name__": "__tom_blender__"})
                return {"status": "success", "mode": "direct", "message": "Script executed in-process"}
            except Exception as e:
                return {"status": "error", "mode": "direct", "message": str(e)}

        if background:
            try:
                subprocess.Popen(
                    [self.blender_path, "--background", "--python", script_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return {"status": "success", "mode": "background", "message": f"Blender launched with script"}
            except Exception as e:
                return {"status": "error", "mode": "background", "message": str(e)}
        else:
            try:
                subprocess.run([self.blender_path, "--python", script_path], timeout=30)
                return {"status": "success", "mode": "foreground", "message": "Blender script completed"}
            except Exception as e:
                return {"status": "error", "mode": "foreground", "message": str(e)}

    def generate_and_execute(self, task: str) -> Dict[str, Any]:
        script = self.generate_script(task)
        result = self.execute_script(script)
        if result["status"] == "success":
            result["script_preview"] = script[:500]
        return result

    def list_capabilities(self) -> Dict[str, str]:
        return {
            "cube": "Create a smooth shaded cube with subdivision",
            "sphere": "Create a glossy UV sphere",
            "cylinder": "Create a smooth cylinder",
            "torus": "Create a torus/donut with material",
            "terrain": "Generate procedural terrain with displacement",
            "lights": "Set up 3-point lighting with area lights",
            "material": "Create procedural noise-based material",
            "animation": "Create bouncing sphere animation",
            "array": "Create XYZ grid array pattern",
            "subdivision": "Create high-detail subdivision sphere",
            "curve": "Create bezier curve path",
            "text": "Create 3D text object",
            "rig": "Create armature skeleton rig",
            "render": "Full scene setup and Cycles render",
            "house": "Build a simple house model",
        }
