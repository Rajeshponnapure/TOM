# Desktop & Mobile UI Frameworks — Complete Knowledge Base

## Framework Selection Matrix

| Goal | Best Choice | Why |
|------|-------------|-----|
| Most beautiful UI | Flutter Desktop | Skia-rendered, 60fps animations, Material 3 |
| Most powerful desktop | Qt 6 / QML | GPU-accelerated, native rendering, docking |
| Best web-tech desktop | Tauri 2.0 | Rust + system webview, tiny binary (~5MB) |
| Largest ecosystem | Electron | HTML/CSS/JS, VS Code, Discord, Figma |
| Best Windows enterprise | WPF / .NET MAUI | Native Windows, XAML, Microsoft toolchain |
| Best for AI SaaS | Tauri + React + Framer | Fast, secure, small binary, modern UI |
| Best Python desktop | PySide6 / PyQt6 | Qt quality from Python |
| Best lightweight | Tauri | 5–15MB binary vs Electron's 150MB+ |
| Best mobile animations | React Native + Reanimated 3 | UI thread worklets, 60fps guaranteed |
| Best cross-platform mobile | Flutter | Single codebase, iOS + Android + desktop |

---

## 1. PySide6 / PyQt6 (Python Qt)

### Installation
```bash
pip install PySide6          # Official Qt binding (LGPL)
pip install PyQt6            # GPL/commercial
```

### Dark QSS Theme (production-grade)
```python
DARK_STYLE = """
QMainWindow, QWidget {
    background: #080c14;
    color: #e2e8f0;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 13px;
}
QPushButton {
    background: #1e2d45;
    border: 1px solid #253550;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    color: #e2e8f0;
}
QPushButton:hover { background: #253550; border-color: #3b82f6; }
QPushButton:pressed { background: #3b82f6; color: white; }
QPushButton[primary="true"] { background: #3b82f6; border-color: #3b82f6; color: white; }
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #0f1624;
    border: 1px solid #1e2d45;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e2e8f0;
    selection-background-color: #1e3a5f;
}
QLineEdit:focus, QTextEdit:focus { border-color: #3b82f6; }
QScrollBar:vertical { background: #0a0e1a; width: 6px; border: none; }
QScrollBar::handle:vertical { background: #253550; border-radius: 3px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #3b82f6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal { background: #0a0e1a; height: 6px; border: none; }
QScrollBar::handle:horizontal { background: #253550; border-radius: 3px; min-width: 20px; }
QScrollBar::handle:horizontal:hover { background: #3b82f6; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
QComboBox {
    background: #1e2d45; border: 1px solid #253550;
    border-radius: 6px; padding: 6px 12px; color: #e2e8f0;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background: #0f1624; color: #e2e8f0; selection-background-color: #1e3a5f; }
QTabWidget::pane { border: 1px solid #1e2d45; }
QTabBar::tab { background: #0f1624; color: #94a3b8; padding: 8px 16px; border-right: 1px solid #1e2d45; }
QTabBar::tab:selected { color: #e2e8f0; border-bottom: 2px solid #3b82f6; }
QGroupBox { border: 1px solid #1e2d45; border-radius: 8px; margin-top: 1em; padding-top: 8px; }
QGroupBox::title { color: #94a3b8; }
QListWidget { background: #0f1624; border: 1px solid #1e2d45; border-radius: 6px; }
QListWidget::item { padding: 8px 12px; color: #e2e8f0; }
QListWidget::item:selected { background: #1e3a5f; }
QListWidget::item:hover { background: #161f30; }
QHeaderView::section { background: #0f1624; color: #94a3b8; border-right: 1px solid #1e2d45; padding: 6px 8px; }
QTableWidget { background: #0f1624; gridline-color: #1e2d45; }
QProgressBar { background: #1e2d45; border-radius: 4px; height: 6px; }
QProgressBar::chunk { background: #3b82f6; border-radius: 4px; }
"""
```

### QPropertyAnimation
```python
from PySide6.QtCore import QPropertyAnimation, QRect, QEasingCurve

def slide_in(widget, from_x=0, to_x=0, duration=300):
    anim = QPropertyAnimation(widget, b"geometry")
    geo = widget.geometry()
    anim.setStartValue(QRect(from_x, geo.y(), geo.width(), geo.height()))
    anim.setEndValue(QRect(to_x, geo.y(), geo.width(), geo.height()))
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()
    return anim  # keep reference alive
```

### QThread Worker Pattern
```python
from PySide6.QtCore import QThread, Signal

class Worker(QThread):
    result  = Signal(str)
    error   = Signal(str)
    progress = Signal(int)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn, self._args = fn, args

    def run(self):
        try:
            r = self._fn(*self._args)
            self.result.emit(str(r))
        except Exception as e:
            self.error.emit(str(e))

# Usage
w = Worker(heavy_function, arg1, arg2)
w.result.connect(label.setText)
w.error.connect(lambda e: print("Error:", e))
w.start()
```

---

## 2. Tkinter — High-Quality Patterns

Tkinter is bundled with Python — great for lightweight tools. Canvas-based animations can reach 30fps.

### Color System
```python
C = {
    "bg":      "#080c14",
    "surface": "#0f1624",
    "surface2":"#161f30",
    "border":  "#1e2d45",
    "border2": "#253550",
    "text":    "#e2e8f0",
    "text2":   "#94a3b8",
    "muted":   "#475569",
    "blue":    "#3b82f6",
    "cyan":    "#06b6d4",
    "purple":  "#8b5cf6",
    "emerald": "#10b981",
    "amber":   "#f59e0b",
    "pink":    "#ec4899",
    "red":     "#ef4444",
}
```

### Custom Canvas Button
```python
class CanvasButton:
    def __init__(self, canvas, x, y, w, h, text, color, command):
        self.cv, self.cmd = canvas, command
        self.rect = canvas.create_rectangle(x, y, x+w, y+h,
            fill=C["surface"], outline=C["border"], width=1, tags="btn")
        self.label = canvas.create_text(x+w//2, y+h//2, text=text,
            fill=color, font=("Segoe UI", 9, "bold"), tags="btn")
        canvas.tag_bind("btn", "<Enter>", self._hover_on)
        canvas.tag_bind("btn", "<Leave>", self._hover_off)
        canvas.tag_bind("btn", "<Button-1>", self._click)

    def _hover_on(self, e): self.cv.itemconfig(self.rect, fill=C["surface2"])
    def _hover_off(self, e): self.cv.itemconfig(self.rect, fill=C["surface"])
    def _click(self, e): self.cmd()
```

### Scrollable Frame
```python
def make_scrollable(parent, bg):
    canvas = tk.Canvas(parent, bg=bg, highlightthickness=0, bd=0)
    sb = tk.Scrollbar(parent, orient="vertical", command=canvas.yview,
                      width=4, relief="flat", bd=0, bg=bg, troughcolor=bg)
    inner = tk.Frame(canvas, bg=bg)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width - 4))
    canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-int(e.delta/120), "units"))
    canvas.configure(yscrollcommand=sb.set)

    return canvas, sb, inner
```

### Status Bar
```python
def make_statusbar(root, bg="#080c14"):
    bar = tk.Frame(root, bg=bg, height=26)
    bar.pack(side="bottom", fill="x")
    tk.Frame(bar, bg="#1e2d45", height=1).pack(fill="x")

    left  = tk.Frame(bar, bg=bg)
    left.pack(side="left", fill="y", padx=10)
    right = tk.Frame(bar, bg=bg)
    right.pack(side="right", fill="y", padx=10)

    dot_cv = tk.Canvas(left, width=10, height=10, bg=bg, highlightthickness=0)
    dot_cv.pack(side="left", pady=8)
    dot = dot_cv.create_oval(1, 1, 9, 9, fill="#10b981", outline="")

    sv = tk.StringVar(value="Ready")
    tk.Label(left, textvariable=sv, bg=bg, fg="#94a3b8",
             font=("Segoe UI", 8)).pack(side="left", padx=(5, 0))

    tk.Label(right, text="TOM v2.0", bg=bg, fg="#475569",
             font=("Segoe UI", 8)).pack(side="right")

    return sv, dot, dot_cv
```

---

## 3. Flutter Desktop

### pubspec.yaml
```yaml
dependencies:
  flutter_animate: ^4.5.0
  rive: ^0.13.0
  lottie: ^3.0.0
  window_manager: ^0.3.9
  go_router: ^13.0.0
  riverpod: ^2.5.1
  flutter_riverpod: ^2.5.1
```

### Staggered List Animation
```dart
import 'package:flutter_animate/flutter_animate.dart';

Widget buildList(List<String> items) {
  return Column(
    children: [
      for (final (i, item) in items.indexed)
        ListTile(title: Text(item))
          .animate(delay: (80 * i).ms)
          .fadeIn(duration: 300.ms)
          .slideY(begin: 0.15, duration: 300.ms, curve: Curves.easeOutQuart),
    ],
  );
}
```

### Custom Painter 60fps
```dart
class WavePainter extends CustomPainter {
  final double t;
  const WavePainter(this.t);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF3B82F6).withOpacity(0.6)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;
    final path = Path();
    for (double x = 0; x <= size.width; x++) {
      final y = size.height / 2 + 20 * math.sin((x / size.width) * 2 * math.pi + t);
      x == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(WavePainter old) => old.t != t;
}
```

---

## 4. Tauri 2.0 + React

### Commands (Rust → React)
```rust
#[tauri::command]
async fn process(input: String, window: tauri::Window) -> Result<String, String> {
    window.emit("progress", 50).ok();
    Ok(format!("Done: {}", input))
}
```

```tsx
const result = await invoke<string>('process', { input: 'data' });
```

### Frameless window
```json
// tauri.conf.json
{ "app": { "windows": [{ "decorations": false, "transparent": true }] } }
```

```tsx
// React: data-tauri-drag-region makes header draggable
<div data-tauri-drag-region className="h-10 bg-slate-900 flex items-center px-4">
  <span>Title</span>
</div>
```

---

## 5. Electron

### Secure IPC
```javascript
// main.js — contextIsolation: true, nodeIntegration: false always
const win = new BrowserWindow({
  webPreferences: {
    preload: path.join(__dirname, 'preload.js'),
    contextIsolation: true,
    nodeIntegration: false,
    sandbox: true,
  },
});

// preload.js — expose only specific APIs
contextBridge.exposeInMainWorld('api', {
  runTask: (data) => ipcRenderer.invoke('run-task', data),
  onProgress: (cb) => ipcRenderer.on('task-progress', (_, v) => cb(v)),
});
```

---

## 6. React Native + Reanimated 3

### Worklet animation (UI thread, 60fps)
```tsx
const scale = useSharedValue(1);
const style = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

// Trigger from JS thread
scale.value = withSpring(1.2, { damping: 15 });
```

### Gesture + animation
```tsx
const pan = Gesture.Pan()
  .onUpdate((e) => { translateX.value = e.translationX; })
  .onEnd(() => { translateX.value = withSpring(0); });
```

---

## 7. Desktop UI Patterns — Universal

### Sidebar width standards
- Icon-only collapsed: 56–72px
- Standard: 220–260px
- Wide with descriptions: 280–320px

### Typography scale
- App title: 16–18px bold
- Section headers: 8–9px bold uppercase letter-spacing
- Body: 9–11px regular
- Button labels: 8–10px semibold
- Status/meta: 7–8px regular

### Color roles
- `#080c14` — deepest background (window fill)
- `#0f1624` — surface cards and panels
- `#161f30` — elevated surface (hover states, inputs)
- `#1e2d45` — default borders
- `#253550` — focused borders, hover borders
- `#e2e8f0` — primary text
- `#94a3b8` — secondary text (labels, descriptions)
- `#475569` — muted/disabled text

### Animation timing
- Micro-interactions: 100–150ms easeOut
- Panel slide in/out: 200–280ms easeOutCubic
- Page transitions: 200–300ms easeInOut
- Loading states: 800–1200ms loop
- Spring stiffness: 120–200, damping: 12–25

### 30fps Tkinter animation loop (safe)
```python
def _animation_loop(self):
    # Do drawing here
    self.root.after(33, self._animation_loop)  # 33ms ≈ 30fps
```

### Quick-action grid sizing
- 5 columns: button width ≈ (panel_width - padding*2) / 5
- Button height: min 34px, ideal 40–46px
- Icon size: 14–16px, label size: 8–9px
- Gap: 4–6px between buttons
- Section padding: 8–12px top/bottom
