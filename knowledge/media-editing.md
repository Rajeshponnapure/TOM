# Media Editing — Complete Knowledge Base

Covers every major video, photo, audio, VFX, motion graphics, color grading, 3D, and rendering application, technique, and production workflow in the world.

---

## 1. VIDEO EDITING — ALL APPLICATIONS

### 1.1 Adobe Premiere Pro

**Overview:** Industry-standard NLE for film, TV, and web. Part of Adobe Creative Cloud. Timeline-based, non-destructive editing.

**Interface:**
- Project panel — import, bin organization, search, metadata
- Source Monitor — preview, set in/out points, subclip
- Program Monitor — timeline playback, resolution dropdown
- Timeline — video/audio tracks, V1/V2..., A1/A2...
- Tools panel — Selection (V), Track Select (A), Ripple Edit (B), Rolling Edit (N), Rate Stretch (X), Razor (C), Slip (Y), Slide (U), Pen (P), Hand (H), Zoom (Z)
- Effects panel — video/audio effects, presets
- Effect Controls — keyframes, motion, opacity, time remapping
- Audio Track Mixer — volume, pan, sends, automation
- Essential Graphics — titles, captions, motion graphics templates (.mogrt)
- Essential Sound — audio type assignment (dialogue, music, SFX, ambience)
- Lumetri Color — embedded color grading panel
- Libraries — Creative Cloud Libraries sync

**Project Setup:**
- New Project -> name, location, renderer (Mercury Playback Engine GPU/CUDA/Metal)
- Sequence Presets: ARRI, RED, Canon, Sony, DSLR, AVCHD, HD/4K/8K
- Custom sequence: resolution, frame rate (23.976, 24, 25, 29.97, 50, 59.94, 60), pixel aspect ratio, field order (progressive), audio sample rate (48kHz), bit depth (16/24/32)
- Scratch disks: same as project, or custom per capture/video preview/audio preview

**Import & Media Management:**
- File > Import or Ctrl+I / Cmd+I
- Supported formats: MP4, MOV, MXF, AVI, DNxHD, ProRes, RED RAW, ARRIRAW, XAVC, AVCHD, HEVC, H.264, H.265, WAV, MP3, AIFF, PNG, JPEG, TIFF, PSD, AI
- Media Browser panel for ingest, proxy creation, tape logging
- Ingest settings: copy media to designated folder, transcode to ProRes/DNxHD, generate proxies (half/quarter resolution, ProRes Proxy, H.264)
- Proxy workflow: Toggle Proxies button in Program Monitor; edit with proxies, switch to full-res for export
- Bins: create, rename (Ctrl+B/Cmd+B), search (filter bin), icon/list/freeform view, column customization (resolution, duration, frame rate, usage, status)
- Metadata: clip name, description, scene, shot/take, log notes, markers with comments and duration
- Label colors: for organization (select clip -> right-click -> label)

**Timeline Editing:**
- Drag clips from Source/Project onto timeline
- Insert edit (comma key) — pushes clips right
- Overwrite edit (period key) — replaces footage underneath
- Replace edit — swap clip keeping duration
- Three-point editing: set in/out on source + in/out on timeline
- Ripple Edit tool — trim and close gap automatically
- Rolling Edit tool — adjust edit point, adjacent clips change duration
- Rate Stretch tool — change clip speed by dragging edges
- Slip tool — change clip's in/out points without moving position
- Slide tool — move clip while adjusting adjacent clips
- Razor tool — cut clip (Ctrl+K / Cmd+K at playhead)
- Track Select Forward/Back — select all clips to right/left
- Lock tracks — prevent accidental edits
- Sync Lock — maintain sync when inserting/deleting
- Linked Selection — video/audio linked by default (Alt-click / Opt-click to unlink)
- Nesting: select clips -> right-click -> Nest (creates nested sequence)
- Multi-camera: create multi-cam source sequence, enable multi-camera monitor, select angle during playback or by numeric keys

**Transitions:**
- Default transition apply: Ctrl+D / Cmd+D (video), Ctrl+Shift+D / Cmd+Shift+D (audio)
- Common: Cross Dissolve, Dip to Black, Dip to White, Film Dissolve, Additive Dissolve
- Push, Wipe, Iris, Page Peel (mostly outdated)
- Morph Cut — smooth jump cuts by warping frames (great for talking heads)
- Customize transition duration in Preferences
- Hold Adjustment Layer over transitions for custom blended effects

**Effects:**
- Video effects: Transform (crop, position, scale, rotation — GPU accelerated), Warp Stabilizer (analyze then smooth/position/scale/perspective/crop), Lumetri Color, Ultra Key (chroma key), Color Key, Track Matte Key, Difference Matte, Blend, Drop Shadow, Bevel, Gaussian Blur, Sharpen, Directional Blur, Mosaic, Time Warp (optical flow time remapping), Speed/Duration (reverse speed, maintain audio pitch)
- Audio effects: Dynamics (compressor, limiter, gate, expander), EQ (parametric, graphic), DeNoise, DeReverb, Reverb, Delay, Multiband Compressor, PitchShifter, Phaser, Chorus, Flanger
- Master effects: Effects applied to entire track via Track Mixer
- Effect presets: save/load custom preset collections
- Adjustment Layers: add effects to adjustment layer for grade/effects applied to everything below

**Keyframes & Animation:**
- Effect Controls panel
- Stopwatch icon to enable keyframing per parameter
- Add/remove keyframes via diamond button
- Keyframe navigation: left/right arrows next to diamond
- Temporal interpolation: Linear, Bezier, Auto Bezier, Continuous Bezier (right-click keyframe)
- Spatial interpolation: Linear, Bezier for Motion path in Program Monitor
- Ease In / Ease Out buttons on keyframe
- Copy/paste keyframes across clips
- Graph Editor for precise curve editing
**Color (Lumetri):**
- Basic Correction: white balance (temp/tint), exposure, contrast, highlights, shadows, whites, blacks, saturation
- Creative: Look presets, intensity, Sharpen, Vibrance, Faded Film
- Curves: RGB and individual channel curves, Hue Saturation Curves (hue vs sat, hue vs luma, luma vs sat)
- Color Wheels: shadows, midtones, highlights — each with master, shadow, midtone, highlight wheels; RGB wheel for lift/gamma/gain
- HSL Secondary: picker tool, hue/sat/luma range, refine via denoise/blur, color correct specific object
- Vignette: amount, midpoint, roundness, feather, highlights
- Color match: shot matching between clips
- LUT support: .cube, .look; Input LUT, Look LUT
- Scopes panel: waveform (RGB, luminance, parade), vectorscope (YUV), histogram, chroma parade
- Comparison View: split screen reference

**Titles & Graphics:**
- Type tool in Program Monitor
- Essential Graphics panel: edit text, shape, transform, fill, stroke, shadow, background
- Text styles: font, style, size, tracking, leading, baseline shift, kerning
- Motion Graphics templates (.mogrt): drag from Essential Graphics, created in After Effects
- Legacy Titler (deprecated but still available)

**Captions:**
- Auto-generate captions via machine learning (English, other languages)
- Manual captions: create caption track, type/subtitle timing
- Import sidecar files: .srt, .stl, .xml, .itt
- Style captions: font, size, color, background, position, alignment

**Export:**
- File > Export > Media (Ctrl+M / Cmd+M)
- H.264 presets: YouTube 2160p/1440p/1080p, Vimeo, Twitter/Facebook, Apple/Android devices
- Match Source presets: adaptive bitrate
- Export settings: format (H.264, HEVC, QuickTime, DNxHR, OpenEXR, DPX, TIFF, PNG)
- Video tab: frame rate, field order, aspect ratio, render at maximum depth, use maximum render quality
- Bitrate: VBR 1-pass, VBR 2-pass (higher quality), CBR
- Target bitrate: 4K H.264 ~40-60 Mbps, 1080p ~10-20 Mbps, 8K HEVC ~100+ Mbps
- Hardware encoding: Enable if available (Intel QuickSync, NVENC, AMD VCE)
- Audio tab: AAC 320kbps or 256kbps, MP3, PCM, Dolby Digital
- Effects tab: Lumetri Look, LUT burn-in
- Captions tab: burn in or embed
- Publish to social directly
- Media Encoder queue for batch exports

**Shortcuts (Default):**
- Ctrl+Z / Cmd+Z — Undo
- Ctrl+S / Cmd+S — Save
- Ctrl+Shift+S / Cmd+Shift+S — Save As
- Space — Play/Stop
- J — Reverse, K — Stop, L — Forward (tap 2-3x for speed)
- I — Mark In, O — Mark Out
- Q — Ripple delete from playhead to previous edit
- W — Ripple delete from playhead to next edit
- ; — Ripple delete selected
- Ctrl+Shift+X / Cmd+Shift+X — Export Frame (snapshot)
- M — Add Marker
- Ctrl+K / Cmd+K — Add Edit (Razor)
- Up/Down — Previous/Next Edit
- Shift+Up/Down — Previous/Next Clip
- + / - — Zoom in/out on timeline
- \ — Fit timeline in window
- A — Track Select Forward Tool
- Shift+A — Track Select Backward Tool
- T — Text tool
- Ctrl+R / Cmd+R — Speed/Duration
- Ctrl+L / Cmd+L — Audio gain
- Ctrl+Shift+E / Cmd+Shift+E — Enable/disable clip
- F — Match frame (find source clip frame)
- Shift+R — Reverse match frame
- Ctrl+T / Cmd+T — New Title
- Alt+drag / Opt+drag — Duplicate clip
- ~ — Full screen (or F11 in newer)

**Pro Tips:**
- Use proxies for 4K/6K/8K footage (ProRes Proxy or 720p H.264)
- Set auto-save every 5 minutes, keep 20 versions
- Render previews (Enter) for smooth timeline playback
- Use After Effects Dynamic Link for VFX/motion graphics
- organize bins with consistent naming: FOOTAGE, AUDIO, GRAPHICS, EXPORTS
- Keyboard shortcut customization: Edit > Keyboard Shortcuts (Ctrl+Alt+K / Cmd+Opt+K)
- Use Productions for multi-project workflows (shared bins across sequences)
- Make duplicate of sequence before experimenting

---

### 1.2 DaVinci Resolve

**Overview:** Industry-leading color grading tool with full NLE, VFX, and audio post-production. Free version is extremely capable; Studio version adds noise reduction, blur effects, HDR grading, and more.

**Pages (workspaces):**
| Page | Function | Keyboard |
|------|----------|----------|
| Media | Import, organize, sync, metadata | Shift+1 |
| Cut | Fast editing, speed editor hardware, source tape | Shift+2 |
| Edit | Full timeline editing, transitions, effects | Shift+3 |
| Fusion | Node-based VFX and motion graphics | Shift+4 |
| Color | Primary/secondary grading, tracking, nodes | Shift+5 |
| Fairlight | Audio post-production, mixing, recording | Shift+6 |
| Deliver | Export and encoding | Shift+7 |

**Media Page:**
- Media Storage panel — browse drives, preview clips
- Viewer — playback, audio waveform
- Sync media via timecode, waveform, or markers
- Import Assists — set reel names, custom metadata
- Clone tool — copy/archive media with checksum verification
- Add cue markers for scene detection

**Cut Page:**
- Source Tape — drag from left to timeline
- Timeline — magnetic-like, simplified tracks
- Fast Review — skim through clips
- Smart Insert — automatically fit clips in timeline
- Precision Edit — trim mode
- Speed Editor Hardware: jog wheel, cut buttons, source tape
- Key features: Auto Edit, Dynamic Trim, Multicam with angle sync
- Transitions: apply via transition menu or Shift+T
- Export directly from Cut page for quick turnarounds

**Edit Page:**
- Traditional track-based timeline
- Dual timeline mode (small full-timeline overview + zoomed edit)
- Source/Record view
- Supported formats: all major RAW and compressed formats
- Timeline tracks: up to 99 video, 99 audio
- Three-point editing: Mark In/Out on source, select track target, insert/overwrite
- Ripple Overwrite, Replace, Place On Top, Fit to Fill
- Trim mode: ripple, roll, slip, slide, dynamic trim
- Transition menu: dissolve, dip to color/white/black, push, wipe, iris, motion blur
- Effects: Resolve FX (film grain, lens flare, glow, mist, starburst, lens blur, chroma key, delta key, luminance key, 3D keyer, color compressor, beauty, smarts reframe, speed warp, retime, stabilized crop)
- OpenFX support: third-party plugins (Sapphire, Continuum, Red Giant)
- Fusion Effects: connect to Fusion page for node comps
- Adjustment clips: apply effects across multiple clips
- Nesting: compound clips for complex sequences
- Retime controls: speed change, optical flow (enhanced better), frame interpolation, reverse, freeze frame
- Multicam: up to 16 angles, angle viewer, switch during playback
- Markers and timeline cues
- Auto scene detection for importing segmented clips
**Fusion Page:**
- Full node-based compositing (equivalent to Nuke)
- Node editor: tools connected via pipes (left=input, right=output)
- Common nodes: Merge (overlay), Transform, Crop, Color Corrector, Brightness/Contrast, Blur, Glow, Shadow, Text+, Background, FastNoise, Shape, Rectangle/Ellipse, Polygon, Bitmap
- Mask nodes: Polygon, B-Spline, Bitmap mask, garbage mask
- Tracking: Planar Tracker, Tracker node (point tracking), Camera Tracker, Stabilizer, Match Move
- Keying: Delta Keyer, Chroma Key, Luminance Key, Difference Key, Ultra Keyer, Primatte
- Paint: Paint node (clone, heal, smear, replace)
- Particles: pEmitter, pRender, pFollower, pBounce, pPhysics, pKill, pCustom
- 3D: Merge3D, Camera3D, Renderer3D, Lights (directional, point, spot, ambient), Shape3D (sphere, cube, cylinder), FBX/OBJ import, displacement, UV map
- Text: Text+ (per-character formatting, transforms, extrusion, bevel), Text3D
- Animation: keyframe editor, spline editor, modifiers (shake, oscillate, wave, motion)
- Tools > Macros: group nodes into reusable macro tools
- Loader/Saver: image sequences, EXR, DPX, PNG
- Catalyzer: AI-based rotoscoping (object mask generation)

**Color Page:**
- Node-based grading — the heart of Resolve
- Color nodes: serial, parallel, layer, splitter/combiner (RGB/YUV)
- Node graph: right-click to add node (Alt+N / Opt+N)
- Node types: correction, serial, parallel, layer, outside/inside, key, matte
- Keyframes per node, keyframe editor
- Gallery: stills, grade recall, reference images
- Lightbox: compare grades across clips in timeline
- Shot matching via automatic color matching (RGB, luminance, curves)

**Primary grading:**
- Wheels: Lift (shadows), Gamma (midtones), Gain (highlights), Offset (global)
- Log wheels when working with log footage
- Primary bars: lift, gamma, gain, offset, contrast, pivot
- Color temperature and tint
- Saturation and luminance controls
- Shadow/HiGhlight range: set thresholds for where lift/gain begins

**HDR Grading:**
- HDR wheels if Studio version
- Color warper for precise hue manipulation
- HDR zones: separate control for specific nit ranges
- Dolby Vision and HDR10+ metadata support
- ST.2084 (PQ) and HLG transfer functions
- Tone mapping for SDR delivery from HDR grade

**Curves:**
- Custom curves — RGB and individual channels
- Hue vs Hue, Hue vs Sat, Hue vs Luma, Luma vs Sat, Sat vs Sat curves
- Point curves with color picker for specific hues

**Color Warper:**
- Grid-based color manipulation
- HSL grid for hue/saturation adjustments
- RGB grid
- Drag grid points to shift colors

**Qualifiers (HSL Secondary):**
- 3D qualifier with hue, saturation, luminance ranges
- RGB picker with highlight, shadow, midtone preference
- Clean up with matte finesse (blur, erode, dilate)
- Show/hide qualifier preview on clip
- Invert qualifier

**Power Windows:**
- Rectangle, Oval, Polygon, Curved (B-Spline), Auto (magic mask with AI)
- Softness/feathering — inner and outer (soft edge)
- Tracking: tracker window panel — point, planar, with rotation, scale, perspective
- Motion blur on tracked windows
- Gradient: linear and radial soft gradients
- Combine windows with keys and mattes

**Tracking:**
- Point Tracker: single feature point, translate/rotate/scale
- Planar Tracker (Studio): full planar surface tracking
- Camera Tracker: 3D solve for adding 3D objects
- Object Removal via clone and planar tracking
- Smart Reframe: AI reframing for different aspect ratios

**Noise Reduction (Studio):**
- Temporal NR: across frames, removes motion artifacts
- Spatial NR: within single frame, reduces grain/noise
- Both adjustable by luma/chroma channels
- Motion estimation

**Color Management:**
- Resolve Color Management (RCM) — input color space, timeline color space, output color space
- DaVinci Wide Gamut as intermediate
- ACES pipeline — IDT, RRT, ODT
- Color space transforms for matching log formats
- Output LUT: apply LUT on clip/node/export

**Scopes:**
- Waveform (YRGB, Luma, RGB overlay, YCbCr Y-only, YCbCr)
- Parade (RGB, YCbCr)
- Vectorscope (YUV, YUV with targets, HLS)
- Histogram (RGB, Luma, all)
- All configurable in scopes panel settings
**Fairlight Page:**
- Full DAW (digital audio workstation) quality
- Up to 2000 tracks, 24-bit/192kHz
- Mixer: faders, EQ, dynamics, pan, sends, bus routing
- EQ: 6-band parametric, filters (high/low pass, notch, shelving)
- Dynamics: compressor, limiter, gate, expander, de-esser
- FX: reverb, delay, chorus, flanger, phaser, distortion, amp sim, guitar/voice FX
- Audio restoration: spectral noise reduction, click removal, hum removal
- Record: punch in/out, loop record, count in
- ADR: Auto-Align Dialogue with guide tracks
- Fairlight Audio Accelerator hardware (optional)
- Loudness metering (LUFS integrated/short-term/momentary True Peak)
- Buses: aux and submix routing
- Automation: read, touch, latch, write modes
- Audio align via waveform to group mics
- Integrate with Edit timeline audio

**Deliver Page:**
- Render presets: YouTube, Vimeo, H.264 Master, ProRes, DNxHD
- Custom export: file format, codec, resolution, frame rate, quality, key frames
- H.264/H.265: encoder (Native, NVENC, Intel QuickSync), quality (automatic->best), encoding profile
- Advanced: enable Retime and Scaling, process LUT, data burn-in, subtitles
- Individual clips render (with source name)
- Render from timeline in/out or entire timeline
- Separate video and audio files
- IMF package delivery for cinema
- DCP (Digital Cinema Package) for theaters (Studio)
- Render job queue, simultaneous render to multiple formats

**Shortcuts:**
- Ctrl+Z / Cmd+Z — Undo
- Ctrl+S / Cmd+S — Save
- Alt+S / Opt+S — Save As
- I — In point, O — Out point
- Q — Insert, W — Overwrite
- T — Trim mode, A — Select mode
- B — Blade / Razor
- Ctrl+B / Cmd+B — Bin
- Shift+F12 — Full screen viewer
- Ctrl+D / Cmd+D — Change clip duration
- Up/Down — previous/next edit
- Ctrl+Up/Dn / Cmd+Up/Dn — Move between tracks
- M — marker
- Ctrl+Shift+= / Cmd+Shift+= — Dynamic trim
- J, K, L — shuttle (backward, stop, forward)
- F — Full-screen viewer
- Ctrl+Del / Cmd+Del — Delete with ripple
- 1-9 — Select target video track
- Shift+1-9 — Select target audio track
- Alt+= / Opt+= — Disable/enable clip
- D — Disable/enable grade

**Pro Tips:**
- Use optimized media for smooth playback: right-click clip > Optimize Media (DNxHR LB or ProRes Proxy)
- Render Cache: Smart mode caches transitions, composites, Fusion
- Color managed workflow: set project color science to DaVinci YRGB Color Managed or ACES
- Create timeline stills for consistent grade across shots
- Use Lightbox to compare with frame-grab from same scene
- Node tree best practice: serial for primary, parallel/second layer for secondary, key nodes for windows/masks
- Ctrl+Shift+N / Cmd+Shift+N — add parallel node
- Ctrl+P / Cmd+P — add layer node
- Duplicate grade across clips: middle-click clip or Alt+drag grade
- Save grade as a still (Shift+Ctrl+S / Shift+Cmd+S for gallery still)
- Use PowerGrade for shared grades across all projects

---

### 1.3 Final Cut Pro X

**Overview:** Apple's professional NLE. Magnetic Timeline, background rendering, metal-accelerated. OS X only.

**Interface:**
- Library: top-level container, contains events and projects
- Event: source clips organized by date/import
- Project: sequences (timelines)
- Viewer: skimming, play controls
- Timeline: magnetic (primary storyline, connected clips)
- Browser: Event clips with filmstrip view
- Inspector: info, effects, color
- Effects Browser: built-in, third-party

**Magnetic Timeline:**
- Primary Storyline: spine where main clips live
- Connected clips: attach to primary storyline, move with it
- Roles: categorize clips (Video, Dialogue, Music, Effects, Titles)
- i (enter/exit), o (out), e (append), w (insert), d (overwrite), q (connect to storyline)
- Trim: drag edges, precision trim tool (T)
- Ripple, Roll, Slip, Slide via trim tool + modifier

**Compound Clips:**
- Select multiple clips, right-click > New Compound Clip
- Nesting for VFX, color grade, or organized groups
- Open compound clip in timeline tab

**Roles:**
- Video, Dialogue, Music, Effects, Titles
- Custom roles: Right-click in timeline index > Edit Roles
- Color-code timeline tracks by role
- Export with role-based audio stems

**Multicam:**
- Create multicam clip from sync'd angles
- Angle viewer for real-time switching
- Multicam editing: cut/trim within multicam clip

**Color Grading:**
- Color Board: Color, Saturation, Exposure wheels with ranges
- Color Curves: RGB and individual channels
- Color Wheels: shadow/midtone/highlight per channel
- Match Color: auto-match color between clips
- Apply presets (.cubes supported but not native)
- Mask shape and color mask for secondary corrections
- Color LUTs: via Custom LUT effect

**Effects:**
- Built-in: blur, glow, sharpen, stylize, keying, distortion
- Transitions: dissolve, wipe, slide, iris, 3D
- Titles: lower thirds, full-screen, credits, cinematic
- Audio effects: compressor, EQ, noise gate, reverb, delay, limiter
- Keying: chroma key, luminance key, garbage matte
- Object tracking: built-in analyzer for masks, effects

**Proxy Workflows:**
- Create optimized/proxy media on import
- Transcode options: create proxy (ProRes Proxy), create optimized (ProRes 422)
- Toggle proxy/original in viewer

**Export:**
- Share > Master File: ProRes, H.264, HEVC
- Compressor for advanced encoding
- Roles-based export: multi-track or individual stems
- Send to Compressor for custom encoding
### 1.4 Avid Media Composer

**Overview:** The standard for Hollywood film and broadcast editing. Dependable, robust media management, shared storage workflows.

**Interface:**
- Project window: bins, settings, formats
- Composer window: source and record side-by-side
- Timeline: track selector panel, segment tools, trim mode
- Bins: containers for clips, sequences, effects (list/script/frame view)
- Effect Palette: video/audio effects categorized
- Audio Mixer: volume, pan, automation
- Tools menu: command palette, console, Media Tool, Capture

**Key Concepts:**
- Shared storage for multi-editor collaboration (Avid NEXIS, ISIS)
- Bin locking for team workflow (read/write)
- User profiles and settings per editor
- Media creation: MXF media files, managed outside project

**Trimming:**
- Smart Tool: yellow (trim), red (segment), marquee
- Trim Mode: single-roller, dual-roller, asymmetric
- Dynamic Trim: play through trim, adjust with JKL
- Trimming with Extend edit, split edit

**Sync & Script Sync:**
- ScriptSync: align script text to takes (via phonetics)
- PhraseFind: search dialogue by spoken phrase
- Group takes synced by timecode

**Collaboration:**
- Shared bins across network
- Check-in/check-out for bin locking
- Background services for media management
- Sequence archiving via AAF/ALE

**Shortcuts:**
- E — Extract (cut and close gap)
- B — Splice-in (insert edit)
- V — Overwrite edit
- A — Source side, S — Record side
- 1-9 — Track selection toggle (hold Ctrl/Cmd for singular)
- Play: L (forward), K (stop), J (reverse)
- T — Trim mode
- Y — Effect Mode
- Ctrl+W / Cmd+W — Close project
- Ctrl+S / Cmd+S — Save

---

### 1.5 CapCut

**Overview:** Free video editor by ByteDance, mobile + desktop, very popular for social media content. Intuitive, template-driven.

**Features:**
- Timeline: drag-drop, multi-track
- Transitions: extensive library (zoom, slide, blur, fade)
- Effects: glitch, retro, film, beauty, split screen
- Text: templates, animated, typewriter, neon
- Stickers, emoji, overlays
- Auto captions (AI-generated)
- Keyframe animation: position, scale, rotation, opacity
- Speed: curve speed control (custom speed ramps)
- Color: adjustment (brightness, contrast, saturation, etc.), curves, LUTs
- Audio: music library, sound effects, voiceover, audio extraction
- Remove background: auto cutout, chroma key
- Motion tracking: text/emoji attached to tracked objects
- Export: up to 4K 60fps, HDR, 50Mbps
- Pro features (CapCut Pro): advanced effects, premium templates, higher quality export

**Strengths:** Extremely fast and mobile-friendly, vast template library, AI features, free for most features
**Weaknesses:** Limited pro color grading, no native proxy workflow

---

### 1.6 Filmora (Wondershare)

**Overview:** Beginner-friendly NLE with drag-and-drop simplicity.

**Key Features:**
- Split screen, green screen, audio ducking
- Built-in effects: elements, overlays, transitions, titles
- Color tuning: auto color correction, 3D LUT
- Motion tracking: capture moving objects
- Keyframing: basic position/scale/rotation animation
- Speed ramping
- Audio: noise removal, equalizer, compressor, reverb
- Export: MP4, MOV, AVI, GIF, Vimeo/YouTube direct
- Filmora Stock: library of effects, music, footage

---

### 1.7 Shotcut

**Overview:** Free, open-source NLE. Cross-platform (Win/Mac/Linux). Based on MLT framework.

**Key Features:**
- Native timeline editing (not track-based)
- Wide format support via FFmpeg
- Proxy editing
- Keyframes for all filter parameters
- Video filters: audio visualization, 360 video, chroma key, color grading
- Audio filters: EQ, compressor, reverb, delay, pitch
- Export via FFmpeg presets
- Source/Player screen and timeline screen
- Hardware acceleration (GPU processing)

---

### 1.8 Kdenlive

**Overview:** Free, open-source NLE for Linux, Windows, macOS. KDE project.

**Key Features:**
- Multi-track timeline
- Proxy editing / transcoding
- Effects: color correction, transform, blur, keying
- Compositing: alpha blending, track compositing modes
- Audio: JACK transport sync, multi-channel
- Keyframes with curves
- Custom transitions via keyframes
- Render presets: DNxHD, ProRes, H.264, lossless
- DLTA (proxy) workflow for 4K/UHD

---

### 1.9 Vegas Pro (MAGIX)

**Overview:** Long-standing pro NLE, originally Sonic Foundry, then Sony, now MAGIX.

**Key Features:**
- Track-based timeline
- Advanced trimming modes (standard, three-point, slip, slide, envelope)
- Video effects: Pan/Crop, track motion, compositing modes
- Audio: multi-track recording, surround mixing, VST support
- Color grading: color wheels, curves, color match, HDR support
- Keyframes: envelope style for all parameters
- Motion tracking and stabilization
- 360 video editing
- GPU acceleration (NVENC, Intel QuickSync, AMD VCE)
- Export: HEVC, AVC, ProRes, MXF, DPX
- Scripting: .NET-based automation

---

### 1.10 HitFilm (by FXhome / Artlist)

**Overview:** Prosumer NLE with built-in VFX compositing. Two tiers: HitFilm (free) and HitFilm Pro.

**Key Features:**
- Timeline editing + compositing in same tool
- VFX: particle simulation, 3D compositing, lights, camera
- Color grading: 3-way color wheels, curves, LUTs, scopes
- Audio: multi-track mixing, EQ, compressor
- Over 400 effects in Pro version
- 4K export in free version
- 8K and 360 VR export in Pro
- Boris FX integration for premium effects
- In-app stock media (Artlist)

---

## 2. VFX & MOTION GRAPHICS

### 2.1 Adobe After Effects

**Overview:** Industry standard for motion graphics, compositing, and VFX. Layer-based with some 3D capabilities. Part of Adobe Creative Cloud.

**Interface:**
- Project panel: footage, compositions, assets
- Composition panel: visual preview (OpenGL/Metal accelerated)
- Timeline panel: layers (video, audio, shape, text, solid, adjustment, null, light, camera)
- Tools: Selection (V), Hand (H), Zoom (Z), Rotation (W), Camera (C), Pan Behind (Y), Shape (Q), Pen (G), Text (Ctrl+T/Cmd+T), Brush (Ctrl+B), Clone Stamp, Eraser
- Effects & Presets panel: searchable effect categories
- Effect Controls panel: parameters per selected layer
- Preview panel: RAM preview, audio preview
- Tracker panel: motion tracking, stabilization
- Character panel: type formatting
- Paragraph panel: alignment
- Brushes panel: for paint/retouch
- Render Queue / Adobe Media Encoder

**Compositions:**
- New comp: Ctrl+N / Cmd+N -> preset (HD/4K/UHD/Custom), resolution, pixel aspect ratio, frame rate, duration, background color
- Pre-compose: Ctrl+Shift+C / Cmd+Shift+C — nest layers into new comp
- Comp nesting: comps as layers inside other comps (infinite hierarchy)

**Layers:**
- Layer types: Video/Audio, Text, Shape, Solid, Adjustment, Null, Light, Camera
- Layer order: bottom to top in stacking order
- Layer switches: shy, collapse transformations, quality (wireframe/draft/best), effect enabled, motion blur, adjustment layer, 3D layer
- Solo: isolate single layer
- Lock: prevent editing specific layer
- Labels: color-code layers by type

**Keyframes & Animation:**
- Toggle animation stopwatch per property
- Add Keyframe: diamond button or Alt+Shift+[property shortcut]
- Keyframe navigation: J (previous), K (next)
- Easy Ease: F9
- Easy Ease In: Shift+F9
- Easy Ease Out: Ctrl+Shift+F9 / Cmd+Shift+F9
- Keyframe types: Linear, Bezier, Continuous Bezier, Auto Bezier, Hold
- Graph Editor: Value graph (property value over time) and Speed graph (velocity of change)
- Separate dimensions: right-click Transform > Separate Dimensions
- Motion path: visible in Composition panel as dotted line with control points

**Keyframe Assistant:**
- Easy Ease, Exponential Scale (for realistic zoom), Convert Audio to Keyframes, Sequence Layers (auto-arrange with overlap), Time Reverse Keyframes

**Expressions:**
- JavaScript-based automation
- Alt+click / Opt+click stopwatch to add expression
- pick whip: drag to link property
- Common expressions: loopOut(), loopIn(), wiggle(freq, amp), time, value, [value[0], 0], linear(t, tMin, tMax, value1, value2), ease(t, tMin, tMax, value1, value2), Math.sin(time * freq) * amp, seedRandom(), posterizeTime(fps), transform.position, thisComp.layer("name").effect("Slider Control")("Slider")
- Expressions Editor: write, syntax highlight, error reporting
- Expression global variables: thisComp, thisLayer, time, value, index, width, height, posterizeTime
**Masks:**
- Shape tools: Rectangle, Rounded Rectangle, Ellipse, Polygon, Star
- Pen tool: freeform Bezier masks (add, subtract, intersect, difference vertices)
- Mask properties: Mask Path, Mask Feather, Mask Opacity, Mask Expansion
- Mask interpolation: keyframe mask path for morphing
- Mask modes: None, Add, Subtract, Intersect, Lighten, Darken, Difference
- RotoBezier: smooth curved masking without control point adjustment
- Auto-trace: generate mask from alpha channel
- Refine Edge (for fine edge detail in masks)

**Tracking:**
- Tracker panel: Track Motion, Stabilize Motion, Transform, Parallel, Perspective (corner pin)
- Tracking types: Position (1 point), Position & Rotation (2 point), Affine (4 point parallel), Perspective (4 point skew)
- Analyze: forward/backward/then stabilize or apply
- Edit target: null object, layer
- Planar Tracking via Mocha AE (included) — planar surface tracking, rotoscoping
- 3D Camera Tracker: solve camera movement from footage, create text/solids/lights in 3D space
- Content-Aware Fill: automatic object removal using reference frames and fill methods (object, surface, edge)

**Effects (Categories):**
- 3D Channel, Audio (Audio waveform, spectrum), Blur & Sharpen (Gaussian, Directional, Radial, Fast Box, Camera Lens, Compound, Motion Blur, Channel Blur, Smart Blur, Reduce Noise, Unsharp Mask, Bilateral Blur), Channel, Color Correction (Curves, Levels, Color Balance, Hue/Saturation, Brightness/Contrast, Exposure, Colorama, Gradient, Tint, Tritone, Leave Color, Change Color, CC Color Offset, CC Toner), Distort (Optics Compensation, Bezier Warp, Bulge, Corner Pin, Displacement Map, Liquify, Mirror, Mesh Warp, Offset, Polar Coordinates, Ripple, Spherize, Transform, Turbulent Displace, Twirl, Wave Warp, CC Lens, CC Bender, Magnify, Smear, Time Displacement), Expression Controls, Generate (4-Color Gradient, Advanced Lightning, Audio Spectrum, Beam, Cell Pattern, Checkboard, Circle, Ellipse, Fill, Fractal Noise, Grid, Lens Flare, Radio Waves, Ramp, Scribble, Stroke, Vegas, Write-on), GPU, Keying (Keylight 1.2, Linear Color Key, Color Difference Key, Color Key, Luma Key, Difference Matte, Extract, Inner/Outer Key, Spill Suppressor), Matte (Matte Choker, Simple Choker, Refine Matte, Matte Cleaner, Advanced Spill Suppressor), Noise & Grain, Perspective (Drop Shadow, Bevel Alpha, Bevel Edges, CC Cylinder, CC Sphere, CC Environment, Radial Shadow, Shadow, 3D Glasses), Simulation (CC Particle World, CC Particle Systems II, CC Rainfall, CC Snow, Card Dance, Caustics, Foam, Shatter, Wave World), Stylize (CC Kaleida, CC Glass, CC Block Load, Cartoon, Color Emboss, Emboss, Find Edges, Glow, Mosaic, Motion Tile, Posterize, Roughen Edges, Scatter, Strobe Light, Texturize, Threshold)

**Shape Layers:**
- Vector shapes: Rectangle, Ellipse, Polygon, Star — repeatable, additive
- Shape attributes: fill (none, color, gradient), stroke (color, width, dash/gap, line cap, line join), transform
- Shape operators: Merge Paths, Pucker & Blat, Offset Paths, Twist, Wiggle Paths, Trim Paths (animated stroke drawing), Repeater (pattern), Round Corners, Zig Zag
- Contents: multiple shapes, groups, combined
- Add button for new shape/operator per group

**Text Animation:**
- Text layer: source text, text properties (position, scale, rotation, opacity, fill, stroke, line anchor, line spacing, character blend)
- Animate: Animate button > enable per-property animation (position, scale, rotation, opacity, tracking, line anchor, fill/stroke color, blur, skew, etc.)
- Range selector: Start/End/Offset, Units (percentage/index), Based On (characters/words/lines)
- Advanced: Shape (square/ramp up/ramp down/triangle/round/smooth), Ease High/Low, Randomize Order
- Text animator groups: multiple animators on one text layer
- Animator per-character/word/line based on selector
- 3D text: enable per-character 3D properties
- Text presets: browse and apply in Effects & Presets panel

**3D Layers:**
- Enable 3D Layer switch: reveals Position Z, Orientation, X/Y/Z Rotation
- Cameras: Multi (one-node/two-node), 15/50/200mm focal length, depth of field (aperture, blur levels, iris shape)
- Lights: Point, Spot, Parallel, Ambient; intensity, shadow darkness, shadow diffusion, falloff
- Material options: casts shadows, light transmission, accepts shadows, reflects, environment layer, transparency
- Cinema 4D Renderer: advanced 3D render engine (hardware tessellation, bevel, extrude text, displacement)
- Cinema 4D Lite integration: create/import C4D files, edit inside AE via Cineware

**Particle Systems (Third-party — Trapcode Suite by Maxon):**
- Trapcode Particular: 3D particle engine, emitter types (point, box, sphere, grid, layer, light), physics (air forces, gravity, bounce, turbulence), particles (sphere, cube, cloudlet, sprite, star, custom texture), auxiliary particles, color/opacity/size over life, motion blur, depth of field, OBJ emission, audio reactivity
- Trapcode Form: 3D particle grid, fractal/audio/layer dispersal, spherical field, kaleidospace, custom layers, OBJ, video mapping
- Trapcode Tao: 3D geometry along path, animation, bevel, recursion
- Trapcode Mir: geometric shape generation, fractal displacement

**Mocha AE:**
- Planar tracking: motion tracking of planar surfaces
- Create masks with X-Spline tools (adjustable at any point)
- Export tracking data: corner pin, transform, stabilize
- OCULA integration for advanced stereo/ROTO
- Import/export masks to AE
- Power Mesh: warped surface tracking

**Rendering:**
- Render Queue: Add to Render Queue (Ctrl+M / Cmd+M)
- Output Module: Lossless, ProRes 4444 (with alpha), Animation, H.264 (via Media Encoder), PNG Sequence, TIFF Sequence, EXR Sequence
- Output Module settings: format, video output (channels, depth, color), audio output, crop, stretch, custom
- Render Settings: quality (draft/best), resolution, proxy use, effects, frame rate, skip existing
- Background rendering: render while working (limited)
- Media Encoder: queues multiple comps, watch folders, time tuner, FBX export
- Stills sequences for frame-by-frame delivery
- Preview: RAM Preview (0-9 predefine skip/span), Audio Preview (.). Shift+0 for full RAM preview

**Shortcuts:**
- Ctrl+N / Cmd+N — New comp
- Ctrl+K / Cmd+K — Comp settings
- Ctrl+Y / Cmd+Y — New solid (Ctrl+Shift+Y / Cmd+Shift+Y for solid settings)
- Ctrl+Alt+Y / Cmd+Opt+Y — New adjustment layer
- T — Opacity, P — Position, S — Scale, R — Rotation, A — Anchor Point
- U — Show all keyframes, UU — Show all modified properties
- E — Effects, F — Mask feather, M — Mask path, MM — All mask properties
- L — Audio levels, LL — Audio waveform
- Ctrl+Shift+D / Cmd+Shift+D — Split layer
- Ctrl+D / Cmd+D — Duplicate
- Ctrl+Shift+C / Cmd+Shift+C — Pre-compose
- [ / ] — Trim in/out to playhead
- Alt+[ / Opt+[ / Alt+] / Opt+] — Trim in/out
- B / N — Set work area start/end
- Home / End — Go to beginning/end of comp
- Page Up/Down — Frame by frame
- Shift+Page Up/Down — 10 frames
- Ctrl+Shift+X / Cmd+Shift+X — Crop to comp

**Pro Tips:**
- Pre-compose often and name comps clearly
- Use Null Objects as control layers for expressions
- Enable GPU acceleration in project settings
- Save custom animation presets (.ffx) via Effects panel
- Use Render Multiple Frames Simultaneously for multi-core rendering
- Purge cache: Edit > Purge > All Memory & Disk Cache
- Work with proxies on original footage for faster preview
- Set comp start time to 00:00 not original source
- Use Adjustment Layer for global effects (noise, vignette, color grade)
- Create and save animation presets from any effect stack
### 2.2 Nuke (Foundry)

**Overview:** Industry standard node-based compositor for high-end VFX and film. Used by every major VFX studio.

**Interface:**
- Node Graph: center workspace, nodes connected by pipes
- Viewer: display node tree output in floating panels
- Properties panel: parameters of selected node
- Toolbar: nodes categorized by function
- Curve Editor: animation curves and keyframes

**Node Workflow:**
- Nodes connected left to right (input -> process -> output)
- Read node: import footage (exr, dpx, tiff, png, jpg, mov)
- Write node: export rendered frames
- Merge node: composite A over B or blend mode
- Backdrop node: organize/comment group of nodes
- Dot node: reroute pipes without processing

**Core Nodes:**
- Merge (Over, Under, Plus, Multiply, Screen, Difference, Stencil, Mask, Mat, Min, Max)
- ColorCorrect: lift, gamma, gain, offset, contrast, saturation
- Grade: blackpoint, whitepoint, lift, multiply, offset, gamma
- Reformat: resize, crop, reformat frame
- Transform: translate, rotate, scale, skew (2D)
- CornerPin: 4-point distortion
- Tracker: point tracking, planar tracking
- Keyer: Primatte, IBK, HueKeyer, DifferenceKeyer, LuminanceKey
- RotoPaint: rotoscope shapes (B-Spline, Bezier) and paint with clone/heal/reveal
- Blur: Gaussian, Defocus, VectorBlur, ZBlur
- Denoise: Remove grain, reduce temporal noise
- ZDefocus: depth-of-field based on Z-channel
- RotoShape: animated shape masks (add, subtract, intersect)
- STMap: shader-driven color mapping for complex color transforms
- Constant: solid color background
- CheckerBoard: checker pattern for viewing transparency
- Premult/Unpremult: handle alpha channels

**Deep Compositing:**
- DeepRead/DeepWrite: load/store deep data
- DeepFromFrames: convert multi-exr frames to deep
- DeepMerge: composite deep images
- DeepCrop, DeepTransform, DeepReformat
- DeepToPoints: points cloud from deep image
- Essential for volumetric VFX (fog, smoke, clouds)

**Keying (Chroma Key):**
- Primatte: advanced keying with replace, refine, garbage matte
- IBK (Image Based Keying): Color, Garbage, Core, Edge mattes
- HueKeyer: key on hue range
- DifferenceKeyer: key difference between clean plate and footage
- Keyer: simple luminance/chroma/RGB key
- KeyMix: composite key with softness, spill suppression

**Tracking & Stabilization:**
- Tracker: 2D/4 corner/planar/Bezier tracking
- PlanarTracker (based on mocha)
- CameraTracker: 3D camera solve from footage, point cloud export
- LensDistortion: analyze/solve lens distortion
- MatchGrade: color match tracked surface

**3D System:**
- Scene: container for 3D objects
- Camera: perspective, focal length, filmback, clipping planes
- Light: point, directional, spot, ambient
- Card: 2D image mapped on 3D card
- Sphere, Cube, Cylinder: basic geometry
- ReadGeo: import OBJ, FBX, Alembic, USD
- Modeler: create/edit geometry
- ScanlineRender: render 3D scene (with motion blur, depth of field, shadows)
- Projection3D: project 2D footage onto 3D geometry
- RayRender: ray-traced rendering

**Animation:**
- Curve Editor: Bezier animation curves
- Copy/Paste Keyframes
- Curve tool: set key, edit tangent handles
- Expression: Tcl/Python-based parameter linking
- Animation menu: bake, retime, sample

**Scripting & Automation:**
- TCL: legacy scripting language in Nuke
- Python: modern API for pipeline integration
- Gizmo: custom node groups saved as .gizmo
- Custom knob creation
- NDK: C++ plugin development
- Hiero: conform, timeline, versioning for Nuke

**Output:**
- Write node: EXR (multipart, multi-channel), DPX, TIFF, PNG, JPEG, MOV, CinemaDNG
- EXR settings: compression (PIZ, ZIP, RLE, DWAA, DWAB), data type (half, float, uint8), multichannel, multilayer
- Frame range, resize, bit depth, colorspace
- Proxy rendering for test shots

**Pro Tips:**
- Tab menu to search and create any node
- Ctrl+/ = node graph search
- Use B (backdrop) to group node trees
- Stick to consistent naming convention (node_type_description)
- Render in EXR format with separate AOV passes
- Use Viewer Input buttons to toggle between node outputs
- Script saves checkpoints to .nuke autosave
- Lens distortion tracked must be applied before 3D camera tracking

---

### 2.3 Fusion (DaVinci Resolve)

**Overview:** Node-based compositor built into DaVinci Resolve (also standalone Fusion). Equivalent to Nuke in capability.

**Workflow (covered in DaVinci Resolve section):**
- Node graph editor inside Resolve
- Text+ for titling
- Planar tracker, camera tracker, keying
- 3D compositing with camera, lights, renderer
- Macros for reusable node trees
- Loader/Saver nodes
- Time nodes: Time Speed, Time Stretch, Retime
- Particle system: pEmitter, pRender, pFollower
- Paint, Clone tools

---

### 2.4 Apple Motion

**Overview:** Real-time motion graphics compositor for macOS. Creates FCP X titles, effects, generators, transitions.

**Key Features:**
- Canvas-based interface
- Behaviors (parameter animation without keyframes): throw, gravity, wind, snap align, random motion, oscillator, fade in/out, motion tracking, match move
- Keyframes also available via Keyframe Editor
- Particles: Cell emitter, shape, scale, speed, birth rate, color over life
- Replicator: multi-cell pattern (grid, circle, line, wave, burst)
- Filters: over 180 (bloom, glow, blurs, distortions, keying)
- 3D: camera, lights, groups, 3D text extrusion (bevel, chamfer)
- Generators: gradient, noise, checkerboard, circles
- Shapes: mask (B-Spline, Bezier), shape (rectangle, oval, round)
- Audio: import, waveform visible, audio parameter behaviors
- Text: advanced formatting, glow, outline, drop shadow, 3D text
- Library templates for FCP X

**Export:**
- Publish as .motion template (installs into FCP X)
- QuickTime export: ProRes, H.264, Animation
- Image sequence: TIFF, PNG, JPEG, DPX, OpenEXR

---

## 3. COLOR GRADING

### 3.1 Color Theory

**Color Attributes:**
- Hue: the color itself (red, green, blue, yellow, etc.), measured in degrees on color wheel (0-360)
- Saturation: intensity / purity of color (gray = 0%, pure = 100%)
- Luminance / Value: brightness (black = 0, white = 100)

**Color Wheel:**
- Primary colors: Red, Green, Blue (RGB — additive)
- Secondary colors: Cyan, Magenta, Yellow (CMY — subtractive)
- Complementary: opposite each other on wheel — Red/Cyan, Green/Magenta, Blue/Yellow
- Analogous: adjacent colors (Blue, Teal, Green) — harmonious look
- Triadic: three equally spaced colors — vibrant and balanced
- Split Complementary: base + two adjacent to complement — contrast without tension
- Tetradic (Rectangle): four colors — rich but needs careful balancing

**Color Temperature:**
- Warm: red/orange/yellow (candlelight, sunset, tungsten ~3200K)
- Cool: blue/cyan (shade, overcast, daylight ~5600K)
- White Balance: adjust temperature/tint to neutralize color casts

**Film Color Theory:**
- Teal/Orange blockbuster look: skin tones pushed orange, shadows pushed teal — strong contrast
- Desaturated shadows with saturated highlights
- Color contrast for storytelling: blue for melancholy, warm for intimacy, green for sickness/envy, red for danger/passion
### 3.2 Primary vs Secondary Correction

**Primary Correction:**
- Adjusts entire image globally
- White balance, exposure, contrast, saturation
- Lift/Gamma/Gain (shadows/midtones/highlights)
- Sets the foundation before secondary work
- Done first in grading workflow

**Secondary Correction:**
- Targets specific areas or color ranges
- Uses qualifiers (HSL), power windows, or masks
- Color grading individual objects, faces, sky, clothing
- Selective saturation, hue shift, luminance adjustment
- Isolates with matte and refines with blur/smoothing

### 3.3 HDR Grading

**HDR Standards:**
- HDR10: static metadata, PQ ST.2084, 10-bit, up to 10,000 nits (typically capped at 1,000-4,000)
- HDR10+: dynamic metadata per-frame, PQ, 10-bit
- Dolby Vision: dynamic metadata, PQ, 12-bit, up to 10,000 nits, tone mapping for SDR
- HLG (Hybrid Log-Gamma): broadcast HDR, backward compatible with SDR

**HDR Workflow:**
- Monitor with HDR reference display (1,000+ nits peak brightness)
- Color space: Rec.2020 primary colors (wider than Rec.709)
- Use HDR scopes (Stops mode in Resolve)
- HDR wheels for luminance zone control
- Reference level: often 100 nits for SDR base
- Peak highlight up to 1,000-4,000 nits
- HDR-to-SDR trim passes for simultaneous delivery

**PQ (Perceptual Quantizer):** ST.2084 — maps absolute luminance values (0-10,000 nits) into 10/12-bit code values with perceptually uniform distribution

**HLG (Hybrid Log-Gamma):** OETF that allocates half the signal to lower half of luminance range; backward compatible on SDR displays

### 3.4 LUTs (Look Up Tables)

**1D LUT:**
- Maps one input value to one output value
- Only affects the luminance curve (gamma)
- Cannot change saturation or hue independently per color channel
- Simple, small file size (.cube, .lut)

**3D LUT:**
- Maps RGB input to RGB output in 3D space
- Controls luminance, hue, saturation independently
- Mesh grid size: 17x17x17 (minimal), 33x33x33 (standard), 65x65x65 (high quality)
- Color transforms: Rec.709/Rec.2020, S-Log/Rec.709, etc.

**LUT Types:**
- Technical LUT (Input LUT): convert log/flat to Rec.709 or working color space
- Creative LUT (Look LUT): stylized color grade (film emulation, teal/orange, bleach bypass)
- Camera LUT: manufacturer-provided for specific camera/log

**Create LUTs:**
- Grade one reference frame perfectly
- Export as .cube from Resolve (Color > Export LUT)
- In Premiere: right-click adjustment/effect > Export LUT
- LUT Calc for technical LUTs

**Apply LUTs:**
- Input LUT: applied in camera RAW settings
- Look LUT: on adjustment layer or color page node
- Output LUT: applied at render for destination color space
- Monitor LUT: for calibration/display

### 3.5 Scopes

**Waveform:**
- Y-axis: luminance (0-100 IRE for SDR, 0-1023 for digital)
- X-axis: horizontal position in frame
- RGB mode: individual red/green/blue channels overlaid
- Luma mode: luminance only
- Parade mode: R, G, B displayed side-by-side separated
- Use: check exposure, balance highlights, level skin tones (~45-70 IRE)

**Vectorscope:**
- Circular display: color wheel projected
- Radial distance from center = saturation
- Angle = hue (R=0, Y=60, G=120, C=180, B=240, M=300)
- Flesh Tone line: diagonal line at ~116 degrees — skin tone sits along this
- Graticule targets: broadcast-legal saturation limits
- Use: check color cast, skin tone accuracy, hue consistency

**Histogram:**
- X-axis: luminance from 0 (black) to 255/1023 (white)
- Y-axis: pixel count at each luminance level
- RGB colors overlaid
- Use: check tonal distribution, clipping (shadows left, highlights right), exposure

**Parade (RGB Parade):**
- Three separate waveform displays for R, G, B
- Side-by-side
- Use: white balance — align red/green/blue peaks together

### 3.6 Skin Tone Correction

**Skin Tone Line:** On vectorscope, skin tones line up on an axis from center to about 11 o'clock (approx. 116 degrees — between yellow and red)
- Warm skin tends toward yellow
- Cool skin toward magenta
- Fix green/magenta casts on skin: shift hue toward flesh line

**Process:**
1. Qualifier: select skin tones with HSL range
2. View matte: ensure clean isolation
3. Adjust Hue vs Hue curve: shift skin to pleasing warmth
4. Use color wheels: tweak gamma/midtone toward desired warmth
5. Avoid clipping skin — keep luminance 55-75 IRE for typical Caucasian, adjust for other skin tones

### 3.7 Matching Shots

**Techniques:**
- Scopes matching: overlay waveform of both shots; adjust lift/gamma/gain until they align
- Reference frame: grade a golden frame, then match all shots to it
- Auto-match: Resolve has shot matching, Premiere Lumetri Match
- Manual: use RGB parade to align white/black points, adjust gamma for midtones
- Lightbox/Comparison View: side-by-side or split-screen with reference grade

**Match Elements:**
- Black point (shadows), White point (highlights), Midtones (gamma), Color cast (global hue/saturation), Contrast ratio

### 3.8 Film Emulation

**Kodak Film Stocks:**
- KODAK 2383: standard theatrical print film — warm highlights, green shadows, crushed blacks
- KODAK 2393: for digital intermediate — slightly cooler, lower contrast
- KODAK 2389: softer, pastel tones
- KODAK Vision3 500T 5219: tungsten balanced, high speed, grain texture
- KODAK 5207 (250D): daylight balanced, fine grain
- KODAK EKTACHROME 100D: reversal film, vibrant saturation, punchy
- KODACHROME: warm, high saturation, deep blacks

**Fuji Film Stocks:**
- FUJI ETERNA: teal/green shadows, natural skin tones, lower saturation
- FUJI PRO 400H: portrait film, soft contrast, muted warmth
- FUJI VELVIA: slide film, extremely high saturation, sharp contrast
- FUJI SUPERIA: consumer film, warm, increased saturation

**Film Grain:**
- Perceptual grain from film stock emulation (Grain35, FilmConvert, Dehancer)
- Adjust grain amount, size, softness
- Match grain to original film stock characteristics
- Use grain to unify CGI with live action

**Film Emulation Process:**
1. Convert log to Rec.709 (technical transform)
2. Apply film print LUT (e.g., Kodak 2383)
3. Adjust exposure and contrast to match
4. Apply halation / bloom effect (light bleeding into shadows)
5. Grain overlay matching intended stock
6. Sometimes gate weave / film shake for authenticity

### 3.9 Log Footage

**Log Formats (Camera Log):**
| Manufacturer | Format | Gamma | Color Gamut |
|---|---|---|---|
| Sony | S-Log2, S-Log3 | S-Gamut, S-Gamut3, S-Gamut3.Cine |
| Canon | C-Log, C-Log2, C-Log3 | Canon Log Gamut |
| Panasonic | V-Log, V-Log L | V-Gamut |
| RED | RED Log3G10, REDLog | REDWideGamutRGB |
| Blackmagic | Blackmagic RAW (BRAW) | DaVinci Wide Gamut |
| ARRI | Log C (EI800/1600) | ARRI Wide Gamut |
| Fujifilm | F-Log, F-Log2 | F-Gamut |

**Log Properties:**
- Flatter contrast curve preserves highlight/shadow detail
- Higher dynamic range capture (12-18+ stops)
- Requires color space transform for viewing
- Not meant for final viewing — must be graded

**Log Workflow:**
1. Apply Input Device Transform (IDT) to map log to working space
2. Working in DaVinci Wide Gamut / ACEScct for flexibility
3. Primary grade: correct exposure, white balance
4. Apply creative look
5. Output transform: mapping to Rec.709 / Rec.2020 / P3-D65

**RED RAW:**
- .r3d files — compressed RAW from RED cameras
- ISO, white balance, color science (IPPM2, etc.) adjustable in RAW settings
- Resolution scaling (full/2K/4K/5K/6K/8K)
- REDCODE compression (3:1 to 22:1)
- IPP2 Pipeline: Camera Raw -> G2G (Gamut to Gamut) -> Tones -> Output

**BRAW (Blackmagic RAW):**
- .braw files — compressed RAW from Blackmagic cameras
- Constant quality / constant bitrate encoding
- Decode quality: full res, half, quarter for performance
- ISO, WB, tint adjustable in RAW panel
- Film Dynamic Range (normal/extended video)

---

## 4. AUDIO EDITING

### 4.1 Adobe Audition

**Overview:** Professional digital audio workstation for recording, editing, mixing, restoration, and mastering. Tight integration with Premiere Pro via Dynamic Link.

**Interface:**
- Waveform Editor: single-track destructive/non-destructive editing
- Multitrack Session: track-based mixing, effects, automation
- Spectral Frequency Display: visualize audio frequencies over time
- Essential Sound panel: audio type (dialogue, music, SFX, ambience)
- Effects Rack: insert effects per track/clip
- Mixer: track faders, pan, sends, bus routing, master

**Multitrack Editing:**
- Tracks: audio, bus, master, submix
- Clip editing: split (Ctrl+K / Cmd+K), trim, fade (crossfade), gain
- Comping: take lanes for multiple takes, comp best parts
- Automation: read/write/latch/touch per track
- Pitch and time stretching (Real-Time, High Quality, iZotope Radius)
- Clip effects: per-clip FX vs track FX

**Spectral Editing:**
- Spectral Frequency Display view
- Spot healing brush: remove specific frequencies (cough, buzz, click) by painting on spectrogram
- Lasso selection: select and remove/attenuate noise
- Marquee: rectangle selection for frequency/time ranges
- Manipulate: cut, copy, paste, silence, generate noise
- Essential for forensic audio restoration
**Noise Reduction:**
- Noise Reduction (adaptive): sample noise print, reduce noise floor
- DeNoise: AI-powered broadband noise removal
- DeReverb: AI-powered reverb reduction
- DeEsser: remove sibilance (S and T sounds)
- Click/Pop Eliminator: automatic or manual click removal
- Clip Restoration: declip distorted audio
- Remove Hum: notch filter for 50/60Hz hum and harmonics
- Sound Remover: remove specific sounds by sampling
- Spectral DeNoise: frequency-dependent noise reduction

**Effects:**
- Dynamics Processing: compressor/limiter/gate with envelope editor
- Parametric Equalizer: 8/30 bands, filters (HP/LP/notch/shelf), real-time analyzer overlay
- Graphic Equalizer: 10/20/30 bands
- Reverb: convolution (impulse response), studio reverb, room, hall, plate
- Delay: echo, multitap, delay with feedback
- Chorus, Flanger, Phaser, Distortion
- Pitch Shifter: transpose, formant preservation
- Mastering: Multiband Compressor, Limiter, Exciter, Loudness Meter
- Amplitude and Compression: Amplify, normalize, fade, gain envelope

**Matching Loudness:**
- Essential Sound > Dialogue > Loudness
- Match Loudness panel: target LUFS, tolerance
- ITU-R BS.1770 loudness standard (Integrated -23 LUFS for broadcast, -14 LUFS for web/YouTube/Spotify)
- Measure: Integrated LUFS, Short-term LUFS, Momentary LUFS, True Peak, Loudness Range (LRA)

**Audio to Video:**
- Dynamic Link with Premiere Pro
- Edit audio in Audition with changes reflected in Premiere
- Multi-track session from Premiere sequence
- Automatically match audio clips with video timeline
- Render and replace for final mix

**Export:**
- Multitrack > Export Multitrack Mix: entire mix, stems, selected tracks
- Waveform: Save As (WAV, AIF, MP3, FLAC, AAC, OGG)
- Sample rate conversion, bit depth, dither options
- Broadcast Wave: iXML metadata for film/TV
- Adobe Media Encoder integration

**Shortcuts:**
- Space — Play/Pause
- I/O — In/Out
- Ctrl+Shift+Space — Play from playhead
- Ctrl+Z / Cmd+Z — Undo
- Ctrl+U — Normalize
- Ctrl+R — Reverb
- Ctrl+P — Parametric EQ

---

### 4.2 Pro Tools (Avid)

**Overview:** Industry standard DAW for professional music recording, film/TV audio post, and sound design. Used in major studios worldwide.

**Interface:**
- Edit Window: timeline, tracks, clips, automation
- Mix Window: faders, inserts, sends, I/O, bus routing
- Transport: play, record, loop, shuttle
- Tracks: Audio, MIDI, Aux, Master Fader, VCA Master, Instrument
- Clip List: all audio regions in session
- Edit Modes: Shuffle, Spot, Slip, Grid
- Edit Tools: Trim, Selector, Grabber, Scrubber, Pencil, Smart Tool

**Recording:**
- Track types: Mono, Stereo, Multi-channel (5.1, 7.1, Atmos)
- Input monitoring: Auto, Input, Auto Input Monitor
- Punch recording: quick punch, loop record, destructive record
- Playback engine: hardware buffer size (64-1024 samples), H/W buffer for latency
- Disk allocation: set record paths per drive for multi-channel tracking

**Editing:**
- Clips (regions) — trim, separate, consolidate, mute
- Crossfade creation: Auto (fades at edit boundaries)
- Elastic Audio: real-time time-stretch/pitch (polyphonic, monophonic, rhythmic, Varispeed)
- Beat Detective / Elastic Time: quantize transients, groove extraction
- Strip Silence: remove silence between sounds
- Tab to Transient (Grabber + Tab): navigate transients
- Playlist comping: create comp track from multiple takes
- AudioSuite: non-real-time processing (EQ, dynamics, pitch, reverb, time compression)

**Mixing:**
- Mix Window: track strips with fader (dB scale), pan, mute/solo
- Inserts: up to 10 per track (A-E slots), real-time plug-ins
- Sends: up to 10 per track, bus routing, pre/post fader
- I/O Setup: input/output bus paths, hardware mapping
- Busses: internal routing for subgroups, effects sends, sidechains
- Automation: Read, Write, Latch, Touch, Off — per track/parameter
- Automation lanes: volume, pan, mute, plug-in parameters
- VCA Master: group faders control multiple tracks via VCA

**Surround Sound:**
- Up to 7.1.2 Dolby Atmos mixing
- Dolby Atmos Music Panner
- Object-based mixing with bed channels
- Binaural monitoring
- Output to Dolby Atmos Renderer

**MIDI:**
- MIDI tracks vs Instrument tracks
- MIDI editor: piano roll, notation view
- Virtual instruments (VI): via Instrument track insert
- MIDI CC automation, aftertouch, pitch bend

**Time & Tempo:**
- Time signature and tempo maps
- Tempo Events: gradual/cardinal changes
- Meter changes
- Conform tempo to audio via Beat Detective
- Tick-based vs sample-based tracks

**Video:**
- Import video file (QuickTime, MXF)
- Video track window
- Spot audio to video timecode
- Pull up/pull down for film-to-video conversion (0.1% speed change)
- Support for AAF/OMF import from NLEs

**Shortcuts:**
- Space — Play/Stop
- 3 — Record
- Ctrl+Space / Cmd+Space — Record (if enabled)
- E — Trim tool
- R — Grabber
- T — Selector
- Y — Scrubber
- F6 — Mix window
- Ctrl+= / Cmd+= — Edit window
- Alt+= / Opt+= — Zoom toggle
- P — Zoom presets
- Ctrl+[ / Cmd+[ — Zoom out
- Ctrl+] / Cmd+] — Zoom in
- ; — Memory location

**Pro Tips:**
- Save session copy with all audio for archiving
- Use low buffer (64/128) for recording, high (512/1024) for mixing
- Organize tracks into groups (drums, guitars, vocals, etc.)
- Print effects (commit) to save CPU
- Use clip gain before fader for fine volume control
- AAF import from Premiere/Avid for post-production

---

### 4.3 Logic Pro X (Apple)

**Overview:** Apple's professional DAW for music production, mixing, and mastering. Known for extensive instrument and effect library.

**Interface:**
- Tracks area: arrange window, tracks, regions
- Editor pane: piano roll, score, step editor, audio editor
- Mixer: channel strips, inserts, sends, automation
- Smart Controls: mapped parameters per track
- Library: patches, presets, instruments, effects
- Browser: loops (Apple Loops), audio files, project files

**Features:**
- Software Instruments: Alchemy (powerful synth), EXS24/Sampler, ES2, Retro Synth, Vintage B3/Clav/EP, Drum Kit Designer, Drummer
- Drummer: AI session drummer, multiple genres, fills, complexity
- Track Stacks: summing stacks (bus grouping), folder stacks (collapsible)
- Flex Time & Pitch: time-stretch, flex pitch correction, vari-speed
- Step Sequencer: pattern-based beat creation
- Audio FX: Channel EQ, Compressor (7 models), Space Designer (convolution reverb), Delay Designer, Vintage EQs/Compressors, Distortion, Modulation, Multipressor, Adaptive Limiter
- MIDI FX: Arpeggiator, Chord Trigger, Transposer, Modulation
- Pitch Correction: Flex Pitch individual note editing, Pitch Correction plugin
- Automation: track/region parameter automation, curve editing
- Drummer loops to full arrangement
- Remix FX: DJ-style effects
- Live Loops: Ableton Live-style clip launching
- Ableton Link: sync with other devices/software

**Mixing in Logic:**
- Channel EQ visualizer for frequency analysis
- Compressor seven types: Platinum, Studio, Vintage VCA/FET/Opto, Classic VCA, VCA (1176/LA-2A emulations)
- Buss compression: glue tracks with stereo buss compressor (Vintage Opto)
- Reverb: Space Designer (IR), Platinum Verb, EnVerb
- Delay: Delay Designer (multi-tap), Tape Delay, Stereo Delay
- Sidechain: in compressor parameters — key input source
- Pre-mastering: Multipressor, Adaptive Limiter, Loudness Meter
- Surround mixing: up to 7.1.2, Dolby Atmos support

**Mastering:**
- Multipressor: multiband dynamics (4 bands)
- ChromaVerb: algorithmic reverb for depth
- Multimeter: level, goniometer, correlation, loudness, frequency analysis
- Loudness Meter: LUFS, True Peak, dynamics, momentary/short-term/integrated
- Adaptive Limiter: maximize loudness with oversample protection
- Match EQ: match frequency spectrum of reference track
- SPAT: immersive/spatial audio for Dolby Atmos

---

### 4.4 FL Studio (Image-Line)

**Overview:** Beat production powerhouse. Pattern-based sequencer, strong for electronic music and hip-hop.

**Interface:**
- Channel Rack: instrument channels, step sequencer
- Playlist: pattern clips, audio clips, arrangement
- Piano Roll: MIDI editing, comprehensive tools (slide, portamento, chop, strum, arp)
- Mixer: insert tracks, effects, sends, master
- Browser: presets, samples, instruments, plugins

**Features:**
- Step Sequencer: classic beat creation, per-step note, velocity, pan
- Piano Roll: MIDI note editing, chords, auto-scale, RMS velocity, arpeggiate, ghost notes, note tools
- Generators (synths): Sytrus (FM), Harmless (subtractive), Harmor (additive/resynthesis), 3xOsc, FLEX, Sakura (string), Transistor Bass, Drumpad
- Sampler: DirectWave, Slicex (beat slicing), Edison (audio editor/recorder)
- Effects: Param EQ 2, Fruity Compressor, Limiter, Multiband Compressor, Reverb 2, Delay 3/4, Gross Beat (time/pitch gating), Vocodex, Maximus (multiband mastering), Soundgoodizer, Hardcore, Distortion, Pitcher, NewTone
- Automation: internal clips per parameter, in mixer/playlist

**Workflow:**
- Create drum pattern in step sequencer
- Open Piano Roll for melodic/harmonic parts
- Arrange patterns in Playlist
- Mix in Mixer with inserts (each channel routed to separate mixer track)
- Master channel for final processing and mastering
- Export: WAV, MP3, OGG, FLAC, MIDI, project zip

**Pro Tips:**
- Route all drums to one mixer insert for parallel compression
- Sidechain bass to kick with Fruity Envelope Controller / Love Philter
- Use Edison for sampling, recording, loop trimming
- Make great use of ghost notes for complex layering
- Layer multiple kicks/snares for unique drum sounds

---

### 4.5 Ableton Live

**Overview:** Industry standard for electronic music production and live performance. Session View for clip launching, Arrangement View for linear production.

**Interface:**
- Session View: scene-based clip launching, non-linear performance
- Arrangement View: linear timeline for recording/editing
- Browser: instruments, effects, samples, presets
- Clip View: MIDI/Audio clip editing with envelopes
- Mixer: track faders, sends, routing, EQ
- Info View, Status Bar: CPU, memory, tempo, warp mode, global quantize

**Session View:**
- Scenes vertical columns, clips per track
- Launch clips/scenes with MIDI controller
- Follow Actions: automate clip changes
- Capture MIDI: retroactively record improvised MIDI
- Unique to Live — designed for performance

**Audio Editing:**
- Warping: complex warp modes (Beats, Tones, Texture, Re-Pitch, Complex, Complex Pro) for time-stretching
- Warp markers: set anchor points for rhythmic correction
- Slice to MIDI: slice audio at transients, map to MIDI
- Consolidate: render selection to new clip
- Crossfade, fade handles, clip envelopes (volume, pan, transpose)
- Comping: take lanes for multiple takes

**MIDI:**
- Piano Roll, velocity editing, scale-aware grid
- MIDI effects: Arpeggiator, Chord, Scale, Pitch, Velocity, Random
- Note expression: per-note pitch bend, pressure, CC
- Capture MIDI
- MPE support (MIDI Polyphonic Expression)

**Instruments (Built-in):**
- Operator: FM synth (4 operators), Wavetable: wavetable synth with morphing, Analog: subtractive synth, Collision: mallet/percussion physical modeling, Electric: electric piano, Tension: string physical modeling, Drift: modern subtractive, Simpler: sample playback, Sampler: advanced multi-layer sampler, Impulse/ Drum Rack: drum samplers

**Audio Effects:**
- EQ Eight, EQ Three, Compressor (standard, VCA, FET, Opto models), Multiband Dynamics, Gate, Reverb (convolution + algorithmic), Delay (Simple/Ping-Pong/Filter), Phaser, Flanger, Chorus, Frequency Shifter, Overdrive, Amp, Cabinet, Redux (bitcrush), Auto Filter, Auto Pan, Saturator, Corpus (physical modeling resonator), Limiter, Utility (gain/pan/width/phase), Hybrid Reverb, Spectral Resonator, Spectral Time

**Max for Live:**
- Extends Live with custom devices
- LFO: modulate any parameter
- Envelope Follower: amplitude control
- Shaper: envelope/curve modulation
- Convolution Reverb Pro
- Create custom devices with Max/MSP

**Mixing & Performance:**
- Return tracks for reverb/delay sends
- Group tracks for bus processing
- Audio routing: sidechain, send only, pre/post
- Master channel for final processing
- Racks: effect chains, instrument layers, macro knobs
- MIDI mapping, key mapping, Follow Actions, Locators, Tempo follower
- Ableton Link: sync with other devices/networks over WiFi
- Push hardware controller integration

**Export:**
- File > Export: audio/midi
- Format: WAV, AIFF, FLAC, Ogg Vorbis, MP3
- Render: master, individual tracks, selected tracks
- Sample rate, bit depth, dither
- Loop mode for seamless looping
### 4.6 Audio Restoration

**Overview:** Cleaning up degraded, noisy, or damaged audio recordings.

**Common Issues & Fixes:**

**Broadband Noise (Hiss, Hum, Room Tone):**
- Capture noise profile from silent portion
- Apply noise reduction (Spectral subtraction, adaptive filtering)
- Audition: Effects > Noise Reduction / Restoration > Noise Reduction (Process)
- iZotope RX: Voice De-noise, De-hum for 50/60Hz

**Clicks & Pops (Vinyl/digital glitches):**
- Manual: zoom into waveform, paint remove in spectral view
- Automatic: Click/Pop Eliminator (Audition), De-click (iZotope RX)
- Spectral repair: interpolate surrounding frequencies

**Clipping (Distorted Peaks):**
- De-clip: reconstruct clipped samples (iZotope RX, Audition Clip Restoration)
- Prevention: leave headroom (peak at -6dB to -3dB for recording)

**Rumble / Low Frequency Noise:**
- High-pass filter (80Hz for rumble, lower for sub-bass preservation)
- Spectral noise reduction: target low rumbling frequencies

**Crackle:**
- De-crackle (iZotope RX): remove surface noise without affecting content
- Spectral brush for targeted crackle removal

**Wind Noise:**
- High-pass filter: wind is sub-200Hz
- Spectral removal: paint out wind bursts
- iZotope RX De-wind (AI-based)

**Reverb Removal:**
- iZotope RX De-reverb: estimate reverb tail, reduce
- Audition DeReverb
- Convolution reverb inversion (advanced)

**Dialogue Isolation:**
- Center channel extraction (prefer M/S processing)
- iZotope RX Voice Isolation
- Spectral noise reduction preserving voice frequencies (80Hz - 12kHz)

**Tools (Third-party):**
- iZotope RX: industry standard — Spectral Repair, Mouth De-click, De-ess, De-hum, De-wind, De-clip, Ambience Match, Dialogue Isolate, Music Rebalance, Loudness Control
- Cedar: broadcast/forensic restoration — DNS, auto-adaptive
- Accusonus ERA: one-knob noise removal, reverb, plosive, click

### 4.7 Mixing

**Core Elements:**

**EQ (Equalization):**
- High-Pass Filter (HPF): remove frequencies below set point (e.g., HPF vocals at 80Hz to remove rumble)
- Low-Pass Filter (LPF): remove frequencies above (e.g., LPF bass at 8kHz)
- Shelf: boost/cut all frequencies above/below a point (low/high shelf)
- Bell: boost/cut at center frequency with Q (bandwidth)
- Notch: narrow cut for problem frequency (e.g., 2-4kHz harshness)
- Common frequency ranges: Sub (20-60Hz), Bass (60-250Hz), Low Mids (250-500Hz), Mids (500Hz-2kHz), Upper Mids (2-4kHz), Presence (4-6kHz), Air/Brilliance (6-20kHz)
- EQ Tips: subtract before boosting; narrow cuts for problem frequencies; wide boosts for tonal shaping
- Frequency masking: overlapping frequencies between instruments cause muddiness — use EQ to carve space

**Compression:**
- Threshold: level at which compression begins
- Ratio: amount of compression (e.g., 4:1 = for every 4dB above threshold, output increases 1dB)
- Attack: how fast compressor reacts (fast = catch transients; slow = let punch through)
- Release: how fast compressor stops (fast for rhythmic content; slow for smooth)
- Knee: how gradually compression engages (hard knee = aggressive; soft knee = gentle)
- Make-up Gain: compensate level reduction
- Types: VCA (versatile, fast), FET (fast, aggressive), Opto (smooth, slow), Vari-Mu (tube, musical)
- Parallel Compression: mix compressed signal with uncompressed for punch + density
- Sidechain: compressor triggered by external source (ducking)

**Reverb:**
- Types: Room (small, natural), Hall (large, lush), Plate (smooth, dense), Spring (twangy, surf), Convolution (captured from real spaces via IR)
- Parameters: Decay Time (RT60), Pre-delay (space before reverb onset), Diffusion (density), Wet/Dry mix, Damping (high-frequency absorption)
- Use: send tracks to aux bus with reverb for cohesive space

**Delay (Echo):**
- Timing: sync'd to tempo (1/4 note, dotted 1/8, etc.)
- Feedback: number of repeats
- Types: Digital (clean), Analog (warm, degraded), Tape (wobble, saturation), Ping Pong (alternating stereo)
- Slapback: single 30-120ms delay — classic rockabilly/vocal

**Panning:**
- Left/Center/Right placement for spatial clarity
- LCR (Left-Center-Right) for maximum separation
- Kick, Snare, Bass, Lead Vocal: center
- Hi-hat, Cymbals, Percussion: hard/wider
- Guitars, Keys, Pads: spread left-right

**Stereo Width:**
- M/S (Mid-Side) processing: adjust stereo width
- Stereo Imager / Widener (caution: phase issues)
- Double tracking (record twice, hard pan L/R)
- Haas Effect: 10-30ms delay on one side (can cause comb filtering)
- Reverb on returns for width

### 4.8 Mastering

**Overview:** Final polish of mix for consistent loudness, translation across playback systems, and format delivery.

**Process:**
1. Reference Tracks: compare with commercial masters in same genre
2. EQ: subtle tonal balance corrections (high shelf for air, low shelf for weight)
3. Compression: gentle bus compression (1.5:1 to 2:1, slow attack, auto release) for glue
4. Multiband Compression: control specific ranges (control sub without affecting vocals)
5. Limiting: peak ceiling at -0.1 to -1.0dBTP (True Peak), gain staging up to desired LUFS
6. Loudness: target -14 LUFS integrated (streaming), -9 to -10 LUFS (radio), -8 to -12 LUFS (general)
7. Stereo Enhancement: widen parts, mid-side EQ

**LUFS (Loudness Units relative to Full Scale):**
- Integrated LUFS: average over entire track
- Short-term LUFS: rolling 3-second window
- Momentary LUFS: rolling 400ms window
- True Peak: inter-sample peak detection (dBTP)
- LRA (Loudness Range): variance between quiet and loud parts
- Standards: -23 LUFS (broadcast), -14 LUFS (streaming), -9 to -10 LUFS (loud radio master)
- Measurement tool: Youlean Loudness Meter, iZotope Insight, Waves WLM

**Stereo Widening:**
- M/S EQ: different EQ for center vs sides
- Stereo imager: add width without phase issues
- Caution: mono compatibility -> check phase correlation meter

**Delivery Formats:**
- WAV: 48kHz/24-bit for video, 44.1kHz/16-bit for CD
- AIFF: identical to WAV but different container
- FLAC: lossless compression
- MP3: 320kbps for streaming; 192kbps for podcast
- AAC: preferable for Apple/streaming (264-320kbps)
- DSD: high-resolution audiophile format

**Loudness Normalization:**
- Streaming platforms normalize loudness: Spotify -14 LUFS, Apple Music -16 LUFS (with sound check), YouTube -14 LUFS, Tidal -14 LUFS
- Master at -1.0dBTP True Peak to avoid distortion after lossy encoding
- True Peak Limiter ensures inter-sample peaks don't exceed ceiling

### 4.9 Foley & Sound Design

**Foley:** Art of creating custom sound effects in sync with picture. Recorded in studio while watching video.

**Foley Categories:**
- Footsteps: different surfaces (concrete, wood, carpet, gravel, grass, snow) recorded with various shoes
- Rustle: cloth movement, fabric shifts, leather creaks
- Props: doors, keys, guns, swords, glasses, cutlery, paper
- Specifics: punches, body falls, slaps, kisses, drinking
- Materials: cloth, cellophane, leaves, water

**Foley Process:**
1. Watch picture, identify required sounds
2. Gather props and surfaces
3. Record with high-quality mic (Schoeps, Sennheiser 416, Neumann KM184)
4. Perform to picture in real-time
5. Edit takes in DAW (align to video, remove extraneous noise)
6. Layer and process (EQ, reverb, pitch) to match scene

**Sound Design Techniques:**
- Layering: multiple sounds combined for a new effect (gunshot = recorded gun + low thud + metal ping + debris scatter)
- Pitch shifting: adjust for variety/weight
- Reversing: reversed audio for surreal/ethereal effects
- Time-stretching: extreme stretch for drones/atmospheres
- Convolution Reverb: place sounds in physical spaces
- Granular Synthesis: scatter grain samples for texture
- Synthesis: design from scratch with oscillators, filters, LFOs
- Field Recording: capture real-world ambience (forest, city, subway, rain)
- Foley pits: gravel pit, water tank, door wall, stair sections

**Sound Design Categories:**
- Ambience/Atmosphere: room tone, nature, city, mechanical hum, wind, rain
- Hard Effects (SFX): guns, explosions, vehicles, doors, impacts
- Interface/UI: clicks, beeps, swooshes, notifications
- Creature/Monster: combination of animal vocals, processed foley, layering
- Magic/Sci-fi: synthesis, manipulated recordings, reversed audio
- Weapons: real weapons + tonal layers + impacts + whoosh passes

**Spectral Processing:**
- Resynthesize audio from spectrogram image (Photosounder, MetaSynth)
- Frequency shifting, ring modulation for metallic sounds
- Comb filtering for robotic effects
- Vocoding for synthesized speech effects

**Software:**
- Krotos: Reformer Pro (AI Foley), Weaponiser, Dehumaniser
- Boom Library: premium sound effect libraries
- Soundminer / Basehead: SFX library management and search
- Pro Tools / Reaper / Nuendo: primary DAWs for sound design
- Kyma: dedicated sound design hardware/software system

---

## 5. PHOTO EDITING

### 5.1 Adobe Photoshop

**Overview:** Industry standard for raster image editing, compositing, retouching, and graphic design.

**Interface:**
- Menu Bar: File, Edit, Image, Layer, Type, Select, Filter, 3D, View, Window, Help
- Options Bar: context-sensitive tool options
- Tools Panel: 60+ tools organized in groups
- Panels: Layers, Channels, Paths, History, Actions, Adjustments, Properties, Library, Brushes, Swatches, Color, Info, Navigator, Character, Paragraph, Tool Presets, Layer Comps, Styles

**Layers:**
- Layer types: Pixel, Adjustment, Fill, Shape, Type, Smart Object, Video, 3D, Background
- Layer groups: organize with folder structure (Ctrl+G / Cmd+G)
- Layer masks: white = visible, black = hidden, gray = partial
- Clipping masks: layer uses transparency of layer below
- Smart Objects: embedded/linked files (raw, vector, other PSD) — non-destructive scaling, filters
- Layer comps: save different layer visibility/position/appearance states
- Blending modes (see below)

**Blending Modes:**
- Normal, Dissolve
- Darken: Darken, Multiply, Color Burn, Linear Burn, Darker Color
- Lighten: Lighten, Screen, Color Dodge, Linear Dodge (Add), Lighter Color
- Contrast: Overlay, Soft Light, Hard Light, Vivid Light, Linear Light, Pin Light, Hard Mix
- Inversion: Difference, Exclusion, Subtract, Divide
- Component: Hue, Saturation, Color, Luminosity
- Pass Through (for groups)

**Selection Tools:**
- Marquee: Rect/Ellipse (Shift = constrain/proportion)
- Lasso: freehand, polygonal (click points), magnetic (edge detection)
- Quick Selection: paint to select (with Auto-Enhance)
- Magic Wand: select by color/tone with Tolerance setting
- Object Selection: AI-based object recognition, rectangle/lasso mode
- Select Subject: AI-powered one-click subject selection
- Select Sky: AI-powered sky selection
- Color Range: select specific colors/skin tones/subject via sampled colors
- Focus Area: select in-focus portions
- Refine Edge / Select and Mask: refine hair/fur, separate foreground
- Pen Tool (Paths): precise vector path creation -> convert to selection
- Quick Mask Mode: paint selection with brush (red overlay)

**Pen Tool Mastery:**
- Click = corner point; Click+drag = smooth point (Bezier handles)
- Hold Alt/Opt + click handle = break handles (convert point)
- Ctrl/Cmd = direct selection of path points
- Path Operations: New, Add to, Subtract from, Intersect, Exclude
- Convert to selection: right-click > Make Selection (feather radius)
- Shape layers: vector masks, scalable infinitely

**Adjustment Layers:**
- Non-destructive: adjustments in separate layer above
- Types: Brightness/Contrast, Levels, Curves, Exposure, Vibrance, Hue/Saturation, Color Balance, Black & White, Photo Filter, Channel Mixer, Color Lookup, Invert, Posterize, Threshold, Gradient Map, Selective Color
- Properties panel: per-adjustment controls
- Clipping mask options: affect only layer below
- Layer masks per adjustment

**Camera Raw (ACR — Adobe Camera Raw):**
- Process raw files (.cr2, .nef, .dng, .arw, .orf, .rw2, .raf, etc.)
- Profiles: Adobe Color, Portrait, Landscape, Vivid, Neutral, Standard
- Basic: White Balance, Temp, Tint, Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Texture, Clarity, Dehaze, Vibrance, Saturation
- Curve: Parametric and Point curves (per channel)
- Detail: Sharpening (Amount, Radius, Detail, Masking), Noise Reduction (Luminance/Detail/Contrast/Color)
- HSL Adjustments (Hue/Saturation/Luminance per color)
- Split Toning: color highlights and shadows independently
- Lens Corrections: profile-based (distortion, vignetting, chromatic aberration) + manual
- Calibration: camera profile, shadow tint, color adjustments per primary
- Effects: Grain (Amount, Size, Roughness), Vignette (Post Crop)
- Transform: Auto, Level, Vertical, Full, Guided perspective correction
- Masking: AI-powered — Select Subject, Select Sky, Brush, Linear/Radial Gradient, Color/Luminance/Depth Range
- Presets: user-defined, downloadable
- Neural Filters: Skin Smoothing, Portrait B&W, Style Transfer, Super Resolution, Colorize, Harmonize
- Open as Smart Object for non-destructive raw
**Retouching:**
- Spot Healing Brush: content-aware fill of small blemishes (Content-Aware, Create Texture, Proximity Match)
- Healing Brush: sample source (Alt+click), paint to replace texture + blend
- Patch Tool: draw selection, drag to target area for replacement
- Content-Aware Move: move object, auto-fill original location
- Clone Stamp: exact pixel copy from source (Alt+click) — use on separate layer (Sample: All Layers)
- Red Eye Tool: automatic red eye removal
- Dodge Tool: lighten (Range: Shadows, Midtones, Highlights)
- Burn Tool: darken (same ranges)
- Sponge Tool: saturate/desaturate
- Frequency Separation: high pass on top (texture), Gaussian blur on bottom (color) — retouch texture without affecting color
- Liquify Filter: push/pull pixels (Forward Warp, Reconstruct, Twirl, Pucker, Bloat, Push Left, Freeze/Thaw Mask, Face-Aware Liquify)
- Content-Aware Fill: new layer, marquee select area, Edit > Content-Aware Fill
- Remove Tool: 2023+ — AI removal brush
- Neural Filters: Skin Smoothing, Smart Portrait, Landscape Mixer, Colorize, Harmonize, Super Zoom, Makeup Transfer

**Filters & Effects:**
- Filter Gallery: Artistic, Brush Strokes, Distort, Sketch, Stylize, Texture
- Blur Gallery: Field Blur (variable blur points), Iris Blur (elliptical focal point), Tilt-Shift (miniature effect), Path Blur (motion blur along path), Spin Blur (radial blur)
- Lens Blur: depth-of-field simulation with depth map
- Camera Raw Filter: apply ACR adjustments to any layer
- Adaptive Wide Angle: correct lens distortion with constraint lines
- Vanishing Point: perspective-aware edits and cloning
- Neural Filters: Portfolio — AI-based filters
- Other: High Pass (for sharpening), Custom (convolution), Maximum, Minimum, Offset

**Compositing:**
- Photomerge: Panorama stitching (Auto, Perspective, Cylindrical, Spherical, Collage)
- HDR Pro: Merge multiple exposures (Remove ghosts, Tone, Adjust Details)
- Auto-Align Layers: align layers based on content
- Auto-Blend Layers: blend exposures or focus stack (Panorama, Stack Images)
- Content-Aware Scale: scale image while protecting subject
- Puppet Warp: deform specific areas with pins (mesh density, expansion)
- Perspective Warp: change perspective of specific regions
- Match Color: match color and luminance between layers

**Batch Processing:**
- Actions: record series of steps, play on other files (Window > Actions)
- Batch: File > Automate > Batch (play action on folder)
- Droplet: save action as executable droplet
- Image Processor: File > Scripts > Image Processor (resize, convert format)
- Variables: data-driven graphics

**Export:**
- Save As: PSD, PSB, TIFF, BMP, GIF, JPEG, PNG, TGA, EPS, PDF, PCX, Raw
- Export As: PNG, JPG, GIF, SVG, WebP — image size, quality, metadata, color space
- Save for Web (Legacy): GIF/JPEG/PNG-8 optimization
- Export Layers To Files: individual files per layer
- PDF Presentation: multi-page PDF from layers/files

**Shortcuts:**
- V — Move, M — Marquee, L — Lasso, W — Quick Selection, C — Crop
- I — Eyedropper, J — Spot Healing Brush, B — Brush, S — Clone Stamp
- E — Eraser, G — Gradient, P — Pen, T — Type, A — Direct Selection
- H — Hand, Z — Zoom
- Ctrl+N / Cmd+N — New, Ctrl+O / Cmd+O — Open
- Ctrl+Z / Cmd+Z — Undo, Ctrl+Alt+Z / Cmd+Opt+Z — Step back
- Ctrl+T / Cmd+T — Free Transform
- Ctrl+J / Cmd+J — Layer via Copy
- Ctrl+E / Cmd+E — Merge layers
- Ctrl+I / Cmd+I — Invert
- Ctrl+D / Cmd+D — Deselect, Ctrl+Shift+I — Invert selection
- Ctrl+L — Levels, Ctrl+M — Curves, Ctrl+U — Hue/Saturation, Ctrl+B — Color Balance
- Ctrl+Shift+X — Liquify
- Ctrl+Alt+Shift+E / Cmd+Opt+Shift+E — Stamp visible
- X — Swap colors, D — Default colors
- [ / ] — Brush size, Shift+[ / ] — Brush hardness
- 0-9 — Layer opacity

**Pro Tips:**
- Work non-destructively with Smart Objects and Adjustment Layers
- Masking: use brush with black/white — black hides, white reveals
- Quick Mask (Q): paint selection precisely
- Save selections (Select > Save Selection) for reuse
- Use layer groups for organization
- Frequency separation for clean portrait retouching
- Use Curves with layer mask for local contrast — paint on mask
- Blending mode shortcuts: Alt+Shift+letter cycles
- Camera Raw filter as Smart Filter on any layer
- Content-Aware Scale protects specific areas with Alpha Channel

---

### 5.2 Adobe Lightroom

**Overview:** Professional photo management and raw development. Catalog-based, non-destructive editing.

**Interface:**
- Library Module: import, organize, rate, keyword, filter, face recognition, map
- Develop Module: raw processing, color, tone, effects, detail
- Map, Book, Slideshow, Print, Web Modules

**Catalog:**
- Master catalog (.lrcat) contains edits, keywords, metadata; previews stored separately
- Previews: Minimal, Embedded & Sidecar, Standard (1440px/2560px), 1:1
- Smart Previews: smaller proxy for offline editing
- Virtual Copies: multiple edits of same master without file duplication
- Ratings: 1-5 stars, picks/flags (P), rejects (X), color labels
- Keywords: hierarchical, synonym sets, auto-suggest
- Face Recognition: identify people, group by face
- Metadata presets: for consistent copyright/IPTC
- Filters: text, attribute, metadata
- Collections: manual, smart (auto-filtering rules), collection sets, quick collection
- Publish Services: direct export to Flickr, 500px, Adobe Stock

**Import:**
- Copy: copy files to organized folder structure
- Move: relocate files preserving folder structure
- Add: add to catalog without moving files
- File renaming: template (date-sequence, custom name)
- Apply during import: Develop settings, metadata, keywords
- Backup: make additional copy to backup drive

**Develop Module Workflow:**
1. Basic Panel: White Balance (Temp/Tint), Auto Tone, Exposure, Contrast, Highlights, Shadows, Whites, Blacks
2. Texture, Clarity, Dehaze
3. Vibrance, Saturation
4. Tone Curve: Parametric + Point Curve per RGB channel
5. HSL / Color: Hue, Saturation, Luminance per individual color
6. B&W: Black & White Mix (luminance per color for grayscale)
7. Split Toning: Color highlights and shadows separately with balance
8. Detail: Sharpening (Amount, Radius, Detail, Masking) + Noise Reduction (Luminance, Color)
9. Lens Corrections: Profile corrections + Manual Transform
10. Effects: Post-Crop Vignetting, Grain
11. Calibration: Camera profile, primary channel adjustments

**Local Adjustments:**
- Graduated Filter: linear gradient mask
- Radial Filter: elliptical gradient mask
- Adjustment Brush: paint adjustments with customizable brush
- AI Masking: Subject, Sky, Background, Objects, People (body parts), by Color, Luminance, Depth
- Intersect Masks: combine multiple mask types

**Presets:**
- User presets: save full or partial Develop settings
- Sync/Develop: copy/paste settings across images
- Auto Sync: all selected images update simultaneously
- .xmp presets compatible with Camera Raw

**Denoise (AI):**
- Lightroom Denoise: AI-based noise reduction preserves detail
- Raw Denoise: available for raw files only, produces DNG
- Enhanced Details: improved detail rendering from raw

**Super Resolution:**
- Enlarge raw files 4x (2x width, 2x height) using AI — produces DNG

**HDR & Panorama Merge:**
- Merge bracketed exposures into 32-bit HDR DNG
- Panorama: Spherical, Cylindrical, Perspective

**Export:**
- File > Export (Ctrl+Shift+E)
- File Settings: JPEG, TIFF, PNG, DNG, original
- Image Sizing, Output Sharpening, Metadata, Watermarking
- Export Presets: save frequently used configurations

**Shortcuts:**
- G — Grid, E — Loupe, D — Develop
- L — Lights Out, P — Pick, X — Reject, U — Unflag
- 1-5 — Rating, 6-9 — Color labels
- Y — Before/After, \ — Before/After toggle
- R — Crop, Q — Spot Removal, K — Adjustment Brush
- M — Graduated Filter, Shift+M — Radial Filter
- Ctrl+Shift+C / Cmd+Shift+C — Copy settings
- Ctrl+Shift+V / Cmd+Shift+V — Paste settings

**Pro Tips:**
- Use smart collections for automatic organization
- Develop presets with Masking auto-applied (Subject/Sky)
- Sync multiple images quickly for base corrections
- Virtual copies for different looks (color vs B&W)
- Use Pick flag + star rating for effective culling
- Use Target Adjustment tool in Tone Curve / HSL

---

### 5.3 Capture One (Phase One)

**Overview:** Professional raw processor and image editor, preferred by studio and commercial photographers for tethering and color.

**Key Features:**
- Tethering: best-in-class live capture support for Phase One, Canon, Nikon, Sony
- Color Editor: advanced per-color adjustments with color picker, hue/saturation/lightness curves per color
- Layers & Masks: pixel + vector masks, fill, gradient, radial, brush, luminance range, color selection masks
- Styles & Presets: apply/aspect, comparison
- Lens Correction: hardware-profile matching
- Tonal Grading: master, shadow, midtone, highlight color controls
- Dehaze, Clarity, Structure
- High Dynamic Range: linear curve for RAW processing
- Film Grain / Film Look
- Noise Reduction: luminance, color, detail preservation
- Sharpening: capture sharpening, output sharpening, threshold
- Focus Mask: highlight in-focus areas
- Spot Removal: heal/clone with size and opacity

**Workflow:**
- Sessions (for tethered shoots) or Catalogs (for library management)
- Adjustments: Exposure, Curve, Levels, Color Balance, White Balance
- Local Adjustments: layers with masks for targeted edits
- Export: TIFF, JPEG, PNG, DNG, EIP
- ProStandard ICC profiles for color accuracy

---

### 5.4 Affinity Photo (Serif)

**Overview:** Professional photo editor, strong Photoshop alternative. One-time purchase. Persona-based workflow.

**Personas:**
- Photo Persona: core editing
- Liquify Persona: push/pull pixels, face-aware liquify
- Develop Persona: raw processing
- Tone Mapping Persona: HDR tone mapping
- Export Persona: batch export
- Panorama Persona: stitch panoramas

**Key Features:**
- Live Filters: non-destructive filter layers
- Blend Modes: same as Photoshop plus more (Negation, Reflect, Glow)
- Adjustments: Levels, Curves, HSL, Black & White, Color Balance, Selective Color, Gradient Map, Shadows/Highlights
- Selection: Flood Selection, Selection Brush, Pen tool
- Layers: Pixel, Image, Adjustment, Fill, Shape, Text, Group, Mask, Live Filter
- Masking: layer masks, clipping masks, intensity/luminosity masks
- Raw Processing: Develop Persona
- HDR Merge, Focus Stacking, Denoise (AI)
- Removal / Healing: Clone, Heal, Inpainting Brush
- Macros, Batch Processing
- Plugins: supports some Photoshop plugins (.8bf)
- Vector Tools: blending, boolean, fill, stroke, power duplicate
- CMYK support, 360 image editing, PSD compatibility

**Strengths:** Excellent value (one-time purchase), very fast performance, full CMYK, strong iPad version

---

### 5.5 GIMP (GNU Image Manipulation Program)

**Overview:** Free, open-source raster image editor. Cross-platform (Win/Mac/Linux).

**Key Features:**
- Layers: pixel, text, group, layer masks, layer modes
- Full paint tools: brush, pencil, airbrush, clone, heal, perspective clone
- Selection: rectangle/ellipse, free/lasso, fuzzy (magic wand), by color, foreground select (AI), paths, quick mask
- Paths tool: Bezier curves, stroke path
- Transformations: Scale, Rotate, Shear, Flip, Perspective, Cage, Unified
- Color tools: Levels, Curves, Color Balance, Hue-Saturation, Brightness-Contrast, Threshold, Posterize, Desaturate, Colorize, Channel Mixer, Gradient Map
- Filters: Blur (Gaussian, Motion, Pixelize), Enhance (Sharpen, Unsharp Mask), Distorts, Noise, Edge detect, Light/Shadow, Map, Render
- Scripting: Script-Fu (Scheme), Python-Fu, GIMP Plug-in API
- GEGL: high bit-depth processing, non-destructive layer effects
- Plugins: G'MIC, Resynthesizer (content-aware fill), BIMP batch processor
- Export: PNG, JPEG, GIF, TIFF, PSD, WEBP, HEIF, SVG, EXR, DPX, PDF
- CMYK soft proofing

**Strengths:** Free and open source, scriptable, GEGL 32-bit float processing, vast plugin library
**Weaknesses:** Non-native UI, limited RAW support (needs UFRaw/RawTherapee), no native adjustment layers

---

### 5.6 Snapseed (Google)

**Overview:** Mobile photo editing app (iOS/Android). Free, touch-friendly, powerful for on-the-go editing.

**Key Features:**
- Tune Image (Ambiance, Brightness, Contrast, Saturation, Shadows, Highlights, Warmth)
- Details (Structure, Sharpening), Curves, White Balance
- Selective Adjust (control points for localized edits)
- Healing Brush, Brush (dodge/burn, saturation, temperature, exposure)
- Portrait (face tune, skin glow, focus, lighting), Glamour Glow
- Tonal Contrast, HDR Scape, Drama, Vintage, Grainy Film, Noir, Retrolux, Grunge
- Black & White (with color filters), Frames, Double Exposure, Text, Lens Blur
- Stack: non-destructive layers of edits, reorderable
- Presets: "Looks" section with style filters

---

### 5.7 VSCO

**Overview:** Mobile photography app and community. Known for film-emulation preset filters.

**Key Features:**
- Presets: film-inspired (Kodak, Fuji, Agfa, Ilford emulations)
- Editing: Exposure, Contrast, Sharpen, Saturation, Skin Tone, HSL, Grain, Fade, Vignette, Border, Temperature, Tint
- Split Tone, HSL per color
- SX-70 (Polaroid) style
- Community: profiles, following, reposts
- VSCO Studio (web): edit on desktop, sync to mobile

---

### 5.8 PicsArt

**Overview:** Full-featured mobile editing and social creative platform.

**Key Features:**
- Photo editing: crop, resize, rotate, adjust (brightness, contrast, color, clarity, curves)
- Stickers, text, shapes, clipart
- Cutout tool: AI background removal
- Photo effects: filters, overlays, blur, magic effects, dispersion, glitch
- Collage, Video editing, Photo to sketch, Face editing
- Layer editing (like Photoshop-light)
- Social community feed, Remix
- Pro version: no ads, premium content

---

### 5.9 Pixelmator Pro (macOS)

**Overview:** Powerful image editor for macOS, Mac-native UI. Recently acquired by Apple.

**Key Features:**
- Full layer-based editing with blend modes
- Machine learning: automatic selection, background removal, color adjustments, crop, retouch
- Adjustments: color balance, levels, curves, HSL, black & white, gradient map, selective color, shadows/highlights, grain
- Effects: blurs, distortions, stylize (bloom, comic, halftone, neon, stamp)
- Retouching: Repair tool, Clone tool, Denoise
- Brushes: over 200, full tablet support
- Vector tools: shapes, pen, text, boolean, alignment
- Color: RGB, CMYK, LAB, grayscale
- RAW support, PSD compatibility
- Batch processing, iCloud sync
- Extremely fast on Apple Silicon

---

## 6. 3D MODELING & ANIMATION

### 6.1 Blender

**Overview:** Free, open-source 3D creation suite. Full pipeline: modeling, sculpting, texturing, rigging, animation, simulation, rendering, compositing, video editing, grease pencil.

**Interface:**
- Workspaces: Layout, Modeling, Sculpting, UV Editing, Texture Paint, Shading, Animation, Rendering, Compositing, Geometry Nodes, Scripting
- Areas: 3D Viewport, Timeline, Outliner, Properties, Shader Editor, Node Editor, UV Editor, Image Editor, Video Sequencer
- Properties Panel: Render, Output, View Layer, Scene, World, Object, Modifiers, Particles, Physics, Constraints, Material, Texture, Data
**Modeling:**
- Mesh Primitives: Plane, Cube, Circle, UV Sphere, Ico Sphere, Cylinder, Cone, Torus, Grid, Monkey
- Edit Mode (Tab): vertices, edges, faces selection
  - Extrude (E), Inset (I), Bevel (Ctrl+B), Loop Cut (Ctrl+R), Knife (K), Merge (M), Fill (F), Make Face (Alt+F)
  - Edge: Bridge Edge Loops, Edge Slide, Offset Edge Slide
  - Normals: Recalculate (Shift+N), Flip (Alt+N)
  - Mesh Clean-up: Merge by Distance, Degenerate Dissolve, Delete Loose
  - Transform: Grab (G), Rotate (R), Scale (S) with axis constraint (X/Y/Z)
  - Snap: Vertex, Edge, Face, Increment, Grid
  - Pivot: Median, Individual Origins, 3D Cursor, Active Element, Bounding Box Center
  - Proportional Editing: O — smooth falloff editing
- Modifiers: Subdivision Surface, Mirror, Multiresolution, Boolean, Solidify, Screw (lathe), Skin, Build, Decimate, Remesh, Weld, Bevel, Array, Shrinkwrap, Simple Deform, Warp, Curve, Lattice, Displace, Wave, Cast, Surface Deform, Laplacian Smooth, Smooth, Triangulate, Weighted Normal
- Curves: Bezier, NURBS, paths; convert to mesh
- Grease Pencil: 2D drawing in 3D space — strokes, fill, vertex color, effects, onion skinning, sculpt mode, modifiers (Array, Mirror, Build, Lattice)

**Sculpting:**
- Brushes: Clay Strips, Clay Thumb, Crease, Draw Sharp, Inflate/Deflate, Grab, Elastic Deform, Multi-plane Scrape, Flatten, Fill/Deepen, Scrape/Pinch, Nudge, Rotate, Snake Hook, Thumb, Simplify, Mask, Pose (articulate), Boundary, Box Trim, Lasso Trim, Mesh Filter, Cloth, Slide Relax, Topology, Smooth, Surface, Pinch, Twist
- Symmetry: mirror across X/Y/Z
- Dyntopo (Dynamic Topology): automatic mesh density
- Multiresolution: multi-level detail
- Remesh: uniform, smooth, sharp
- Voxel Remesh: uniform resolution regardless of topology, watertight
- Mask: brush, lasso, box, extract, smooth, inflate
- Face Sets: paint groups for visibility/hide
- Cloth Filter: simulate cloth on sculpt mesh

**UV Mapping:**
- UV Editor: view and edit UVs
- Unwrap: Smart UV Project, Unwrap, Lightmap Pack, Follow Active Quads
- Mark Seams: edges marked as cut lines
- Pin UVs: lock vertices during unwrap
- Texture Atlas multiple objects
- UV Sculpt for adjustment

**Texturing (Shading):**
- Shader Editor (Node-based):
  - Principled BSDF: main surface shader (Base Color, Roughness, Metallic, Specular, Clearcoat, IOR, Transmission, Emission, Alpha, Normal, Subsurface, Anisotropic, Sheen)
  - Diffuse BSDF, Glossy BSDF, Glass BSDF, Transparent BSDF, Emission
  - Mix Shader, Add Shader, Mix RGB
  - Texture Nodes: Image Texture, Noise Texture, Voronoi, Wave, Musgrave, Gradient, Magic, Brick, Checker
  - Input: Ambient Occlusion, Bevel, Camera Data, Fresnel, Layer Weight, Light Path, Normal, Object Info
  - Color: Bright/Contrast, Gamma, Hue/Sat, Invert, MixRGB, RGB Curves
  - Vector: Bump, Displacement, Mapping, Normal Map, Vector Curves, Vector Displacement, Vector Rotate
  - Converter: Math, Map Range, RGB to BW, Separate/Combine XYZ/RGB/HSV
- Texture Paint: paint directly on 3D model in 3D Viewport or UV Editor — brushes, stencils, clone, smear, soften

**Rigging:**
- Armatures: bones (Edit Mode — extrude, subdivide, mirror)
- Constraints: Copy Location, Copy Rotation, Track To, Floor, Limit Location/Rotation/Scale, Stretch To, Child Of, Action, Armature, IK (Inverse Kinematics), Spline IK, Damped Track, Locked Track, Follow Path, Shrinkwrap, Transform
- IK Rig: chain of bones with one IK target, pole target for bending direction
- Weight Painting: vertex weights per bone (paint mode)
- Automatic Weights: from bone heat
- Metarig (Rigify): auto-rig humanoid, generate full control rig
- Driver: drive property from other property via expression
- Shape Keys: per-vertex morph targets (blendshapes)
- Bone Collections: organize bones into groups

**Animation:**
- Keyframes: I — insert keyframe menu (Location, Rotation, Scale, All)
- Auto Keying: auto records keyframes on property change
- Graph Editor: F-Curves, handles (Vector, Auto, Auto Clamped, Free), Modifiers (Cycles, Noise, Generator, Limiter, Stepped)
- Dope Sheet: keyframe overview, Action Editor
- NLA (Non-Linear Animation): combine actions, strips, blending, tracks
- Walk Cycle: create loop cycle, repeat modifier
- Camera Animation: fly/walk navigation, track to constraint
- Path Animation: Follow Path constraint on curve
- Motion Paths: visual path of bone/object over time
- Pose to Pose vs Straight Ahead

**Rendering — Cycles (Path Tracer):**
- CPU + GPU (CUDA, OptiX, Metal, HIP)
- Sampling: samples count, noise threshold, adaptive sampling
- Light Paths: Max Bounces, Diffuse/Glossy/Transmission/Volume Bounces
- Denoising: OptiX (GPU), OpenImageDenoise (CPU)
- Caustics, Subsurface Scattering, Volume (Principled Volume)
- Motion Blur, Depth of Field
- Passes/AOVs: Combined, Diffuse, Glossy, Transmission, Shadow, AO, Normal, Z, Object/Material Index, UV, Mist, Emission, Cryptomatte
- Light Groups: separate light contributions (Studio)

**Rendering — Eevee (Real-time Rasterizer):**
- GPU-only, deferred shading
- Screen-space reflections, refraction, Bloom, DOF, Motion Blur
- Volumetrics, Ambient Occlusion (SSAO)
- Irradiance Volume, Reflection Cubemap
- Fast iterative look development

**Output:**
- File Format: PNG, JPEG, TIFF, OpenEXR (multilayer, half/float), DPX, HDR
- Color Management: Filmic, sRGB, Rec.709, ACES, AgX
- EXR: multilayer with all render passes
- Animation: FFmpeg-based video (H.264, HEVC, ProRes, DNxHD, AV1)

**Compositor (Built-in):**
- Node-based compositing: Render Layers, Input, Output, Color, Converter, Filter, Vector, Matte, Distort, Group
- Cryptomatte for easy matte extraction

**Geometry Nodes:**
- Node-based procedural modeling
- Input: Mesh, Curve, Points, Volume, Instance, Collection, Material
- Operations: Transform, Join, Separate, Subdivide, Triangulate, Merge by Distance, Extrude, Delete Geometry, Set Shade Smooth, Set Material, Distribute Points on Faces, Instance on Points, Realize Instances, Raycast, Sample Nearest
- Fields: Math, Switch, Accumulate Field, Map Range, Color Ramp, Float Curve, Mix
- Utilities: Accumulate Field, Blend, Capture Attribute, Proximity, Attribute Statistic

**Physics & Simulation:**
- Particles: Hair (guide curves + children), Emitter (physics, force fields, collision), Boids
- Cloth: simulation mesh with stiffness, damping, sewing, pressure, self-collision
- Soft Body: deformable mesh, springs, goal, self-collision
- Rigid Body: active and passive, collision shapes, constraints, cache
- Fluid (Mantaflow): liquid (domain, flow, effector) and gas/smoke/fire
- Dynamic Paint: paint from brush objects, particle trails, dissolve
- Force Fields: Wind, Gravity, Magnetic, Turbulence, Vortex, Curve Guide
- Collision: enable object collisions for particle/mesh interaction

**Grease Pencil (2D Animation):**
- 2D drawing in 3D space — strokes, vertex colors, layers, onion skinning
- Effects: thickness, opacity, tint, texture
- Modifiers: Array, Mirror, Build, Lattice
- Animation: keyframe per layer, interpolation

**Video Sequencer (VSE):**
- Strips: Movie, Image, Scene, Sound, Mask, Effect
- Multi-track timeline, proxy rendering, color grading

**Scripting:**
- Python API: full control of Blender data (bpy.context, bpy.data, bpy.ops)
- Add-ons: community, enable/disable, custom development
- UI: panels, menus, operators, properties

**Shortcuts:**
- Tab — Edit mode toggle
- 1/2/3 — Vertex/Edge/Face select
- G — Grab, R — Rotate, S — Scale
- Shift+A — Add, E — Extrude, I — Inset
- Ctrl+B — Bevel, Ctrl+R — Loop Cut, K — Knife
- O — Proportional Editing
- Shift+D — Duplicate, Alt+D — Linked Duplicate
- H — Hide, Alt+H — Unhide
- Z — Viewport shading menu
- N — Properties panel toggle
- M — Merge, P — Separate, Ctrl+J — Join
- Ctrl+P — Parent, Alt+P — Clear parent
- F3 — Search menu

**Pro Tips:**
- Add-ons: Node Wrangler, Auto Mirror, Loop Tools, Bool Tool
- Bake normal maps for high->low poly transfer
- Modifier stack: Mirror -> Subdivision Surface -> Displace
- Export FBX for Maya/Unity, glTF/GLB for web
- Use Collections to organize scene
- Render EXR multilayer for post-grade flexibility
- Combine Cycles beauty + Cryptomatte for easy compositing

---

### 6.2 Autodesk Maya

**Overview:** Industry standard for 3D animation, modeling, rigging, and effects in film, TV, and games.

**Interface:**
- Viewport 2.0: real-time display
- Shelf: customizable tool shortcuts
- Toolbox: Select, Lasso, Move, Rotate, Scale, Universal Manipulator
- Channel Box: attribute values per object
- Layer Editor: display/render layers
- Outliner: scene hierarchy
- Time Slider: animation controls, keyframes
- Attribute Editor: detailed property editing

**Modeling:**
- Polygon: Extrude, Bevel, Bridge, Connect, Insert Edge, Cut, Crease, Reduce, Smooth, Boolean
- Mesh Cleanup, Quadrangulate, Fill Hole, Mirror, Transfer Attributes
- NURBS: CV Curve, EP Curve, Revolve, Loft, Planar, Extrude, Birail, Boundary
- Subdiv Surfaces: hybrid polygon/NURBS
- Sculpting: Brush-based (Grab, Smooth, Clay, Inflate, Flatten, Pinch, Crease)

**Rigging:**
- Joints: hierarchical skeleton joints
- IK Handles: single-chain, rotate-plane, spline IK
- Constraints: parent, point, orient, scale, aim, pole vector, geometry, normal, tangent
- Skinning: smooth bind, rigid bind, interactive skin bind
- Paint Skin Weights: weight painting with brushes
- Blend Shapes: per-vertex morph targets
- Deformers: lattice, cluster, nonlinear (bend, twist, flare, sine, squash), sculpt, jiggle, wire, wrap, blend
- Muscle System: realistic muscle/skin deformation

**Animation:**
- Keyframing: set key (S), auto key
- Graph Editor: curve editing, tangents (spline, linear, stepped, flat, plateau)
- Dope Sheet: keyframe timing
- Animation Layers: non-linear blending
- Motion Trail: visual path preview
- HumanIK: full body IK rig for bipeds
- Time Editor: non-linear animation editing
- Animation Snapshot, Ghosting, Turntable
- Motion Capture import and retargeting

**Dynamics & Effects:**
- nParticles: point, cloud, tube, ball, sprite; with fields (gravity, air, turbulence, drag, vortex, Newton, radial)
- nCloth: cloth simulation (garments, soft bodies)
- nMesh: passive/active collision mesh
- nRigid: rigid body dynamics
- Fluid Effects: 3D/2D fluid containers, smoke, fire, explosions, clouds
- Maya Hair: curve-based dynamic hair/fur
- Fur: attach/render realistic fur
- Bifrost: visual programming for effects (liquids, destruction, aerosols, cloth)
- Bifrost Ocean: procedural ocean simulation

**Rendering:**
- Arnold: path tracer — physically-based, AOVs, subsurface, volumes, atmosphere
- Render Setup: render layers, light groups, override collections
- Batch render, IPR interactive rendering
- Viewport 2.0 with hardware render
- USD workflow: import/export, layers, variants

**Pro Tips:**
- Use Reference Editor for asset management
- Maya Embedded Language (MEL) + Python scripting
- Rig with naming conventions (L/R, _JNT, _CTRL, _GRP)
- Outliner organization with groups
- Bifrost for procedural destruction and complex FX

---

### 6.3 Cinema 4D (Maxon)

**Overview:** Intuitive 3D modeling, animation, motion design tool. Strong MoGraph system.

**Key Features:**
- Modeling: parametric primitives, generators (Extrude, Lathe, Loft, Sweep, Boolean, Array, Atom Array), modeling tools (knife, bevel, extrude, bridge, stitch, sculpt)
- MoGraph: Cloner (linear, radial, grid, object), Effectors (Random, Shader, Formula, Plain, Delay, Step, Sound, Spline, Target), Fracture (Voronoi), Matrix, MoText, Tracer, Instance
- Animation: keyframes, F-Curves, timeline, motion clips (non-linear), character (joints, IK, weight painting, CMotion), Magic Marquee for motion clips
- Dynamics: rigid body, soft body, cloth, motor, connector, spring
- Particles: Thinking Particles (node-based), Pyro (fire/smoke)
- Hair: dynamic hair/fur system
- Character: joints, IK, weight painting, morph, CMotion
- Rendering: Redshift (GPU), Physical (CPU, legacy), Standard, Sketch & Toon
- Mograph + Dynamics integration: combine for motion graphics
- Take System: multi-pass render, variation management
- XPresso: node-based scripting for logic/animation
- BodyPaint 3D: integrated 3D painting, UV editing
- Sculpting: brush-based sculpting tools
- Volume Builder/Remesher: voxel-based boolean and remeshing
- OpenVDB support: import/export volumes
- FBX, OBJ, Alembic, USD import/export
- Python API, C++ SDK

**Strengths:** Fast learning curve, excellent MoGraph, Redshift integration, stable
**Uses:** Motion design, broadcast graphics, product visualization

---
### 6.4 3ds Max (Autodesk)

**Overview:** 3D modeling and rendering software for game development, visualization, and VFX.

**Key Features:**
- Modeling: Poly modeling, Editable Poly, Editable Mesh, Splines, NURBS, Modifier stack (Bend, Twist, Taper, Stretch, Lattice, FFD, Displace, TurboSmooth, MeshSmooth, Symmetry, Shell, Cap Holes, Optimize, Relax, Mirror, PathDeform, Skin, Morpher, Hair & Fur, Cloth)
- Animation: keyframes, curve editor, dope sheet, constraints, layered animation, CAT (Character Animation Toolkit), biped, skinning, crowd simulation
- Materials: Slate Material Editor (node-based), Physical Material, PBR workflow, OSL maps
- Rendering: Arnold, V-Ray, Corona, Scanline, ART, Quicksilver
- Dynamics: MassFX (rigid body, ragdoll, cloth, constraints), Particle Flow (node-based particle system), Thinking Particles
- Scene management: Layers, Containers, Scene Explorer, XRef
- Scripting: MAXScript, Python
- Data Channel modifier for procedural data flow
- FBX export for game engines
- State Sets for multi-pass rendering
- Texture baking: render to texture
- Procedural mapping via OSL

**Strengths:** Strong poly modeling tools, huge plugin library (V-Ray, Forest Pack, RailClone, Phoenix FD), game dev standard alongside Maya
**Uses:** Game assets, architectural visualization, product design, broadcast

---

### 6.5 Houdini (SideFX)

**Overview:** Procedural 3D software. Node-based workflow with powerful simulation tools. Industry standard for high-end VFX.

**Key Features:**
- Procedural Workflow: nodes generate/modify data; changes propagate downstream automatically
- SOP (Surface Operators): geometry creation/modification (sphere, box, grid, revolve, subdivide, smooth, normal, point jitter, vdbfrompolygons)
- VEX: high-performance shading language (like C) for custom attributes, displacements, and procedural patterns
- VOPs: visual programming with VEX nodes
- Particles: POP Network — intuitive particle system (forces, collisions, lifespan, follow curves, source from geometry)
- Pyro: volumetric fire, smoke, explosions — adaptive density, temperature, fuel, feedback, combustion
- FLIP Fluids: Liquid simulation — viscosity, surface tension, wave tank, whitewater, mist
- Destruction: RBD (Rigid Body Dynamics) — Voronoi fracture, glue network, constraints, active/passive objects, debris, dust
- Crowds: agent-based simulation, animation blending, terrain adaptation, ragdoll
- Terrain: HeightField nodes — noise, erosion, mask, layer, paint, colorize
- Solaris (USD): scene assembly with USD, render with Karma (path tracer), stage manager, LOP nodes
- Karma: physically-based render engine (CPU/GPU), XPU mode
- Compositing: COP network — image processing, EXR manipulation
- Character rigging: KineFX — SOP-based rigging with unpack, layout, deform, blend
- Vellum: unified cloth, soft body, inflatable, hair simulation
- LOPs (Lighting Operators): USD-based lighting layout
- TOPs (Task Operators): job scheduling, render farm management
- HDA (Houdini Digital Asset): package node networks for reuse in Maya, Unreal, Unity
- PDG (Procedural Dependency Graph): automate asset generation, rendering, caching
- FBX/OBJ/USD/Alembic import/export

**Strengths:** Unmatched procedural control, best-in-class simulation (pyro, fluids, destruction), fully node-based
**Weaknesses:** Steep learning curve, different mindset from direct modeling tools

---

### 6.6 ZBrush (Maxon)

**Overview:** Industry standard for digital sculpting. Combines 2.5D and 3D sculpting with millions of polygons.

**Key Features:**
- Sculpting: 1000+ brushes (Standard, Clay Buildup, Dam Standard, Move, Inflate, SnakeHook, Smooth, Pinch, hPolish, TrimDynamic, ClayPolish, TrimAdaptive, IMM brushes), stroke types (DragDot, FreeHand, Spray, DragRect)
- DynaMesh: uniform polygon remeshing, preserves silhouette, projection detail
- ZRemesher: auto-retopology with guide curves (target poly count, adaptive size, curve intensity)
- Subdivision Levels: multi-resolution (highest poly detail for sculpting, lowest for base mesh)
- PolyPaint: color directly on model without UVs (use Polypaint mode, paint with RGB intensity)
- Alphas: texture stamps for detail (skin pores, scales, fabric weave)
- MicroMesh: replace polygons with mesh instances
- FiberMesh: generate hair/fur/grass from surface strands (grooming brushes)
- ZModeler: polygon modeling inside ZBrush (edge loops, extrude, bevel, bridge)
- Fiber, NoiseMaker, Surface Noise, Layer Brushes
- UV Master: automatic UV unwrap
- GoZ: seamless transfer to Maya, Blender, C4D, 3ds Max, Modo, Lightwave
- Decimation Master: reduce poly count while preserving detail
- Transpose Master: pose entire model with transpose line
- Spotlight: interactive texture projection
- ShadowBox: extract mesh from silhouette
- Arrays: duplicate instances along curve/path
- Timeline: basic animation with keyframes
- Render: BPR (Best Preview Render) with ambient occlusion, shadows, depth of field, subsurface
- Export: OBJ, FBX, STL, Alembic, 3D Print formats
- IMM (Insert Multi Mesh): brush inserts pre-made meshes

**Pro Tips:**
- Start with DynaMesh at low resolution, increase as detail develops
- Use ZRemesher for clean quad topology after sculpting
- Polypaint then extract texture map via UV Master
- Use layers for non-destructive sculpting variations
- Keep subdivision levels for returning to lower res

---

### 6.7 Substance 3D (Adobe)

**Overview:** Industry standard for 3D texturing and material creation.

**Substance 3D Painter:**
- Real-time PBR texturing on 3D models
- Layers: paint/effect/filter/mask layers (non-destructive)
- Smart Materials: procedural materials that adapt to mesh curvature/position/ambient occlusion
- Smart Masks: auto-generated masks (edges, cavities, curvature, position, light)
- Brushes: stamp, projection, particle, eraser with pen pressure
- Texture sets: multiple UV sets for different mesh parts
- Baking: normal, AO, curvature, position, ID, thickness, world space normal maps from high->low poly
- Particle brushes: scatter, spray, drag
- Materials: metalic/roughness and specular/gloss workflows
- Export: PSD, PNG, TGA, TIFF, custom channel packing
- Scripting: Python API
- Filters: blur, levels, HSL, blend, transform
- Iray preview: physically-based viewport
- USD, FBX, OBJ, glTF input
- HDR environment lighting

**Substance 3D Designer:**
- Node-based procedural material creation
- Nodes: Perlin noise, Blur, Levels, Gradient Map, Histogram Scan, Blend, Tile Generator, Shape, Slope Blur, Water Level, Ambient Occlusion, Normal, Height Blend, Distance
- Bitmap/Mesh Input: import images and 3D models as input
- Output: creates .sbsar packages with exposed parameters
- Infinite variation: tweak parameters for unique materials
- 3D view: preview on model
- Export: PNG, TGA, TIFF with channel packing

**Substance 3D Sampler:**
- Real-world material capture from photos
- Input: single image or photo series
- Processing: auto crop, perspective correction, extract material (albedo, normal, roughness, height)
- Filters: adjust, tweak channels, blend modes
- Output: .sbsar substance material
- 3D model import for projection reference

**Substance 3D Stager:**
- Scene layout and rendering for product visualization
- Models, materials, lights, cameras, environment
- Real-time ray tracing viewport
- Iray render output
- Photoshop PSD export with layers

---

### 6.8 Unreal Engine (Epic Games)

**Overview:** Real-time 3D engine for games, film, broadcast, architecture, and simulation. Nanite and Lumen redefine what's possible in real-time.

**Key Features:**
- Real-time rendering: Nanite (virtualized micropolygon geometry), Lumen (dynamic global illumination/bounces), Temporal Super Resolution (upscaling)
- Sequencer: cinematic non-linear editor within UE — cameras, animation, audio, event tracks, sub-sequences, fades, blends
- Niagara: next-gen VFX system — particle/collision/behavior node graphs, custom HLSL, data interfaces
- Control Rig: procedural character animation rig within Sequencer
- MetaHuman: high-fidelity digital human creation framework
- World Partition: large world streaming
- Megascans: photoscanned material/asset library (via Quixel Bridge)
- Datasmith: import CAD/archives into UE
- Blueprints: visual scripting (event graphs, nodes, function graphs)
- Material Editor: node-based PBR materials (shading models: lit, unlit, skin, eye, hair, cloth, subsurface, clear coat)
- Render Pipeline: Forward (mobile/VR), Deferred (default high-end), Ray Tracing (hardware RT reflections, shadows, AO, translucency)
- Post-Processing: bloom, DOF, motion blur, color grading (LUT), vignette, grain, chromatic aberration, tone mapper (ACES, Uncharted, Reinhard)
- Audio: MetaSounds (procedural audio), Wwise integration
- Pixel Streaming: browser-based 3D via WebRTC
- Virtual Production: live compositing, camera tracking, LED wall workflow, nDisplay
- Multi-user editing: collaborative sessions
- Asset management: content browser, collections, redirectors
- Python scripting for pipeline automation

**Pro Tips:**
- Use Lumen for GI, it's dynamic and requires no baked lighting
- Nanite removes need for LODs but has transparency limitations
- Virtual textures reduce memory at high resolution
- Use World Settings for lightmass importance volume
- Sequencer + take recorder for in-engine cinematic capture

---

### 6.9 Unity

**Overview:** Popular real-time 3D development engine for games, mobile, AR/VR, film, simulation.

**Key Features:**
- Rendering Pipelines: URP (Universal Render Pipeline — lightweight, mobile), HDRP (High Definition Render Pipeline — high-end, film)
- Shader Graph: node-based shader creation (PBR, unlit, lit, custom fog, tessellation)
- VFX Graph: GPU particle/HSP simulation system — spawn, update, render blocks, exposed parameters
- Timeline: cinematic sequencing — director, playable tracks, animation, activation, audio
- Cinemachine: smart camera system — virtual cameras, noise, composition, dolly tracks, free look
- Post-Processing: bloom, DOF, motion blur, color grading (LUT, curves, lifts/gamma/gain), vignette, grain, chromatic aberration
- DOTS (Data-Oriented Tech Stack): ECS (Entity Component System) for performance
- Burst Compiler: high-performance native code generation
- AR Foundation: cross-platform AR development
- Animation Rigging: constraint-based rigging in Editor
- Timeline Signals: event communication in sequences
- Asset Store: marketplace for assets, tools, services
- Addressables: asset management for runtime
- Light Probes, Reflection Probes, Lightmaps
- NavMesh: AI pathfinding
- Probuilder, Polybrush: in-editor modeling/UV
- Shader Graph + VFX Graph integration
- C# scripting, Visual Scripting (bolt-style)

**Pro Tips:**
- URP for mobile/performance, HDRP for visual quality
- VFX Graph for GPU-driven particle effects
- Timeline + Cinemachine for in-game cutscene production
- Use Addressables for memory management
- DOTS for high-performance gameplay scenarios

---

## 7. RENDERING

### 7.1 CPU vs GPU Rendering

**CPU Rendering:**
- Relies on processor cores (Intel/AMD)
- Advantages: larger memory capacity, stable, industry-standard for production, predictable, can handle massive scenes
- Slower per compute unit but more feature-complete
- Examples: Arnold CPU, RenderMan, V-Ray CPU, Cycles CPU, Corona
- Best for: final frame rendering, complex scenes with heavy geometry/textures

**GPU Rendering:**
- Relies on graphics cards (NVIDIA/AMD)
- Advantages: significantly faster (10-100x in some cases), interactive feedback, real-time viewport
- Limitations: VRAM constrained (8-48GB typical), can't handle scenes exceeding GPU memory
- Examples: Redshift, Octane, V-Ray GPU, Cycles GPU, Eevee, Arnold GPU
- Best for: look development, preview, final renders with moderate scene complexity

**Hybrid Rendering:**
- Some engines support both CPUs and GPUs in combination (V-Ray, Cycles, Arnold)
- Use CPU + GPU for maximum throughput
- Note: GPU VRAM is limiting factor; CPU memory is much larger

### 7.2 Render Engines

**By Engine:**
- **Cycles (Blender):** Open source path tracer, CPU/GPU, physically accurate, full-featured (subsurface, volumetrics, caustics, AOVs)
- **Eevee (Blender):** Real-time rasterizer, GPU only, screen-space effects, fast but approximations
- **Arnold (Autodesk):** Production path tracer, physically-based, used in film, ray-only bounce model, atmosphere, subsurface, AOVs
- **V-Ray (Chaos):** Versatile production renderer, CPU/GPU/ hybrid, adaptive lights, GPU denoiser, V-Ray Frame Buffer (VFB) with layers/color corrections
- **Redshift (Maxon):** Biased GPU renderer (unbiased option), very fast, uses out-of-core texturing (handles massive scenes), strong for motion design/VFX
- **Octane (OTOY):** Unbiased GPU renderer, spectral rendering, AI denoising, very fast iterative look development
- **RenderMan (Pixar):** Advanced path tracer for film, RIS (Reyes + Integrator), developed for Pixar films, LPEs (Light Path Expressions)
- **Corona (Chaos):** CPU renderer, easy setup, physically accurate, strong interior visualization
- **Karma (SideFX):** Houdini's engine, CPU/GPU (XPU), USD-native, physically-based

### 7.3 Path Tracing vs Rasterization

**Path Tracing:**
- Simulates physical light transport (photons bouncing in scene)
- Generates images by tracing millions of light paths
- Produces accurate reflections, refractions, soft shadows, GI, caustics
- Slower but photorealistic
- Convergence: noise reduces over time as more samples accumulate
- Used by: Cycles, Arnold, V-Ray, Octane, Redshift, RenderMan

**Rasterization:**
- Projects geometry directly to screen pixels
- Fast — real time (30-240+ fps)
- Approximations: screen-space reflections, shadow maps, ambient occlusion
- Not physically accurate but fast enough for interactive
- Used by: Eevee, Unreal Engine, Unity, game engines generally
- Hybrid approaches increasingly common (UE Lumen + Nanite)

### 7.4 Render Settings

**Samples:**
- Number of rays traced per pixel; higher = cleaner image, longer render
- Adaptive sampling: render more samples in noisy areas, fewer in clean areas
- Typical values: 128-4096 depending on scene, denoiser quality

**Bounces:**
- Maximum number of times a light ray bounces before termination
- Total bounces, diffuse bounces, glossy bounces, transmission bounces, volume bounces
- Higher = more realistic GI but slower
- Typical: 8-16 total, lower for interiors in some engines

**Denoising:**
- AI/Optix denoiser: removes noise from low-sample renders
- OpenImageDenoise (CPU), OptiX (NVIDIA GPU), Intel denoiser
- Greatly reduces render time; slight quality trade-off
- Can add denoising as a post-process AOV

**AOVs (Arbitrary Output Variables / Render Passes):**
- Separate channels for compositing: beauty, diffuse, glossy, transmission, shadows, reflection, refraction, ambient occlusion, normal, Z-depth, position, motion vector, UV, object/material ID, cryptomatte, mist, emission, volume, subsurface, alpha
- Essential for compositing in Nuke/After Effects/Fusion
- EXR format typically used for multilayer storage

### 7.5 Render Farm Setup

**Render Farm Software:**
- Render queue: submit jobs, distribute across nodes
- Deadline (Thinkbox/AWS): industry standard, supports all major renderers, cloud bursting, scalable
- Thinkbox Deadline: plugin-based, custom job types, usage-based reporting
- Qube!: render farm manager, strong integration
- Tractor (Pixar): robust scheduling, dependency graph
- Royal Render: flexible, cross-platform
- OpenCue: open source (Google/Sony Pictures Imageworks)

**Setup:**
- Render nodes: dedicated machines with powerful CPUs/GPUs
- Shared storage: NAS/SAN for project files, textures, scene cache
- Job submission: submit from workstation, farm distributes
- Pool management: prioritize jobs, allocate nodes by task type
- Cloud bursting: extra capacity from AWS/Azure/GCP batch render
- Monitoring: web dashboard to track progress, node health, error logs

**Pro Tips:**
- Always test render with a single frame before farm submission
- Use versioning for scene files shipped to farm
- Cache simulations/caches locally or on shared storage
- Frame interleave: render every Nth frame (e.g., every 12th) then fill gaps
- Use proxies at low res for look dev, final at full res

### 7.6 Output Formats

- **EXR (OpenEXR):** High dynamic range, multi-channel, multi-layer, lossless/ lossy compression (PIZ, ZIP, RLE, DWAA, DWAB), half/float/uint32 — standard for VFX
- **DPX (Digital Picture Exchange):** Cineon legacy, 10-bit log, film scanning/recording, uncompressed
- **TIFF:** 8/16/32-bit, LZW/zip compression, widespread compatibility, printing
- **PNG:** 8/16-bit, lossless, alpha support, web-delivery
- **JPEG:** Lossy, small file, 8-bit, final delivery not for VFX
- **HDR / Radiance:** 32-bit float HDR for environment maps
- **TGA (Targa):** Legacy, alpha support, 8/16/24/32-bit

### 7.7 ACES Color Pipeline

**ACES (Academy Color Encoding System):**
- Industry standard color management for VFX/film
- Components:
  - **IDT (Input Device Transform):** convert camera-specific color to ACES
  - **ACES2065-1 (AP0):** reference space, wide gamut
  - **ACEScg (AP1):** working space for rendering/compositing
  - **RRT (Reference Rendering Transform):** creative look transform
  - **ODT (Output Device Transform):** map to display (Rec.709, P3-D65, Rec.2020, DCI P3)
- Benefits: consistent color across applications, unified pipeline, wide gamut
- ACEScc (color correction space): log-based for grading
- ACEScct: like ACEScc but with toe for better dark handling

---

## 8. MOTION DESIGN & ANIMATION PRINCIPLES

### 8.1 12 Principles of Animation (Disney/Ollie Johnston & Frank Thomas)

1. **Squash and Stretch**: elasticity of objects — squashes on impact, stretches on acceleration (maintain volume)
2. **Anticipation**: small preparatory action before main action (wind-up before pitch, crouch before jump)
3. **Staging**: present idea clearly — camera angle, composition, timing, avoid confusing audience
4. **Straight Ahead vs Pose-to-Pose**: SA = draw frame-by-frame sequentially; PtP = key poses first, fill in-between later
5. **Follow Through & Overlapping Action**: parts continue moving after main body stops (hair, clothes, jiggle)
6. **Slow In & Slow Out (Ease In/Ease Out)**: more frames near extremes, fewer in middle — natural motion
7. **Arcs**: organic motion follows curved paths, not straight lines (pendulum, limbs, head turns)
8. **Secondary Action**: subtle supporting actions (facial expressions while walking, breathing while standing)
9. **Timing**: number of frames per action determines speed/weight/emotion
10. **Exaggeration**: push movement, expression, physics beyond real for clarity/impact
11. **Solid Drawing**: consider 3D form, weight, volume, perspective in 2D
12. **Appeal**: characters/design should be interesting, pleasing, charismatic — not necessarily cute

### 8.2 Easing Curves

**Types:**
- Linear: constant speed, mechanical/unrealistic
- Ease In (Slow In): starts slow, speeds up (accelerate)
- Ease Out (Slow Out): starts fast, slows down (decelerate)
- Ease In-Out: slow start, fast middle, slow end — most natural
- Custom Bezier: user-defined curves for precise timing
- Bounce: overshoot and rebound at end
- Elastic: stretch/oscillate before settling
- Spring: damped oscillation settling
- Steps: no interpolation, hard jumps (stop motion)

**Keyframe Interpolation in Software:**
- After Effects: Easy Ease (F9), Keyframe Assistant
- Blender: Vector, Auto, Auto Clamped, Free handles
- Curve Editor: edit speed graph for precise velocity control

### 8.3 Typography Animation

**Techniques:**
- Fade/Opacity, Position (sliding/flying in), Scale (growing/shrinking)
- Tracking (letter-spacing) animation — letters spread apart or tighten
- Skew/Shear for dynamic tilt
- 3D rotation per character (X/Y/Z axis)
- Typewriter / Text reveal — per-character sequential appearance
- Gradient fill / animated gradient on text
- Text blur in/out (character blur)
- Masking text or text reveal shapes
- Kinetic typography: text moves to match audio/rhythm
- Text on path (curved motion path or shape)
- Animated underline/highlight
- Per-word/character color cycling

**Software:** After Effects (range selectors), Apple Motion, Blender Grease Pencil

### 8.4 Logo Animation

**Techniques:**
- Geometric construction: layers build up sequentially
- Reveal: wipe, radial wipe, mask reveal, gradient wipe
- Pulse: scale pulse on beat
- Glow/neon pass: light sweep across logo
- 3D extrusion: depth, rotation, bevel
- Morph: shape transition between logo states
- Particle: logo formed/dispersed by particles
- Stomp: heavy impact animation
- Hypersweep: trim paths on outlined logo
- Flourish: elegant swooshes, decorative lines

**Software:** After Effects (shape layers, trim paths, 3D), Cinema 4D (MoGraph, Redshift), Blender

### 8.5 Storyboarding

**Process:**
1. Thumbnails: small quick sketches of key shots
2. Rough boards: basic framing, character blocking, camera moves
3. Clean boards: final approved drawings with notes
4. Animatic: timed sequence of storyboard frames with temp audio
5. Storyboard software: Toon Boom Storyboard Pro, Blender (Grease Pencil), Photoshop, Procreate, Boords

**Elements per panel:**
- Frame borders (aspect ratio)
- Character posing and expression
- Camera angle, lens, distance (wide, medium, close-up, extreme close-up)
- Camera movement (pan, tilt, dolly, track, crane, zoom)
- Dialogue text
- Action descriptions
- Arrow notation for direction/movement
- Timing in seconds or frames

---

## 9. PRODUCTION PIPELINE

### 9.1 Pre-Production

**Script:**
- Written narrative, scene descriptions, dialogue, action
- Screenplay format: Courier 12pt, slug lines (INT/EXT, LOCATION, TIME)
- Formatting tools: Final Draft, Fade In, Celtx, WriterDuet

**Storyboard:**
- Visual translation of script
- Draw each shot with composition, camera angle, lighting direction
- Helps identify issues before production

**Animatic (Leica Reel):**
- Storyboard panels edited to timing with scratch audio
- Refine pacing, identify missing coverage
- Locked cut before production

**Concept Art:**
- Character designs, environment designs, color scripts
- Mood boards for visual reference
- Style frame (proof-of-concept still)

**Budgeting & Scheduling:**
- Script breakdown: elements per scene (cast, props, locations, FX)
- Production schedule: shoot days, post timeline
- Budget categories: crew, talent, equipment, locations, post-production, music, deliverables

### 9.2 Production

**Shooting (Live Action):**
- Camera: sensor size (full frame, Super 35, S35, large format), resolution (HD, 4K, 6K, 8K, 12K)
- Lenses: prime vs zoom, focal length, T-stop, close focus
- Lighting: key, fill, backlight, practicals, HMI, LED, tungsten
- Sound: boom mic (shotgun), lavaliers, field recorder, sound report
- Video village: director, DIT, playback
- DIT: data management (backup, transcoding, dailies creation)
- Slating: scene, take, camera roll, audio roll

**Motion Capture:**
- Optical: markers tracked by cameras (Vicon, OptiTrack, Motive)
- Inertial: suits with IMUs (Xsens, Rokoko, Perception Neuron)
- Facial: head-mounted cameras (FACS-based, helmets)
- Solve and clean: retarget to character rig

**CG Production:**
- Modeling: characters, environments, props
- Texturing: PBR maps, look development
- Rigging: skeleton, controls, skinning
- Layout: camera placement, set dressing, blocking
- Animation: body mechanics, performance, facial

### 9.3 Post-Production

**Offline Edit:**
- Assembly cut: all footage placed in timeline
- Rough cut: refine scene pacing, remove bad takes
- Fine cut: exact timing, temporary transitions
- Picture lock: no more timeline changes

**Online Edit:**
- Conform: relink proxies to original camera files
- Color grading: primary -> secondary -> final grade
- VFX: compositing, set extensions, greenscreen

**VFX Pipeline Steps:**
1. Plate prep: clean plates, tracking markers removal
2. Tracking: matchmove, camera solve, object tracking
3. Modeling: assets needed for scenes
4. Texturing: surface detail
5. Rigging: for animated assets
6. Animation: motion performance
7. FX: particles, fluids, simulations
8. Lighting: match scene lighting
9. Rendering: compute final passes
10. Compositing: integrate all elements seamlessly

**Audio Post:**
- Dialog editing: clean takes, ADR sync
- Sound design: SFX, foley, ambience
- Music: score, licensed tracks
- Mix: balance all elements, dialogue intelligibility
- Mastering: final loudness, formats

**Deliverables:**
- Master: ProRes 4444 XQ, DNxHR 444, DPX film scan
- Broadcast: XDCAM, IMX, AVC-Intra, MXF OP1a
- Streaming: H.264/H.265 MP4, specific profile/level
- DCP: Digital Cinema Package — MXF JPEG 2000, subtitle XML
- Audio stems: dialogue, music, SFX separated

### 9.4 File Formats, Codecs, Containers

**Containers (Wrappers):**
- MOV (QuickTime): versatile, all codecs
- MP4 (MPEG-4 Part 14): streaming, H.264/H.265
- MXF (Material eXchange Format): broadcast/professional
- AVI: legacy Windows container
- MKV (Matroska): open source, all codecs

**Codecs:**
- H.264 (AVC): most compatible delivery codec, good quality/size
- H.265 (HEVC): ~50% better compression than H.264 at same quality
- ProRes (Apple): intraframe, editing codec — Proxy, LT, 422, 422 HQ, 4444, 4444 XQ
- DNxHD/DNxHR (Avid): intraframe, editing/mezzanine — LB, SQ, HQ, HQX, 444
- REDCODE (RED): compressed RAW — .r3d files
- ARRIRAW (ARRI): uncompressed RAW — .ari files
- Blackmagic RAW (BRAW): compressed RAW
- XAVC (Sony): Long GOP/intraframe, HD/4K
- AVCHD: consumer/camcorder, H.264 based
- DPX: uncompressed image sequence for film
- OpenEXR: high dynamic range multilayer
- FFV1: lossless archival codec
- VP9/AV1: open, royalty-free streaming codecs

**Mezzanine (Intermediate) Codecs:** ProRes 422 HQ, DNxHR HQ, CineForm, all suitable for editing with good quality and reasonable file size

### 9.5 Workflow Management Software

**ShotGrid (Autodesk, formerly Shotgun):**
- Production tracking, asset management, review/approval
- Pipeline integrations: Maya, Nuke, Houdini, After Effects, Unreal
- Version tracking, notes, thumbnails, playblast review
- Schedule, task assignment, milestone tracking
- API for custom pipeline tools

**Ftrack:**
- Review and approval platform, project management
- Integrations: Adobe, Autodesk, SideFX, Unreal
- Media review with annotations
- Asset management, task schedules, custom fields
- Actions engine for automation

**Kitsu (CGWire):**
- Open source production tracker for animation/VFX
- Asset management, task lists, playblast review
- Pipeline: integrations with Blender, Maya, Krita
- Open RV review integration
- Collaboration, chat, version history

**Others:**
- **perforce** (Helix Core): version control for binary assets
- **Git LFS**: large file storage for git-based repos
- **Synology / QNAP**: NAS for shared storage
- **Resilio Sync**: peer-to-peer sync for remote teams
- **OpenRV**: open source review and playback tool (formerly RV)
- **cineSync**: remote review and annotation (ftrack)

---

*This knowledge base covers the entire media editing, VFX, audio, photo, 3D, rendering, motion design, and production pipeline landscape. Use it as a definitive reference for any application, technique, or workflow question.*
