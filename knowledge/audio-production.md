# Audio Production & Editing -- Complete Guide

## Table of Contents

1. [DAWs](#daws)
2. [Audio Editing Fundamentals](#audio-editing)
3. [Audio Effects](#audio-effects)
4. [Mixing](#mixing)
5. [Mastering](#mastering)
6. [Sound Design & Synthesis](#sound-design)
7. [Sampling](#sampling)
8. [MIDI](#midi)
9. [VST/AU Plugins](#plugins)
10. [Field Recording & Foley](#field-recording)
11. [Audio Restoration](#audio-restoration)
12. [Speech Synthesis](#speech-synthesis)
13. [Python for Audio](#python-audio)

---

## DAWs

### Ableton Live

Ableton Live features dual view: Arrangement View (linear timeline) and Session View (clip launcher for live performance). Warp Markers enable real-time time-stretching. Racks (Instrument, Drum, Effects) provide macro control. Max for Live extends functionality with visual programming.

```python
import live
proj = live.Set()
proj.open("project.als")
track = proj.tracks[0]
track.clips[0].name = "Verse 1"
device = track.add_device("Ableton", "Compressor")
device.parameters["Threshold"].value = -12.0
```

### FL Studio

Pattern-based step sequencer with Piano roll for MIDI editing. Mixer supports 125+ tracks. Built-in synths include Sytrus (FM), Harmor (additive/resynthesis), 3xOSC.

```python
import flstudio
proj = flstudio.Project()
pat = proj.create_pattern("Drums")
pat.add_note(36, 0, 0.25, 100)  # kick
pat.add_note(38, 0.5, 0.25, 80) # snare
pat.add_note(42, 0.25, 0.25, 60) # hi-hat
```

### Logic Pro (macOS only)

Features Flex Time (time-stretch), Flex Pitch (Melodyne-style correction), Drummer (virtual session drummer), Alchemy (advanced synth), ChromaVerb, Step FX. Controlled via AppleScript.

### Pro Tools

Industry standard for professional recording, editing, mixing, and film scoring. Elastic Audio for time-stretching, AudioSuite for destructive processing, Clip Gain per-clip volume, Surround/Atmos mixing.

### Cubase

Chord Track and Chord Pads for harmony. VariAudio for pitch correction. Expression Maps for articulations. MixConsole with complete channel strip. Built-in synths: HALion, Groove Agent SE, Retrologue.

### Reaper

Extremely lightweight (~15MB) and customizable. ReaScript (EEL/Lua/Python). Parameter modulation and flexible routing. Built-in JSFX effects. Affordable license.

```python
import reaper_python as RPR
RPR.Main_OnCommand(40001, 0)
RPR.InsertMedia("guitar.wav", 0)
fx = RPR.TrackFX_GetByName(0, "ReaComp", True)
RPR.TrackFX_SetParam(0, fx, 0, -12.0)
```

---

## Audio Editing Fundamentals

### Core Operations

- **Cut:** Remove selection to clipboard
- **Copy:** Duplicate selection to clipboard
- **Paste:** Insert clipboard at cursor
- **Trim:** Remove everything outside selection
- **Silence:** Replace selection with silence
- **Crop:** Delete all but selection

### Fades & Crossfades

```python
from pydub import AudioSegment

audio = AudioSegment.from_file("input.wav")
faded = audio.fade_in(3000).fade_out(3000)

audio1 = AudioSegment.from_file("track1.wav")
audio2 = AudioSegment.from_file("track2.wav")
crossfaded = audio1.append(audio2, crossfade=2000)
```

### Pitch Shift & Time Stretch

```python
from pydub import AudioSegment
audio = AudioSegment.from_file("vocal.wav")

# Pitch shift (+3 semitones)
new_sr = int(audio.frame_rate * (2 ** (3 / 12)))
shifted = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sr})
shifted = shifted.set_frame_rate(audio.frame_rate)

# High-quality via librosa
import librosa
import soundfile as sf
y, sr = librosa.load("vocal.wav", sr=44100)

y_stretched = librosa.effects.time_stretch(y=y, rate=0.67)
y_shifted = librosa.effects.pitch_shift(y=y, sr=sr, n_steps=2)
sf.write("output.wav", y_shifted, sr)
```

### Normalization

```python
from pydub import AudioSegment
import numpy as np
import librosa

audio = AudioSegment.from_file("track.wav")

# Peak normalization (to -1 dBFS)
normalized = audio - (audio.max_dBFS + 1)

# RMS normalization (to -18 dBFS)
y, sr = librosa.load("track.wav")
rms = np.sqrt(np.mean(y**2))
target = 10 ** (-18 / 20)
y_norm = y * (target / (rms + 1e-10))

# Loudness normalization (ITU-R BS.1770 to -14 LUFS)
import pyloudnorm as pyln
y, sr = librosa.load("track.wav", sr=44100, mono=False)
meter = pyln.Meter(sr)
loudness = meter.integrated_loudness(y)
y_loud = pyln.normalize.loudness(y, loudness, -14.0)
sf.write("loud_normalized.wav", y_loud, sr)
```

---

## Audio Effects

### EQ (Equalization)

```python
from pydub import AudioSegment
from pydub.scipy_effects import low_pass_filter, high_pass_filter

audio = AudioSegment.from_file("mix.wav")
lp = low_pass_filter(audio, 5000)
hp = high_pass_filter(audio, 80)

def parametric_eq(audio, freq, q, gain_db):
    from scipy import signal
    import numpy as np
    from numpy import pi, cos, sin
    samples = np.array(audio.get_array_of_samples(), dtype=np.float64)
    sr = audio.frame_rate
    A = 10 ** (gain_db / 40)
    w0 = 2 * pi * freq / sr
    alpha = sin(w0) / (2 * q)
    b = [1 + alpha * A, -2 * cos(w0), 1 - alpha * A]
    a = [1 + alpha / A, -2 * cos(w0), 1 - alpha / A]
    filtered = signal.lfilter(b, a, samples)
    return audio._spawn(filtered.astype(np.int16).tobytes())
```

### Compression

```python
def compress(samples, threshold=-20, ratio=4, sr=44100):
    import numpy as np
    eps = 1e-10
    db = 20 * np.log10(np.abs(samples) + eps)
    reduction = np.maximum(0, db - threshold) * (1 - 1/ratio)
    gain = 10 ** (-reduction / 20)
    release = int(sr * 0.05)
    for i in range(1, len(gain)):
        if gain[i] > gain[i-1]:
            c = 1 - np.exp(-1 / release)
            gain[i] = gain[i-1] + c * (gain[i] - gain[i-1])
    return samples * gain

def sidechain(target, side_sig, threshold=-20, ratio=4):
    env = np.abs(side_sig)
    env_db = 20 * np.log10(env + 1e-10)
    reduction = np.maximum(0, env_db - threshold) * (1 - 1/ratio)
    gain = 10 ** (-reduction / 20)
    return target * gain
```

### Reverb

```python
from scipy import signal
import numpy as np

def convolution_reverb(samples, ir_path, dry_wet=0.3):
    import soundfile as sf
    ir, _ = sf.read(ir_path)
    wet = signal.fftconvolve(samples, ir, mode="full")[:len(samples)]
    wet = wet / (np.max(np.abs(wet)) + 1e-10)
    return (1 - dry_wet) * samples + dry_wet * wet

def schroeder_reverb(samples, sr=44100, decay=0.5):
    def comb(x, d, g):
        a = np.zeros(d + 1); a[0] = 1; a[d] = -g
        return signal.lfilter([1], a, x)
    delays = [1051, 1607, 2237, 3491]
    gains = [decay ** (d / max(delays)) for d in delays]
    wet = np.zeros_like(samples)
    for d, g in zip(delays, gains):
        wet += comb(samples, d, g)
    return wet


### Delay

```python
def delay(samples, sr=44100, delay_ms=500, feedback=0.3, mix=0.5):
    d = int(sr * delay_ms / 1000)
    buf = np.zeros(d)
    out = np.copy(samples)
    for i in range(len(samples)):
        s = buf[i % d]
        out[i] = (1 - mix) * samples[i] + mix * s
        buf[i % d] = samples[i] + feedback * s
    return out
```

### Modulation Effects

```python
def chorus(samples, sr=44100, rate=0.5, depth=0.7, voices=3):
    out = np.zeros_like(samples)
    for v in range(voices):
        lfo = depth * np.sin(2*np.pi*rate*np.arange(len(samples))/sr + v*2*np.pi/voices)
        d = np.round(lfo * sr * 0.01).astype(int)
        delayed = np.zeros_like(samples)
        for i in range(len(samples)):
            idx = i - d[i]
            if 0 <= idx < len(samples):
                delayed[i] = samples[idx]
        out += delayed * (0.3 / voices)
    return samples * 0.5 + out

def flanger(samples, sr=44100, rate=0.3, depth=0.9):
    buf = np.zeros(int(sr * 0.01))
    out = np.zeros_like(samples)
    for i in range(len(samples)):
        delay_s = int(depth * (0.005 + 0.005 * np.sin(2*np.pi*rate*i/sr)) * sr)
        idx = i % len(buf)
        s = buf[(idx - delay_s) % len(buf)]
        out[i] = samples[i] + 0.7 * s
        buf[idx] = samples[i] + 0.3 * s
    return out
```

### Distortion & Saturation

```python
def soft_clip(samples, threshold=0.5):
    out = np.copy(samples)
    m = np.abs(samples) > threshold
    out[m] = np.sign(samples[m]) * (threshold + (1-threshold)*np.tanh((np.abs(samples[m])-threshold)/(1-threshold)))
    return out

def tube_saturation(samples, drive=2.0):
    return np.tanh(samples * drive) / np.tanh(drive) * 0.9

def fuzz(samples, gain=20, tone=0.5):
    from scipy import signal
    clipped = np.clip(samples * gain, -1, 1)
    clipped[clipped > 0] = clipped[clipped > 0] ** 0.7
    b, a = signal.butter(1, tone * 4000 / (44100 / 2), "low")
    return signal.lfilter(b, a, clipped)
```

### Limiter

```python
def brickwall_limiter(samples, sr=44100, threshold=-0.5, lookahead_ms=5):
    look = int(sr * lookahead_ms / 1000)
    thresh = 10 ** (threshold / 20)
    padded = np.pad(samples, (look, 0), mode="edge")
    env = np.array([np.max(np.abs(padded[i:i+look*2])) for i in range(len(samples))])
    gain = np.ones_like(samples)
    gain[env > thresh] = thresh / (env[env > thresh] + 1e-10)
    # Release smoothing
    rel = int(sr * 0.1)
    for i in range(1, len(gain)):
        if gain[i] > gain[i-1]:
            c = 1 - np.exp(-1 / rel)
            gain[i] = gain[i-1] + c * (gain[i] - gain[i-1])
    return samples * gain
```

### Noise Gate

```python
def noise_gate(samples, sr=44100, threshold=-40):
    thresh = 10 ** (threshold / 20)
    env = np.convolve(np.abs(samples), np.ones(int(sr*0.01))/int(sr*0.01), mode="same")
    gain = np.ones_like(samples)
    open_g = False
    rel = int(sr * 0.1)
    for i in range(len(samples)):
        if not open_g and env[i] > thresh:
            open_g = True
        elif open_g and env[i] < thresh * 0.5:
            open_g = False
        cur = 1.0 if open_g else 0.001
        if i > 0:
            gain[i] = gain[i-1] + (1 - np.exp(-1/rel)) * (cur - gain[i-1])
        else:
            gain[i] = cur
    return samples * gain
```

---

## Mixing

### Panning

```python
def panner(samples, pan):
    """pan: -1 (left), 0 (center), 1 (right)"""
    lg = np.sqrt(0.5 * (1 - pan))
    rg = np.sqrt(0.5 * (1 + pan))
    if samples.ndim == 1:
        s = np.zeros((len(samples), 2))
        s[:, 0] = samples * lg
        s[:, 1] = samples * rg
        return s
    return samples * np.array([lg, rg])
```

### Bussing

```python
class AudioBuss:
    def __init__(self, name):
        self.name = name
        self.inputs = []
        self.plugins = []
        self.gain = 1.0
    def add_input(self, track, gain=1.0):
        self.inputs.append((track, gain))
    def add_plugin(self, fn):
        self.plugins.append(fn)
    def process(self):
        if not self.inputs:
            return np.zeros(0)
        length = max(len(t) for t,_ in self.inputs)
        mix = np.zeros(length)
        for t, g in self.inputs:
            padded = np.pad(t, (0, length - len(t)))
            mix += padded * g
        for p in self.plugins:
            mix = p(mix)
        return mix * self.gain
```

### Sidechain Pump

```python
def sidechain_pump(kick, bass, threshold=-20, ratio=4):
    env = np.abs(kick)
    env = np.convolve(env, np.ones(441)//441, mode="same")
    env_db = 20 * np.log10(env + 1e-10)
    reduction = np.maximum(0, env_db - threshold) * (1 - 1/ratio)
    gain = 10 ** (-reduction / 20)
    return bass * gain
```

### Mixing Reference Levels

| Element | Peak (dBFS) | Pan | EQ Focus |
|---------|-------------|-----|----------|
| Kick | -6 to -3 | Center | 50-100 Hz |
| Snare | -6 to -3 | Center | 200 Hz, 5 kHz |
| Hi-hat | -12 to -8 | L/R | 8-12 kHz |
| Bass | -6 to -3 | Center | 50-200 Hz |
| Lead Vocal | -6 to -3 | Center | 3-5 kHz |
| Guitar | -10 to -6 | Spread | Cut 200-400 Hz |
| Pad | -14 to -10 | Wide | LP 8 kHz |
| FX | -18 to -12 | Varies | Context |

---

## Mastering

### Loudness Standards

| Platform | Integrated LUFS | True Peak |
|----------|-----------------|-----------|
| Spotify | -14 | -1 dBTP |
| Apple Music | -16 | -1 dBTP |
| YouTube | -14 | -1 dBTP |
| Broadcast (EBU R128) | -23 | -1 dBTP |
| Podcast | -16 to -18 | -1 dBTP |

### Mastering Chain

```python
def master_track(input_path, output_path, target=-14):
    import librosa, soundfile as sf, numpy as np
    from scipy import signal

    y, sr = librosa.load(input_path, sr=44100, mono=False)
    if y.ndim == 1:
        y = np.stack([y, y], axis=0)

    # 1. High-pass below 30 Hz
    b, a = signal.butter(2, 30/(sr/2), "high")
    y = signal.lfilter(b, a, y, axis=1)

    # 2. Presence boost
    b, a = signal.butter(2, [3000/(sr/2), 6000/(sr/2)], "band")
    presence = signal.lfilter(b, a, y, axis=1)
    y = y + 0.15 * presence

    # 3. Multiband compression
    b_lp, a_lp = signal.butter(2, 200/(sr/2), "low")
    b_hp, a_hp = signal.butter(2, 4000/(sr/2), "high")
    low = signal.lfilter(b_lp, a_lp, y, axis=1)
    high = signal.lfilter(b_hp, a_hp, y, axis=1)
    mid = y - low - high

    for band in [low, mid, high]:
        env = np.abs(band)
        env_db = 20*np.log10(np.clip(env, 1e-10, None))
        red = np.maximum(0, env_db - (-20)) * (1 - 1/2.5)
        band *= (10 ** (-red / 20))

    y = low + mid + high

    # 4. Limiter
    peak = np.max(np.abs(y))
    if peak > 0.95:
        y *= (0.95 / peak)
    y = np.clip(y, -0.99, 0.99)

    # 5. Loudness normalization
    import pyloudnorm as pyln
    meter = pyln.Meter(sr)
    if y.ndim > 1:
        yt = y.T
    else:
        yt = y
    loud = meter.integrated_loudness(yt)
    y = pyln.normalize.loudness(yt, loud, target)
    if y.ndim > 1:
        y = y.T

    sf.write(output_path, y, sr)
```

### Stereo Width

```python
def stereo_width(samples, width=1.0):
    if samples.ndim != 2 or samples.shape[1] != 2:
        return samples
    mid = (samples[:, 0] + samples[:, 1]) / 2
    side = (samples[:, 0] - samples[:, 1]) / 2 * width
    return np.stack([mid + side, mid - side], axis=1)

def ms_process(samples, mid_fn=None, side_fn=None):
    mid = (samples[:, 0] + samples[:, 1]) / 2
    side = (samples[:, 0] - samples[:, 1]) / 2
    if mid_fn: mid = mid_fn(mid)
    if side_fn: side = side_fn(side)
    return np.stack([mid + side, mid - side], axis=1)
```

---

## Sound Design & Synthesis

### Subtractive Synthesis

```python
def subtractive_synth(freq=440, sr=44100, duration=2.0, cutoff=1000):
    from scipy import signal
    t = np.linspace(0, duration, int(sr * duration))

    saw = 2 * (t * freq - np.floor(t * freq + 0.5))
    tri = 2 * np.abs(2 * (t*freq - np.floor(t*freq + 0.5))) - 1
    sqr = np.sign(np.sin(2 * np.pi * freq * t))
    osc = 0.5 * saw + 0.3 * tri + 0.2 * sqr

    b, a = signal.butter(2, cutoff / (sr/2))
    filtered = signal.lfilter(b, a, osc)

    env = np.ones_like(t)
    env[:int(0.1*sr)] = np.linspace(0, 1, int(0.1*sr))
    env[-int(0.3*sr):] = np.linspace(1, 0, int(0.3*sr))

    return filtered * env * 0.5
```

### FM Synthesis

```python
def fm_synth(carrier=440, modulator=220, index=2, duration=2.0, sr=44100):
    t = np.linspace(0, duration, int(sr * duration))
    mod = index * np.sin(2 * np.pi * modulator * t)
    return np.sin(2 * np.pi * carrier * t + mod)

def fm_bell(freq=440, duration=2.0, sr=44100):
    t = np.linspace(0, duration, int(sr * duration))
    op1 = np.sin(2 * np.pi * freq * t) * np.exp(-4 * t)
    op2 = np.sin(2 * np.pi * freq * t + 5 * op1) * np.exp(-2 * t)
    return op2 * 0.5
```

### Wavetable Synthesis

```python
def wavetable_osc(wt, freq=440, duration=2.0, sr=44100):
    t = np.linspace(0, duration, int(sr * duration))
    phase = np.mod(t * freq, 1.0)
    idx = phase * (len(wt) - 1)
    i0 = np.floor(idx).astype(int)
    i1 = np.ceil(idx).astype(int)
    frac = idx - i0
    return (1-frac) * wt[i0] + frac * wt[i1]
```

### Granular Synthesis

```python
def granular(samples, grain_size=0.1, density=50, pitch_shift=0, sr=44100):
    gs = int(grain_size * sr)
    out = np.zeros(len(samples) * 2)
    speed = 2 ** (pitch_shift / 12)
    for _ in range(int(density * len(out) / sr)):
        start = np.random.randint(0, len(samples) - gs)
        grain = samples[start:start + gs]
        if pitch_shift != 0:
            new_len = int(gs / speed)
            grain = np.interp(np.linspace(0, gs, new_len), np.arange(gs), grain)
        grain *= np.hanning(len(grain))
        pos = np.random.randint(0, max(1, len(out) - len(grain)))
        end = min(pos + len(grain), len(out))
        out[pos:end] += grain[:end - pos]
    return out / np.max(np.abs(out)) * 0.7
```

### Physical Modeling

```python
def karplus_strong(freq=220, duration=2.0, sr=44100, feedback=0.99):
    delay = int(sr / freq)
    buf = np.random.uniform(-0.5, 0.5, delay)
    out = np.zeros(int(sr * duration))
    for i in range(len(out)):
        out[i] = buf[i % delay]
        buf[i % delay] = feedback * (buf[i % delay] + buf[(i+1) % delay]) / 2
    return out
```

---

## Sampling

```python
class Sampler:
    def __init__(self, sample_path):
        import librosa
        self.y, self.sr = librosa.load(sample_path, sr=44100)
    def play(self, pitch=60, velocity=100):
        ratio = 2 ** ((pitch - 60) / 12)
        new_len = int(len(self.y) / ratio)
        pitched = np.interp(np.linspace(0, len(self.y), new_len), np.arange(len(self.y)), self.y)
        return pitched * (velocity / 127)
```

---

## MIDI

MIDI protocol: Note On (0x90+ch, note, vel), Note Off (0x80+ch, note, vel), CC (0xB0+ch, cc, val)

```python
import mido
out = mido.open_output("Midi Through Port-0")
out.send(mido.Message("note_on", note=60, velocity=100))

mid = mido.MidiFile("song.mid")
for track in mid.tracks:
    for msg in track:
        if msg.type == "note_on":
            print(f"Note {msg.note}")
```

### CC Numbers

| CC | Parameter | CC | Parameter |
|----|-----------|----|-----------|
| 1 | Modulation | 7 | Volume |
| 10 | Pan | 11 | Expression |
| 64 | Sustain | 71 | Resonance |
| 74 | Filter Cutoff | 91 | Reverb Send |

---

## VST/AU Plugins

Formats: VST3 (Win/Mac), AU (Mac), AAX (Pro Tools), CLAP (new open standard)

```python
import dawdreamer as daw
engine = daw.RenderEngine(44100, 512)
engine.load_plugin("C:/VST/Serum.dll")
engine.set_parameter(0, 0.5)
engine.load_preset("C:/Presets/Bass.fxp")
audio = engine.render(4.0)
```

---

## Field Recording & Foley

Equipment: Shotgun (directional), Contact (surfaces), Binaural (3D), Zoom H-series, Sound Devices.

Foley: Footsteps (gravel/wood), Cloth (fabric near mic), Punches (meat/cabbage), Breaks (celery), Rain (rice on paper), Kiss (back of hand).

---

## Audio Restoration

```python
def remove_hum(y, sr=44100, freq=50):
    from scipy import signal
    for f in [freq, freq*2, freq*3, freq*4, freq*5]:
        b, a = signal.iirnotch(f, 30, sr)
        y = signal.lfilter(b, a, y)
    return y

def spectral_gate(y, sr=44100, threshold_db=-50):
    from scipy.ndimage import median_filter
    import librosa
    S = np.abs(librosa.stft(y))
    mask = librosa.amplitude_to_db(S) > threshold_db
    return librosa.istft(S * mask, length=len(y))
```

---

## Speech Synthesis

```python
import pyttsx3
engine = pyttsx3.init()
engine.setProperty("rate", 150)
engine.say("Hello world")
engine.runAndWait()

from gtts import gTTS
tts = gTTS(text="Hello world", lang="en")
tts.save("output.mp3")
```

---

## Python for Audio

| Library | Purpose |
|---------|---------|
| pydub | High-level manipulation |
| librosa | Analysis (STFT, MFCC, beats) |
| soundfile | Read/write audio files |
| sounddevice | Play/record |
| mido | MIDI I/O |
| pyloudnorm | Loudness (BS.1770) |

### Audio File Formats

| Format | Type | Use |
|--------|------|-----|
| WAV | Uncompressed PCM | Production |
| FLAC | Lossless | Archival |
| MP3 | Lossy | Distribution |
| AAC | Lossy | Streaming |
| AIFF | PCM | Mac production |
