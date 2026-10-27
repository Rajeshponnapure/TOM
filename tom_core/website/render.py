"""Render a planned website to static files: index.html, styles.css, script.js, favicon.svg.

No framework and no build step: the folder opens straight from disk and can be uploaded to any host
(Netlify, GitHub Pages, cPanel). Semantic sections, one <h1>, labelled form fields, keyboard-usable
navigation, reduced-motion support, SEO meta + Open Graph + schema.org JSON-LD.
Facts the owner did not give render as visible placeholders (class "placeholder"), never invented.
"""
from __future__ import annotations

import html
import json
import re
from typing import Any, Dict, List
from urllib.parse import quote, quote_plus

from tom_core.website.brief import SiteBrief

SECTION_TITLES = {"about": "About", "offerings": "", "features": "Why Us", "gallery": "Gallery",
                  "process": "How It Works", "order": "", "faq": "FAQ", "visit": "Visit", "contact": "Contact"}

_ICONS = {
    "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    "heart": '<path d="M12 20s-7-4.4-7-10a4 4 0 017-2.6A4 4 0 0119 10c0 5.6-7 10-7 10z"/>',
    "leaf": '<path d="M5 19c0-8 6-14 15-14 0 9-6 15-14 15"/><path d="M5 19l7-7"/>',
    "clock": '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
    "truck": '<path d="M3 7h11v8H3zM14 10h4l3 3v2h-7z"/><circle cx="7" cy="17" r="1.6"/><circle cx="17" cy="17" r="1.6"/>',
    "shield": '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
    "users": '<circle cx="9" cy="9" r="3"/><path d="M3 19c0-3 3-5 6-5s6 2 6 5"/><circle cx="17" cy="8" r="2.4"/><path d="M16 14c3 0 5 1.8 5 4.5"/>',
    "award": '<circle cx="12" cy="9" r="5"/><path d="M9 13.5L8 21l4-2 4 2-1-7.5"/>',
    "sparkle": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6"/>',
    "check": '<path d="M5 12l4 4 10-10"/>',
}
_ICON_ORDER = ("star", "leaf", "heart", "clock", "truck", "shield", "users", "award")


def esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def icon(name: str) -> str:
    body = _ICONS.get(name) or _ICONS["sparkle"]
    return (f'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


def placeholder(text: str) -> str:
    return f'<span class="placeholder" title="Fill this in before publishing">[{esc(text)}]</span>'


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:48] or "item"


def _wa_link(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    # wa.me needs the international form; a bare local number can't be dialled from a link reliably.
    return f"https://wa.me/{digits}" if (phone.strip().startswith("+") and len(digits) >= 10) else ""


# ── sections ──────────────────────────────────────────────────────────────

def _hero(c: Dict[str, Any], brief: SiteBrief) -> str:
    h = c.get("hero", {})
    name = brief.name or "Your Business Name"
    secondary_target = "#offerings" if "offerings" in brief.blueprint.sections else "#about"
    cta_target = "#order" if "order" in brief.blueprint.sections else "#contact"
    loc = f'<p class="hero-meta">{icon("clock")} {esc(brief.hours)}</p>' if brief.hours else ""
    return f"""
<section id="home" class="hero">
  <div class="hero-art" aria-hidden="true"><span></span><span></span><span></span></div>
  <div class="container hero-inner reveal">
    <p class="eyebrow">{esc(name)}{(' · ' + esc(brief.location)) if brief.location else ''}</p>
    <h1>{esc(h.get('headline') or name)}</h1>
    <p class="lead">{esc(h.get('subheadline'))}</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="{cta_target}">{esc(h.get('cta_primary') or brief.blueprint.cta)}</a>
      <a class="btn btn-ghost" href="{secondary_target}">{esc(h.get('cta_secondary') or 'Explore')}</a>
    </div>
    {loc}
  </div>
</section>"""


def _about(c: Dict[str, Any], brief: SiteBrief) -> str:
    a = c.get("about", {})
    # small models sometimes echo a key name ("paragraphs") as a list item — only real sentences count
    paras = "".join(f"<p>{esc(p)}</p>" for p in a.get("paragraphs", []) if isinstance(p, str) and len(p.split()) >= 6)
    highlights = "".join(
        f'<li class="card">{icon(_ICON_ORDER[i % len(_ICON_ORDER)])}<div><h3>{esc(x.get("title"))}</h3>'
        f'<p>{esc(x.get("text"))}</p></div></li>'
        for i, x in enumerate(a.get("highlights", [])) if isinstance(x, dict))
    return f"""
<section id="about" class="section">
  <div class="container split reveal">
    <div>
      <p class="eyebrow">About</p>
      <h2>{esc(a.get('heading') or 'Our Story')}</h2>
      {paras}
    </div>
    <ul class="highlights" role="list">{highlights}</ul>
  </div>
</section>"""


def _offerings(c: Dict[str, Any], brief: SiteBrief) -> str:
    o = c.get("offerings", {})
    groups = [g for g in o.get("groups", []) if isinstance(g, dict) and g.get("items")]
    tabs = "".join(
        f'<button type="button" class="tab{" active" if i == 0 else ""}" data-filter="{slug(g.get("name"))}" '
        f'aria-pressed="{"true" if i == 0 else "false"}">{esc(g.get("name"))}</button>'
        for i, g in enumerate(groups)) if len(groups) > 1 else ""
    panels = []
    for i, g in enumerate(groups):
        items = []
        for it in g.get("items", []):
            if not isinstance(it, dict):
                continue
            price = f'<span class="price">{esc(it.get("price"))}</span>' if it.get("price") else ""
            items.append(f'<article class="item card"><div class="item-head"><h3>{esc(it.get("name"))}</h3>{price}</div>'
                         f'<p>{esc(it.get("description"))}</p></article>')
        panels.append(f'<div class="group" data-group="{slug(g.get("name"))}"{"" if i == 0 or not tabs else " hidden"}>'
                      f'<h3 class="group-title">{esc(g.get("name"))}</h3><div class="grid-3">{"".join(items)}</div></div>')
    return f"""
<section id="offerings" class="section section-soft">
  <div class="container reveal">
    <p class="eyebrow">{esc(brief.blueprint.offer_label)}</p>
    <h2>{esc(o.get('heading') or brief.blueprint.offer_label)}</h2>
    <p class="section-intro">{esc(o.get('intro'))}</p>
    {f'<div class="tabs" role="toolbar" aria-label="Filter {esc(brief.blueprint.offer_label)}">{tabs}</div>' if tabs else ''}
    {''.join(panels)}
  </div>
</section>"""


def _features(c: Dict[str, Any], brief: SiteBrief) -> str:
    f = c.get("features", {})
    cards = "".join(
        f'<article class="feature card">{icon(x.get("icon") if x.get("icon") in _ICONS else _ICON_ORDER[i % len(_ICON_ORDER)])}'
        f'<h3>{esc(x.get("title"))}</h3><p>{esc(x.get("text"))}</p></article>'
        for i, x in enumerate(f.get("items", [])) if isinstance(x, dict))
    return f"""
<section id="features" class="section">
  <div class="container reveal">
    <p class="eyebrow">Why Us</p>
    <h2>{esc(f.get('heading') or 'Why people choose us')}</h2>
    <div class="grid-4">{cards}</div>
  </div>
</section>"""


def _gallery(c: Dict[str, Any], brief: SiteBrief) -> str:
    g = c.get("gallery", {})
    tiles = "".join(
        f'<figure class="tile tile-{i % 6}"><div class="tile-art" role="img" aria-label="{esc(x.get("caption"))}">'
        f'{icon(_ICON_ORDER[i % len(_ICON_ORDER)])}</div><figcaption>{esc(x.get("caption"))}</figcaption></figure>'
        for i, x in enumerate(g.get("items", [])) if isinstance(x, dict))
    return f"""
<section id="gallery" class="section section-soft">
  <div class="container reveal">
    <p class="eyebrow">Gallery</p>
    <h2>{esc(g.get('heading') or 'A look inside')}</h2>
    <!-- To use real photos, replace each tile-art block with an img element: see images/README.txt -->
    <div class="gallery">{tiles}</div>
  </div>
</section>"""


def _process(c: Dict[str, Any], brief: SiteBrief) -> str:
    p = c.get("process", {})
    steps = "".join(f'<li class="step card"><span class="step-n">{i}</span><h3>{esc(s.get("title"))}</h3>'
                    f'<p>{esc(s.get("text"))}</p></li>'
                    for i, s in enumerate((s for s in p.get("steps", []) if isinstance(s, dict)), 1))
    return f"""
<section id="process" class="section">
  <div class="container reveal">
    <p class="eyebrow">How It Works</p>
    <h2>{esc(p.get('heading') or 'How it works')}</h2>
    <ol class="steps" role="list">{steps}</ol>
  </div>
</section>"""


def _order(c: Dict[str, Any], brief: SiteBrief) -> str:
    o = c.get("order", {})
    links = []
    if brief.phone:
        links.append(f'<a class="btn btn-light" href="tel:{esc(re.sub(r"[^0-9+]", "", brief.phone))}">Call {esc(brief.phone)}</a>')
        if (wa := _wa_link(brief.phone)):
            links.append(f'<a class="btn btn-outline-light" href="{esc(wa)}" target="_blank" rel="noopener">WhatsApp us</a>')
    links.append(f'<a class="btn btn-outline-light" href="#contact">{esc(o.get("button") or brief.blueprint.cta)}</a>')
    return f"""
<section id="order" class="cta-band">
  <div class="container cta-inner reveal">
    <div>
      <h2>{esc(o.get('heading') or brief.blueprint.cta)}</h2>
      <p>{esc(o.get('text'))}</p>
    </div>
    <div class="cta-actions">{''.join(links)}</div>
  </div>
</section>"""


def _faq(c: Dict[str, Any], brief: SiteBrief) -> str:
    f = c.get("faq", {})
    items = "".join(f'<details class="faq-item"><summary>{esc(x.get("q"))}</summary><p>{esc(x.get("a"))}</p></details>'
                    for x in f.get("items", []) if isinstance(x, dict) and x.get("q"))
    return f"""
<section id="faq" class="section section-soft">
  <div class="container narrow reveal">
    <p class="eyebrow">FAQ</p>
    <h2>{esc(f.get('heading') or 'Frequently asked questions')}</h2>
    <div class="faq">{items}</div>
  </div>
</section>"""


def _visit(c: Dict[str, Any], brief: SiteBrief) -> str:
    address = esc(brief.location) if brief.location else placeholder("Add your full address")
    hours = esc(brief.hours) if brief.hours else placeholder("Add your opening hours")
    if brief.location:
        q = quote(brief.location)
        mapframe = (f'<iframe title="Map showing {esc(brief.location)}" loading="lazy" '
                    f'referrerpolicy="no-referrer-when-downgrade" src="https://maps.google.com/maps?q={q}&amp;output=embed"></iframe>')
        directions = (f'<a class="btn btn-primary" target="_blank" rel="noopener" '
                      f'href="https://www.google.com/maps/search/?api=1&amp;query={quote_plus(brief.location)}">Get directions</a>')
    else:
        mapframe = '<div class="map-placeholder">Map appears here once the address is added.</div>'
        directions = ""
    return f"""
<section id="visit" class="section">
  <div class="container split reveal">
    <div>
      <p class="eyebrow">Visit</p>
      <h2>{esc(c.get('visit', {}).get('heading') or 'Come and see us')}</h2>
      <dl class="facts">
        <div><dt>{icon('users')} Address</dt><dd>{address}</dd></div>
        <div><dt>{icon('clock')} Hours</dt><dd>{hours}</dd></div>
      </dl>
      {directions}
    </div>
    <div class="map">{mapframe}</div>
  </div>
</section>"""


def _contact(c: Dict[str, Any], brief: SiteBrief) -> str:
    phone = (f'<a href="tel:{esc(re.sub(r"[^0-9+]", "", brief.phone))}">{esc(brief.phone)}</a>'
             if brief.phone else placeholder("Add your phone number"))
    email = f'<a href="mailto:{esc(brief.email)}">{esc(brief.email)}</a>' if brief.email else placeholder("Add your email")
    action = f' action="mailto:{esc(brief.email)}" method="post" enctype="text/plain"' if brief.email else ""
    return f"""
<section id="contact" class="section section-soft">
  <div class="container split reveal">
    <div>
      <p class="eyebrow">Contact</p>
      <h2>{esc(c.get('contact', {}).get('heading') or 'Get in touch')}</h2>
      <p>{esc(c.get('contact', {}).get('text'))}</p>
      <ul class="contact-list" role="list">
        <li>{icon('heart')} <span>Phone:</span> {phone}</li>
        <li>{icon('sparkle')} <span>Email:</span> {email}</li>
      </ul>
    </div>
    <form class="card form" id="contact-form" data-email="{esc(brief.email)}" data-whatsapp="{esc(_wa_link(brief.phone))}"{action} novalidate>
      <div class="field"><label for="f-name">Your name</label><input id="f-name" name="name" autocomplete="name" required></div>
      <div class="field"><label for="f-contact">Phone or email</label><input id="f-contact" name="contact" required></div>
      <div class="field"><label for="f-msg">Message</label><textarea id="f-msg" name="message" rows="4" required></textarea></div>
      <button class="btn btn-primary" type="submit">Send message</button>
      <p class="form-note" role="status" aria-live="polite"></p>
    </form>
  </div>
</section>"""


_RENDERERS = {"hero": _hero, "about": _about, "offerings": _offerings, "features": _features,
              "gallery": _gallery, "process": _process, "order": _order, "faq": _faq,
              "visit": _visit, "contact": _contact}


def _json_ld(c: Dict[str, Any], brief: SiteBrief) -> str:
    data: Dict[str, Any] = {"@context": "https://schema.org", "@type": brief.blueprint.schema_type,
                            "name": brief.name or "Your Business Name",
                            "description": c.get("seo", {}).get("description", "")}
    if brief.location:
        data["address"] = brief.location
    if brief.phone:
        data["telephone"] = brief.phone
    if brief.email:
        data["email"] = brief.email
    return json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")


def render_html(c: Dict[str, Any], brief: SiteBrief) -> str:
    bp = brief.blueprint
    sections = [s for s in bp.sections if s in _RENDERERS]
    name = brief.name or "Your Business Name"
    seo = c.get("seo", {})
    title = seo.get("title") or f"{name} | {bp.label.title()}"
    nav = "".join(f'<li><a href="#{s}">{esc(SECTION_TITLES.get(s) or (bp.offer_label if s == "offerings" else s.title()))}</a></li>'
                  for s in sections if s not in ("hero", "order"))
    heading_font, body_font = bp.fonts
    fonts = (f"https://fonts.googleapis.com/css2?family={quote_plus(heading_font)}:wght@500;700"
             f"&family={quote_plus(body_font)}:wght@400;600&display=swap")
    body = "".join(_RENDERERS[s](c, brief) for s in sections)
    footer_bits = [esc(name)]
    if brief.location:
        footer_bits.append(esc(brief.location))
    return f"""<!DOCTYPE html>
<html lang="en" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(seo.get('description'))}">
<meta name="keywords" content="{esc(seo.get('keywords'))}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(seo.get('description'))}">
<meta name="theme-color" content="{esc(bp.palette[1])}">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{esc(fonts)}">
<link rel="stylesheet" href="styles.css">
<script type="application/ld+json">
{_json_ld(c, brief)}
</script>
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
  <div class="container header-inner">
    <a class="brand" href="#home">{icon('sparkle')}<span>{esc(name)}</span></a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">
      <span class="sr-only">Menu</span><span class="bar"></span><span class="bar"></span><span class="bar"></span>
    </button>
    <nav id="site-nav" class="site-nav" aria-label="Main"><ul role="list">{nav}</ul></nav>
  </div>
</header>
<main id="main">{body}
</main>
<footer class="site-footer">
  <div class="container footer-inner">
    <p><strong>{esc(name)}</strong> · {esc(c.get('tagline'))}</p>
    <p>{' · '.join(footer_bits)} · &copy; <span id="year"></span></p>
  </div>
</footer>
<script src="script.js" defer></script>
</body>
</html>
"""


def render_css(brief: SiteBrief) -> str:
    ink, primary, accent, bg, soft = brief.blueprint.palette
    heading_font, body_font = brief.blueprint.fonts
    return f""":root {{
  --ink: {ink};
  --primary: {primary};
  --accent: {accent};
  --bg: {bg};
  --soft: {soft};
  --muted: color-mix(in srgb, var(--ink) 65%, var(--bg));
  --line: color-mix(in srgb, var(--ink) 12%, var(--bg));
  --radius: 18px;
  --shadow: 0 10px 30px -12px color-mix(in srgb, var(--ink) 35%, transparent);
  --font-head: "{heading_font}", Georgia, serif;
  --font-body: "{body_font}", system-ui, -apple-system, "Segoe UI", sans-serif;
}}
*, *::before, *::after {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; scroll-padding-top: 80px; }}
body {{ margin: 0; font-family: var(--font-body); color: var(--ink); background: var(--bg); line-height: 1.65; font-size: 1.0625rem; }}
img {{ max-width: 100%; display: block; }}
h1, h2, h3 {{ font-family: var(--font-head); line-height: 1.15; margin: 0 0 .6em; }}
h1 {{ font-size: clamp(2.4rem, 5.5vw, 4.2rem); }}
h2 {{ font-size: clamp(1.9rem, 3.6vw, 2.8rem); }}
h3 {{ font-size: 1.15rem; }}
p {{ margin: 0 0 1em; }}
a {{ color: var(--primary); }}
:focus-visible {{ outline: 3px solid var(--accent); outline-offset: 3px; border-radius: 6px; }}
.container {{ width: min(1160px, 100% - 2.5rem); margin-inline: auto; }}
.narrow {{ width: min(820px, 100% - 2.5rem); }}
.sr-only {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }}
.skip-link {{ position: absolute; left: 1rem; top: -3rem; background: var(--ink); color: var(--bg); padding: .6rem 1rem; border-radius: 8px; z-index: 100; }}
.skip-link:focus {{ top: 1rem; }}
.icon {{ width: 1.6rem; height: 1.6rem; flex: none; color: var(--primary); }}
.eyebrow {{ text-transform: uppercase; letter-spacing: .14em; font-size: .8rem; font-weight: 600; color: var(--primary); margin-bottom: .8rem; }}
.section {{ padding: clamp(4rem, 9vw, 7rem) 0; }}
.section-soft {{ background: var(--soft); }}
.section-intro {{ max-width: 60ch; color: var(--muted); margin-bottom: 2rem; }}
.card {{ background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius); padding: 1.5rem; box-shadow: var(--shadow); }}
.btn {{ display: inline-flex; align-items: center; gap: .5rem; padding: .9rem 1.5rem; border-radius: 999px; font-weight: 600; text-decoration: none; border: 2px solid transparent; transition: transform .2s, box-shadow .2s, background .2s; cursor: pointer; font: inherit; font-weight: 600; }}
.btn:hover {{ transform: translateY(-2px); box-shadow: var(--shadow); }}
.btn-primary {{ background: var(--primary); color: #fff; }}
.btn-ghost {{ border-color: currentColor; color: var(--ink); background: transparent; }}
.btn-light {{ background: #fff; color: var(--primary); }}
.btn-outline-light {{ border-color: rgba(255,255,255,.8); color: #fff; }}
/* header */
.site-header {{ position: sticky; top: 0; z-index: 50; background: color-mix(in srgb, var(--bg) 88%, transparent); backdrop-filter: blur(10px); border-bottom: 1px solid transparent; transition: border-color .3s, box-shadow .3s; }}
.site-header.scrolled {{ border-color: var(--line); box-shadow: 0 6px 20px -16px var(--ink); }}
.header-inner {{ display: flex; align-items: center; justify-content: space-between; min-height: 72px; }}
.brand {{ display: inline-flex; align-items: center; gap: .55rem; font-family: var(--font-head); font-weight: 700; font-size: 1.35rem; color: var(--ink); text-decoration: none; }}
.site-nav ul {{ display: flex; gap: 1.6rem; list-style: none; margin: 0; padding: 0; }}
.site-nav a {{ color: var(--ink); text-decoration: none; font-weight: 600; font-size: .95rem; }}
.site-nav a:hover {{ color: var(--primary); }}
.nav-toggle {{ display: none; background: none; border: 0; padding: .5rem; cursor: pointer; }}
.nav-toggle .bar {{ display: block; width: 24px; height: 2px; margin: 5px 0; background: var(--ink); transition: transform .3s, opacity .3s; }}
/* hero */
.hero {{ position: relative; overflow: hidden; padding: clamp(5rem, 12vw, 9rem) 0; background: linear-gradient(135deg, var(--soft), var(--bg) 60%); }}
.hero-inner {{ position: relative; max-width: 760px; }}
.lead {{ font-size: clamp(1.1rem, 2vw, 1.3rem); color: var(--muted); max-width: 58ch; }}
.hero-actions {{ display: flex; flex-wrap: wrap; gap: 1rem; margin: 2rem 0 1.5rem; }}
.hero-meta {{ display: inline-flex; align-items: center; gap: .5rem; color: var(--muted); font-size: .95rem; }}
.hero-art span {{ position: absolute; border-radius: 50%; filter: blur(2px); opacity: .55; }}
.hero-art span:nth-child(1) {{ width: 420px; height: 420px; right: -120px; top: -100px; background: radial-gradient(circle at 30% 30%, var(--accent), transparent 70%); }}
.hero-art span:nth-child(2) {{ width: 300px; height: 300px; right: 18%; bottom: -140px; background: radial-gradient(circle, var(--primary), transparent 70%); opacity: .25; }}
.hero-art span:nth-child(3) {{ width: 160px; height: 160px; right: 8%; top: 45%; border: 2px dashed color-mix(in srgb, var(--primary) 40%, transparent); background: none; }}
/* layouts */
.split {{ display: grid; grid-template-columns: 1.1fr 1fr; gap: clamp(2rem, 5vw, 4rem); align-items: start; }}
.grid-3 {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1.25rem; }}
.grid-4 {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1.25rem; }}
.highlights {{ display: grid; gap: 1rem; list-style: none; margin: 0; padding: 0; }}
.highlights li {{ display: flex; gap: 1rem; align-items: flex-start; }}
.highlights h3 {{ margin-bottom: .25rem; }}
.highlights p {{ margin: 0; color: var(--muted); }}
/* offerings */
.tabs {{ display: flex; flex-wrap: wrap; gap: .6rem; margin-bottom: 1.5rem; }}
.tab {{ border: 1px solid var(--line); background: var(--bg); color: var(--ink); padding: .55rem 1.1rem; border-radius: 999px; font: inherit; font-weight: 600; cursor: pointer; }}
.tab.active {{ background: var(--primary); color: #fff; border-color: var(--primary); }}
.group {{ margin-bottom: 2rem; }}
.group-title {{ font-size: 1.4rem; margin: 1rem 0; }}
.tabs ~ .group .group-title {{ display: none; }}
.item-head {{ display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; }}
.item p {{ color: var(--muted); margin: 0; }}
.price {{ font-weight: 700; color: var(--primary); white-space: nowrap; }}
.feature .icon {{ width: 2.2rem; height: 2.2rem; margin-bottom: 1rem; }}
.feature p {{ color: var(--muted); margin: 0; }}
/* gallery */
.gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }}
.tile {{ margin: 0; border-radius: var(--radius); overflow: hidden; background: var(--bg); box-shadow: var(--shadow); }}
.tile-art {{ aspect-ratio: 4 / 3; display: grid; place-items: center; }}
.tile-art .icon {{ width: 3rem; height: 3rem; color: #fff; opacity: .9; }}
.tile-0 .tile-art {{ background: linear-gradient(135deg, var(--primary), var(--accent)); }}
.tile-1 .tile-art {{ background: linear-gradient(135deg, var(--accent), var(--ink)); }}
.tile-2 .tile-art {{ background: linear-gradient(160deg, var(--ink), var(--primary)); }}
.tile-3 .tile-art {{ background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 70%, #fff), var(--primary)); }}
.tile-4 .tile-art {{ background: linear-gradient(200deg, var(--primary), color-mix(in srgb, var(--ink) 80%, var(--accent))); }}
.tile-5 .tile-art {{ background: linear-gradient(135deg, var(--ink), var(--accent)); }}
.tile figcaption {{ padding: .9rem 1.1rem; font-weight: 600; }}
/* steps */
.steps {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1.25rem; list-style: none; padding: 0; margin: 0; }}
.step-n {{ display: inline-grid; place-items: center; width: 2.4rem; height: 2.4rem; border-radius: 50%; background: var(--primary); color: #fff; font-weight: 700; margin-bottom: 1rem; }}
.step p {{ color: var(--muted); margin: 0; }}
/* call to action */
.cta-band {{ background: linear-gradient(120deg, var(--primary), color-mix(in srgb, var(--primary) 55%, var(--ink))); color: #fff; padding: clamp(3rem, 7vw, 5rem) 0; }}
.cta-inner {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 2rem; }}
.cta-inner h2 {{ color: #fff; margin-bottom: .3em; }}
.cta-inner p {{ opacity: .9; margin: 0; max-width: 55ch; }}
.cta-actions {{ display: flex; flex-wrap: wrap; gap: .8rem; }}
/* faq */
.faq-item {{ border-bottom: 1px solid var(--line); padding: 1.1rem 0; }}
.faq-item summary {{ cursor: pointer; font-weight: 600; font-size: 1.05rem; list-style: none; display: flex; justify-content: space-between; gap: 1rem; }}
.faq-item summary::after {{ content: "+"; color: var(--primary); font-size: 1.4rem; line-height: 1; }}
.faq-item[open] summary::after {{ content: "–"; }}
.faq-item p {{ margin: .8rem 0 0; color: var(--muted); }}
/* visit + contact */
.facts {{ display: grid; gap: 1rem; margin: 0 0 1.5rem; }}
.facts dt {{ display: flex; align-items: center; gap: .5rem; font-weight: 600; }}
.facts dd {{ margin: .2rem 0 0 2.1rem; color: var(--muted); }}
.map {{ border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow); min-height: 320px; background: var(--soft); }}
.map iframe {{ width: 100%; height: 100%; min-height: 360px; border: 0; display: block; }}
.map-placeholder {{ display: grid; place-items: center; min-height: 320px; color: var(--muted); padding: 2rem; text-align: center; }}
.contact-list {{ list-style: none; padding: 0; margin: 1.5rem 0 0; display: grid; gap: .8rem; }}
.contact-list li {{ display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }}
.contact-list span {{ font-weight: 600; }}
.form {{ display: grid; gap: 1rem; }}
.field {{ display: grid; gap: .35rem; }}
.field label {{ font-weight: 600; font-size: .95rem; }}
.field input, .field textarea {{ font: inherit; padding: .8rem 1rem; border: 1px solid var(--line); border-radius: 12px; background: var(--bg); color: var(--ink); }}
.field input:focus, .field textarea:focus {{ outline: 2px solid var(--primary); border-color: transparent; }}
.field.invalid input, .field.invalid textarea {{ border-color: #dc2626; }}
.form-note {{ margin: 0; font-size: .92rem; color: var(--muted); min-height: 1.4em; }}
.placeholder {{ background: #fff4c2; color: #6b4e00; border: 1px dashed #c99a00; border-radius: 6px; padding: 0 .35rem; font-size: .92em; }}
/* footer */
.site-footer {{ background: var(--ink); color: color-mix(in srgb, var(--bg) 80%, transparent); padding: 2.5rem 0; font-size: .95rem; }}
.footer-inner {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 1rem; }}
.footer-inner p {{ margin: 0; }}
/* motion */
.reveal {{ opacity: 0; transform: translateY(24px); transition: opacity .7s ease, transform .7s ease; }}
.reveal.visible {{ opacity: 1; transform: none; }}
.no-js .reveal {{ opacity: 1; transform: none; }}
@media (prefers-reduced-motion: reduce) {{
  html {{ scroll-behavior: auto; }}
  .reveal {{ opacity: 1; transform: none; transition: none; }}
  .btn {{ transition: none; }}
}}
/* responsive */
@media (max-width: 860px) {{
  .split {{ grid-template-columns: 1fr; }}
  .nav-toggle {{ display: block; }}
  .site-nav {{ position: absolute; inset: 72px 0 auto 0; background: var(--bg); border-bottom: 1px solid var(--line); display: none; }}
  .site-nav.open {{ display: block; }}
  .site-nav ul {{ flex-direction: column; gap: 0; padding: .5rem 1.25rem 1rem; }}
  .site-nav a {{ display: block; padding: .8rem 0; border-bottom: 1px solid var(--line); }}
  .nav-toggle[aria-expanded="true"] .bar:nth-child(2) {{ transform: translateY(7px) rotate(45deg); }}
  .nav-toggle[aria-expanded="true"] .bar:nth-child(3) {{ opacity: 0; }}
  .nav-toggle[aria-expanded="true"] .bar:nth-child(4) {{ transform: translateY(-7px) rotate(-45deg); }}
}}
"""


JS = """(function () {
  'use strict';
  document.documentElement.classList.remove('no-js');
  var header = document.querySelector('.site-header');
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') { nav.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); }
    });
  }
  var onScroll = function () { if (header) header.classList.toggle('scrolled', window.scrollY > 10); };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  var reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('visible'); io.unobserve(en.target); } });
    }, { threshold: 0.12 });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('visible'); });
  }

  document.querySelectorAll('.tabs').forEach(function (bar) {
    var section = bar.parentElement;
    bar.addEventListener('click', function (e) {
      var btn = e.target.closest('.tab');
      if (!btn) return;
      bar.querySelectorAll('.tab').forEach(function (b) {
        var on = b === btn; b.classList.toggle('active', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      section.querySelectorAll('.group').forEach(function (g) { g.hidden = g.getAttribute('data-group') !== btn.getAttribute('data-filter'); });
    });
  });

  var year = document.getElementById('year');
  if (year) year.textContent = String(new Date().getFullYear());

  var form = document.getElementById('contact-form');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var ok = true;
      form.querySelectorAll('[required]').forEach(function (f) {
        var bad = !f.value.trim(); f.parentElement.classList.toggle('invalid', bad); if (bad) ok = false;
      });
      var note = form.querySelector('.form-note');
      if (!ok) { note.textContent = 'Please fill in every field.'; return; }
      var name = form.elements.name.value.trim(), contact = form.elements.contact.value.trim(), msg = form.elements.message.value.trim();
      var text = msg + '\\n\\n— ' + name + ' (' + contact + ')';
      var email = form.getAttribute('data-email'), wa = form.getAttribute('data-whatsapp');
      if (email) {
        window.location.href = 'mailto:' + email + '?subject=' + encodeURIComponent('Website enquiry from ' + name) + '&body=' + encodeURIComponent(text);
        note.textContent = 'Opening your email app to send this message…';
      } else if (wa) {
        window.open(wa + '?text=' + encodeURIComponent(text), '_blank', 'noopener');
        note.textContent = 'Opening WhatsApp to send this message…';
      } else {
        note.textContent = 'Online messages are not set up yet — please call or visit us.';
      }
    });
  }
})();
"""


def render_favicon(brief: SiteBrief) -> str:
    letter = esc((brief.name or brief.blueprint.label or "W")[:1].upper())
    _ink, primary, accent, _bg, _soft = brief.blueprint.palette
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{primary}"/><stop offset="1" stop-color="{accent}"/></linearGradient></defs>'
            f'<rect width="64" height="64" rx="16" fill="url(#g)"/><text x="32" y="43" font-family="Georgia,serif" '
            f'font-size="34" font-weight="700" fill="#fff" text-anchor="middle">{letter}</text></svg>')


IMAGES_README = """Put your own photos here (JPG/WebP, about 1600 px wide).

In index.html, each gallery tile has a <div class="tile-art" ...> block. Replace it with:
    <img src="images/your-photo.jpg" alt="What the photo shows" loading="lazy" width="800" height="600">

Real photos of your products and space make the biggest difference to how professional the site looks.
"""


def placeholders_in(html_text: str) -> List[str]:
    return sorted(set(re.findall(r'class="placeholder"[^>]*>\[([^\]]+)\]', html_text)))
