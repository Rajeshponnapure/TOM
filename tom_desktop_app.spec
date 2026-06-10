# -*- mode: python ; coding: utf-8 -*-

# Native tkinter desktop app — no pywebview / .NET hooks needed.
_extra_hooks = []


a = Analysis(
    ['tom_desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[
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
        ('tom without bng.png', '.'),
        ('tom with bng.png', '.'),
    ],
    hiddenimports=[
        # Heavy / optional dependencies the agent pulls in dynamically
        'google_auth_oauthlib.flow', 'google.oauth2.credentials',
        'imapclient', 'pytesseract', 'reportlab',
        'langchain_core', 'langchain_ollama',
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
import os as _os
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
