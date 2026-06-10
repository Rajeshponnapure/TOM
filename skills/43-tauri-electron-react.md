# Tauri 2.0 + Electron + React — Desktop App Skill

## Stack Comparison

| | Tauri 2.0 | Electron |
|---|---|---|
| Binary size | ~5–15MB | ~150MB+ |
| RAM | ~50MB | ~200–400MB |
| Backend | Rust | Node.js |
| Frontend | Any web tech | Any web tech |
| Security | Strict CSP, no Node in renderer | Node access in renderer (requires care) |
| Best for | Lightweight, secure AI tools | Complex SaaS, large ecosystems |

---

## 1. Tauri 2.0 — Project Setup

### CLI
```bash
npm create tauri-app@latest my-app
# Choose: React + TypeScript
cd my-app && npm install
npm run tauri dev
```

### Cargo.toml dependencies
```toml
[dependencies]
tauri = { version = "2", features = ["tray-icon", "image-ico", "image-png"] }
tauri-plugin-shell = "2"
tauri-plugin-fs = "2"
tauri-plugin-notification = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
```

### Frontend package.json
```json
{
  "dependencies": {
    "@tauri-apps/api": "^2",
    "@tauri-apps/plugin-shell": "^2",
    "@tauri-apps/plugin-fs": "^2",
    "react": "^18.3",
    "react-dom": "^18.3",
    "framer-motion": "^11",
    "zustand": "^4",
    "tailwindcss": "^3",
    "clsx": "^2",
    "lucide-react": "^0.400"
  }
}
```

---

## 2. Tauri Commands + IPC

### Rust backend (src-tauri/src/main.rs)
```rust
use tauri::Manager;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct TaskResult {
    output: String,
    duration_ms: u64,
}

#[tauri::command]
async fn run_task(input: String, window: tauri::Window) -> Result<TaskResult, String> {
    // Emit progress events while working
    window.emit("task:progress", 25).ok();
    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    window.emit("task:progress", 75).ok();

    Ok(TaskResult {
        output: format!("Processed: {}", input),
        duration_ms: 150,
    })
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![run_task])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### React frontend
```tsx
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { useEffect, useState } from 'react';

function useTask() {
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    const unlisten = listen<number>('task:progress', (e) => setProgress(e.payload));
    return () => { unlisten.then(f => f()); };
  }, []);

  const run = async (input: string) => {
    setProgress(0);
    const res = await invoke<{ output: string; duration_ms: number }>('run_task', { input });
    setResult(res.output);
    setProgress(100);
  };

  return { run, progress, result };
}
```

---

## 3. Custom Frameless Window (Tauri)

### tauri.conf.json
```json
{
  "app": {
    "windows": [{
      "title": "My App",
      "width": 1400,
      "height": 900,
      "minWidth": 1100,
      "minHeight": 700,
      "decorations": false,
      "transparent": true,
      "vibrancy": "dark"
    }]
  }
}
```

### React Custom Title Bar
```tsx
import { getCurrentWindow } from '@tauri-apps/api/window';
import { motion } from 'framer-motion';

const appWindow = getCurrentWindow();

export function TitleBar({ title }: { title: string }) {
  return (
    <div
      className="h-10 flex items-center justify-between px-4 select-none"
      data-tauri-drag-region  // Makes this area draggable
    >
      <span className="text-sm font-semibold text-slate-200">{title}</span>
      <div className="flex gap-2">
        <WindowButton
          color="#F59E0B"
          onClick={() => appWindow.minimize()}
          title="Minimize"
        />
        <WindowButton
          color="#10B981"
          onClick={() => appWindow.toggleMaximize()}
          title="Maximize"
        />
        <WindowButton
          color="#EF4444"
          onClick={() => appWindow.close()}
          title="Close"
        />
      </div>
    </div>
  );
}

function WindowButton({ color, onClick, title }: { color: string; onClick: () => void; title: string }) {
  return (
    <motion.button
      onClick={onClick}
      title={title}
      className="w-3 h-3 rounded-full"
      style={{ backgroundColor: color }}
      whileHover={{ scale: 1.3 }}
      whileTap={{ scale: 0.9 }}
    />
  );
}
```

---

## 4. React + Framer Motion — Full Layout

```tsx
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';

// Sidebar Item with animated indicator
export function SidebarItem({
  icon, label, active, onClick,
}: { icon: React.ReactNode; label: string; active?: boolean; onClick: () => void }) {
  return (
    <motion.button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
        active
          ? 'bg-blue-600/20 text-blue-400'
          : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
      }`}
      whileHover={{ x: 2 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.15, ease: 'easeOut' }}
    >
      <span className="flex-shrink-0 w-4 h-4">{icon}</span>
      <span className="flex-1 text-left">{label}</span>
      <AnimatePresence>
        {active && (
          <motion.div
            key="indicator"
            layoutId="nav-indicator"
            className="w-1.5 h-1.5 rounded-full bg-blue-400"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
          />
        )}
      </AnimatePresence>
    </motion.button>
  );
}

// Page Transition Wrapper
const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit:    { opacity: 0, y: -8 },
};

export function PageTransition({ children, key: k }: { children: React.ReactNode; key: string }) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={k}
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

// Metric Card with animated number
import { useMotionValue, useSpring, useEffect } from 'framer-motion';

export function MetricCard({ label, value, color }: { label: string; value: number; color: string }) {
  const motionVal = useMotionValue(0);
  const spring = useSpring(motionVal, { damping: 30, stiffness: 200 });
  const [display, setDisplay] = useState(0);

  useEffect(() => { motionVal.set(value); }, [value]);
  useEffect(() => spring.on('change', (v) => setDisplay(Math.round(v))), [spring]);

  return (
    <motion.div
      className="rounded-xl border border-slate-800 bg-slate-900/50 p-5"
      whileHover={{ borderColor: color, scale: 1.01 }}
      transition={{ duration: 0.2 }}
    >
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-bold" style={{ color }}>{display}</p>
    </motion.div>
  );
}
```

---

## 5. Electron — Secure IPC Pattern

### main.js
```javascript
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let win;

function createWindow() {
  win = new BrowserWindow({
    width: 1400, height: 900,
    minWidth: 1100, minHeight: 700,
    frame: false,                    // Custom titlebar
    backgroundColor: '#080C14',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,        // Security: always true
      nodeIntegration: false,        // Security: always false
      sandbox: true,
    },
  });
  win.loadURL('http://localhost:5173');
}

ipcMain.handle('run-command', async (event, { cmd, args }) => {
  // Handle commands from renderer
  return { result: `Executed ${cmd}`, args };
});

app.whenReady().then(createWindow);
```

### preload.js
```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  runCommand: (cmd, args) => ipcRenderer.invoke('run-command', { cmd, args }),
  onProgress:  (cb) => ipcRenderer.on('progress', (_, v) => cb(v)),
  offProgress: ()   => ipcRenderer.removeAllListeners('progress'),
  minimize:    ()   => ipcRenderer.send('window:minimize'),
  maximize:    ()   => ipcRenderer.send('window:maximize'),
  close:       ()   => ipcRenderer.send('window:close'),
});
```

### React renderer
```tsx
declare global {
  interface Window {
    electron: {
      runCommand: (cmd: string, args: any) => Promise<any>;
      onProgress: (cb: (v: number) => void) => void;
      offProgress: () => void;
      minimize: () => void;
      maximize: () => void;
      close: () => void;
    };
  }
}

function useElectronCommand() {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    window.electron.onProgress(setProgress);
    return () => window.electron.offProgress();
  }, []);

  const run = async (cmd: string, args: any) => {
    setProgress(0);
    return window.electron.runCommand(cmd, args);
  };

  return { run, progress };
}
```

---

## 6. Tailwind + shadcn/ui — Dark Design System

### Tailwind config
```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg:       '#080c14',
        surface:  '#0f1624',
        surface2: '#161f30',
        border:   '#1e2d45',
        blue:     '#3b82f6',
        cyan:     '#06b6d4',
        purple:   '#8b5cf6',
        emerald:  '#10b981',
        amber:    '#f59e0b',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow':       'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          from: { boxShadow: '0 0 10px #3b82f620' },
          to:   { boxShadow: '0 0 20px #3b82f640, 0 0 40px #3b82f620' },
        },
      },
    },
  },
};
```

### Quick-action button component
```tsx
import { motion } from 'framer-motion';
import { clsx } from 'clsx';

interface QuickActionProps {
  icon: React.ReactNode;
  label: string;
  color: string;
  onClick: () => void;
}

export function QuickAction({ icon, label, color, onClick }: QuickActionProps) {
  return (
    <motion.button
      onClick={onClick}
      className="flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs font-semibold transition-colors"
      style={{ color }}
      whileHover={{
        backgroundColor: `${color}15`,
        borderColor: `${color}40`,
        scale: 1.04,
        y: -2,
      }}
      whileTap={{ scale: 0.96 }}
      transition={{ duration: 0.15 }}
    >
      <span className="text-lg">{icon}</span>
      <span className="text-[10px] font-medium text-slate-400">{label}</span>
    </motion.button>
  );
}
```

---

## 7. Performance Rules

### Tauri
- Batch Rust commands — avoid one `invoke()` per keypress; debounce to 16ms
- Use `listen()` for streaming data; never poll with `invoke()` in a loop
- Binary is compiled; Rust panics crash the app — always use `Result<T, String>` returns
- `tauri-plugin-fs` > raw `invoke()` for filesystem — has proper permissions

### Electron
- `contextIsolation: true` + `nodeIntegration: false` always — security non-negotiable
- Never put sensitive logic in preload.js — it runs in renderer context
- Use `worker_threads` for heavy computation — never block the main process
- Minimize IPC payload size — serialize only what the UI needs
- `setBackgroundThrottling(false)` prevents animation jank when window loses focus

### React
- `React.memo()` + `useCallback` on heavy components receiving callbacks
- `useDeferredValue` for search/filter to keep input responsive
- Virtualize lists >50 items with `@tanstack/react-virtual`
- Lazy-load route components: `const Page = React.lazy(() => import('./Page'))`
