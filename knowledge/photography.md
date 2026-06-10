# Photography & Image Editing -- Complete Guide

## Table of Contents

1. [Camera Settings](#camera-settings)
2. [Composition Rules](#composition)
3. [Photography Genres](#genres)
4. [Lighting](#lighting)
5. [Color Theory](#color-theory)
6. [Post-Processing](#post-processing)
7. [Raw Development](#raw-development)
8. [Color Grading](#color-grading)
9. [Retouching](#retouching)
10. [HDR](#hdr)
11. [Focus Stacking](#focus-stacking)
12. [Panorama Stitching](#panorama)
13. [Camera Hardware](#hardware)

---

## Camera Settings

### Exposure Triangle

**Aperture (f-stop):** Controls depth of field
- f/1.0-1.8: Very shallow DOF, bokeh (portraits, low light)
- f/2.0-2.8: Shallow DOF (portrait, indoor)
- f/4.0-5.6: Moderate DOF (street, event)
- f/8.0-11: Deep DOF, sharpest (landscape)
- f/16-22: Max DOF, diffraction starts (macro)

**Shutter Speed:** Controls motion blur
- 1/8000-1/2000: Freeze fast motion (sports)
- 1/250-1/60: Handheld safe zone
- 1/30-1/4: Motion blur (panning, low light)
- 1/2-30s: Heavy blur (waterfalls, night)
- Bulb (30s+): Astro, star trails

**ISO:** Sensor sensitivity
- 100-200: No noise, max DR (daylight)
- 400-800: Minimal noise (overcast)
- 1600-3200: Moderate noise (low light)
- 6400+: Heavy noise (night, extreme)

### Exposure Triangle Formula

```python
import math
def calculate_ev(aperture, shutter, iso=100):
    return math.log2(aperture**2 / shutter) - math.log2(iso / 100)

# Sunny 16 rule: f/16, shutter = 1/ISO, EV 15
```

### White Balance

| Preset | Temp (K) | Use |
|--------|----------|-----|
| Daylight | 5500 | Sunny |
| Shade | 7000 | Shadows |
| Cloudy | 6500 | Overcast |
| Tungsten | 3200 | Incandescent |
| Fluorescent | 4000 | Office |
| Flash | 5500 | Speedlight |

### Metering Modes

- **Matrix/Evaluative:** Entire scene, intelligent
- **Center-weighted:** 60-80% center
- **Spot:** 1-5% circle, high contrast
- **Highlight-weighted:** Protect highlights

### Histogram

Left = shadows, middle = midtones, right = highlights.
- Left spike: underexposed
- Right spike: overexposed
- Both edges clipped: lost detail
- Even mountain: good exposure

---

## Composition Rules

### Rule of Thirds

Divide frame 3x3. Place key elements on lines or intersections.

```python
from PIL import Image, ImageDraw
def add_grid(image_path):
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    c = (255, 255, 255, 80)
    draw.line([(w//3,0),(w//3,h)], fill=c, width=1)
    draw.line([(2*w//3,0),(2*w//3,h)], fill=c, width=1)
    draw.line([(0,h//3),(w,h//3)], fill=c, width=1)
    draw.line([(0,2*h//3),(w,2*h//3)], fill=c, width=1)
    return img
```

### Additional Rules

- **Leading Lines:** Roads, rivers, fences guide the eye
- **Symmetry:** Mirror images, reflections
- **Golden Ratio:** 1.618:1, more dynamic than rule of thirds
- **Framing:** Use arches, windows, branches to frame subject
- **Negative Space:** Empty area for breathing room
- **Depth Layers:** Foreground, midground, background
- **Fill the Frame:** Get close, eliminate distractions

---

## Photography Genres

### Portrait: f/1.4-2.8, 85-135mm, Eye AF, Rembrandt/butterfly/split lighting

```python
import cv2
import numpy as np
def portrait_blur(image_path, blur=15):
    img = cv2.imread(image_path)
    face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face.detectMultiScale(gray, 1.1, 4)
    mask = np.zeros(img.shape[:2], np.uint8)
    for (x, y, w, h) in faces:
        cv2.ellipse(mask, (x+w//2, y+h//2), (w, h), 0, 0, 360, 255, -1)
    mask = cv2.GaussianBlur(mask, (99,99), 30)
    blurred = cv2.GaussianBlur(img, (blur,blur), 0)
    m = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR) / 255.0
    return (img * m + blurred * (1-m)).astype(np.uint8)
```

### Landscape: f/8-16, 14-35mm, tripod, golden hour, hyperfocal focus, ND filters

### Macro: f/8-16, focus rail, ring flash, 1:1+ magnification, extension tubes

### Street: f/5.6-8, 28-50mm, zone focus, 1/250s+, decisive moment

### Astro: f/1.4-2.8, 14-24mm, 500/FL rule, ISO 3200-6400, manual infinity focus

### Wildlife: f/2.8-5.6, 200-800mm, 1/500s+, AF-C, eye visible, clean background

### Product: f/8-16, 50-100mm, focus stack, light tent, two strobes at 45 degrees

### Fashion: f/2.8-8, 24-200mm, beauty dish/strip boxes, model movement

---

## Lighting

### Natural Light

| Time | Quality | Temp |
|------|---------|------|
| Golden Hour | Warm, soft | 3500K |
| Blue Hour | Cool, even | 9000K |
| Midday | Harsh | 5500K |
| Overcast | Soft diffused | 6500K |

### Studio Strobes

| Type | Power | Recycle |
|------|-------|---------|
| Monolight | 300-1000Ws | 0.5-2s |
| Pack + Head | 1200-2400Ws | 0.1-1s |
| Speedlight | 50-100Ws | 2-5s |

### Modifiers

| Modifier | Quality | Use |
|----------|---------|-----|
| Softbox | Soft, directional | General |
| Octabox | Very soft, round catchlight | Portrait |
| Beauty Dish | Medium, contrasty | Glamour |
| Snoot | Hard circle | Accent |
| Grid | Narrow beam | Controlled |
| Strip Box | Narrow rectangle | Rim light |
| Umbrella | Wide, uncontrolled | Spread |
| Ring Flash | Even, shadowless | Macro, fashion |

### Portrait Lighting Patterns

| Pattern | Setup | Effect |
|---------|-------|--------|
| Rembrandt | 45 deg, 45 deg above | Triangle on shadow cheek |
| Butterfly | Front, above camera | Shadow under nose |
| Loop | 30 deg side, slightly above | Small nose shadow |
| Split | 90 deg to subject | Half lit, half shadow |
| Short | Far side lit | Slimming |
| Broad | Near side lit | Widening |

---

## Color Theory

### Color Wheel: Complementary (opposite), Analogous (adjacent), Triadic (equal spacing)

### HSL Adjustments

```python
import cv2
import numpy as np

def adjust_hsl(image_path, color_shifts=None):
    img = cv2.imread(image_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    ranges = {
        "red": [(0,10),(160,179)], "orange": [(10,25)],
        "yellow": [(25,35)], "green": [(35,85)],
        "blue": [(100,130)], "purple": [(130,160)]
    }
    if color_shifts:
        for color, (h_shift, s_shift, v_shift) in color_shifts.items():
            for lo, hi in ranges.get(color, []):
                mask = (hsv[...,0] >= lo) & (hsv[...,0] <= hi)
                hsv[...,0][mask] = (hsv[...,0][mask] + h_shift) % 180
                hsv[...,1][mask] = np.clip(hsv[...,1][mask] * (1 + s_shift/100), 0, 255)
                hsv[...,2][mask] = np.clip(hsv[...,2][mask] * (1 + v_shift/100), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
```

### Split Toning

```python
def split_tone(img, h_hue=30, h_sat=15, s_hue=220, s_sat=15):
    arr = np.array(img, dtype=np.float32) / 255.0
    gray = np.dot(arr[...,:3], [0.299, 0.587, 0.114])
    hi_mask = gray
    sh_mask = 1 - gray
    # Apply tints
    for c, tint in enumerate([(h_hue, h_sat), (s_hue, s_sat)]):
        h, s = tint
        rgb = np.array([1,1,1])  # simplified color translation
        for i in range(3):
            arr[...,i] += rgb[i] * (hi_mask if c==0 else sh_mask) * s / 200
    return np.clip(arr, 0, 1)
```

---

## Post-Processing

### Software: Lightroom, Capture One, Darktable (free), RawTherapee (free), DxO PhotoLab, Affinity Photo, GIMP (free)

### Adjustments Reference

| Setting | Range | Effect |
|---------|-------|--------|
| Exposure | -5 to +5 EV | Global brightness |
| Contrast | -100 to +100 | S-curve steepness |
| Highlights | -100 to 0 | Recover blown areas |
| Shadows | 0 to +100 | Lift dark areas |
| Whites | -100 to +100 | Set white point |
| Blacks | -100 to +100 | Set black point |
| Clarity | -100 to +100 | Local contrast |
| Dehaze | -100 to +100 | Atmospheric removal |
| Vibrance | -100 to +100 | Smart saturation |
| Saturation | -100 to +100 | Full saturation |
| Sharpening | 0-150 | Edge detail |
| Noise Reduction | 0-100 | Luminance/color |

---

## Raw Development

```python
import rawpy
import cv2
import numpy as np

def process_raw(raw_path, output_path):
    raw = rawpy.imread(raw_path)
    rgb = raw.postprocess(use_camera_wb=True, half_size=False,
                          no_auto_bright=True, output_bps=16)
    img = rgb.astype(np.float32) / 65535.0

    # Gamma correction
    img = img ** (1/2.2)

    # Base curve
    img = np.clip((img - 0.01) / (0.99 - 0.01), 0, 1) ** 1.1

    img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    cv2.imwrite(output_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
```

---

## Retouching

### Frequency Separation

```python
def freq_sep(image, smooth_r=9, blend=0.5):
    img = cv2.imread(image).astype(np.float32) / 255.0
    low = cv2.GaussianBlur(img, (0,0), smooth_r)
    high = img - low
    low_s = cv2.bilateralFilter((low*255).astype(np.uint8), 9, 75, 75)
    return np.clip(low_s.astype(np.float32)/255*blend + high*blend + img*(1-blend), 0, 1)
```

### Dodge & Burn

```python
def dodge_burn(image, amount=15):
    img = cv2.imread(image).astype(np.float32)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (0,0), 50)
    mask = (gray - blurred + 128) / 255.0
    midtones = 1 - np.abs(gray/255.0 - 0.5) * 2
    adj = (mask - 0.5) * midtones * (amount/100)
    for c in range(3):
        img[...,c] = np.clip(img[...,c] + adj * 255, 0, 255)
    return img.astype(np.uint8)
```

---

## HDR

```python
import cv2
import numpy as np

def merge_hdr(images, exposures):
    return cv2.createMergeDebevec().process(images, times=np.array(exposures, dtype=np.float32))

def tonemap(hdr):
    return np.clip(cv2.createTonemapReinhard(gamma=2.2).process(hdr) * 255, 0, 255).astype(np.uint8)

def exposure_fusion(images):
    return np.clip(cv2.createMergeMertens().process(images) * 255, 0, 255).astype(np.uint8)
```

---

## Focus Stacking

```python
def focus_stack(images):
    gray = [cv2.cvtColor(i, cv2.COLOR_BGR2GRAY) for i in images]
    h, w = gray[0].shape
    focus = [cv2.GaussianBlur(cv2.Laplacian(g, cv2.CV_32F), (3,3), 0) for g in gray]
    stack = np.stack(focus, axis=-1)
    idx = np.argmax(stack, axis=-1)
    result = np.zeros((h, w, 3), dtype=np.float32)
    weight = np.zeros((h, w), dtype=np.float32)
    for i in range(len(images)):
        wgt = np.exp(-((idx - i) ** 2) / 50)
        for c in range(3):
            result[...,c] += images[i][...,c] * wgt
        weight += wgt
    return (result / np.maximum(weight, 1e-10)[...,np.newaxis]).astype(np.uint8)
```

---

## Panorama Stitching

```python
def stitch(images):
    stitcher = cv2.Stitcher.create(cv2.Stitcher_PANORAMA)
    status, result = stitcher.stitch(images)
    return result if status == cv2.Stitcher_OK else images[0]
```

---

## Camera Hardware

### Sensor Sizes

| Format | Size (mm) | Crop |
|--------|-----------|------|
| Full Frame | 36x24 | 1.0x |
| APS-C (Canon) | 22.2x14.8 | 1.6x |
| APS-C (Nikon/Sony) | 23.6x15.6 | 1.5x |
| Micro Four Thirds | 17.3x13 | 2.0x |
| 1-inch | 13.2x8.8 | 2.7x |
| Medium Format | 53.7x40.2 | 0.64x |

### Equivalence: FF f/2 = APS-C f/1.4, FF 50mm = APS-C 33mm

### Lens Types

| Type | FL | Use |
|------|-----|-----|
| Ultra Wide | 8-16mm | Architecture, astro |
| Wide | 16-35mm | Landscape |
| Standard | 35-70mm | Street, general |
| Telephoto | 70-200mm | Portrait, event |
| Super Tele | 200-800mm | Wildlife, sports |
| Macro | 60-105mm | Close-up |
| Tilt-Shift | 17-24mm | Architecture |
