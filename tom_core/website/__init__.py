"""Professional website building: understand → ask what only the owner knows → write each section →
render a multi-file site → verify it before reporting success.

    brief = understand("build a website for my bakery")
    if should_ask(brief): show question_text(brief); later apply_answers(brief, reply)
    result = await build(brief, ask)

`ask(system, user)` is any async model call returning text. Replaced a single model call that had to
return the whole site as one JSON blob (index.html + style.css), which broke whenever the JSON did and
produced a generic one-page template with invented details (owner report 2026-10-27).
"""
from __future__ import annotations

import json
import os
import re
from html.parser import HTMLParser
from typing import Any, Awaitable, Callable, Dict, List, Optional

from tom_core.website import render
from tom_core.website.brief import (SiteBrief, apply_answers, merge_extracted, question_text, questions,
                                    should_ask, understand)

Ask = Callable[[str, str], Awaitable[str]]
Progress = Callable[[str], None]

__all__ = ["understand", "should_ask", "question_text", "questions", "apply_answers", "merge_extracted",
           "extract_answers", "build", "verify", "SiteBrief"]

_RULES = ("Write in clear, warm, professional American English for a real small business website. "
          "Use ONLY facts from the brief. Never invent: years in business, awards, ratings, customer counts, "
          "certifications, staff names, addresses, phone numbers, prices or opening hours. Prefer concrete, "
          "sensory, specific wording over generic marketing phrases. No placeholders like lorem ipsum. "
          "Return ONLY valid JSON matching the requested shape — no markdown, no comments.")


def parse_json(text: str) -> Any:
    t = (text or "").strip()
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.DOTALL).strip()      # qwen3 reasoning blocks
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, re.DOTALL)
    if fence:
        t = fence.group(1).strip()
    start = min([i for i in (t.find("{"), t.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("no JSON in the reply")
    end = max(t.rfind("}"), t.rfind("]"))
    return json.loads(t[start:end + 1])


async def _ask_json(ask: Ask, user: str, check: Callable[[Any], bool]) -> Optional[Any]:
    """One model call for one section; one retry with the error; None when both fail (fallback used)."""
    last = ""
    for attempt in range(2):
        prompt = user if attempt == 0 else f"{user}\n\nYour previous reply could not be used ({last}). Return only the JSON."
        try:
            data = parse_json(await ask(_RULES, prompt))
            if check(data):
                return data
            last = "it did not have the requested fields"
        except Exception as exc:                       # malformed JSON, model error, timeout
            last = f"{type(exc).__name__}: {str(exc)[:120]}"
    return None


def _strs(xs: Any, n: int) -> bool:
    return isinstance(xs, list) and len(xs) >= n


# Claims a small model adds although told not to ("Award-Winning Pastries", "since 1998", "5,000 happy
# customers", "rated 4.9 stars"). A sentence with one is removed unless the owner said it.
_CLAIMS = re.compile(
    r"\b(?:award[- ]?winning|awards?|since (?:19|20)\d\d|\d+\+?\s*(?:years|yrs)|(?:thousands|hundreds|millions) of|"
    r"\d[\d,]*\+?\s*(?:happy\s+|satisfied\s+)?(?:customers|clients|patients|students|orders|reviews)|"
    r"rated|ratings?|\d(?:\.\d)?\s*stars?|#\s?1|number one|best in (?:the )?(?:city|town|region|country|state)|"
    r"certified|accredited|michelin|famous|renowned|for (?:many )?years|for decades|decades|for generations|"
    r"generations of|loyal (?:following|customers|clientele)|well[- ]known|trusted by|beloved by|favou?rite of)\b",
    re.IGNORECASE)
_BRACKET = re.compile(r"\[[^\]]{2,40}\]")
_KEEP_KEYS = {"price", "icon", "keywords"}


def _scrub(content: Dict[str, Any], brief: SiteBrief) -> int:
    """Remove unsupported claims and [placeholders] from model text in place; returns how many went."""
    owner = f"{brief.request} {brief.extra} {brief.offerings}".lower()
    removed = 0

    def text(value: str) -> str:
        nonlocal removed
        if brief.name:
            value = re.sub(r"\[(?:your |the )?(?:business|bakery|shop|company|store|brand|restaurant|clinic)?\s*name\]",
                           brief.name, value, flags=re.IGNORECASE)
        parts = re.split(r"(?<=[.!?])\s+", value)
        keep = [p for p in parts if not _BRACKET.search(p)
                and all(m.group(0).lower() in owner for m in _CLAIMS.finditer(p))]
        removed += len(parts) - len(keep)
        return " ".join(keep).strip()

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                out[k] = v if k in _KEEP_KEYS or k.startswith("_") else walk(v)
            return out
        if isinstance(node, list):
            items = [walk(x) for x in node]
            # a card whose title or text was removed is dropped whole, as is an emptied paragraph
            return [x for x in items if x and not (isinstance(x, dict) and any(
                k in x and not x[k] for k in ("title", "text", "q", "a", "name", "caption")))]
        if isinstance(node, str):
            return text(node)
        return node

    for key in list(content):
        if not key.startswith("_"):
            content[key] = walk(content[key])
    return removed


# ── fallback content (used per section when the model is unavailable or fails twice) ─────────────

def _fallback(brief: SiteBrief) -> Dict[str, Any]:
    bp = brief.blueprint
    name = brief.name or f"Our {bp.label.split(' /')[0].title()}"
    where = f" in {brief.location}" if brief.location else ""
    groups = [{"name": g, "items": [{"name": f"{g} — ask about today's selection",
                                     "description": f"Speak to us about our current {g.lower()}.", "price": ""}]}
              for g in bp.offer_groups]
    return {
        "tagline": f"A {bp.label} you can count on{where}.",
        "seo": {"title": f"{name} | {bp.label.title()}{where}",
                "description": f"{name} is a {bp.label}{where}. See our {bp.offer_label.lower()}, opening hours and how to reach us.",
                "keywords": f"{bp.label}{where}, {bp.offer_label.lower()}"},
        "hero": {"headline": f"Welcome to {name}", "subheadline": f"A {bp.label}{where} built around care, quality and you.",
                 "cta_primary": bp.cta, "cta_secondary": f"See our {bp.offer_label.lower()}"},
        "about": {"heading": "Our story",
                  "paragraphs": [f"{name} is a {bp.label}{where}. We focus on doing the essentials exceptionally well.",
                                 "Every visit should feel easy and personal — that is the standard we hold ourselves to."],
                  "highlights": [{"title": "Quality first", "text": "Careful work and honest materials."},
                                 {"title": "Personal service", "text": "We listen, and we remember what you like."},
                                 {"title": "Easy to reach", "text": "Call, message or visit — whatever suits you."}]},
        "offerings": {"heading": bp.offer_label, "intro": f"Here is what {name} offers.", "groups": groups},
        "features": {"heading": f"Why choose {name}",
                     "items": [{"title": t, "text": x, "icon": i} for t, x, i in (
                         ("Made with care", "Attention to detail in everything we do.", "heart"),
                         ("Fresh and consistent", "The same high standard every single time.", "leaf"),
                         ("On time", "We respect your schedule.", "clock"),
                         ("Trusted locally", "Built on word of mouth and repeat visits.", "users"))]},
        "gallery": {"heading": "A look inside", "items": [{"caption": c} for c in (
            f"Inside {name}", f"Our {bp.offer_groups[0].lower()}", "Behind the counter", "Made fresh",
            "Details that matter", "See you soon")]},
        "process": {"heading": "How it works", "steps": [
            {"title": "Get in touch", "text": "Call, message or use the form below."},
            {"title": "Tell us what you need", "text": "We'll suggest the best option for you."},
            {"title": "We take care of it", "text": "You get exactly what was agreed, on time."}]},
        "order": {"heading": bp.cta, "text": "Tell us what you need and we'll confirm the details with you.",
                  "button": bp.cta},
        "faq": {"heading": "Frequently asked questions", "items": [
            {"q": "How do I contact you?", "a": "Use the phone number or form on this page and we'll reply quickly."},
            {"q": "Do I need to book in advance?", "a": "For larger or custom requests, a little notice helps us do our best work."},
            {"q": "Where are you located?", "a": "See the Visit section for the address and directions."}]},
        "visit": {"heading": "Come and see us"},
        "contact": {"heading": "Get in touch", "text": "Questions, orders or feedback — we'd love to hear from you."},
    }


# ── writing ──────────────────────────────────────────────────────────────

async def write_content(brief: SiteBrief, ask: Ask, progress: Progress = lambda m: None) -> Dict[str, Any]:
    bp = brief.blueprint
    content = _fallback(brief)
    used_fallback: List[str] = []
    b = brief.summary()
    groups = ", ".join(bp.offer_groups)
    price_rule = ("Use a price ONLY if the brief states it; otherwise use an empty string for price."
                  if bp.priced else "Use an empty string for price.")
    owner_items = (f"The owner's own offerings come first and must all appear: {brief.offerings}. "
                   if brief.offerings else "")
    jobs = [
        ("hero", "the headline and search details",
         f"{b}\n\nWrite the top of the home page. JSON: {{\"tagline\": str (max 8 words), "
         "\"hero\": {\"headline\": str (max 9 words, memorable, not generic), \"subheadline\": str (1-2 sentences), "
         f"\"cta_primary\": str (2-4 words; the button for '{bp.cta}'), "
         f"\"cta_secondary\": str (2-4 words; the button to browse the {bp.offer_label.lower()})}}, "
         "\"seo\": {\"title\": str (max 60 chars, includes business name and type and city if known), "
         "\"description\": str (140-160 chars), \"keywords\": str (comma-separated, 6-10)}}",
         lambda d: isinstance(d, dict) and isinstance(d.get("hero"), dict) and d["hero"].get("headline")),
        ("about", "the story",
         f"{b}\n\nWrite the About section. JSON: {{\"heading\": str, \"paragraphs\": [2 or 3 paragraphs, "
         "50-80 words each], \"highlights\": [3 objects {\"title\": str (2-4 words), \"text\": str (one sentence)}]}",
         lambda d: isinstance(d, dict) and _strs(d.get("paragraphs"), 2) and _strs(d.get("highlights"), 2)),
        ("offerings", f"the {bp.offer_label.lower()}",
         f"{b}\n\nWrite the '{bp.offer_label}' section. {owner_items}Group items into categories such as: {groups}. "
         f"Give each category 3-5 items typical for this {bp.label}, with an appetising/specific 12-20 word "
         f"description. {price_rule} JSON: {{\"heading\": str, \"intro\": str (one sentence), \"groups\": "
         "[{\"name\": str, \"items\": [{\"name\": str, \"description\": str, \"price\": str}]}]}",
         lambda d: isinstance(d, dict) and _strs(d.get("groups"), 1)
         and all(isinstance(g, dict) and _strs(g.get("items"), 1) for g in d["groups"])),
        ("features", "why customers choose them",
         f"{b}\n\nWrite 4 reasons customers choose this business (no invented facts). JSON: {{\"heading\": str, "
         "\"items\": [4 objects {\"title\": str (2-4 words), \"text\": str (one sentence), \"icon\": one of "
         "star|leaf|heart|clock|truck|shield|users|award}]}",
         lambda d: isinstance(d, dict) and _strs(d.get("items"), 3)),
        ("faq", "the FAQs",
         f"{b}\n\nWrite 5 FAQs real customers of this {bp.label} ask (ordering, timing, customisation, "
         "payment, delivery or parking as relevant). Answers must not state facts missing from the brief — say "
         "'contact us' for anything specific. JSON: {\"heading\": str, \"items\": [{\"q\": str, \"a\": str}]}",
         lambda d: isinstance(d, dict) and _strs(d.get("items"), 3)),
    ]
    if "gallery" in bp.sections:
        jobs.append(("gallery", "gallery captions",
                     f"{b}\n\nWrite 6 short gallery captions (3-6 words) for photos this business should show. "
                     "JSON: {\"heading\": str, \"items\": [{\"caption\": str}]}",
                     lambda d: isinstance(d, dict) and _strs(d.get("items"), 4)))
    if "process" in bp.sections:
        jobs.append(("process", "how it works",
                     f"{b}\n\nWrite 3 or 4 steps describing how a customer works with this business. "
                     "JSON: {\"heading\": str, \"steps\": [{\"title\": str, \"text\": str (one sentence)}]}",
                     lambda d: isinstance(d, dict) and _strs(d.get("steps"), 3)))
    jobs.append(("order", "the call to action",
                 f"{b}\n\nWrite a short call-to-action band. Main action: '{bp.cta}'. "
                 "JSON: {\"heading\": str (max 7 words), \"text\": str (one sentence), \"button\": str (2-4 words)}, "
                 "plus \"contact\": {\"heading\": str, \"text\": str (one sentence)} in the same object.",
                 lambda d: isinstance(d, dict) and d.get("heading")))
    for key, what, prompt, check in jobs:
        progress(f"Writing {what}…")
        data = await _ask_json(ask, prompt, check)
        if data is None:
            used_fallback.append(key)
            continue
        if key == "hero":
            content["hero"].update({k: v for k, v in data["hero"].items() if isinstance(v, str) and v})
            if isinstance(data.get("seo"), dict):
                content["seo"].update({k: v for k, v in data["seo"].items() if isinstance(v, str) and v})
            if isinstance(data.get("tagline"), str) and data["tagline"].strip():
                content["tagline"] = data["tagline"].strip()
        elif key == "order":
            contact = data.pop("contact", None)
            content["order"].update({k: v for k, v in data.items() if isinstance(v, str) and v})
            if isinstance(contact, dict):
                content["contact"].update({k: v for k, v in contact.items() if isinstance(v, str) and v})
        else:
            content[key] = data
    if not bp.priced or not re.search(r"\d", brief.offerings + brief.extra):
        # Prices never come from the model unless the owner gave figures.
        for g in content.get("offerings", {}).get("groups", []):
            for it in g.get("items", []) if isinstance(g, dict) else []:
                if isinstance(it, dict):
                    it["price"] = ""
    content["_removed_claims"] = _scrub(content, brief)
    for key, fallback in _fallback(brief).items():          # a section emptied by the scrub gets standard text
        if key in content and isinstance(fallback, dict) and isinstance(content[key], dict):
            for field, value in fallback.items():
                if not content[key].get(field):
                    content[key][field] = value
    content["_fallback_sections"] = used_fallback
    return content


async def extract_answers(brief: SiteBrief, reply: str, ask: Optional[Ask]) -> SiteBrief:
    """Structured parse first; a free-text reply is also read by the model (fills empty fields only)."""
    apply_answers(brief, reply)
    if ask is None or brief.skip_questions or not brief.extra:
        return brief
    data = await _ask_json(
        ask, "Extract the business details the owner wrote. Use an empty string for anything not stated — never "
             "guess. JSON: {\"name\": str, \"location\": str, \"phone\": str, \"email\": str, \"hours\": str, "
             "\"offerings\": str, \"style\": str, \"audience\": str}\n\nOwner wrote:\n" + reply[:1500],
        lambda d: isinstance(d, dict))
    return merge_extracted(brief, data)


# ── verification ────────────────────────────────────────────────────────

class _Scan(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set = set()
        self.anchors: List[str] = []
        self.h1 = 0
        self.imgs_no_alt = 0
        self.inputs: List[str] = []
        self.label_for: set = set()
        self.meta: Dict[str, str] = {}
        self.local_refs: List[str] = []
        self.title = ""
        self._in_title = False
        self.text_words = 0
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and (a.get("href") or "").startswith("#"):
            self.anchors.append(a["href"][1:])
        if tag == "h1":
            self.h1 += 1
        if tag == "img" and not a.get("alt"):
            self.imgs_no_alt += 1
        if tag in ("input", "textarea", "select") and a.get("type") not in ("hidden", "submit"):
            self.inputs.append(a.get("id") or "")
        if tag == "label" and a.get("for"):
            self.label_for.add(a["for"])
        if tag == "meta" and a.get("name"):
            self.meta[a["name"]] = a.get("content") or ""
        if tag == "link" and a.get("rel") == "stylesheet" and not re.match(r"https?:", a.get("href") or ""):
            self.local_refs.append(a["href"])
        if tag == "script" and a.get("src") and not re.match(r"https?:", a["src"]):
            self.local_refs.append(a["src"])
        if tag == "title":
            self._in_title = True
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.text_words += len(data.split())


def verify(folder: str, brief: SiteBrief) -> Dict[str, Any]:
    """Re-read the built files and check what a reviewer would: structure, links, SEO, accessibility."""
    index = os.path.join(folder, "index.html")
    if not os.path.isfile(index):
        return {"ok": False, "issues": ["index.html is missing"], "checks": []}
    with open(index, encoding="utf-8") as fh:
        page = fh.read()
    scan = _Scan()
    scan.feed(page)
    issues, checks = [], []
    expected = [s if s != "hero" else "home" for s in brief.blueprint.sections]
    missing = [s for s in expected if s not in scan.ids]
    (issues if missing else checks).append(f"sections missing: {missing}" if missing else f"{len(expected)} sections present")
    broken = sorted({a for a in scan.anchors if a and a not in scan.ids})
    (issues if broken else checks).append(f"links to missing sections: {broken}" if broken else "every in-page link resolves")
    absent = [r for r in scan.local_refs if not os.path.isfile(os.path.join(folder, r))]
    (issues if absent else checks).append(f"missing files: {absent}" if absent else "styles.css and script.js present")
    (checks if scan.h1 == 1 else issues).append(f"{scan.h1} <h1> heading(s)")
    (checks if scan.title.strip() else issues).append("page title set" if scan.title.strip() else "no <title>")
    (checks if scan.meta.get("description") else issues).append(
        "meta description set" if scan.meta.get("description") else "no meta description")
    (checks if "viewport" in scan.meta else issues).append("mobile viewport" if "viewport" in scan.meta else "no viewport meta")
    unlabelled = [i for i in scan.inputs if not i or i not in scan.label_for]
    (issues if unlabelled else checks).append(f"form fields without labels: {unlabelled}" if unlabelled else "every form field labelled")
    if scan.imgs_no_alt:
        issues.append(f"{scan.imgs_no_alt} image(s) without alt text")
    if re.search(r"lorem ipsum|\{\{|\}\}|TODO", page, re.IGNORECASE):
        issues.append("template filler text found")
    (checks if scan.text_words >= 350 else issues).append(f"{scan.text_words} words of content")
    items = page.count('class="item card"')
    if "offerings" in brief.blueprint.sections:
        (checks if items >= 4 else issues).append(f"{items} {brief.blueprint.offer_label.lower()} items")
    return {"ok": not issues, "issues": issues, "checks": checks, "words": scan.text_words,
            "placeholders": render.placeholders_in(page)}


# ── build ───────────────────────────────────────────────────────────────

def _folder_for(brief: SiteBrief, root: Optional[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", (brief.name or f"{brief.blueprint.key}_website").lower()).strip("_")[:40] or "website"
    if root:
        path, n = os.path.join(root, base), 2
        while os.path.exists(path):
            path, n = os.path.join(root, f"{base}_{n}"), n + 1
        return path
    from tools.document_creator import _output_path as gated          # R3: workspace write gate
    path, n = gated(os.path.join("websites", base)), 2
    while os.path.exists(path):
        path, n = gated(os.path.join("websites", f"{base}_{n}")), n + 1
    return path


def _readme(brief: SiteBrief, report: Dict[str, Any]) -> str:
    todo = "\n".join(f"- {p}" for p in report.get("placeholders", [])) or "- nothing — every fact was provided"
    return f"""# {brief.name or 'Website'} — website

Built by TOM for a {brief.blueprint.label}. Open `index.html` in a browser to preview.

## Before you publish
{todo}
- Replace the gallery tiles with real photos (see `images/README.txt`).
- Check every menu/service item and add your real prices.

## Publish it (free options)
- **Netlify Drop**: drag this folder onto https://app.netlify.com/drop
- **GitHub Pages**: push the folder to a repository and enable Pages.
- Any web host: upload the files to the public folder (e.g. `public_html`).

The contact form opens the visitor's email app (or WhatsApp) addressed to you — no server needed.
"""


async def build(brief: SiteBrief, ask: Ask, progress: Progress = lambda m: None,
                root: Optional[str] = None) -> Dict[str, Any]:
    content = await write_content(brief, ask, progress)
    folder = _folder_for(brief, root)
    progress("Rendering the pages…")
    os.makedirs(os.path.join(folder, "images"), exist_ok=True)
    files = {"index.html": render.render_html(content, brief), "styles.css": render.render_css(brief),
             "script.js": render.JS, "favicon.svg": render.render_favicon(brief),
             os.path.join("images", "README.txt"): render.IMAGES_README}
    for name, text in files.items():
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    progress("Checking the result…")
    report = verify(folder, brief)
    with open(os.path.join(folder, "README.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_readme(brief, report))
    fallback = content.get("_fallback_sections", [])
    status = "success" if report["ok"] else "unverified"
    lines = [f"{'Built' if report['ok'] else 'Built, but the check found problems in'} the {brief.blueprint.label} "
             f"website for {brief.name or 'your business'}.",
             f"Folder: {folder}",
             "Sections: " + ", ".join(render.SECTION_TITLES.get(s) or (brief.blueprint.offer_label if s == 'offerings' else s.title())
                                      for s in brief.blueprint.sections),
             "Checked: " + "; ".join(report["checks"])]
    if report["issues"]:
        lines.append("Problems: " + "; ".join(report["issues"]))
    if report["placeholders"]:
        lines.append("Fill in before publishing (highlighted on the page): " + ", ".join(report["placeholders"]))
    if not brief.offerings:
        lines.append(f"The {brief.blueprint.offer_label.lower()} items are suggestions typical for a "
                     f"{brief.blueprint.label} — edit them to match what you really sell.")
    if fallback:
        lines.append("The model could not write: " + ", ".join(fallback) + " — standard text was used there.")
    if content.get("_removed_claims"):
        lines.append(f"Removed {content['_removed_claims']} unsupported claim(s) the model added (awards, years, "
                     "ratings, customer counts or placeholders) — tell me any that are true and I'll add them.")
    return {"status": status, "response_type": "website", "path": folder,
            "index": os.path.join(folder, "index.html"), "verification": report,
            "message": "\n".join(lines)}
