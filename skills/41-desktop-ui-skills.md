# Desktop UI Development — Comprehensive Skill Guide

## Frameworks at a Glance

| Framework | Language | Best For | Binary Size | Learning Curve |
|-----------|----------|----------|-------------|----------------|
| PySide6 / PyQt6 | Python | AI tools, data apps, professional software | Medium | Medium |
| Flutter Desktop | Dart | Smooth animated apps, cross-platform | Large | Medium-High |
| Tauri | Rust + JS/TS | Lightweight modern apps, web-tech stack | Tiny (<5MB) | Medium |
| Electron | Node.js + JS/TS | Complex SaaS platforms, large ecosystem | Large (100MB+) | Low |
| .NET MAUI | C# + XAML | Windows enterprise, Microsoft ecosystem | Medium | Medium |
| WPF | C# + XAML | Windows-only high-end tools | Small | High |
| Tkinter | Python | Quick tools, scripts, bundled with Python | Tiny | Low |

---

## 1. PySide6 / PyQt6 — Python Qt

### Quick Start
```bash
pip install PySide6
python -c "import PySide6; print('Qt OK')"
```

### Main Window Template
```python
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QScrollArea, QFrame,
    QSplitter, QStackedWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor, QPalette, QFont, QIcon

DARK_STYLE = """
QMainWindow, QWidget {
    background: #0f1624;
    color: #e2e8f0;
    font-family: 'Segoe UI', system-ui;
    font-size: 13px;
}
QPushButton {
    background: #1e2d45;
    border: 1px solid #253550;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover { background: #253550; border-color: #3b82f6; }
QPushButton:pressed { background: #3b82f6; color: white; }
QPushButton[primary="true"] { background: #3b82f6; border-color: #3b82f6; color: white; }
QPushButton[primary="true"]:hover { background: #2563eb; }
QLineEdit, QTextEdit {
    background: #161f30;
    border: 1px solid #1e2d45;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e2e8f0;
}
QLineEdit:focus, QTextEdit:focus { border-color: #3b82f6; }
QScrollBar:vertical { background: #0f1624; width: 6px; }
QScrollBar::handle:vertical { background: #253550; border-radius: 3px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #3b82f6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("App")
        self.resize(1400, 900)
        self.setMinimumSize(1100, 700)
        QApplication.instance().setStyleSheet(DARK_STYLE)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background: #080c14; border-right: 1px solid #1e2d45;")
        root.addWidget(sidebar)

        # Content
        content = QWidget()
        root.addWidget(content, 1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
```

### Background Worker (QThread)
```python
class Worker(QThread):
    result = Signal(str)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, task_fn, *args):
        super().__init__()
        self._task_fn = task_fn
        self._args = args

    def run(self):
        try:
            result = self._task_fn(*self._args)
            self.result.emit(str(result))
        except Exception as e:
            self.error.emit(str(e))

# Usage
worker = Worker(my_slow_function, arg1, arg2)
worker.result.connect(lambda r: label.setText(r))
worker.error.connect(lambda e: label.setText(f"Error: {e}"))
worker.start()
```

### Custom Animated Widget (QPainter)
```python
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPen, QBrush

class PulseOrb(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def _tick(self):
        self._t += 0.05
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        pulse = 1.0 + 0.06 * math.sin(self._t)
        r = min(w, h) * 0.35 * pulse

        # Radial glow
        grad = QRadialGradient(cx, cy, r * 2)
        grad.setColorAt(0, QColor(59, 130, 246, 60))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(cx - r*2), int(cy - r*2), int(r*4), int(r*4))

        # Core sphere
        grad2 = QRadialGradient(cx - r*0.2, cy - r*0.2, r)
        grad2.setColorAt(0, QColor("#1e40af"))
        grad2.setColorAt(1, QColor("#080c14"))
        p.setBrush(QBrush(grad2))
        p.setPen(QPen(QColor("#3b82f6"), 1.5))
        p.drawEllipse(int(cx - r), int(cy - r), int(r*2), int(r*2))

        # Orbiting particle
        angle = self._t * 1.2
        ox = cx + r * 1.3 * math.cos(angle)
        oy = cy + r * 1.3 * math.sin(angle) * 0.5
        p.setBrush(QBrush(QColor("#06b6d4")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(ox - 4), int(oy - 4), 8, 8)
        p.end()
```

---

## 2. Flutter Desktop

### pubspec.yaml dependencies
```yaml
dependencies:
  flutter:
    sdk: flutter
  provider: ^6.1.0
  animations: ^2.0.11
  flutter_animate: ^4.5.0
  window_manager: ^0.3.8
  bitsdojo_window: ^0.1.6
```

### App Entry + Dark Theme
```dart
import 'package:flutter/material.dart';
import 'package:window_manager/window_manager.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await windowManager.ensureInitialized();
  WindowOptions opts = const WindowOptions(
    size: Size(1400, 900),
    minimumSize: Size(1100, 700),
    center: true,
    backgroundColor: Colors.transparent,
    titleBarStyle: TitleBarStyle.hidden,
  );
  await windowManager.waitUntilReadyToShow(opts, () async {
    await windowManager.show();
    await windowManager.focus();
  });
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'App',
      themeMode: ThemeMode.dark,
      darkTheme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF3B82F6),
          secondary: Color(0xFF06B6D4),
          surface: Color(0xFF0F1624),
          background: Color(0xFF080C14),
        ),
        scaffoldBackgroundColor: const Color(0xFF080C14),
        fontFamily: 'Inter',
      ),
      home: const HomeScreen(),
    );
  }
}
```

### Animated List Item
```dart
class AnimatedListItem extends StatefulWidget {
  final String title;
  final int index;
  const AnimatedListItem({required this.title, required this.index, super.key});

  @override
  State<AnimatedListItem> createState() => _AnimatedListItemState();
}

class _AnimatedListItemState extends State<AnimatedListItem>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _opacity;
  late Animation<Offset> _slide;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: 300 + widget.index * 60),
    );
    _opacity = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeOut),
    );
    _slide = Tween<Offset>(
      begin: const Offset(0, 0.3),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeOutQuart));
    _ctrl.forward();
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _opacity,
      child: SlideTransition(
        position: _slide,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF0F1624),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF1E2D45)),
          ),
          child: Text(widget.title,
            style: const TextStyle(color: Color(0xFFE2E8F0))),
        ),
      ),
    );
  }
}
```

---

## 3. Tauri — Rust + React

### Project Structure
```
src/                  ← React frontend
  components/
  App.tsx
src-tauri/
  src/
    main.rs           ← Rust entry + commands
    commands/         ← Tauri commands
  tauri.conf.json
```

### React + Framer Motion UI
```tsx
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

interface SidebarItemProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
}

export function SidebarItem({ icon, label, active, onClick }: SidebarItemProps) {
  return (
    <motion.button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
        active
          ? "bg-blue-600/20 text-blue-400"
          : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
      )}
      whileHover={{ x: 2 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
    >
      <span className="flex-shrink-0">{icon}</span>
      <span>{label}</span>
      {active && (
        <motion.div
          layoutId="sidebar-indicator"
          className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400"
        />
      )}
    </motion.button>
  );
}
```

### Page Transitions
```tsx
const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

export function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        variants={pageVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
        className="flex-1 overflow-auto"
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
```

---

## 4. Electron — Node.js

### IPC Pattern (secure)
```javascript
// preload.js — only expose what's needed
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('electron', {
  runTask: (data) => ipcRenderer.invoke('run-task', data),
  onProgress: (cb) => ipcRenderer.on('task-progress', (_, v) => cb(v)),
  removeListeners: () => ipcRenderer.removeAllListeners('task-progress'),
});
```

```javascript
// main.js — handle IPC
const { ipcMain } = require('electron');
ipcMain.handle('run-task', async (event, data) => {
  // send progress updates
  event.sender.send('task-progress', 50);
  const result = await doHeavyWork(data);
  event.sender.send('task-progress', 100);
  return result;
});
```

```tsx
// React renderer
declare const window: Window & {
  electron: {
    runTask: (data: any) => Promise<any>;
    onProgress: (cb: (v: number) => void) => void;
    removeListeners: () => void;
  }
};

function useTask() {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    window.electron.onProgress(setProgress);
    return () => window.electron.removeListeners();
  }, []);
  const run = async (data: any) => window.electron.runTask(data);
  return { run, progress };
}
```

---

## 5. Desktop UI Patterns

### Sidebar Navigation
```
Width: 220–280px (fixed) or 72px (icon-only collapsed)
Content: logo → nav items → agent/tool sections → pinned status card
Scroll: inner canvas/scrollable when content overflows
Toggle: hamburger button collapses to icon-only or hides completely
```

### Command Palette (Cmd+K / Ctrl+K)
Essential for power users. Overlay with fuzzy search across all actions.

```python
# Tkinter command palette
class CommandPalette:
    def __init__(self, root, actions):
        self.root = root
        self.actions = actions
        root.bind("<Control-k>", self.open)

    def open(self, event=None):
        win = tk.Toplevel(self.root)
        win.geometry("560x400+%d+%d" % (
            self.root.winfo_x() + self.root.winfo_width()//2 - 280,
            self.root.winfo_y() + 120
        ))
        win.configure(bg="#161f30")
        win.overrideredirect(True)
        win.grab_set()

        entry = tk.Entry(win, bg="#161f30", fg="#e2e8f0",
            font=("Segoe UI", 14), relief="flat", bd=0,
            insertbackground="#3b82f6")
        entry.pack(fill="x", padx=16, pady=16, ipady=8)
        entry.focus_set()

        results = tk.Listbox(win, bg="#0f1624", fg="#e2e8f0",
            selectbackground="#1e3a5f", font=("Segoe UI", 11),
            relief="flat", highlightthickness=0, bd=0)
        results.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        def search(*_):
            q = entry.get().lower()
            results.delete(0, "end")
            for label, cmd in self.actions:
                if not q or q in label.lower():
                    results.insert("end", f"  {label}")
        entry.bind("<KeyRelease>", search)
        search()

        def execute(_=None):
            idx = results.curselection()
            if idx:
                self.actions[idx[0]][1]()
            win.destroy()
        results.bind("<Double-Button-1>", execute)
        entry.bind("<Return>", execute)
        win.bind("<Escape>", lambda _: win.destroy())
```

### Status Bar
Bottom status bar: connection state, model name, memory count, last action.

```python
def build_statusbar(parent, bg="#080c14"):
    bar = tk.Frame(parent, bg=bg, height=26)
    bar.pack(fill="x", side="bottom")
    tk.Frame(bar, bg="#1e2d45", height=1).pack(fill="x")

    inner = tk.Frame(bar, bg=bg)
    inner.pack(fill="x", padx=12)

    # Status dot + text
    dot_canvas = tk.Canvas(inner, width=10, height=10, bg=bg, highlightthickness=0)
    dot_canvas.pack(side="left", pady=7)
    dot = dot_canvas.create_oval(1, 1, 9, 9, fill="#10b981", outline="")

    status_var = tk.StringVar(value="Ready")
    tk.Label(inner, textvariable=status_var, bg=bg, fg="#94a3b8",
        font=("Segoe UI", 8)).pack(side="left", padx=(6, 0))

    # Right side info
    tk.Label(inner, text="v2.0 · Gemma 4", bg=bg, fg="#475569",
        font=("Segoe UI", 8)).pack(side="right")

    return status_var, dot, dot_canvas
```

---

## 6. Performance Guidelines

### Tkinter
- Never call `root.update()` or `root.update_idletasks()` inside animation loops
- Use `after()` scheduling — never `time.sleep()` in the main thread
- Batch Canvas operations: delete all and redraw, don't move individual items
- Use `StringVar`, `IntVar` etc. — only update the variable, not the widget directly
- Limit canvas items: >5000 items causes visible slowdown

### Qt (PySide6)
- All UI updates must happen on the main thread (use `Signal` from `QThread`)
- Use `QTimer.singleShot(0, fn)` to defer work to the next event loop tick
- Cache `QPixmap`/`QImage` — don't load from disk on every paint
- `setUpdatesEnabled(False)` when doing bulk widget changes, then `True` after

### Flutter
- Never call `setState()` from a build method
- Use `const` constructors everywhere possible
- `RepaintBoundary` around expensive widgets that update independently
- `ListView.builder` not `ListView` with children for long lists
- Profile with `flutter run --profile`, check DevTools for jank

### Tauri / Electron
- Never block the main process — always use `async/await` or `worker_threads`
- Debounce expensive operations triggered by input (search, resize)
- Virtualize long lists (react-window, tanstack-virtual)
- Lazy-load heavy modules with `React.lazy()` + `Suspense`
