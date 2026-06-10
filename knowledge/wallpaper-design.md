# Wallpaper Design -- Complete Guide

## Table of Contents

1. [Design Principles](#design-principles)
2. [Resolution Standards](#resolution-standards)
3. [Art Styles](#art-styles)
4. [Tools](#tools)
5. [Techniques](#techniques)
6. [Color Palettes](#color-palettes)
7. [Mobile Best Practices](#mobile-best-practices)
8. [Python Automation](#python-automation)

---

## Design Principles

### Composition

Wallpaper composition follows the same rules as any visual art, with special considerations for the display surface. A wallpaper must work with UI elements (icons, taskbar/dock, clock, widgets) rather than compete with them. The focal point should be offset from center to leave room for icons.

```python
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def analyze_composition(image_path):
    """Analyze a wallpaper's composition"""
    img = Image.open(image_path)
    w, h = img.size
    arr = np.array(img.convert('L'))

    # Calculate focal point (brightest region)
    from scipy.ndimage import center_of_mass
    com = center_of_mass(arr)
    focal_x, focal_y = com[1] / w, com[0] / h

    # Check rule of thirds alignment
    thirds_x = abs(focal_x - 1/3) < 0.05 or abs(focal_x - 2/3) < 0.05
    thirds_y = abs(focal_y - 1/3) < 0.05 or abs(focal_y - 2/3) < 0.05

    # Safe zone for icons (top-left, bottom-right areas)
    safe_zone_brightness = {
        'top_left': np.mean(arr[int(h*0.05):int(h*0.2), int(w*0.05):int(w*0.2)]),
        'bottom_right': np.mean(arr[int(h*0.8):int(h*0.95), int(w*0.8):int(w*0.95)])
    }

    return {
        'focal_point': (focal_x, focal_y),
        'on_thirds': thirds_x or thirds_y,
        'safe_zone_luminance': safe_zone_brightness
    }
```

### Key Principles for Wallpapers

- **Focal Point:** Place where the eye lands first. Offset from center.
- **Focal Area Contrast:** Bright areas draw attention first.
- **Safe Zones:** Top-left and bottom-right should have low detail for icons.
- **Reading Direction:** Western viewers scan left-to-right, top-to-bottom.
- **Depth:** Foreground, midground, background creates immersion.
- **Flow:** Lines and gradients should guide the eye across the image.
- **Balance:** Symmetry OR intentional asymmetry, never accidental imbalance.

---

## Resolution Standards

### Desktop

| Name | Resolution | Aspect | Pixels |
|------|------------|--------|--------|
| HD (720p) | 1280 x 720 | 16:9 | 921,600 |
| FHD (1080p) | 1920 x 1080 | 16:9 | 2,073,600 |
| WUXGA | 1920 x 1200 | 16:10 | 2,304,000 |
| QHD (2K) | 2560 x 1440 | 16:9 | 3,686,400 |
| UW-FHD | 2560 x 1080 | 21:9 | 2,764,800 |
| UW-QHD | 3440 x 1440 | 21:9 | 4,953,600 |
| 4K UHD | 3840 x 2160 | 16:9 | 8,294,400 |
| UW-4K | 5120 x 2160 | 21:9 | 11,059,200 |
| 5K | 5120 x 2880 | 16:9 | 14,745,600 |
| 8K UHD | 7680 x 4320 | 16:9 | 33,177,600 |

### Mobile

| Device | Resolution | Aspect | PPI |
|--------|------------|--------|-----|
| iPhone SE (3rd) | 750 x 1334 | 9:19.5 | 326 |
| iPhone 14/15 | 1179 x 2556 | 9:19.5 | 460 |
| iPhone 14/15 Pro | 1179 x 2556 | 9:19.5 | 460 |
| iPhone 14/15 Pro Max | 1290 x 2796 | 9:19.5 | 460 |
| iPhone 14/15 Plus | 1284 x 2778 | 9:19.5 | 458 |
| Samsung S24 | 1080 x 2340 | 9:19.5 | 425 |
| Samsung S24+ | 1440 x 3120 | 9:19.5 | 513 |
| Samsung S24 Ultra | 1440 x 3120 | 9:19.5 | 505 |
| Google Pixel 8 | 1080 x 2400 | 9:20 | 428 |
| Google Pixel 8 Pro | 1344 x 2992 | 9:20 | 489 |
| iPad Pro 12.9 | 2048 x 2732 | 4:3 | 264 |
| iPad Air | 1640 x 2360 | ~4:3 | 264 |

### Safe Zones for Desktop

```
┌─────────────────────────────────┐
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ <- Menu bar / dock (top)
│ ░░   ░░░░░░░░░░░░░░░░░░░░░░░░  │ <- App icons
│ ░░   ░░░░░░░░░░░░░░░░░░░░░░░░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░ ░░   │ <- Taskbar (bottom, some OS)
└─────────────────────────────────┘
```

### Multi-Monitor Considerations

| Setup | Total Width | Notes |
|-------|-------------|-------|
| Dual 1920x1080 | 3840 x 1080 | Span or duplicate |
| Triple 1920x1080 | 5760 x 1080 | Very wide panorama |
| 2560x1440 + 1920x1080 | 4480 x 1440 | Different heights |
| Dell U4919DW (32:9) | 5120 x 1440 | Super ultrawide |

---

## Art Styles

### Minimalist

Clean, simple, large areas of solid color or subtle gradients. Low cognitive load. Works well as desktop wallpaper because icons remain readable.

**Characteristics:** Monochrome or limited palette (2-3 colors), generous negative space, simple geometric shapes, thin lines, no texture.

```python
def generate_minimalist(w=2560, h=1440, bg=(245, 245, 245), accent=(100, 100, 200)):
    from PIL import Image, ImageDraw
    import math
    img = Image.new('RGB', (w, h), bg)
    draw = ImageDraw.Draw(img)
    # Single large circle offset from center
    cx, cy = w * 0.65, h * 0.4
    r = min(w, h) * 0.35
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=accent, outline=None)
    # Subtle line accent
    draw.line([(0, h*0.7), (w, h*0.7)], fill=(180, 180, 180), width=2)
    return img
```

### Abstract

Non-representational forms, flowing shapes, dynamic compositions. Often uses gradients, blurs, and overlapping translucent elements.

**Characteristics:** Fluid organic shapes, gradient transitions, depth from blur, bright accent colors, asymmetry.

### Geometric

Precise shapes, tessellations, isometric designs, mandalas. Strong structure and order.

**Characteristics:** Sharp angles, repeating patterns, isometric grids, symmetry, polygonal art, wireframes.

### Nature & Landscape

Photos or digital paintings of mountains, forests, oceans, sunsets. Most popular category.

**Characteristics:** Atmospheric perspective, warm/cool color zones, depth layers, silhouettes.

### Space

Stars, galaxies, nebulae, planets. Dark backgrounds with bright celestial objects.

**Characteristics:** Very dark bg (near-black), star fields, glowing nebula gradients, planet rings, aurora effects.

### Cyberpunk

Neon-lit dystopian cityscapes. High contrast, magenta/cyan/blue palette.

**Characteristics:** Dark background, neon glow, grid lines, rain effects, holographic elements, 1980s futurism.

### Vaporwave

Retro 1980s/90s aesthetic. Pastel gradients, glitch effects, Greek busts, CRT scanlines, VHS artifacts.

**Characteristics:** Pastel pink/blue/teal palette, sunsets with strong banding, grid floors, retro typography, glitch/distortion.

### Dark

Deep blacks, subtle textures, minimal highlights. Battery-friendly for OLED screens.

**Characteristics:** True black (#000000) backgrounds, subtle dark gradients, thin accent lines, glow effects on dark backgrounds.

### Gradient

Smooth or sharp color transitions. Can be simple (2-color linear) or complex (multi-stop with noise).

### 3D Rendered

Blender 3D scenes rendered specifically for wallpaper use. Abstract geometry, architectural scenes, surreal environments.

### AI-Generated

Created with Stable Diffusion, Midjourney, DALL-E. Dreamlike, surreal, or hyperrealistic.

### Digital Painting

Hand-painted in Procreate, Photoshop, Clip Studio Paint. Full artistic control.

### Photo Manipulation

Composite photography with blending, masks, color grading, and atmospheric effects.

---

## Tools

### Raster: Photoshop, Krita, GIMP, Affinity Photo, Procreate (iPad)

### Vector: Illustrator, Inkscape, Affinity Designer, CorelDRAW

### 3D: Blender, Cinema 4D, Maya

### AI Generation: Stable Diffusion, Midjourney, DALL-E, Leonardo.ai

### Python Libraries: Pillow, numpy, matplotlib, OpenCV, Stable Diffusion WebUI API

---

## Techniques

### Gradient Mapping

```python
def gradient_map(image_path, color1=(10, 10, 50), color2=(200, 100, 50), color3=(255, 200, 100)):
    """Apply gradient map: map grayscale to color gradient"""
    from PIL import Image
    import numpy as np

    img = Image.open(image_path).convert('L')  # grayscale
    arr = np.array(img, dtype=np.float32) / 255.0

    # Create gradient lookup
    gradient = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        t = i / 255.0
        if t < 0.5:
            u = t * 2
            r = int(color1[0] * (1-u) + color2[0] * u)
            g = int(color1[1] * (1-u) + color2[1] * u)
            b = int(color1[2] * (1-u) + color2[2] * u)
        else:
            u = (t - 0.5) * 2
            r = int(color2[0] * (1-u) + color3[0] * u)
            g = int(color2[1] * (1-u) + color3[1] * u)
            b = int(color2[2] * (1-u) + color3[2] * u)
        gradient[i] = [r, g, b]

    # Apply mapping
    indices = (arr * 255).astype(int)
    result = gradient[indices]
    return Image.fromarray(result)
```

### Duotone

```python
def duotone(image, highlight_color=(255, 100, 50), shadow_color=(20, 10, 40)):
    """Two-color duotone effect"""
    import numpy as np
    from PIL import Image

    img = Image.open(image).convert('L')
    arr = np.array(img, dtype=np.float32) / 255.0

    result = np.zeros((*arr.shape, 3), dtype=np.uint8)
    for c in range(3):
        result[..., c] = (shadow_color[c] * (1 - arr) + highlight_color[c] * arr).astype(np.uint8)

    return Image.fromarray(result)
```

### Glassmorphism

```python
def glassmorphism(w=2560, h=1440):
    """Create glassmorphism-style wallpaper"""
    from PIL import Image, ImageDraw, ImageFilter
    import numpy as np
    import random

    img = Image.new('RGB', (w, h), (25, 25, 40))
    draw = ImageDraw.Draw(img)

    # Background blobs
    colors = [(100, 50, 200), (50, 150, 200), (200, 80, 120)]
    for color in colors:
        cx, cy = random.randint(0, w), random.randint(0, h)
        r = random.randint(200, 500)
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color, outline=None)

    # Blur background
    img = img.filter(ImageFilter.GaussianBlur(80))

    # Glass panel overlay
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    panel_w, panel_h = int(w*0.6), int(h*0.5)
    px, py = (w - panel_w)//2, (h - panel_h)//2
    draw.rounded_rectangle([px, py, px+panel_w, py+panel_h],
                          radius=30, fill=(255, 255, 255, 30))

    # Glass border
    draw.rounded_rectangle([px, py, px+panel_w, py+panel_h],
                          radius=30, outline=(255, 255, 255, 60), width=2)

    return Image.alpha_composite(img.convert('RGBA'), overlay)
```

### Particle Systems

```python
def generate_particle_wallpaper(w=2560, h=1440, num_particles=500):
    """Generate a particle system wallpaper"""
    from PIL import Image, ImageDraw
    import math
    import random

    img = Image.new('RGBA', (w, h), (5, 5, 15, 255))
    draw = ImageDraw.Draw(img)

    particles = []
    for _ in range(num_particles):
        x = random.randint(0, w)
        y = random.randint(0, h)
        vx = random.uniform(-0.3, 0.3)
        vy = random.uniform(-0.3, 0.3)
        r = random.randint(1, 3)
        alpha = random.randint(30, 150)
        particles.append([x, y, vx, vy, r, alpha])

    # Simulate motion and draw trail
    for step in range(100):
        for p in particles:
            p[0] += p[2]
            p[1] += p[3]
            if p[0] < 0 or p[0] > w: p[2] *= -1
            if p[1] < 0 or p[1] > h: p[3] *= -1

        # Draw connections between close particles
        for i in range(len(particles)):
            for j in range(i+1, len(particles)):
                dx = particles[i][0] - particles[j][0]
                dy = particles[i][1] - particles[j][1]
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < 150:
                    alpha = int(50 * (1 - dist/150))
                    draw.line([(particles[i][0], particles[i][1]),
                              (particles[j][0], particles[j][1])],
                             fill=(100, 150, 255, alpha), width=1)

    # Draw particles
    for p in particles:
        draw.ellipse([p[0]-p[4], p[1]-p[4], p[0]+p[4], p[1]+p[4]],
                    fill=(100, 150, 255, p[5]))

    return img
```

### Fractal Generation

```python
def mandelbrot(w=2560, h=1440, max_iter=100):
    """Generate Mandelbrot set wallpaper"""
    import numpy as np
    from PIL import Image

    xmin, xmax = -2.5, 1.5
    ymin, ymax = -1.5, 1.5
    x = np.linspace(xmin, xmax, w)
    y = np.linspace(ymin, ymax, h)
    X, Y = np.meshgrid(x, y)
    C = X + 1j * Y
    Z = np.zeros_like(C)
    div = np.zeros(C.shape, dtype=int)

    for i in range(max_iter):
        mask = np.abs(Z) <= 2
        Z[mask] = Z[mask]**2 + C[mask]
        div[mask] = i

    # Color mapping
    div = (div * 255 // max_iter).astype(np.uint8)
    arr = np.stack([div * 2, div, div // 2, np.full(div.shape, 255)], axis=2)
    return Image.fromarray(arr, 'RGBA')
```

### Typography Layout

```python
def typography_wallpaper(text="DREAM", w=2560, h=1440):
    """Large typography-centered wallpaper"""
    from PIL import Image, ImageDraw, ImageFont
    import math

    img = Image.new('RGB', (w, h), (10, 10, 20))
    draw = ImageDraw.Draw(img)

    # Large text (requires heavy font file)
    font_size = min(w, h) // 5

    # Manual large character rendering as fallback
    scale = 0.6
    ch_w = int(w * 0.85)
    ch_h = int(h * 0.6)
    cx, cy = (w - ch_w) // 2, (h - ch_h) // 2

    # Create gradient overlay
    for y_pos in range(cy, cy + ch_h):
        t = (y_pos - cy) / ch_h
        color = int(100 + 155 * math.sin(t * math.pi))
        draw.line([(cx, y_pos), (cx + ch_w, y_pos)],
                 fill=(color, color // 2, color // 3))

    # Add grid lines
    for x_pos in range(0, w, 100):
        draw.line([(x_pos, 0), (x_pos, h)], fill=(255, 255, 255, 15), width=1)
    for y_pos in range(0, h, 100):
        draw.line([(0, y_pos), (w, y_pos)], fill=(255, 255, 255, 15), width=1)

    return img
```

### Pattern Generation

```python
def seamless_pattern(w=2560, h=1440, tile_size=200):
    """Generate a seamless repeating pattern wallpaper"""
    from PIL import Image, ImageDraw
    import math

    img = Image.new('RGB', (w, h), (245, 245, 245))
    draw = ImageDraw.Draw(img)

    # Draw one tile
    def draw_tile(draw, ox, oy, size, color):
        cx, cy = ox + size//2, oy + size//2
        r = size * 0.3
        for i in range(6):
            angle = i * math.pi / 3
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            draw.ellipse([px-15, py-15, px+15, py+15], fill=color)

    colors = [(50, 100, 150), (200, 80, 60), (240, 200, 80),
              (100, 180, 100), (150, 100, 200)]

    cls = 0
    for x in range(-tile_size, w + tile_size, tile_size):
        for y in range(-tile_size, h + tile_size, tile_size):
            draw_tile(draw, x, y, tile_size, colors[cls % len(colors)])
            cls += 1

    return img
```

### Neon Glow

```python
def neon_glow(w=2560, h=1440):
    """Neon glow effects wallpaper"""
    from PIL import Image, ImageDraw, ImageFilter
    import math

    bg = Image.new('RGBA', (w, h), (5, 5, 15, 255))
    glow_layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer)

    # Draw neon curves
    colors = [(255, 50, 100), (50, 200, 255), (255, 200, 50)]
    points_count = 6

    for ci, color in enumerate(colors):
        cx = w * (0.3 + ci * 0.2)
        cy = h * 0.5
        points = []
        for i in range(points_count):
            angle = i * 2 * math.pi / points_count + ci * 0.5
            px = cx + w * 0.15 * math.cos(angle)
            py = cy + h * 0.2 * math.sin(angle)
            points.append((px, py))

        # Draw curve through points
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            draw.line([(x1, y1), (x2, y2)], fill=(*color, 200), width=4)

    # Apply glow blur
    glow = glow_layer.filter(ImageFilter.GaussianBlur(15))
    glow2 = glow_layer.filter(ImageFilter.GaussianBlur(5))

    result = Image.alpha_composite(bg, glow)
    result = Image.alpha_composite(result, glow2)
    result = Image.alpha_composite(result, glow_layer)
    return result
```

---

## Color Palettes

### Popular Wallpaper Palettes

| Name | Colors | Vibe |
|------|--------|------|
| Ocean | #0a1628, #1a3a5a, #2a7a8a, #4ac0d0, #e0f8ff | Calm, deep |
| Sunset | #1a0a2a, #5a1a4a, #9a3a5a, #d07a4a, #f0c86a | Warm, dramatic |
| Forest | #0a1a0a, #1a3a1a, #2a5a2a, #4a8a3a, #8aca6a | Natural, earthy |
| Neon | #0a0a1a, #1a0a3a, #ff3080, #00ffc0, #ffd000 | Cyberpunk, energetic |
| Monochrome | #0a0a0a, #2a2a2a, #5a5a5a, #8a8a8a, #cacaca | Clean, professional |
| Pastel | #f0e0ff, #ffe0f0, #e0fff0, #fff0e0, #e0f0ff | Soft, calm |
| Desert | #2a1a0a, #4a3a1a, #7a5a2a, #b08a4a, #d0b07a | Warm, earthy |
| Aurora | #0a0a1a, #0a3a2a, #2a7a4a, #8abe6a, #c0f0c0 | Magical, green |

### Color Generation

```python
import colorsys
import random

def generate_palette(base_hue=None, count=5, style='analogous'):
    if base_hue is None:
        base_hue = random.random()

    hues = []
    if style == 'analogous':
        hues = [(base_hue + i * 0.03) % 1.0 for i in range(count)]
    elif style == 'complementary':
        hues = [base_hue, (base_hue + 0.5) % 1.0]
        for i in range(2, count):
            hues.append((base_hue + 0.1 * i) % 1.0)
    elif style == 'triadic':
        hues = [base_hue, (base_hue + 0.333) % 1.0, (base_hue + 0.667) % 1.0]
        for i in range(3, count):
            hues.append((base_hue + 0.05 * i) % 1.0)
    elif style == 'random':
        hues = [random.random() for _ in range(count)]

    palette = []
    for i, h in enumerate(hues):
        s = 0.3 + random.random() * 0.4
        v = 0.4 + random.random() * 0.4
        if i == 0:  # accent color more saturated
            s = 0.7 + random.random() * 0.3
            v = 0.7 + random.random() * 0.3
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        hex_color = '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))
        palette.append(hex_color)

    return palette
```

---

## Mobile Best Practices

### Safe Zones for iPhone

```
┌──────────────────┐
│ ░░ Status Bar ░░ │ <- Time, battery, signal (top)
│ ░░             ░░ │ <- Dynamic Island / notch
│                  │
│                  │ <- Main wallpaper area
│                  │
│                  │
│                  │
│ ░░              ░░│ <- Home indicator (bottom)
│ ░░  Dock      ░░ │ <- App dock
└──────────────────┘
```

### Dark Mode Variants

```python
def generate_dark_variant(image_path, output_path):
    """Create a dark mode version of a wallpaper"""
    from PIL import Image
    import numpy as np

    img = Image.open(image_path).convert('RGB')
    arr = np.array(img, dtype=np.float32)

    # Reduce brightness
    arr *= 0.3

    # Crush blacks
    arr = np.clip(arr - 30, 0, 255)

    # Boost saturation slightly
    gray = np.mean(arr, axis=2, keepdims=True)
    arr = arr * 0.7 + gray * 0.3

    result = Image.fromarray(arr.astype(np.uint8))
    result.save(output_path)
```

### OLED Best Practices

- Use pure black (#000000) for backgrounds to turn off pixels
- Avoid bright elements near edges (burn-in risk)
- Keep static elements (status bar area) dark
- Limit bright, saturated colors in static positions
- Provide both light and dark variants
- Test on actual OLED device to check for black crush

---

## Python Automation

### Pillow Utilities

```python
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np
import os

def batch_resize(input_dir, output_dir, target_size=(2560, 1440), crop=True):
    """Batch resize wallpapers to target resolution"""
    os.makedirs(output_dir, exist_ok=True)
    for fname in os.listdir(input_dir):
        if fname.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(os.path.join(input_dir, fname))
            if crop:
                # Center crop to target aspect ratio
                target_ratio = target_size[0] / target_size[1]
                img_ratio = img.width / img.height
                if img_ratio > target_ratio:
                    new_w = int(img.height * target_ratio)
                    offset = (img.width - new_w) // 2
                    img = img.crop([offset, 0, offset + new_w, img.height])
                else:
                    new_h = int(img.width / target_ratio)
                    offset = (img.height - new_h) // 2
                    img = img.crop([0, offset, img.width, offset + new_h])
            img = img.resize(target_size, Image.LANCZOS)
            img.save(os.path.join(output_dir, fname))

def apply_vignette(image, strength=0.3):
    """Apply vignette effect"""
    w, h = image.size
    X, Y = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h))
    dist = np.sqrt(X**2 + Y**2)
    mask = np.clip(1 - dist * strength, 0, 1)
    arr = np.array(image, dtype=np.float32)
    for c in range(3):
        arr[..., c] = arr[..., c] * mask
    return Image.fromarray(arr.astype(np.uint8))
```

### numpy / matplotlib Generative Art

```python
import numpy as np
import matplotlib.pyplot as plt

def reaction_diffusion(w=2560, h=1440, steps=10000):
    """Gray-Scott reaction-diffusion simulation as wallpaper"""
    size = (h // 4, w // 4)  # smaller for speed, then upscale
    U = np.ones(size)
    V = np.zeros(size)

    # Seed pattern
    V[size[0]//2-20:size[0]//2+20, size[1]//2-20:size[1]//2+20] = 1.0

    Da, Db = 0.16, 0.08
    f, k = 0.035, 0.065  # stripes
    # f, k = 0.012, 0.050  # spots

    for _ in range(steps):
        Lu = np.roll(U, 1, axis=0) + np.roll(U, -1, axis=0) + \
             np.roll(U, 1, axis=1) + np.roll(U, -1, axis=1) - 4*U
        Lv = np.roll(V, 1, axis=0) + np.roll(V, -1, axis=0) + \
             np.roll(V, 1, axis=1) + np.roll(V, -1, axis=1) - 4*V
        reaction = U * V * V
        U += Da * Lu - reaction + f * (1 - U)
        V += Db * Lv + reaction - (f + k) * V

    # Upscale and colorize
    from scipy.ndimage import zoom
    U = zoom(U, 4, order=1)
    arr = np.clip(U * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, 'L').convert('RGB')

def plasma_fractal(w=2560, h=1440, roughness=0.5):
    """Plasma fractal / cloud effect wallpaper"""
    size = min(w, h)
    # Diamond-square algorithm
    arr = np.zeros((size, size))
    step = size
    scale = 1.0
    while step > 1:
        half = step // 2
        # Diamond step
        for y in range(half, size, step):
            for x in range(half, size, step):
                avg = (arr[y-half, x-half] + arr[y-half, x+half] +
                       arr[y+half, x-half] + arr[y+half, x+half]) / 4
                arr[y, x] = avg + scale * np.random.uniform(-1, 1)
        # Square step
        for y in range(0, size, half):
            for x in range((y+half) % step, size, step):
                vals = []
                if y > 0: vals.append(arr[y-half, x])
                if y < size-1: vals.append(arr[y+half, x])
                if x > 0: vals.append(arr[y, x-half])
                if x < size-1: vals.append(arr[y, x+half])
                arr[y, x] = np.mean(vals) + scale * np.random.uniform(-1, 1)
        step //= 2
        scale *= roughness

    arr = np.clip(arr, -1, 1)
    arr = (arr + 1) / 2 * 255
    result = Image.fromarray(arr.astype(np.uint8), 'L').resize((w, h))
    # Colorize
    return Image.merge('RGB', [result, result.point(lambda x: x*0.5), result.point(lambda x: 255-x)])
```

### Stable Diffusion API

```python
import requests
import base64
from PIL import Image
import io

def generate_sd_wallpaper(prompt, width=2560, height=1440, api_url="http://127.0.0.1:7860"):
    """Generate wallpaper via Stable Diffusion API"""
    payload = {
        "prompt": f"{prompt}, wallpaper, high quality, trending on artstation",
        "negative_prompt": "text, watermark, signature, low quality, blurry",
        "width": min(width, 2048),
        "height": min(height, 2048),
        "steps": 30,
        "cfg_scale": 7,
        "sampler_name": "Euler a",
        "batch_size": 1,
    }
    resp = requests.post(f"{api_url}/sdapi/v1/txt2img", json=payload)
    data = resp.json()
    img_data = base64.b64decode(data['images'][0])
    img = Image.open(io.BytesIO(img_data))
    img = img.resize((width, height), Image.LANCZOS)
    return img

# ControlNet for wallpaper generation
def generate_with_controlnet(prompt, control_image, width=2560, height=1440):
    """Generate wallpaper guided by composition reference"""
    import cv2
    # Edge detection for composition guidance
    edges = cv2.Canny(np.array(control_image), 100, 200)
    _, buffer = cv2.imencode('.png', edges)
    control_encoded = base64.b64encode(buffer).decode()

    payload = {
        "prompt": prompt,
        "negative_prompt": "text, watermark",
        "width": min(width, 2048),
        "height": min(height, 2048),
        "steps": 30,
        "alwayson_scripts": {
            "controlnet": {
                "args": [{
                    "input_image": control_encoded,
                    "module": "canny",
                    "model": "control_v11p_sd15_canny",
                    "weight": 0.8
                }]
            }
        }
    }
    resp = requests.post("http://127.0.0.1:7860/sdapi/v1/txt2img", json=payload)
    data = resp.json()
    img_data = base64.b64decode(data['images'][0])
    img = Image.open(io.BytesIO(img_data))
    img = img.resize((width, height), Image.LANCZOS)
    return img
```

### Batch Generation with Upscaling

```python
def batch_generate_wallpapers(prompts, output_dir, count_per_prompt=1):
    """Generate multiple wallpapers from prompts"""
    import os
    os.makedirs(output_dir, exist_ok=True)

    for prompt in prompts:
        for i in range(count_per_prompt):
            img = generate_sd_wallpaper(prompt)
            fname = prompt.replace(' ', '_')[:30] + f'_{i}.png'
            img.save(os.path.join(output_dir, fname))
            print(f"Generated: {fname}")

def upscale_wallpaper(image_path, output_path, scale=2):
    """Upscale wallpaper using ESRGAN / Real-ESRGAN"""
    import subprocess
    subprocess.run([
        "realesrgan-ncnn-vulkan",
        "-i", image_path,
        "-o", output_path,
        "-s", str(scale),
        "-m", "models/realesrgan-x4plus"
    ])
```

### Watermark Removal

```python
def remove_watermark(image, watermark_region=None):
    """Simple watermark removal via inpainting"""
    import cv2
    import numpy as np

    img = np.array(image)
    if watermark_region:
        x, y, w, h = watermark_region
        mask = np.zeros(img.shape[:2], np.uint8)
        mask[y:y+h, x:x+w] = 255
    else:
        # Automatic detection: look for semi-transparent text
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        _, mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8))

    result = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
    return Image.fromarray(result)
```

---

## Export & Delivery

### File Format Recommendations

| Use Case | Format | Quality | Notes |
|----------|--------|---------|-------|
| Desktop PNG | PNG-24 | Lossless | Best quality, larger files |
| Desktop JPEG | JPEG | 95-100% | Smaller files, slight loss |
| Mobile iOS | PNG | Lossless | iOS supports HEIF too |
| Mobile Android | JPEG | 95% | Wallpaper compression |
| Web display | WebP | 90% | Efficient format |
| Print | TIFF | 16-bit | For physical printing |

### Metadata

```python
def embed_metadata(image_path, title, author, description=""):
    """Embed metadata into wallpaper PNG"""
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo

    img = Image.open(image_path)
    metadata = PngInfo()
    metadata.add_text("Title", title)
    metadata.add_text("Author", author)
    metadata.add_text("Description", description)
    metadata.add_text("Software", "Python Wallpaper Generator")

    img.save(image_path, pnginfo=metadata)
```

### Naming Convention

```
[Style]_[Subject]_[Resolution]_[ColorVariant]_v[Version].png

Examples:
Abstract_Waves_2560x1440_Dark_v01.png
Minimal_Mountain_3840x2160_Teal_v02.png
Cyberpunk_City_3440x1440_Neon_v03.png
Space_Nebula_1080x2400_Dark_v04.png
```
