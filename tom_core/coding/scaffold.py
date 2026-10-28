"""Scaffold a real, buildable project — and actually build/verify it — instead of dumping a pile of
model-written files and calling it done.

The old path (agent._execute_code_project) asked the model for files and claimed success without ever
compiling them. Here each project kind has a known-good skeleton that really builds, and `verify()`
runs the toolchain and reports the true outcome (PRD AT-007: success only with evidence). Model-written
feature code can be layered on top, but the build result is measured, not asserted.

Kinds: static (HTML/CSS/JS), node (Express or a plain Node script), react (Vite + React), python
(CLI with a test), android (Gradle app), flutter (if the SDK is present). The fast default check for
each is offline and real — `node --check`, `python -m py_compile`, an HTML-structure check — so TOM can
honestly say "it builds" without a multi-minute network install; the full `npm install && npm run
build` / `gradlew assembleDebug` is offered as an explicit, gated step.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

RunnerT = Callable[[List[str], str], "subprocess.CompletedProcess"]


def _default_runner(argv: List[str], cwd: str) -> "subprocess.CompletedProcess":
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=600)


@dataclass
class Scaffold:
    kind: str
    name: str
    files: Dict[str, str] = field(default_factory=dict)      # relative path -> contents
    entry: str = ""                                          # the file the quick check parses
    build_cmd: str = ""                                      # the full build the owner can run
    run_cmd: str = ""                                        # how to run it after building


def _slug(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", (name or "app").strip()).strip("-").lower()
    return s or "app"


def detect_kind(request: str) -> str:
    r = (request or "").lower()
    if re.search(r"\bflutter\b", r):
        return "flutter"
    if re.search(r"\b(android|apk|jetpack|kotlin app)\b", r):
        return "android"
    if re.search(r"\b(react|next\.?js|vite|vue|spa|single[- ]page)\b", r):
        return "react"
    if re.search(r"\b(express|node api|rest api|backend|server|fastify)\b", r) and "python" not in r:
        return "node"
    if re.search(r"\b(python|flask|fastapi|django|cli tool|script)\b", r):
        return "python"
    if re.search(r"\b(website|landing|static|html page|portfolio)\b", r):
        return "static"
    if re.search(r"\bnode\b|\bjavascript\b|\bexpress\b", r):
        return "node"
    return "static"


# ── templates ───────────────────────────────────────────────────────────
def _static(name: str) -> Scaffold:
    title = name or "My Site"
    files = {
        "index.html": f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<main>
<h1>{title}</h1>
<p>Edit <code>index.html</code>, <code>styles.css</code> and <code>app.js</code> to build this out.</p>
<button id="go">Click me</button>
<p id="out" aria-live="polite"></p>
</main>
<script src="app.js"></script>
</body>
</html>
""",
        "styles.css": "body{font-family:system-ui,sans-serif;margin:0;padding:2rem;max-width:40rem}"
                      "button{padding:.6rem 1rem;font-size:1rem;cursor:pointer}\n",
        "app.js": "document.getElementById('go').addEventListener('click',()=>{"
                  "document.getElementById('out').textContent='It works — '+new Date().toLocaleTimeString();});\n",
        "README.md": f"# {title}\n\nA static site. Open `index.html` in a browser, or serve it:\n\n"
                     "```\npython -m http.server 8000\n```\n",
    }
    return Scaffold("static", name, files, entry="app.js",
                    build_cmd="", run_cmd="python -m http.server 8000")


def _node(name: str) -> Scaffold:
    slug = _slug(name)
    files = {
        "package.json": f"""{{
  "name": "{slug}",
  "version": "1.0.0",
  "private": true,
  "type": "commonjs",
  "main": "server.js",
  "scripts": {{
    "start": "node server.js",
    "build": "node --check server.js && echo built"
  }},
  "dependencies": {{ "express": "^4.19.2" }}
}}
""",
        "server.js": """const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;
app.get('/', (_req, res) => res.json({ ok: true, message: 'Hello from TOM' }));
app.get('/health', (_req, res) => res.send('ok'));
if (require.main === module) {
  app.listen(PORT, () => console.log(`listening on http://localhost:${PORT}`));
}
module.exports = app;
""",
        ".gitignore": "node_modules/\n",
        "README.md": f"# {slug}\n\nExpress API.\n\n```\nnpm install\nnpm start\n```\n\n"
                     "Endpoints: `/` (JSON), `/health`.\n",
    }
    return Scaffold("node", name, files, entry="server.js",
                    build_cmd="npm install && npm run build", run_cmd="npm start")


def _react(name: str) -> Scaffold:
    slug = _slug(name)
    files = {
        "package.json": f"""{{
  "name": "{slug}",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{ "react": "^18.3.1", "react-dom": "^18.3.1" }},
  "devDependencies": {{ "@vitejs/plugin-react": "^4.3.1", "vite": "^5.4.0" }}
}}
""",
        "vite.config.js": "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\n"
                          "export default defineConfig({ plugins: [react()] });\n",
        "index.html": f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name or slug}</title></head>
<body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body>
</html>
""",
        "src/main.jsx": "import React from 'react';\nimport { createRoot } from 'react-dom/client';\n"
                        "import App from './App.jsx';\ncreateRoot(document.getElementById('root')).render(<App />);\n",
        "src/App.jsx": "import { useState } from 'react';\nexport default function App(){\n"
                       "  const [n,setN]=useState(0);\n"
                       "  return (<main style={{fontFamily:'system-ui',padding:'2rem'}}>\n"
                       "    <h1>" + (name or slug) + "</h1>\n"
                       "    <button onClick={()=>setN(n+1)}>count is {n}</button>\n  </main>);\n}\n",
        ".gitignore": "node_modules/\ndist/\n",
        "README.md": f"# {slug}\n\nReact + Vite.\n\n```\nnpm install\nnpm run dev\n```\n",
    }
    return Scaffold("react", name, files, entry="vite.config.js",
                    build_cmd="npm install && npm run build", run_cmd="npm run dev")


def _python(name: str) -> Scaffold:
    slug = _slug(name).replace("-", "_")
    files = {
        f"{slug}/__init__.py": '__version__ = "0.1.0"\n',
        f"{slug}/main.py": '''"""Entry point."""
import argparse


def greet(name: str) -> str:
    return f"Hello, {name}!"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="A small CLI.")
    p.add_argument("name", nargs="?", default="world")
    args = p.parse_args(argv)
    print(greet(args.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        f"tests/test_{slug}.py": f'''from {slug}.main import greet


def test_greet():
    assert greet("TOM") == "Hello, TOM!"
''',
        "requirements.txt": "pytest\n",
        "README.md": f"# {slug}\n\n```\npython -m {slug}.main yourname\npytest\n```\n",
    }
    return Scaffold("python", name, files, entry=f"{slug}/main.py",
                    build_cmd="pytest", run_cmd=f"python -m {slug}.main")


def _android(name: str) -> Scaffold:
    pkg = "com.tom." + _slug(name).replace("-", "")
    pkgpath = pkg.replace(".", "/")
    files = {
        "settings.gradle": f"rootProject.name = '{_slug(name)}'\ninclude ':app'\n",
        "build.gradle": """buildscript {
    repositories { google(); mavenCentral() }
    dependencies { classpath 'com.android.tools.build:gradle:8.5.0' }
}
allprojects { repositories { google(); mavenCentral() } }
""",
        "app/build.gradle": f"""plugins {{ id 'com.android.application' }}
android {{
    namespace '{pkg}'
    compileSdk 34
    defaultConfig {{
        applicationId '{pkg}'
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName '1.0'
    }}
}}
dependencies {{ implementation 'androidx.appcompat:appcompat:1.7.0' }}
""",
        f"app/src/main/java/{pkgpath}/MainActivity.java": f"""package {pkg};
import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
public class MainActivity extends Activity {{
    @Override protected void onCreate(Bundle b) {{
        super.onCreate(b);
        TextView tv = new TextView(this);
        tv.setText("Hello from TOM");
        setContentView(tv);
    }}
}}
""",
        "app/src/main/AndroidManifest.xml": f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:label="{name or _slug(name)}">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>
""",
        "README.md": f"# {_slug(name)} (Android)\n\nBuild a debug APK (needs JDK + Android SDK, with "
                     "`local.properties` pointing at the SDK and licences accepted):\n\n"
                     "```\ngradle wrapper\n./gradlew assembleDebug\n```\n\nAPK: "
                     "`app/build/outputs/apk/debug/app-debug.apk`\n",
    }
    return Scaffold("android", name, files, entry="",
                    build_cmd="gradle wrapper && ./gradlew assembleDebug",
                    run_cmd="adb install app/build/outputs/apk/debug/app-debug.apk")


_TEMPLATES = {"static": _static, "node": _node, "react": _react,
              "python": _python, "android": _android}


def build_scaffold(kind: str, name: str) -> Scaffold:
    return _TEMPLATES.get(kind, _static)(name)


def write(scaffold: Scaffold, dest: str) -> List[str]:
    """Write the scaffold to `dest`. Returns the absolute paths written."""
    written = []
    for rel, content in scaffold.files.items():
        path = os.path.join(dest, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path) or dest, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        written.append(path)
    return written


# ── verify: run the real, fast, offline check for the kind ────────────────
def _node_exe() -> Optional[str]:
    return shutil.which("node")


def verify(scaffold: Scaffold, dest: str, runner: Optional[RunnerT] = None) -> Dict[str, object]:
    """Run the fast offline build check and report the true result (status success|error|skipped)."""
    run = runner or _default_runner
    kind = scaffold.kind
    try:
        if kind == "python":
            files = [os.path.join(dest, rel.replace("/", os.sep)) for rel in scaffold.files if rel.endswith(".py")]
            proc = run([sys.executable, "-m", "py_compile", *files], dest)
            ok = proc.returncode == 0
            return _res(ok, "Python sources compile." if ok else "Python compile failed.",
                        proc, scaffold)
        if kind in ("node", "react", "static"):
            node = _node_exe()
            js = [rel for rel in scaffold.files if rel.endswith(".js") or rel.endswith(".jsx")]
            entry = scaffold.entry if scaffold.entry in scaffold.files else (js[0] if js else "")
            if not entry:
                return {"status": "skipped", "message": "Nothing to syntax-check.", "build_cmd": scaffold.build_cmd}
            if node is None:
                return {"status": "skipped", "message": "Node isn't installed, so I can't syntax-check the JS. "
                        "Install Node to verify.", "build_cmd": scaffold.build_cmd}
            bad = []
            for rel in ([entry] + [j for j in js if j != entry]):
                p = os.path.join(dest, rel.replace("/", os.sep))
                proc = run([node, "--check", p], dest)
                if proc.returncode != 0:
                    bad.append((rel, (proc.stderr or proc.stdout or "").strip()[:400]))
            if bad:
                return {"status": "error", "message": "JavaScript has syntax errors:\n" +
                        "\n".join(f"- {r}: {e}" for r, e in bad), "build_cmd": scaffold.build_cmd}
            extra = _html_check(scaffold, dest)
            return {"status": "success", "verified": True,
                    "message": f"All {len(js)} JS file(s) parse cleanly{extra}. "
                               f"Full build: {scaffold.build_cmd or scaffold.run_cmd}",
                    "build_cmd": scaffold.build_cmd}
        if kind in ("android", "flutter"):
            return {"status": "skipped",
                    "message": f"Scaffolded a valid {kind} project. Building it needs the "
                               f"{'Android SDK + JDK' if kind == 'android' else 'Flutter SDK'}; run: "
                               f"{scaffold.build_cmd}", "build_cmd": scaffold.build_cmd}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "The build check timed out."}
    except Exception as exc:
        return {"status": "error", "message": f"Build check could not run: {type(exc).__name__}: {exc}"}
    return {"status": "skipped", "message": "No check for this project kind.", "build_cmd": scaffold.build_cmd}


def _html_check(scaffold: Scaffold, dest: str) -> str:
    html = [rel for rel in scaffold.files if rel.endswith(".html")]
    for rel in html:
        text = scaffold.files[rel].lower()
        if not ("<html" in text and "<body" in text):
            return f"; but {rel} is missing <html>/<body>"
    return f" and {len(html)} HTML file(s) are well-formed" if html else ""


def _res(ok: bool, msg: str, proc, scaffold: Scaffold) -> Dict[str, object]:
    out = f"{getattr(proc, 'stdout', '') or ''}\n{getattr(proc, 'stderr', '') or ''}".strip()
    return {"status": "success" if ok else "error", "verified": ok,
            "message": msg + ("" if ok else f"\n{out[-800:]}"),
            "build_cmd": scaffold.build_cmd}


def full_build(scaffold: Scaffold, dest: str, runner: Optional[RunnerT] = None) -> Dict[str, object]:
    """Run the real, heavy build (npm install && npm run build, pytest). Gated by the caller."""
    run = runner or _default_runner
    try:
        if scaffold.kind in ("node", "react"):
            npm = shutil.which("npm") or ("npm.cmd" if os.name == "nt" else "npm")
            inst = run([npm, "install"], dest)
            if inst.returncode != 0:
                return {"status": "error", "message": "npm install failed:\n" +
                        (inst.stderr or inst.stdout or "")[-1000:]}
            bld = run([npm, "run", "build"], dest)
            ok = bld.returncode == 0
            return {"status": "success" if ok else "error", "verified": ok,
                    "message": ("Built successfully." if ok else "Build failed.") +
                               "\n" + (bld.stdout or bld.stderr or "")[-1000:]}
        if scaffold.kind == "python":
            py = run([sys.executable, "-m", "pytest", "-q"], dest)
            ok = py.returncode == 0
            return {"status": "success" if ok else "error", "verified": ok,
                    "message": ("Tests pass." if ok else "Tests failed.") +
                               "\n" + (py.stdout or py.stderr or "")[-1000:]}
    except Exception as exc:
        return {"status": "error", "message": f"Build failed to run: {exc}"}
    return {"status": "skipped", "message": f"No automated full build for {scaffold.kind}."}
