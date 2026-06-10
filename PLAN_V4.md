# TOM v4 — Skill System, Knowledge Base, Language Mastery & Self-Evolution Plan

## Overview
Transform Tom into a universal AI with complete skill mastery across ALL domains,
ALL programming languages, self-evolution capability, and hardware control.

---

## Phase 1: Skill Files (skills/*.md)
Create 30+ domain-specific skill files that Tom loads at runtime.

### Skill Domains:
1. **ui-ux-design** — Best UI/UX design principles, color theory, typography, layout, accessibility
2. **frontend-dev** — HTML, CSS, JavaScript, React, Next.js, Angular, Vue, Svelte, Tailwind, shadcn/ui
3. **backend-dev** — FastAPI, Node.js, Express, NestJS, Django, Spring Boot, Go, Rust
4. **3d-animation** — Three.js, WebGL, Blender, CSS 3D transforms, Canvas 3D, GSAP 3D
5. **motion-animation** — GSAP, Framer Motion, CSS animations, Lottie, Rive, keyframe animation
6. **database** — PostgreSQL, MySQL, MongoDB, Redis, SQLite, indexing, optimization, sharding
7. **data-engineering** — ETL pipelines, data warehousing, Spark, Airflow, dbt, streaming
8. **data-science** — pandas, numpy, scikit-learn, stats, visualization, feature engineering
9. **data-cleaning** — Missing data, outliers, normalization, validation, deduplication
10. **android-dev** — Kotlin, Jetpack Compose, MVVM, Room, Retrofit, Firebase, Material 3
11. **ios-dev** — Swift, SwiftUI, Core ML, URLSession, async/await, Combine
12. **macos-dev** — SwiftUI, AppKit, Metal, Core ML, Menu bar apps, AppleScript
13. **windows-dev** — C#, .NET 8, WinUI 3, WPF, MAUI, Win32, DirectX
14. **email-writing** — Professional email tone, structure, templates, follow-ups
15. **content-generation** — Blog posts, articles, social media, copywriting, SEO
16. **excel-skills** — Formulas, pivot tables, VBA, charts, data analysis, Power Query
17. **word-skills** — Formatting, styles, templates, mail merge, table of contents
18. **powerpoint-skills** — Slide design, transitions, animations, templates, storytelling
19. **power-bi** — DAX, measures, relationships, visuals, dashboards, data modeling
20. **cross-platform** — Flutter, React Native, Kotlin Multiplatform, Tauri, Electron
21. **devops** — Docker, Kubernetes, CI/CD, GitHub Actions, AWS, Terraform, monitoring
22. **cybersecurity** — OWASP, encryption, auth, network security, vulnerability assessment
23. **networking** — TCP/IP, DNS, HTTP/2, WebSockets, gRPC, load balancing
24. **mobile-ui** — Material Design, Human Interface Guidelines, responsive design
25. **testing** — Unit, integration, E2E, TDD, pytest, Jest, Playwright, Selenium
26. **system-design** — Architecture patterns, microservices, scalability, caching, CDN
27. **game-dev** — Unity, Unreal, Godot, 2D/3D physics, rendering pipelines
28. **blockchain** — Solidity, smart contracts, Web3, DeFi, NFTs
29. **machine-learning** — Supervised/unsupervised learning, neural networks, transformers
30. **deep-learning** — CNNs, RNNs, GANs, transformers, PyTorch, TensorFlow, JAX
31. **nlp** — Tokenization, embeddings, RAG, fine-tuning, prompt engineering, LLMs
32. **computer-vision** — OpenCV, object detection, segmentation, OCR, image generation

---

## Phase 2: Knowledge Base (knowledge/*.md)
Extracted from GitHub, internet, docs for Tom to reference while working.

### Knowledge Files:
- `knowledge/best-practices.md` — Universal coding best practices
- `knowledge/design-patterns.md` — All software design patterns with examples
- `knowledge/architecture-patterns.md` — Microservices, event-driven, CQRS, etc.
- `knowledge/api-design.md` — REST, GraphQL, gRPC API design standards
- `knowledge/security-best-practices.md` — Security standards for all platforms
- `knowledge/testing-strategies.md` — Testing methodologies by domain
- `knowledge/performance-optimization.md` — Performance tips for every platform
- `knowledge/deployment-strategies.md` — Deployment for web, mobile, desktop

---

## Phase 3: System Prompt / Instructions
- `SYSTEM_PROMPT.md` — Complete system instructions for Tom's optimal behavior
- Covers tone, approach, problem-solving, quality standards, workflow

---

## Phase 4: Programming Language Knowledge
- `knowledge/languages/` directory with one file per language:
  - Syntax, idioms, best practices, common pitfalls, frameworks
  - C, C++, C#, Java, Python, JavaScript, TypeScript, Go, Rust, Swift, Kotlin
  - HTML, CSS, SCSS, SQL, R, MATLAB, Dart, Lua, Ruby, PHP, Perl
  - Haskell, Scala, Clojure, Elixir, Erlang, OCaml, F#, Zig, Nim, Julia
  - Assembly, Bash, PowerShell, VBA, COBOL, Fortran, Lisp, Prolog

---

## Phase 5: Auto-Evolution System
- **tools/self_evolution.py** (existing — enhance)
  - Auto-detect current version from git tags
  - Check for newer versions of dependencies
  - Auto-update capability via git pull
  - Version management and changelog generation
  - Self-improvement through performance metrics
- **Git/GitHub integration**:
  - Auto-commit, push, pull, branch management
  - GitHub Actions workflow management
  - Issue/PR creation from agent decisions

---

## Phase 6: Mouse/Keyboard Control
- **tools/hardware_control.py** (NEW)
  - Mouse: move, click, drag, scroll, double-click, right-click
  - Keyboard: type, press keys, hotkeys, copy/paste
  - Screen: capture region, locate on screen, color detection
  - Application: focus window, resize, move
  - Based on pyautogui + ctypes + win32api + SendInput

---

## Phase 7: Model-Agnostic Support
- Enhance `_fetch_ollama_models()` to query any Ollama model
- Auto-detect model capabilities (vision, tools, context length)
- Dynamic model switching without restart
- Fallback chain: preferred → fast → any available

---

## Phase 8: Desktop App Integration
- All skills loaded at startup into Tom's knowledge
- Language knowledge available for code generation in any language
- Mouse/keyboard control via sidebar button
- Auto-evolution via settings panel
- Model switching from dropdown (already exists, enhance)
