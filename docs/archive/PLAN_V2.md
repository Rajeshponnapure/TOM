# TOM v2 — Massive Upgrade Plan

## 🎯 Vision
Tom evolves from a basic task-executor into a **fully autonomous personal AI assistant** that understands complex human commands, interacts with any application, debits itself through errors, remembers user details with security awareness, and operates via a multi-agent hierarchy.

---

## 🏗️ Architecture Overview

```
                     ┌─────────────────────────────────────┐
                     │         USER (Rajesh)               │
                     │  Voice / Text / GUI / Web           │
                     └──────────────┬──────────────────────┘
                                    │
                     ┌──────────────▼──────────────────────┐
                     │       AGENT ORCHESTRATOR            │
                     │  Parses intent → Delegates → Verif. │
                     │  Compound NLP: "Open X and do Y"    │
                     └──┬────┬────┬────┬────┬────┬─────────┘
                        │    │    │    │    │    │
          ┌─────────────┘    │    │    │    │    └──────────────┐
          ▼                  ▼    ▼    ▼    ▼                   ▼
   ┌──────────┐   ┌──────────────────────────────────────┐  ┌──────────┐
   │  Voice   │   │         TOOL LAYER                   │  │  Multi-  │
   │  Engine  │   │  ┌──────┐┌───────┐┌───────────────┐  │  │  Agent   │
   │(fixed)   │   │  │NLP   ││Browser││WebAutomation  │  │  │  System  │
   │          │   │  │Parser││Tools  ││Suite (NEW)    │  │  │  CEO/CTO │
   └──────────┘   │  └──────┘└───────┘└───────────────┘  │  │  CMO/CPO │
                  │  ┌──────┐┌───────┐┌───────────────┐  │  └──────────┘
                  │  │Safety││User   ││Screen+Vision  │  │
                  │  │Guards││Profile││Tools (ENH)    │  │
                  │  └──────┘└───────┘└───────────────┘  │
                  │  ┌──────┐┌───────┐┌───────────────┐  │
                  │  │Self- ││RAG    ││Learner        │  │
                  │  │Evolut││Memory ││(ML Enhanced)  │  │
                  │  └──────┘└───────┘└───────────────┘  │
                  └──────────────────────────────────────┘
```

---

## 📋 Phase Breakdown

### PHASE 1: Advanced NLP (Compound Intent Parsing)
**Files:** `tools/nlp_parser.py`, `agent.py`

**Current Problem:** "Open WhatsApp and text Rajesh hi" → treats entire sentence as app name.

**Solution:**
- [x] Rewrite `parse_with_llm()` to extract **multi-step compound intents**
- [x] Add `compound_tasks` array support: `[{action, app, person, message}, ...]`
- [x] Add intent chaining: `and`, `then`, `after that`, `also`
- [x] Improve person name extraction with context-aware patterns
- [x] Add message body extraction with quote-aware parsing
- [x] Add `app_action` field: what to DO in the app (text, open, create, edit, delete)
- [x] LLM gets enhanced schema with compound support

**NLP Output Schema (NEW):**
```json
{
  "intent": "compound",
  "compound_tasks": [
    {"intent": "open_app", "app_name": "whatsapp", "app_action": "open"},
    {"intent": "whatsapp_message", "app_name": "whatsapp", "person_name": "Rajesh", "message_body": "hi", "app_action": "text"}
  ],
  "primary_intent": "whatsapp_message",
  "app_name": "whatsapp",
  "person_name": "Rajesh",
  "message_body": "hi"
}
```

---

### PHASE 2: Web Automation Suite (DevTools + Auto-Debug)
**Files:** `tools/browser_tools.py` → `tools/web_automation.py` (NEW)

**Current Problem:** Can open URL and click elements but cannot inspect errors, network, or console.

**Solutions:**
- [x] Create `tools/web_automation.py` with:
  - `open_devtools()` → Opens Chrome DevTools
  - `capture_console_logs()` → Returns all console messages (log, warn, error)
  - `capture_network_requests()` → Returns all network requests with status codes
  - `capture_network_errors()` → Returns failed network requests
  - `execute_in_console(js)` → Run JS in console context
  - `get_page_errors()` → Collects JS errors, 404s, console errors
  - `click_elements_by_text(text)` → Find and click buttons by visible text
  - `click_all_buttons()` → Clicks every interactive element, reports results
  - `fill_form_fields(data)` → Fills form fields with user data (smart matching)
  - `verify_page_functionality()` → Runs full verification suite
  - `auto_debug_loop(url, max_iterations)` → Full auto-debug cycle:
    1. Open URL
    2. Wait for load
    3. Capture console errors + network errors
    4. Analyze errors with LLM
    5. Generate fix
    6. Apply fix
    7. Reload and retest
    8. Repeat until clean or max iterations

---

### PHASE 3: Screen Vision & UI Interaction
**Files:** `tools/screen_tools.py` (enhance), `tools/vision_tools.py` (NEW)

**Current Problem:** Only basic OCR text extraction, no visual understanding.

**Solution:**
- [x] Add element detection (buttons, inputs, links) via visual analysis
- [x] Add region-based OCR (specific areas of screen)
- [x] Add click-by-coordinate capability
- [x] Add visual diff comparison (before/after action)
- [x] Integrate with Playwright for combined DOM + visual understanding

---

### PHASE 4: User Profile & Security Layer
**Files:** `safety/guards.py`, `tom_brain/user_profile.json`

**Current Problem:** No user detail memory, no website legitimacy checking.

**Solution:**
- [ ] Expand `user_profile.json`:
  ```json
  {
    "name": "Rajesh Ponnapureddy",
    "phone": "+91XXXXXXXXXX",
    "email": "ponnapureddyrajesh43936@gmail.com",
    "address": "...",
    "trusted_sites": ["gmail.com", "whatsapp.com", "github.com", ...],
    "blocked_sites": [],
    "detail_sharing_rules": {
      "email": {"allowed_domains": ["gmail.com", "outlook.com", ...], "requires_approval": true},
      "phone": {"allowed_domains": ["whatsapp.com"], "requires_approval": true},
      "address": {"requires_approval": true}
    }
  }
  ```
- [ ] Add `SecurityGuards.analyze_website(url)` → Returns safety score
- [ ] Add domain reputation checking
- [ ] Add context-aware detail release (only when action is legitimate)
- [ ] Add security audit trail with full logging
- [ ] Implement "impossible to bypass" security: every detail release requires:
  1. URL reputation check ✓
  2. Intent legitimacy analysis ✓
  3. User approval for sensitive details ✓
  4. Full audit logging ✓

---

### PHASE 5: Voice Mode Fix
**Files:** `tools/voice_tools.py`, `tom_desktop_app.py`, `tom_web_ui.py`

**Current Problem:** Voice mode doesn't work, button is missing/not acknowledged.

**Solution:**
- [ ] Debug microphone detection
- [ ] Fix edge-tts fallback chain
- [ ] Fix Tkinter voice button integration
- [ ] Fix Web UI voice button (pywebview JS bridge)
- [ ] Add proper error messages for voice issues
- [ ] Add fallback: if microphone fails, use text input with voice simulation
- [ ] Test voice pipeline end-to-end

---

### PHASE 6: Multi-Agent Architecture (CEO/CTO/CMO/CPO)
**Files:** `tools/agent_orchestrator.py` (NEW), `agent.py` (modify)

**Solution:**
- [ ] Create `AgentOrchestrator` class with hierarchy:
  ```
  CEO (AgentOrchestrator)
  ├── CTO (Technical Lead) — code, architecture, debugging
  ├── CMO (Marketing Lead) — content, social, communication
  ├── CPO (Product Lead) — product decisions, features
  ├── CFO (Finance Lead) — budget, expenses
  └── COO (Operations Lead) — scheduling, task management
  ```
- [ ] Each agent has:
  - `capabilities`: what it can do
  - `workflow`: how it processes tasks
  - `delegate(task)`: pass task to sub-agent
  - `report()`: return status/results
- [ ] Task decomposition: CEO breaks complex tasks → delegates to sub-agents
- [ ] Result aggregation: combine results from multiple agents
- [ ] Error escalation: sub-agent fails → CEO re-routes

---

### PHASE 7: Machine Learning Enhancement
**Files:** `tools/learning.py`, `tools/self_evolution.py`

**Solution:**
- [ ] Collect interaction data for pattern learning
- [ ] Implement online learning from user feedback
- [ ] Train intent classification model from collected data
- [ ] Use RAG for dynamic knowledge retrieval
- [ ] Implement reinforcement learning from task success/failure

---

## 🔄 Workflow Diagram

```
User Input: "Open WhatsApp and text Rajesh hi"
    │
    ▼
┌─────────────────────────────────────┐
│ Phase 1: NLP Parser                 │
│ Compound intent detected:           │
│ 1. open_app(whatsapp)               │
│ 2. whatsapp_message(Rajesh, "hi")   │
└────────────┬────────────────────────┘
             │
    ┌────────▼────────┐
    │ Safety Check    │
    │ Is WhatsApp     │
    │ safe? Is msg    │
    │ appropriate?    │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Execute Step 1  │
    │ Open WhatsApp   │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Execute Step 2  │
    │ Find Rajesh     │
    │ Type "hi"       │
    │ Send            │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Verify          │
    │ Message sent?   │
    │ Any errors?     │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Report Result   │
    │ "Done ✓"        │
    └─────────────────┘
```

---

## 🛡️ Security Architecture

```
User Details Requested
    │
    ▼
┌─────────────────────────────┐
│ 1. URL Analysis             │
│    - Check against known    │
│      trusted sites list     │
│    - Check domain age/reput │
│    - Check for HTTPS        │
│    - Score: 0-100           │
└───────────┬─────────────────┘
            │
    ┌───────▼─────────────────┐
    │ 2. Intent Analysis      │
    │    - Is the action      │
    │      legitimate?        │
    │    - Login? Register?   │
    │    - Payment?           │
    │    - Data harvest?      │
    └───────┬─────────────────┘
            │
    ┌───────▼─────────────────┐
    │ 3. Detail Release Check │
    │    - What detail?       │
    │    - Allowed for this   │
    │      action/site?       │
    │    - Requires approval? │
    └───────┬─────────────────┘
            │
    ┌───────▼─────────────────┐
    │ 4. User Approval        │
    │    (if required)        │
    │    Show: "Tom wants to  │
    │    share your email on  │
    │    example.com. Allow?" │
    └───────┬─────────────────┘
            │
    ┌───────▼─────────────────┐
    │ 5. Full Audit Log       │
    │    Record: timestamp,    │
    │    site, action, detail, │
    │    approval status       │
    └─────────────────────────┘
```

---

## 📐 Implementation Order

1. **Phase 1** (NLP) → Must come first, everything depends on understanding
2. **Phase 2** (Web Automation) → Core capability for building/testing web apps
3. **Phase 3** (Screen Vision) → Enhanced visual understanding
4. **Phase 4** (Security) → Critical before storing/sharing user details
5. **Phase 5** (Voice) → Fix existing broken functionality
6. **Phase 6** (Multi-Agent) → Advanced orchestration
7. **Phase 7** (ML) → Continuous improvement
