# TOM — Team Video: Recording Script & YouTube Upload Guide

Everything here follows the **Content Submission Guide, Part 3 (The Video)**.
Target length **4:00 – 4:30** (allowed: 2–5 min, shorter is better). One video per team.

> **Word rule.** The guide disqualifies articles and social posts that contain the word
> "hackathon" (even as a hashtag). Keep it out of the video, its title, description, tags
> and thumbnail as well. Talk about the thing you built.

---

## 0. The story in one line (everyone memorise this)

> **"TOM is a desktop assistant that does real work — files, email, documents — and gets better at *your* workflow every time you correct it, because what it learns is stored in Hindsight."**

The business problem, in plain words: *every professional re-explains the same preferences to their tools
every week ("PDFs go in Invoices", "keep emails short", "don't touch my installers").
TOM is told once, remembers for weeks, and applies it without being asked.*

What the judges score (say things that earn these — weights from the problem statement):

| Criterion | Weight | Where this video earns it |
| --- | --- | --- |
| Innovation | 30% | Act 1→4: an agent that *does* things and *learns how you like them done*, not a chatbot |
| Use of Hindsight memory | 25% | Acts 2, 4, 6 + Memory screen: retain → recall → reflect, live, visible |
| Technical implementation | 20% | "Under the hood" beat: retain/recall/reflect, offline queue, never blocks a task, approval before file moves |
| User experience | 15% | Plain-English commands, green **Remembering** card, approval prompt, Memory screen |
| Real-world impact | 10% | Closing beat: who this helps and what "adoption" looks like |

---

## 1. Roles (adjust to your team size)

| Role | Does |
| --- | --- |
| **Presenter** (one voice for the demo) | Types the commands, narrates Acts 1–6 |
| **Team members (everyone)** | On camera in the intro (one sentence each) and in the wrap-up |
| **Editor** | Assembles clips, adds title cards, exports 1080p MP4 |

The guide prefers **talking head + screen recording**. Put a small webcam box in a corner during the demo,
full-screen face only for the intro and wrap-up.

---

## 2. Before you record (do all of this — ~30 min)

### 2.1 Use the real Hindsight, not the offline stand-in
The video must show *Hindsight*. The `--offline` mode is only a stand-in for tests.

1. Create a Hindsight Cloud account: <https://ui.hindsight.vectorize.io>
2. In **billing**, add promo code **MEMHACK99** for the free credits (the problem statement says to add it *after* you register).
3. Create an API key and put it in `.env`:
   ```ini
   HINDSIGHT_API_KEY=hsk_...
   TOM_LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_...
   GROQ_MODEL=openai/gpt-oss-120b
   ```
   (Act 5, the email draft, needs the LLM.)
4. Start `python demo\run_demo.py` (or the desktop app) and confirm the memory line says
   **`Long-term memory: ONLINE — Hindsight Cloud`**. If it says OFFLINE, stop and fix that first — it is the whole video.

### 2.2 Reset the demo **before every take**
The demo uses its own memory bank and a sandbox folder, never your real files. Memory persists, so a second
take on the same bank starts with the rules already learned and Act 1 will look wrong.

```bat
python demo\seed_history.py --fresh
```
It prints two variables (`HINDSIGHT_BANK_ID`, `TOM_DOWNLOADS_DIR`). Set them in the terminal you record in
(cmd: `set NAME=value`; PowerShell: `$env:NAME='value'`).

### 2.3 Screen setup
* OBS (free): **Settings → Video**: Base and Output resolution **1920×1080**, 30 fps. Record to MP4. Record the screen, never a phone pointed at it.
* Increase terminal/app font size (Ctrl + `+`) until the back row could read it.
* Close notifications (Windows Focus Assist on), close unrelated tabs/apps, hide the desktop icons, use a plain wallpaper.
* Open in advance: (1) terminal in the TOM folder, (2) File Explorer on `demo\sandbox\Downloads`, (3) the TOM desktop app on **Chat**, (4) the GitHub repo tab.
* Do a full dry run once. Don't read the script word for word — the guide says use it as a guide; authenticity beats polish. If you slip, keep going.

### 2.4 Two ways to run the demo (pick one and stick to it)
* **Terminal (easiest to keep clean):** `python demo\run_demo.py` (press Enter between acts).
* **Desktop app (looks more like a product):** `python tom_desktop_app.py`, type the lines below in **Chat**, and finish in the **Memory** screen.

The script below works for both. Commands you type are in `code`.

---

## 3. The script (with timings)

### 0:00 – 0:30 · INTRO (on camera, full screen)
*Show: each teammate in turn, name on screen. Then cut to the TOM logo/title card.*

> **Presenter:** "Hi, I'm **[NAME]**. This is **[NAME 2]** and **[NAME 3]**." *(each says their own name)*
> "We built **TOM** — an assistant that runs on your computer and actually does the work: it organises your files, writes your emails, builds documents.
> The problem we care about is small but constant: you have to tell your tools the same preferences again and again. TOM is told once — and it remembers, using **Hindsight**."

Title card (2 seconds): **TOM — an agent that remembers how you work.**

---

### 0:30 – 1:00 · THE PROBLEM (screen)
*Show: File Explorer on `demo\sandbox\Downloads`, messy: invoices, screenshots, installers, decks mixed together. Then the terminal / Chat.*

> "This is a real person's Downloads folder — invoices, screenshots, installers, decks, all mixed up.
> Let's ask TOM to tidy it. **This is TOM on day one — no memory of me.**"

Type: `organize my downloads`

*Show: TOM's plan and the **approval prompt** (count of files, target folders). Approve it.*

> "Notice it asks before moving anything. It's sensible — but it filed my **invoices under Documents**.
> That's not where I look for bills. A normal assistant would make the same mistake next week, and the week after.
> That's the problem."

*Cue: point at the `Documents/` folder containing the PDFs.*

---

### 1:00 – 3:30 · THE DEMO (screen + small webcam box)

**Act 2 — one correction (≈ 30 s)** — *retain*
Type: `No — PDFs always go in Invoices, not Documents.`

*Show: TOM replies "Got it — I'll remember that." and lists `.pdf files → Invoices/`, plus "Saved to long-term memory".*

> "One sentence. TOM extracts the rule — PDFs to Invoices — and **retains it in Hindsight**. No settings file, no retraining."

*Optional (5 s): switch to the **Memory** screen → **Refresh**: the new memory is at the top of the list.*

**Act 3 — time passes (≈ 15 s)**
Run (a second terminal, or cut-away): `python demo\seed_history.py --history --refill`

> "Now imagine three weeks later. Behind the scenes I've added a few earlier sessions —
> screenshots go in their own folder, never touch installers, my email style — and dropped fresh files into the folder."

*Show: Explorer refreshes with new messy files.*

**Act 4 — the payoff (≈ 50 s)** — *recall — the most important 50 seconds of the video, slow down*
Type, with **different wording**: `tidy up my downloads folder`

*Show: the green **Remembering** card listing `.pdf → Invoices/`, `screenshot → Screenshots/`, `leave installers where they are`; then the approval prompt; approve; then File Explorer with files in the right folders and the installer untouched.*

> "Different words. New files. I didn't remind it of anything.
> Before every task, TOM **recalls** what Hindsight knows about me — and you can see exactly what it used, right here.
> PDFs went to Invoices. Screenshots went where I share them from. And it left my installers alone, because I told it once."

*Cue: freeze/zoom on the green card for 3 seconds. This is the before/after moment.*

**Act 5 — memory beyond files (≈ 30 s)**
Type: `email Ravi about the budget review on Friday`

*Show: a short draft, action items as bullets, signed the way you asked. Nothing is sent — it is a draft.*

> "The same memory shapes writing. I once said 'keep it under 120 words, bullets for actions, sign off as …' — and the draft follows it, for a different person and topic."

**Act 6 — reflect (≈ 20 s)**
Type: `what have you learned about me?`

*Show: the grouped summary of standing preferences.*

> "And I can ask what it has learned. That's Hindsight **reflect** reasoning over everything it retained."

**Memory screen (≈ 15 s)** — *transparency*
*Show: **Memory** screen → **Recall** with `PDFs`: the stored facts behind Act 4.*

> "Memory here isn't a black box. You can search it, inspect it, and see why TOM did what it did."

---

### 3:30 – 4:00 · UNDER THE HOOD (screen: VS Code / GitHub)
*Show: `tools/hindsight_memory.py` (large font), scrolling to `retain`, `recall`, `reflect`.*

> "Three calls. **Retain** after a correction or a finished task. **Recall** before TOM decides how to act. **Reflect** for 'what have you learned'.
> Two things I care about as an engineer: every call is time-boxed, so a slow memory server can never freeze a task — and if Hindsight is unreachable, TOM keeps working and queues what it learned to disk and syncs it later.
> And nothing that moves your files runs without your approval, with an undo for the last organisation."

*Optional 5 s: `tests/` folder — "the memory behaviour is covered by tests".*

---

### 4:00 – 4:30 · WRAP-UP (on camera again, everyone in frame)
> **Presenter:** "The one thing that surprised us: **a single correction was enough.** We expected to need lots of examples; with Hindsight, one sentence changed how TOM behaves weeks later, across different wording and new files."
> "It has limits — [say ONE honest one, e.g. *the desktop apps other than WhatsApp can't be driven yet, and TOM asks before it acts*] — but the direction is clear: assistants that stop making you repeat yourself."
> "TOM is open source — the link is in the description. Thanks for watching."

*End card (3 s): repo URL + "Memory by Hindsight".*

Total ≈ 4:30. **If you're running long, cut in this order:** Act 6 → Act 5 → the optional Memory-screen peeks → the code-file beat (keep at least the retain/recall/reflect sentence over the README diagram).

---

## 4. Don't-forget list (what the guide and judges look for)

- [ ] Intro says who you are, what you built, and why (guide: 30 s)
- [ ] You **show the agent failing without memory** (Act 1)
- [ ] **Retain and recall happen live**, on screen (Acts 2 and 4)
- [ ] A clear **before / after** moment (Act 1 vs Act 4)
- [ ] It's obvious **how Hindsight is used** (Acts 2/4/6, code beat, Memory screen)
- [ ] One key takeaway / what surprised you (wrap-up)
- [ ] **2–5 minutes**, **1080p or higher**, screen recording (not a phone), voiceover; talking head is a plus
- [ ] The word "hackathon" appears nowhere (video, title, description, thumbnail)
- [ ] Real Hindsight Cloud shown as ONLINE, not the offline stand-in

---

## 5. YouTube: titles, thumbnail, description, upload

### 5.1 Five title options (pick one, ≤ 70 characters reads best)
1. I taught my AI agent one rule — it still followed it three weeks later
2. My file-organising AI finally stopped putting invoices in the wrong folder
3. I built an assistant that learns from every correction (Hindsight memory demo)
4. One correction, zero reminders: an agent that remembers how you work
5. Why my desktop agent stopped repeating the same mistake

### 5.2 Thumbnail (guide: create it with Google Nano Banana; a free Gmail account works)
1. Open Gemini with your Google account, choose image generation (Nano Banana), attach a clear photo of one or more teammates.
2. Paste this prompt (Prompt 6 of the guide, filled in):

   > Generate a viral thumbnail for this YouTube video. Make it attention grabbing and something people scrolling would want to click. The aspect ratio must be 16:9. Include the attached person/people looking surprised, a messy folder turning into neat folders (Invoices, Screenshots), and short bold text: "IT REMEMBERED". Do not include the word hackathon.
   > Video script: *[paste section 3 of this document]*
3. Download the image (1280×720 or larger, 16:9, under 2 MB works best for YouTube).

### 5.3 Description template
```
TOM is a desktop agent that does real work — files, email, documents — and learns how YOU like it done.
Correct it once and it remembers, using Hindsight agent memory: retain after a correction, recall before it acts, reflect on demand.

In this video:
0:00 Intro
0:30 The problem: an agent with no memory
1:00 Live demo: one correction, then the payoff
3:30 How Hindsight memory is wired in
4:00 What surprised us

Project (open source): https://github.com/Rajeshponnapure/TOM
Hindsight on GitHub: https://github.com/vectorize-io/hindsight
Hindsight docs: https://hindsight.vectorize.io/
What is agent memory: https://vectorize.io/what-is-agent-memory

#AIAgents #AgentMemory #Hindsight #LLM
```
(Fix the timestamps to match your final cut.)

### 5.4 Upload steps (one person uploads; the video is one per team)
1. Sign in at <https://studio.youtube.com> → **Create → Upload videos** → choose the exported MP4.
2. Paste the title and description. Under **Thumbnail → Upload file**, use the Nano Banana image (custom thumbnails need a verified YouTube account — verify your phone number first if it's greyed out).
3. **Audience:** "No, it's not made for kids."
4. **Visibility: Public** (not Unlisted, not Private). Publish.
5. Open the video in a private window to confirm it plays without signing in.
6. **Do not** share a Google Drive link instead — the guide requires an actual YouTube post.
7. Send the YouTube link to the team. Every teammate reuses that same link in their own article and LinkedIn post (the guide asks for one video per team, and one article + one social post per person).

---

## 6. Export checklist
- [ ] MP4, 1920×1080 (or higher), audio clear (record a 10-second mic test first)
- [ ] Length between 2:00 and 5:00
- [ ] No API keys, tokens or personal email visible (check `.env`, browser tabs, Explorer paths). Blur if needed.
- [ ] Title card at the start, end card with the repo URL
