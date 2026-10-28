"""
TOM Blender Control — Automates Blender 3D modeling via Python API.
Generates and executes Blender Python scripts for 3D creation.
"""
import os
import re
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
        configured = (os.environ.get("BLENDER_PATH") or "").strip().strip('"')
        if configured and os.path.isfile(configured):
            return configured
        # Any installed version, newest first (the fixed 3.5–4.3 list missed newer releases).
        import glob
        found = sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe"),
                       key=lambda p: [int(x) for x in re.findall(r"\d+", os.path.basename(os.path.dirname(p)))],
                       reverse=True)
        if found:
            return found[0]
        try:
            kwargs = {"capture_output": True, "text": True, "timeout": 5}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(["where", "blender"], **kwargs)
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
        # The subject wins over modifiers: "a low-poly house with lights" is a house (with lights), not a
        # lighting demo on a cube (live check 2026-10-27).
        if re.search(r"\b(house|home|building|cottage|cabin|hut)\b", task_lower):
            code = self._house_script() if re.search(r"\blights?|lit|glow|lamp|night|evening\b", task_lower) \
                else self._house_base()
        elif "cube" in task_lower:
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
        return self._house_base() + _HOUSE_LIGHTS

    def _house_base(self) -> str:
        return '''import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def mat(name, rgb, rough=0.8):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    return m


def box(name, size, loc, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    o.name = name
    o.data.materials.append(material)
    return o


# Walls (6 x 4 x 3 m), standing on the ground
walls = box("TOM_House", (6, 4, 3), (0, 0, 1.5), mat("Walls", (0.85, 0.75, 0.6)))

# Gable roof with a 0.4 m overhang
ov, ridge = 0.4, 4.7
verts = [(-3 - ov, -2 - ov, 3), (3 + ov, -2 - ov, 3), (3 + ov, 2 + ov, 3), (-3 - ov, 2 + ov, 3),
         (-3 - ov, 0, ridge), (3 + ov, 0, ridge)]
faces = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
mesh = bpy.data.meshes.new("TOM_RoofMesh")
mesh.from_pydata(verts, [], faces)
mesh.update()
roof = bpy.data.objects.new("TOM_Roof", mesh)
bpy.context.collection.objects.link(roof)
roof.data.materials.append(mat("Roof", (0.55, 0.18, 0.1), 0.6))

# Door, windows (on the front face, y = -2), chimney
wood = mat("Door", (0.3, 0.17, 0.08))
box("TOM_Door", (0.9, 0.1, 1.9), (0.9, -2.03, 0.95), wood)
frame = mat("WindowFrame", (0.95, 0.95, 0.92))
for i, x in enumerate((-1.6, 2.3)):
    box(f"TOM_WindowFrame_{i + 1}", (1.0, 0.06, 0.9), (x, -2.02, 1.8), frame)
box("TOM_Chimney", (0.5, 0.5, 1.4), (-1.8, 0.9, 4.3), mat("Brick", (0.45, 0.2, 0.15)))

# Ground, a stone path to the door, low-poly trees
bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "TOM_Ground"
ground.data.materials.append(mat("Grass", (0.18, 0.42, 0.12)))
box("TOM_Path", (1.0, 4.0, 0.02), (0.9, -4.0, 0.01), mat("Stone", (0.55, 0.55, 0.52)))
leaves, bark = mat("Leaves", (0.12, 0.38, 0.14)), mat("Bark", (0.28, 0.17, 0.08))
for i, (x, y) in enumerate(((-5.5, -2.5), (5.8, 1.5), (-4.8, 3.5))):
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.18, depth=1.2, location=(x, y, 0.6))
    bpy.context.active_object.data.materials.append(bark)
    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=1.1, depth=2.6, location=(x, y, 2.4))
    tree = bpy.context.active_object
    tree.name = f"TOM_Tree_{i + 1}"
    tree.data.materials.append(leaves)
print("TOM house model created")
'''

    def execute_script(self, script: str, background: bool = True, timeout: int = 120) -> Dict[str, Any]:
        if not self.blender_path and not self._has_bpy:
            return {"status": "error", "message": "Blender not found. Install Blender or run in direct mode."}

        script_path = project_path_str("tom_brain", "_blender_script.py")
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        with open(script_path, "w") as f:
            f.write(script)

        if self._has_bpy and not self.blender_path:
            # In-process exec() is blocked (tool-permissions.md §2): a script runs only inside a
            # separate Blender process, never inside TOM itself.
            from tom_core.policy.engine import ActionClass
            from tom_core.tools.guard import enforce
            gate = enforce("blender.exec_in_process", ActionClass.BLOCKED, payload={"script": script_path})
            return {**gate.refusal(), "mode": "direct"}

        # NOTE: this used to fire-and-forget with subprocess.Popen() and report
        # "success" the instant the process merely *launched* -- never waiting
        # for Blender to finish, never checking its exit code, with stdout/
        # stderr both discarded to DEVNULL. Combined with none of the script
        # templates saving/exporting anything, every "Blender create a house"
        # style request reported success while producing zero files on disk.
        # subprocess.run(..., timeout=...) always waits and captures output,
        # whether or not the caller asked for "background" (Blender itself
        # still runs headless via --background either way).
        # --factory-startup: the owner's own add-ons must not break TOM's job (live check 2026-10-27: the
        # blender_mcp add-on crashed while unregistering at exit, Blender returned 1, and every scene was
        # reported as failed although it had been saved).
        cmd = [self.blender_path, "--factory-startup", "--background", "--python", script_path] if background \
            else [self.blender_path, "--factory-startup", "--python", script_path]
        mode = "background" if background else "foreground"
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"status": "error", "mode": mode,
                    "message": f"Blender did not finish within {timeout}s (script may still be rendering)."}
        except Exception as e:
            return {"status": "error", "mode": mode, "message": str(e)}
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip()[-800:]
            return {"status": "error", "mode": mode,
                    "message": f"Blender exited with code {proc.returncode}: {tail}"}
        return {"status": "success", "mode": mode, "message": "Blender script completed",
                "stdout_tail": (proc.stdout or "").strip()[-500:]}

    def generate_and_execute(self, task: str) -> Dict[str, Any]:
        import re as _re
        import uuid as _uuid
        # A plain int(time.time()) here collided when two requests landed in
        # the same second: the second run's "no file produced" case then read
        # the first run's leftover file at the same path and falsely reported
        # success. uuid4 guarantees a fresh directory every call.
        slug = _re.sub(r"[^a-z0-9]+", "_", task.lower()).strip("_")[:40] or "scene"
        out_dir = project_path_str("tom_brain", "blender_output", f"{slug}_{_uuid.uuid4().hex[:8]}")
        script = self.generate_script(task)
        return self._run_scene(script, out_dir)

    def _run_scene(self, script: str, out_dir: str) -> Dict[str, Any]:
        finalized, blend_path, png_path = self._finalize_script(script, out_dir)
        result = self.execute_script(finalized)
        if result["status"] != "success" and os.path.isfile(blend_path) and "code" in result.get("message", ""):
            # Blender saved the scene, then failed while shutting down: the work is there.
            result.update(status="success", note=result.get("message", "")[:300])
        if result["status"] == "success":
            result["script_preview"] = script[:500]
            # Don't just trust Blender's exit code: confirm the scene actually
            # landed on disk before calling this a success.
            if os.path.isfile(blend_path):
                result["path"] = blend_path
                result["paths"] = [blend_path] + ([png_path] if os.path.isfile(png_path) else [])
                result["message"] = f"Blender scene saved to {blend_path}"
            else:
                result["status"] = "error"
                result["message"] = (
                    "Blender ran without error but no .blend file was found afterward "
                    f"(expected {blend_path}). {result.get('stdout_tail', '')}"[:800])
        return result

    def assemble_scene(self, asset_mains, hdri_path: str = "", task: str = "asset scene") -> Dict[str, Any]:
        """Import downloaded glTF models (asset_mains: list of .gltf/.glb paths), optionally light the
        world with an HDRI, frame a camera, then save + preview-render and verify the file landed."""
        import re as _re
        import uuid as _uuid
        slug = _re.sub(r"[^a-z0-9]+", "_", (task or "scene").lower()).strip("_")[:40] or "scene"
        out_dir = project_path_str("tom_brain", "blender_output", f"{slug}_{_uuid.uuid4().hex[:8]}")
        mains = [p.replace("\\", "/") for p in (asset_mains or []) if p]
        if not mains and not hdri_path:
            return {"status": "error", "message": "No assets to assemble."}
        lines = [
            "import bpy, math",
            "bpy.ops.wm.read_factory_settings(use_empty=True)",
            "imported = []",
        ]
        for p in mains:
            ext = os.path.splitext(p)[1].lower()
            op = "import_scene.gltf" if ext in (".gltf", ".glb") else (
                "import_scene.fbx" if ext == ".fbx" else "import_scene.obj" if ext == ".obj" else "")
            if not op:
                continue
            lines += [
                "try:",
                f"    before = set(bpy.data.objects)",
                f"    bpy.ops.{op}(filepath={p!r})",
                f"    imported += [o for o in bpy.data.objects if o not in before]",
                "except Exception as _e:",
                f"    print('TOM import failed for {os.path.basename(p)}:', _e)",
            ]
        # spread multiple models out along X so they don't overlap at the origin
        lines += [
            "roots = [o for o in imported if o.parent is None]",
            "for i, o in enumerate(roots):",
            "    o.location.x += (i - (len(roots)-1)/2.0) * 2.5",
        ]
        if hdri_path:
            h = hdri_path.replace("\\", "/")
            lines += [
                "world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')",
                "bpy.context.scene.world = world",
                "world.use_nodes = True",
                "nt = world.node_tree; nt.nodes.clear()",
                "bg = nt.nodes.new('ShaderNodeBackground')",
                "env = nt.nodes.new('ShaderNodeTexEnvironment')",
                f"env.image = bpy.data.images.load({h!r})",
                "out = nt.nodes.new('ShaderNodeOutputWorld')",
                "nt.links.new(env.outputs['Color'], bg.inputs['Color'])",
                "nt.links.new(bg.outputs['Background'], out.inputs['Surface'])",
            ]
        else:
            lines += [
                "light_data = bpy.data.lights.new('key', 'SUN'); light_data.energy = 3.0",
                "light = bpy.data.objects.new('key', light_data); bpy.context.collection.objects.link(light)",
                "light.rotation_euler = (math.radians(55), 0, math.radians(45))",
            ]
        # frame a camera on everything imported
        lines += [
            "cam_data = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_data)",
            "bpy.context.collection.objects.link(cam); bpy.context.scene.camera = cam",
            "cam.location = (6, -6, 4); cam.rotation_euler = (math.radians(63), 0, math.radians(46))",
            "bpy.context.scene.render.engine = 'CYCLES' if 'CYCLES' in "
            "[e.identifier for e in bpy.types.RenderEngine.__subclasses__() if hasattr(e,'identifier')] else "
            "bpy.context.scene.render.engine",
        ]
        return self._run_scene("\n".join(lines), out_dir)

    def _finalize_script(self, script: str, out_dir: str):
        """Append a save (+ preview render, unless the template already
        renders one) so a generated scene leaves a real file behind instead
        of vanishing when Blender's headless process exits."""
        os.makedirs(out_dir, exist_ok=True)
        blend_path = os.path.join(out_dir, "scene.blend").replace("\\", "/")
        already_renders = "render.render(" in script
        png_path = (os.path.join(os.path.expanduser("~"), "Desktop", "TOM_Render.png").replace("\\", "/")
                    if already_renders else os.path.join(out_dir, "preview.png").replace("\\", "/"))
        lines = [script.rstrip(), "", _STAGE, "", f"bpy.ops.wm.save_as_mainfile(filepath={blend_path!r})"]
        if not already_renders:
            lines += [
                "bpy.context.scene.render.resolution_percentage = 50",
                f"bpy.context.scene.render.filepath = {png_path!r}",
                "try:",
                "    bpy.ops.render.render(write_still=True)",
                "except Exception as _tom_render_exc:",
                "    print('TOM preview render skipped:', _tom_render_exc)",
            ]
        return "\n".join(lines), blend_path, png_path

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


# Appended to every generated scene: a camera that frames all objects and a key light when the template
# made none — without them the preview render was empty (live check 2026-10-27).
_STAGE = '''
import mathutils as _tom_mu
_tom_scene = bpy.context.scene
_tom_meshes = [o for o in _tom_scene.objects if o.type == "MESH"]
if _tom_meshes:
    _tom_pts = [o.matrix_world @ _tom_mu.Vector(c) for o in _tom_meshes for c in o.bound_box]
    _tom_lo = _tom_mu.Vector([min(p[i] for p in _tom_pts) for i in range(3)])
    _tom_hi = _tom_mu.Vector([max(p[i] for p in _tom_pts) for i in range(3)])
    _tom_center = (_tom_lo + _tom_hi) / 2
    _tom_size = max((_tom_hi - _tom_lo).length, 1.0)
else:
    _tom_center, _tom_size = _tom_mu.Vector((0, 0, 0)), 4.0
if not any(o.type == "CAMERA" for o in _tom_scene.objects):
    bpy.ops.object.empty_add(location=_tom_center)
    _tom_target = bpy.context.active_object
    _tom_target.name = "TOM_CameraTarget"
    bpy.ops.object.camera_add(location=_tom_center + _tom_mu.Vector((0.9, -1.1, 0.6)) * _tom_size)
    _tom_cam = bpy.context.active_object
    _tom_track = _tom_cam.constraints.new(type="TRACK_TO")
    _tom_track.target = _tom_target
    _tom_track.track_axis = "TRACK_NEGATIVE_Z"
    _tom_track.up_axis = "UP_Y"
    _tom_scene.camera = _tom_cam
if not any(o.type == "LIGHT" for o in _tom_scene.objects):
    bpy.ops.object.light_add(type="SUN", location=_tom_center + _tom_mu.Vector((4, -4, 8)))
    bpy.context.active_object.rotation_euler = (0.9, 0.15, 0.5)   # from the front-left, so walls are lit too
    bpy.context.active_object.data.energy = 3.0
if _tom_scene.world is None:
    _tom_scene.world = bpy.data.worlds.new("TOM_World")
    _tom_scene.world.color = (0.35, 0.45, 0.6)
'''

# "with lights": a warm lamp over the door, glowing windows, and a soft evening sun.
_HOUSE_LIGHTS = '''
_glow = bpy.data.materials.new(name="Window_Glow")
_glow.use_nodes = True
_bsdf = _glow.node_tree.nodes["Principled BSDF"]
_bsdf.inputs["Base Color"].default_value = (1.0, 0.75, 0.4, 1.0)
for _name in ("Emission Color", "Emission"):
    if _name in _bsdf.inputs:
        _bsdf.inputs[_name].default_value = (1.0, 0.7, 0.35, 1.0)
if "Emission Strength" in _bsdf.inputs:
    _bsdf.inputs["Emission Strength"].default_value = 6.0
for _i, _x in enumerate((-1.6, 2.3)):                  # glowing panes just in front of the window frames
    bpy.ops.mesh.primitive_cube_add(size=1, location=(_x, -2.06, 1.8))
    _win = bpy.context.active_object
    _win.scale = (0.8, 0.02, 0.7)
    bpy.ops.object.transform_apply(scale=True)
    _win.name = f"TOM_Window_{_i + 1}"
    _win.data.materials.append(_glow)
bpy.ops.object.light_add(type="POINT", location=(0.9, -2.7, 2.3))
_lamp = bpy.context.active_object
_lamp.name = "TOM_PorchLight"
_lamp.data.energy = 250
_lamp.data.color = (1.0, 0.8, 0.5)
for _i, _x in enumerate((-1.6, 2.3)):                  # window light spilling onto the lawn
    bpy.ops.object.light_add(type="AREA", location=(_x, -2.4, 1.8))
    _spill = bpy.context.active_object
    _spill.name = f"TOM_WindowSpill_{_i + 1}"
    _spill.rotation_euler = (1.5708, 0, 0)
    _spill.data.energy = 120
    _spill.data.color = (1.0, 0.7, 0.4)
bpy.ops.object.light_add(type="SUN", location=(6, -6, 8))
_sun = bpy.context.active_object
_sun.name = "TOM_EveningSun"
_sun.rotation_euler = (1.1, 0.2, 0.8)
_sun.data.energy = 1.2
_sun.data.color = (1.0, 0.6, 0.4)
bpy.context.scene.world = bpy.context.scene.world or bpy.data.worlds.new("TOM_World")
bpy.context.scene.world.color = (0.02, 0.03, 0.08)     # dusk sky so the lights read
print("TOM house lights added")
'''
