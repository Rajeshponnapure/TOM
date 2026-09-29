# -*- mode: python ; coding: utf-8 -*-

# Native tkinter desktop app — no pywebview / .NET hooks needed.
_extra_hooks = []

import os as _os

_ROOT = _os.path.abspath(globals().get("SPECPATH") or _os.getcwd())  # SPECPATH IS the spec's dir

# Everything that should ship next to the app. PyInstaller aborts the whole
# build when a data path is missing, and 'awesome-claude-skills' is a vendored
# (gitignored) repo that a clean checkout does not have — so the list is built
# from what actually exists here, and anything dropped is reported out loud.
# The dest names matter: a directory must keep its own name or the app would
# look for knowledge/ and tools/ in the wrong place inside the bundle.
_DATAS = [
    ('config', 'config'),
    ('safety', 'safety'),
    ('tools', 'tools'),
    ('agents', 'agents'),
    ('resources', 'resources'),
    ('knowledge', 'knowledge'),
    ('skills', 'skills'),
    ('awesome-claude-skills', 'awesome-claude-skills'),
    ('AGENTS.md', '.'),
    ('CLAUDE.md', '.'),
    ('SYSTEM_PROMPT.md', '.'),
]
_missing = [src for src, _dest in _DATAS
            if not _os.path.exists(_os.path.join(_ROOT, src))]
if _missing:
    print(f"[SPEC] Not in this checkout, skipping: {', '.join(_missing)}")
_datas = [(src, dest) for src, dest in _DATAS
          if _os.path.exists(_os.path.join(_ROOT, src))]


a = Analysis(
    ['tom_desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        # Heavy / optional dependencies the agent pulls in dynamically
        'google_auth_oauthlib.flow', 'google.oauth2.credentials',
        'imapclient', 'pytesseract', 'reportlab',
        'langchain_core', 'langchain_ollama',
        # Groq is the default provider whenever GROQ_API_KEY is set: the import
        # lives inside llm_factory.make_groq_model(), so pin it explicitly.
        'langchain_groq', 'groq', 'openai', 'httpx',
        'apscheduler', 'apscheduler.schedulers.background',
        'docx', 'openpyxl', 'pptx',
        'matplotlib', 'plotly',
        'edge_tts', 'cv2', 'bs4', 'lxml', 'requests',
        'pygame', 'psutil',
        'chromadb', 'onnxruntime',
        # Voice stack (talk-back + listening) — keep so the frozen exe can speak/listen
        'pyttsx3', 'speech_recognition', 'pyaudio',
    ],
    hookspath=_extra_hooks,
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Torch is ~487MB and pulls native CUDA/MKL DLLs that crash in onefile bundles.
        'torch', 'torchvision', 'torchaudio',
        'sentence_transformers',
        # NOTE: tkinter MUST NOT be excluded — the native desktop app is built on it.
        'bpy',
        'langchain_community.embeddings.huggingface',
        'langchain_community.embeddings.sentence_transformer',
        'langchain_community.vectorstores.scann',
    ],
    noarchive=False,
    optimize=0,
)
# ── Bundle trim (production) ────────────────────────────────────────────
# Drop the vendored repo's .git objects — dead weight inside the exe.
a.datas = [
    d for d in a.datas
    if "awesome-claude-skills/.git" not in d[0].replace(_os.sep, "/")
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='tom_desktop_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
