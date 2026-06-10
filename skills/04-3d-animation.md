# 3D Animation — Comprehensive Skill Guide

> **Knowledge Base Reference:** Load these files for deeper domain coverage:
> - `knowledge/blender_cgi/sculpting_texturing_rigging.json` — ZBrush sculpting workflow (DynaMesh, Subdivision), PBR texturing (Substance Painter/Designer), character rigging (Rigify, IK/FK systems, facial shape keys, corrective blendshapes)
> - `knowledge/blender_cgi/animation_vfx_simulation.json` — 12 Principles of Animation applied in 3D, body mechanics, VFX (Niagara, Houdini), physics simulation (cloth, hair, rigid/soft body), motion capture retargeting
> - `knowledge/blender_cgi/rendering_mocap_production.json` — Cycles/Eevee settings, 3-point lighting, compositing/VFX workflow (keying, tracking), AI 3D creation tools, USD/OpenUSD pipeline, industry production pipelines
> - `knowledge/blender_cgi/blender_complete.json` — Complete Blender reference: modeling, modifiers, materials, rendering, animation, simulation
> - `knowledge/blender_cgi/industry_software.json` — Maya, 3ds Max, Houdini, Substance Painter/Designer, ZBrush, Marvelous Designer, Nuke

## Table of Contents
1. Three.js Fundamentals
2. WebGL Basics
3. GLSL Shader Programming
4. 3D Model Formats (glTF, OBJ, FBX)
5. Animation Rigging
6. Skeletal Animation
7. Particle Systems
8. Post-Processing Effects
9. CSS 3D Transforms
10. Perspective Tricks
11. Canvas 3D Rendering
12. GSAP 3D Plugin
13. 3D Scene Optimization
14. LOD (Level of Detail)
15. Frustum Culling

---

## 1. Three.js Fundamentals

### Scene Setup

```javascript
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// Core components
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a2e);
scene.fog = new THREE.Fog(0x1a1a2e, 10, 50);

const camera = new THREE.PerspectiveCamera(
  75,                                    // FOV
  window.innerWidth / window.innerHeight, // Aspect ratio
  0.1,                                   // Near plane
  1000                                   // Far plane
);
camera.position.set(5, 5, 10);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({
  antialias: true,
  alpha: true,
});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
document.body.appendChild(renderer.domElement);

// Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.autoRotate = true;
controls.autoRotateSpeed = 2.0;

// Resize handler
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// Animation loop
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();
```

### Materials & Geometry

```javascript
// Basic geometries
const box = new THREE.BoxGeometry(1, 1, 1);
const sphere = new THREE.SphereGeometry(1, 32, 32);
const cylinder = new THREE.CylinderGeometry(1, 1, 2, 32);
const torus = new THREE.TorusGeometry(1, 0.4, 16, 100);
const plane = new THREE.PlaneGeometry(10, 10);
const ring = new THREE.RingGeometry(0.5, 1, 32);
const cone = new THREE.ConeGeometry(1, 2, 32);

// Materials
const basic = new THREE.MeshBasicMaterial({ color: 0x44aa88, wireframe: false });
const standard = new THREE.MeshStandardMaterial({
  color: 0x2563eb,
  roughness: 0.4,
  metalness: 0.6,
  emissive: 0x112244,
  emissiveIntensity: 0.2,
});
const physical = new THREE.MeshPhysicalMaterial({
  color: 0x2563eb,
  roughness: 0.1,
  metalness: 0.9,
  clearcoat: 0.3,
  clearcoatRoughness: 0.25,
  envMap: environmentMap,
  envMapIntensity: 1.0,
});
const matcap = new THREE.MeshMatcapMaterial({ matcap: matcapTexture });
const toon = new THREE.MeshToonMaterial({ color: 0x2563eb });

// Mesh = Geometry + Material
const mesh = new THREE.Mesh(sphere, standard);
mesh.position.set(0, 1, 0);
mesh.scale.set(1, 1, 1);
mesh.rotation.x = Math.PI / 4;
scene.add(mesh);
```

### Lighting

```javascript
// Ambient light (base illumination)
const ambient = new THREE.AmbientLight(0x404060, 0.5);
scene.add(ambient);

// Directional light (sun)
const sun = new THREE.DirectionalLight(0xffffff, 1.5);
sun.position.set(10, 20, 5);
sun.castShadow = true;
sun.shadow.mapSize.width = 2048;
sun.shadow.mapSize.height = 2048;
sun.shadow.camera.near = 0.5;
sun.shadow.camera.far = 50;
sun.shadow.camera.left = -10;
sun.shadow.camera.right = 10;
sun.shadow.camera.top = 10;
sun.shadow.camera.bottom = -10;
scene.add(sun);

// Point light (bulb)
const point = new THREE.PointLight(0xff4400, 1, 10);
point.position.set(2, 3, 4);
scene.add(point);

// Spot light
const spot = new THREE.SpotLight(0xffffff, 1);
spot.position.set(0, 5, 0);
spot.target.position.set(0, 0, 0);
spot.angle = Math.PI / 6;
spot.penumbra = 0.5;
spot.decay = 1;
spot.distance = 30;
scene.add(spot);

// Hemisphere light (sky/ground)
const hemi = new THREE.HemisphereLight(0x87ceeb, 0x362907, 0.6);
scene.add(hemi);
```

---

## 2. WebGL Basics

### WebGL Pipeline

```
Vertex Data → Vertex Shader → Primitive Assembly → Rasterization → Fragment Shader → Framebuffer
```

### WebGL2 Context

```javascript
const canvas = document.getElementById('gl-canvas');
const gl = canvas.getContext('webgl2', {
  alpha: false,
  antialias: true,
  preserveDrawingBuffer: false,
});

gl.viewport(0, 0, canvas.width, canvas.height);
gl.clearColor(0.1, 0.1, 0.2, 1.0);
gl.enable(gl.DEPTH_TEST);
gl.enable(gl.BLEND);
gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

function render() {
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  // Draw calls here
  requestAnimationFrame(render);
}
render();
```

---

## 3. GLSL Shader Programming

### Vertex Shader

```glsl
// vertex.glsl
uniform mat4 modelViewMatrix;
uniform mat4 projectionMatrix;
uniform float uTime;

attribute vec3 position;
attribute vec3 normal;
attribute vec2 uv;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vPosition;

void main() {
    vUv = uv;
    vNormal = normalize(normalMatrix * normal);

    // Wave displacement
    vec3 pos = position;
    pos.z += sin(position.x * 2.0 + uTime) * 0.1;
    pos.z += cos(position.y * 2.0 + uTime * 0.8) * 0.1;

    vPosition = (modelViewMatrix * vec4(pos, 1.0)).xyz;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
}
```

### Fragment Shader

```glsl
// fragment.glsl
uniform vec3 uColor;
uniform vec3 uLightPosition;
uniform float uTime;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vPosition;

void main() {
    // Lighting calculation
    vec3 lightDir = normalize(uLightPosition - vPosition);
    float diff = max(dot(vNormal, lightDir), 0.0);

    // Fresnel effect
    vec3 viewDir = normalize(-vPosition);
    float fresnel = pow(1.0 - max(dot(vNormal, viewDir), 0.0), 2.0);

    // Animated pulse
    float pulse = sin(uTime * 2.0) * 0.5 + 0.5;

    vec3 color = uColor * (0.3 + diff * 0.7);
    color += vec3(0.5, 0.8, 1.0) * fresnel * 0.5;
    color += vec3(1.0, 0.3, 0.5) * pulse * 0.1;

    gl_FragColor = vec4(color, 1.0);
}
```

### Three.js ShaderMaterial

```javascript
const material = new THREE.ShaderMaterial({
  vertexShader: vertexShaderSource,
  fragmentShader: fragmentShaderSource,
  uniforms: {
    uTime: { value: 0 },
    uColor: { value: new THREE.Color(0x2563eb) },
    uLightPosition: { value: new THREE.Vector3(5, 10, 5) },
    uTexture: { value: texture },
  },
  transparent: true,
  side: THREE.DoubleSide,
  wireframe: false,
});
```

### Common Shader Effects

```glsl
// Glow effect
float glow = exp(-distance(vUv, vec2(0.5)) * 2.0);
gl_FragColor = vec4(mix(color, glowColor, glow * 0.5), 1.0);

// Dissolve
float noise = texture2D(uNoise, vUv).r;
float cutoff = smoothstep(uProgress - 0.1, uProgress + 0.1, noise);
if (cutoff < 0.5) discard;

// Ripple
float ripple = sin(distance(vUv, vec2(0.5)) * 20.0 - uTime * 3.0) * 0.5 + 0.5;
color += vec3(ripple * 0.1);
```

---

## 4. 3D Model Formats

### glTF (GL Transmission Format) — Preferred

```javascript
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

const loader = new GLTFLoader();
const dracoLoader = new DRACOLoader();
dracoLoader.setDecoderPath('/draco/');
loader.setDRACOLoader(dracoLoader);

loader.load(
  '/models/scene.gltf',  // or .glb (binary)
  (gltf) => {
    const model = gltf.scene;
    scene.add(model);

    // Access animations
    const mixer = new THREE.AnimationMixer(model);
    gltf.animations.forEach((clip) => {
      mixer.clipAction(clip).play();
    });

    // Access materials for customization
    model.traverse((child) => {
      if (child.isMesh) {
        child.material = new THREE.MeshStandardMaterial({
          map: child.material.map,
          roughness: 0.3,
          metalness: 0.7,
        });
      }
    });
  },
  (progress) => console.log(`Loading: ${(progress.loaded / progress.total * 100).toFixed(0)}%`),
  (error) => console.error('Error loading model:', error)
);
```

### OBJ/MTL Loader

```javascript
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js';

const mtlLoader = new MTLLoader();
mtlLoader.load('/models/model.mtl', (materials) => {
  materials.preload();
  const objLoader = new OBJLoader();
  objLoader.setMaterials(materials);
  objLoader.load('/models/model.obj', (object) => {
    scene.add(object);
  });
});
```

### FBX Loader

```javascript
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';

const loader = new FBXLoader();
loader.load('/models/model.fbx', (object) => {
  object.scale.set(0.01, 0.01, 0.01); // FBX often needs scaling
  scene.add(object);
});
```

### Model Optimization Checklist

- [ ] Export as glTF/GLB (not OBJ or FBX for web)
- [ ] Use Draco compression for geometry
- [ ] Use KTX2 for texture compression
- [ ] Limit polygon count (under 100k for web)
- [ ] Bake lighting into vertex colors or lightmaps
- [ ] Merge geometries when possible (BufferGeometryUtils)
- [ ] Remove unused bones, animations, materials

---

## 5. Animation Rigging

### Manual Rigging in Three.js

```javascript
function createArmRig() {
  const group = new THREE.Group();

  // Shoulder
  const shoulder = new THREE.Bone();
  shoulder.position.y = 1.5;

  // Upper arm
  const upperArm = new THREE.Bone();
  upperArm.position.y = -0.3;
  shoulder.add(upperArm);

  // Forearm
  const forearm = new THREE.Bone();
  forearm.position.y = -0.3;
  upperArm.add(forearm);

  // Hand
  const hand = new THREE.Bone();
  hand.position.y = -0.25;
  forearm.add(hand);

  const skeleton = new THREE.Skeleton([shoulder, upperArm, forearm, hand]);

  // Skinned mesh
  const geometry = new THREE.CylinderGeometry(0.1, 0.1, 1, 8);
  const skinIndices = [];
  const skinWeights = [];

  // Map vertices to bones
  for (let i = 0; i < geometry.attributes.position.count; i++) {
    const y = geometry.attributes.position.getY(i);
    skinIndices.push(y > 0 ? 0 : 1, 0, 0, 0);
    skinWeights.push(1, 0, 0, 0);
  }

  geometry.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(skinIndices, 4));
  geometry.setAttribute('skinWeight', new THREE.Float32BufferAttribute(skinWeights, 4));

  const material = new THREE.MeshStandardMaterial({ skinning: true });
  const mesh = new THREE.SkinnedMesh(geometry, material);
  mesh.bind(skeleton);

  return { mesh, skeleton, shoulder, upperArm, forearm, hand };
}
```

---

## 6. Skeletal Animation

```javascript
// AnimationMixer for bone animations
const mixer = new THREE.AnimationMixer(model);

// Keyframe tracks
const track = new THREE.VectorKeyframeTrack(
  '.bones[UpperArm].position',
  [0, 1, 2],                     // times
  [0, 0, 0, 0, -0.5, 0, 0, 0, 0]  // values (x,y,z per keyframe)
);

const clip = new THREE.AnimationClip('wave', 2, [track]);
const action = mixer.clipAction(clip);

action.setLoop(THREE.LoopRepeat);
action.clampWhenFinished = false;
action.timeScale = 1;
action.play();

// Update in animation loop
function animate() {
  const delta = clock.getDelta();
  mixer.update(delta);
  renderer.render(scene, camera);
}
```

---

## 7. Particle Systems

```javascript
// BufferGeometry particles
const particleCount = 10000;
const positions = new Float32Array(particleCount * 3);
const colors = new Float32Array(particleCount * 3);
const sizes = new Float32Array(particleCount);

for (let i = 0; i < particleCount; i++) {
  positions[i * 3] = (Math.random() - 0.5) * 50;
  positions[i * 3 + 1] = (Math.random() - 0.5) * 50;
  positions[i * 3 + 2] = (Math.random() - 0.5) * 50;

  colors[i * 3] = Math.random() * 0.5 + 0.5;
  colors[i * 3 + 1] = Math.random() * 0.5;
  colors[i * 3 + 2] = Math.random() * 0.8 + 0.2;

  sizes[i] = Math.random() * 3 + 1;
}

const geometry = new THREE.BufferGeometry();
geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

const texture = new THREE.CanvasTexture(generateCircleTexture());
const material = new THREE.PointsMaterial({
  size: 0.2,
  map: texture,
  blending: THREE.AdditiveBlending,
  depthWrite: false,
  transparent: true,
  vertexColors: true,
  opacity: 0.8,
});

const particles = new THREE.Points(geometry, material);
scene.add(particles);

// Animate
function animateParticles(time) {
  const positions = particles.geometry.attributes.position.array;
  for (let i = 0; i < particleCount; i++) {
    positions[i * 3 + 1] += Math.sin(time + i) * 0.001;
  }
  particles.geometry.attributes.position.needsUpdate = true;
}

function generateCircleTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 32;
  canvas.height = 32;
  const ctx = canvas.getContext('2d');
  const gradient = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
  gradient.addColorStop(0, 'rgba(255,255,255,1)');
  gradient.addColorStop(0.5, 'rgba(255,255,255,0.5)');
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 32, 32);
  return canvas;
}
```

---

## 8. Post-Processing Effects

```javascript
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { GlitchPass } from 'three/addons/postprocessing/GlitchPass.js';
import { FilmPass } from 'three/addons/postprocessing/FilmPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));

// Bloom
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  0.5,  // strength
  0.4,  // radius
  0.85  // threshold
);
composer.addPass(bloomPass);

// Anti-aliasing
const smaaPass = new SMAAPass(window.innerWidth, window.innerHeight);
composer.addPass(smaaPass);

// Optional effects
// composer.addPass(new GlitchPass());
// composer.addPass(new FilmPass(0.35, 0.025, 648, false));

function animate() {
  requestAnimationFrame(animate);
  composer.render();
}
```

---

## 9. CSS 3D Transforms

```css
/* 3D Card Flip */
.card-container {
  perspective: 1000px;
}

.card {
  width: 200px;
  height: 300px;
  position: relative;
  transform-style: preserve-3d;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.card:hover {
  transform: rotateY(180deg);
}

.card-front, .card-back {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
}

.card-back {
  transform: rotateY(180deg);
}

/* Parallax layers */
.parallax-container {
  perspective: 800px;
  perspective-origin: center;
  overflow-x: hidden;
  overflow-y: auto;
}

.parallax-layer {
  position: absolute;
  inset: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.layer-0 { transform: translateZ(-300px) scale(1.375); }
.layer-1 { transform: translateZ(-200px) scale(1.25); }
.layer-2 { transform: translateZ(-100px) scale(1.125); }
.layer-3 { transform: translateZ(0) scale(1); }
```

### 3D Transform Functions

```css
transform:
  translateX(50px)
  translateY(-100px)
  translateZ(200px)
  rotateX(45deg)
  rotateY(30deg)
  rotateZ(15deg)
  scale3d(1.2, 1.2, 1.2)
  skewX(10deg);

transform-origin: center center -100px;
transform-style: preserve-3d; /* For nested 3D */
```

---

## 10. Perspective Tricks

### Forced Perspective with CSS

```css
/* Create depth illusion without WebGL */
.depth-scene {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
}

.depth-scene img:nth-child(1) {
  transform: scale(0.6) translateY(60px);
  opacity: 0.5;
  z-index: 1;
}

.depth-scene img:nth-child(2) {
  transform: scale(0.8) translateY(30px);
  opacity: 0.75;
  z-index: 2;
}

.depth-scene img:nth-child(3) {
  transform: scale(1);
  z-index: 3;
}
```

### Parallax with Intersection Observer

```javascript
function parallaxScroll(container) {
  const layers = container.querySelectorAll('[data-speed]');

  container.addEventListener('scroll', () => {
    const scrollTop = container.scrollTop;

    layers.forEach(layer => {
      const speed = parseFloat(layer.dataset.speed);
      layer.style.transform = `translateY(${scrollTop * speed}px)`;
    });
  });
}
```

---

## 11. Canvas 3D Rendering

```javascript
// Fake 3D with Canvas 2D
class Canvas3D {
  constructor(canvas) {
    this.ctx = canvas.getContext('2d');
    this.objects = [];
    this.camera = { x: 0, y: 0, z: 500 };
    this.fov = 250;
  }

  project(x, y, z) {
    const scale = this.fov / (this.fov + z + this.camera.z);
    return {
      x: x * scale + this.ctx.canvas.width / 2,
      y: y * scale + this.ctx.canvas.height / 2,
      scale,
    };
  }

  cube(x, y, z, size, color) {
    const vertices = [
      [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
      [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
    ].map(v => ({
      x: x + v[0] * size,
      y: y + v[1] * size,
      z: z + v[2] * size,
    }));

    const projected = vertices.map(v => this.project(v.x, v.y, v.z));
    // Draw faces with projected coordinates
    // ... rendering logic
  }

  render() {
    this.ctx.clearRect(0, 0, this.ctx.canvas.width, this.ctx.canvas.height);
    // Sort by depth, render back-to-front
    this.objects.sort((a, b) => (b.z - a.z));
    this.objects.forEach(obj => {
      // Draw each object
    });
    requestAnimationFrame(() => this.render());
  }
}
```

---

## 12. GSAP 3D Plugin

```javascript
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

// Three.js integration with GSAP
function animateWithGSAP(mesh, camera) {
  const tl = gsap.timeline({
    scrollTrigger: {
      trigger: '.scene-container',
      start: 'top top',
      end: 'bottom top',
      scrub: 1,
    },
  });

  tl.to(mesh.rotation, {
    x: Math.PI * 2,
    y: Math.PI * 2,
    duration: 3,
    ease: 'none',
  });

  tl.to(camera.position, {
    z: 15,
    y: 3,
    duration: 3,
    ease: 'power2.inOut',
  }, 0);

  tl.to(mesh.scale, {
    x: 2,
    y: 2,
    z: 2,
    duration: 1.5,
    ease: 'back.out(2)',
  }, 0.5);
}

// Spring physics for 3D
gsap.to(mesh.position, {
  x: 5,
  duration: 2,
  ease: 'elastic.out(1, 0.3)',
});

gsap.to(mesh.material, {
  opacity: 0.5,
  duration: 1,
  ease: 'power3.out',
});
```

---

## 13. 3D Scene Optimization

### Performance Techniques

```javascript
// Instanced rendering (same geometry, different transforms)
const count = 10000;
const dummy = new THREE.Object3D();
const geometry = new THREE.BoxGeometry(0.1, 0.1, 0.1);
const material = new THREE.MeshStandardMaterial({ color: 0x2563eb });
const instancedMesh = new THREE.InstancedMesh(geometry, material, count);

for (let i = 0; i < count; i++) {
  dummy.position.set(
    (Math.random() - 0.5) * 100,
    (Math.random() - 0.5) * 100,
    (Math.random() - 0.5) * 100,
  );
  dummy.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, 0);
  dummy.scale.setScalar(Math.random() * 2 + 0.5);
  dummy.updateMatrix();
  instancedMesh.setMatrixAt(i, dummy.matrix);
}
instancedMesh.instanceMatrix.needsUpdate = true;

// Merge geometries
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
const mergedGeometry = mergeGeometries([geo1, geo2, geo3]);
const mergedMesh = new THREE.Mesh(mergedGeometry, sharedMaterial);
```

### Rendering Budget

| Target | Desktop | Mobile |
|--------|---------|--------|
| Draw calls | < 200 | < 50 |
| Triangles | < 500k | < 100k |
| Lights | < 8 | < 3 |
| Shadow maps | < 2 | < 1 |
| Particle count | < 50k | < 10k |
| Textures | < 256MB | < 64MB |
| Post-processing | 1-2 passes | None |

---

## 14. LOD (Level of Detail)

```javascript
import { LOD } from 'three';

const lod = new LOD();

const highDetail = createMesh(32, 32);
const midDetail = createMesh(16, 16);
const lowDetail = createMesh(8, 8);
const veryLow = createMesh(4, 4);

lod.addLevel(highDetail, 0);    // Distance 0
lod.addLevel(midDetail, 20);    // Distance 20
lod.addLevel(lowDetail, 50);    // Distance 50
lod.addLevel(veryLow, 100);     // Distance 100

scene.add(lod);

// Update LOD every frame (or with throttling)
function animate() {
  lod.update(camera);
  renderer.render(scene, camera);
}
```

---

## 15. Frustum Culling

```javascript
const frustum = new THREE.Frustum();
const projScreenMatrix = new THREE.Matrix4();

function updateFrustum() {
  projScreenMatrix.multiplyMatrices(
    camera.projectionMatrix,
    camera.matrixWorldInverse
  );
  frustum.setFromProjectionMatrix(projScreenMatrix);
}

function isInView(object) {
  // For bounding sphere culling
  const sphere = new THREE.Sphere();
  object.geometry.computeBoundingSphere();
  sphere.copy(object.geometry.boundingSphere);
  sphere.applyMatrix4(object.matrixWorld);

  return frustum.intersectsSphere(sphere);
}

// Three.js does this automatically for Mesh objects
// For custom culling:
function renderVisibleOnly(objects) {
  updateFrustum();
  objects.forEach(obj => {
    obj.visible = isInView(obj);
  });
}
```

---

## Resources & References

- **Three.js**: threejs.org — Official docs, examples, fundamentals
- **glTF Sample Models**: github.com/KhronosGroup/glTF-Sample-Models
- **Shader Toy**: shadertoy.com — GLSL shader playground
- **Poly Haven**: polyhaven.com — Free HDRI, textures, models
- **Mixamo**: mixamo.com — Character animations
- **Sketchfab**: sketchfab.com — 3D model marketplace
- **GSAP**: greensock.com — ScrollTrigger and animation tools
- **Blender**: blender.org — Free 3D modeling and animation suite
