"""Understand a website request before writing anything (deterministic, instant).

"build a website for my bakery" needs a menu, opening hours, a map and a way to order a custom cake;
"a site for my dental clinic" needs services, the team and appointment booking. Each kind of business
has a blueprint: the sections a professional site of that kind has, the facts only the owner can give
(name, address, phone, hours) and a fitting visual style. Facts the owner did not give are asked for —
never invented — and anything still missing at build time becomes a clearly marked placeholder.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Blueprint:
    key: str
    label: str                      # "bakery"
    schema_type: str                # schema.org type for the JSON-LD block
    offer_label: str                # what the offerings section is called on the site
    offer_groups: Tuple[str, ...]   # default categories of offerings
    sections: Tuple[str, ...]       # page order (see render.SECTION_TITLES)
    cta: str                        # main call to action
    physical: bool = True           # has a place customers visit → hours + map
    palette: Tuple[str, str, str, str, str] = ("#1f2937", "#2563eb", "#f59e0b", "#ffffff", "#f3f4f6")
    fonts: Tuple[str, str] = ("Poppins", "Inter")    # heading, body (Google Fonts)
    priced: bool = True             # offerings normally show prices


# palette = (ink, primary, accent, background, soft surface)
BLUEPRINTS: Dict[str, Blueprint] = {b.key: b for b in (
    Blueprint("bakery", "bakery", "Bakery", "Menu",
              ("Breads", "Cakes", "Pastries & Cookies", "Custom Orders"),
              ("hero", "about", "offerings", "features", "gallery", "order", "faq", "visit", "contact"),
              "Order a custom cake", palette=("#3b2418", "#8b4a2b", "#e07a5f", "#fffaf3", "#f6ead8"),
              fonts=("Playfair Display", "Lato")),
    Blueprint("cafe", "café", "CafeOrCoffeeShop", "Menu",
              ("Coffee", "Tea & Cold Drinks", "Breakfast", "Snacks & Desserts"),
              ("hero", "about", "offerings", "features", "gallery", "faq", "visit", "contact"),
              "See the menu", palette=("#2b2118", "#6f4e37", "#d4a373", "#fffdf8", "#f3ebe0"),
              fonts=("Playfair Display", "Lato")),
    Blueprint("restaurant", "restaurant", "Restaurant", "Menu",
              ("Starters", "Main Course", "Breads & Rice", "Desserts", "Beverages"),
              ("hero", "about", "offerings", "features", "gallery", "order", "faq", "visit", "contact"),
              "Reserve a table", palette=("#1c1917", "#9a3412", "#f59e0b", "#fffbf5", "#f5ede3"),
              fonts=("Playfair Display", "Source Sans 3")),
    Blueprint("salon", "salon / spa", "BeautySalon", "Services & Prices",
              ("Hair", "Skin & Facials", "Nails", "Bridal & Packages"),
              ("hero", "about", "offerings", "features", "gallery", "order", "faq", "visit", "contact"),
              "Book an appointment", palette=("#2d1b2e", "#9d4b73", "#e8b4bc", "#fffafb", "#f8eef1"),
              fonts=("Cormorant Garamond", "Montserrat")),
    Blueprint("gym", "gym / fitness studio", "ExerciseGym", "Programs & Membership",
              ("Memberships", "Personal Training", "Group Classes"),
              ("hero", "about", "offerings", "features", "process", "order", "faq", "visit", "contact"),
              "Book a free trial", palette=("#0f172a", "#dc2626", "#facc15", "#ffffff", "#f1f5f9"),
              fonts=("Oswald", "Inter")),
    Blueprint("clinic", "clinic", "MedicalClinic", "Services",
              ("Consultations", "Diagnostics", "Specialist Care", "Preventive Health"),
              ("hero", "about", "offerings", "features", "process", "order", "faq", "visit", "contact"),
              "Book an appointment", palette=("#0b2537", "#0e7490", "#22c55e", "#ffffff", "#ecf7f9"),
              fonts=("Poppins", "Inter"), priced=False),
    Blueprint("dental", "dental clinic", "Dentist", "Treatments",
              ("General Dentistry", "Cosmetic Dentistry", "Orthodontics", "Emergency Care"),
              ("hero", "about", "offerings", "features", "process", "order", "faq", "visit", "contact"),
              "Book a check-up", palette=("#0b2537", "#0284c7", "#2dd4bf", "#ffffff", "#eef7fc"),
              fonts=("Poppins", "Inter"), priced=False),
    Blueprint("hotel", "hotel / homestay", "Hotel", "Rooms & Amenities",
              ("Rooms", "Dining", "Experiences"),
              ("hero", "about", "offerings", "features", "gallery", "order", "faq", "visit", "contact"),
              "Check availability", palette=("#1e1b16", "#7c5c3b", "#c9a227", "#fffdf7", "#f4efe4"),
              fonts=("Cormorant Garamond", "Lato")),
    Blueprint("realestate", "real-estate agency", "RealEstateAgent", "Properties & Services",
              ("Buy", "Sell", "Rent", "Property Management"),
              ("hero", "about", "offerings", "features", "process", "order", "faq", "visit", "contact"),
              "Book a viewing", palette=("#111827", "#1d4ed8", "#f59e0b", "#ffffff", "#f1f5f9"),
              fonts=("Poppins", "Inter"), priced=False),
    Blueprint("law", "law / consulting firm", "LegalService", "Practice Areas",
              ("Advisory", "Disputes", "Documentation", "Compliance"),
              ("hero", "about", "offerings", "features", "process", "order", "faq", "visit", "contact"),
              "Book a consultation", palette=("#111827", "#1e3a5f", "#b08d57", "#ffffff", "#f3f4f6"),
              fonts=("Libre Baskerville", "Source Sans 3"), priced=False),
    Blueprint("school", "school / coaching centre", "EducationalOrganization", "Courses",
              ("Programs", "Batches & Timings", "Online Classes"),
              ("hero", "about", "offerings", "features", "process", "order", "faq", "visit", "contact"),
              "Enquire about admission", palette=("#1e1b4b", "#4f46e5", "#f59e0b", "#ffffff", "#eef2ff"),
              fonts=("Poppins", "Inter")),
    Blueprint("photography", "photography studio", "ProfessionalService", "Packages",
              ("Weddings", "Portraits", "Events", "Commercial"),
              ("hero", "about", "gallery", "offerings", "process", "order", "faq", "contact"),
              "Check a date", physical=False, palette=("#0a0a0a", "#262626", "#d4af37", "#ffffff", "#f5f5f5"),
              fonts=("Cormorant Garamond", "Montserrat")),
    Blueprint("portfolio", "personal portfolio", "Person", "Work",
              ("Projects", "Skills", "Experience"),
              ("hero", "about", "offerings", "features", "process", "contact"),
              "Get in touch", physical=False, palette=("#0f172a", "#7c3aed", "#06b6d4", "#ffffff", "#f5f3ff"),
              fonts=("Space Grotesk", "Inter"), priced=False),
    Blueprint("startup", "software / startup product", "Organization", "Features & Pricing",
              ("Starter", "Growth", "Enterprise"),
              ("hero", "features", "about", "process", "offerings", "faq", "order", "contact"),
              "Start free", physical=False, palette=("#0f172a", "#4f46e5", "#22d3ee", "#ffffff", "#f1f5f9"),
              fonts=("Plus Jakarta Sans", "Inter")),
    Blueprint("shop", "shop / store", "Store", "Products",
              ("New Arrivals", "Best Sellers", "Gift Ideas"),
              ("hero", "about", "offerings", "features", "gallery", "order", "faq", "visit", "contact"),
              "Visit the store", palette=("#1f2937", "#be185d", "#f59e0b", "#ffffff", "#fdf2f8"),
              fonts=("Poppins", "Inter")),
    Blueprint("business", "business", "LocalBusiness", "Services",
              ("Core Services", "Packages", "Support"),
              ("hero", "about", "offerings", "features", "process", "order", "faq", "visit", "contact"),
              "Get in touch"),
)}

# business words → blueprint (first match wins; specific before generic)
_KINDS: Tuple[Tuple[str, str], ...] = (
    ("bakery", r"bakery|bakeries|bakehouse|cake shop|cakes? (?:studio|business)|patisserie|pastry shop|bake shop|home baker"),
    ("cafe", r"caf[eé]|coffee shop|coffee house|tea house|tea stall|juice bar"),
    ("restaurant", r"restaurant|dhaba|diner|bistro|eatery|food truck|cloud kitchen|biryani|pizzeria|catering"),
    ("dental", r"dental|dentist|orthodont"),
    ("clinic", r"clinic|hospital|doctor|physiotherap|diagnostic|medical|healthcare|pharmacy"),
    ("salon", r"salon|spa\b|beauty parlou?r|barber|makeup artist|nail studio"),
    ("gym", r"\bgym\b|fitness|yoga studio|crossfit|martial arts|dance studio|zumba"),
    ("hotel", r"hotel|resort|homestay|guest ?house|hostel|\bb&b\b|villa rental"),
    ("realestate", r"real[- ]?estate|realtor|property (?:dealer|agency|consultant)|builders?\b|construction company"),
    ("law", r"law firm|lawyer|advocate|attorney|legal|consult(?:ing|ancy)|chartered accountant|\bca firm\b|accounting firm|tax consultant"),
    ("school", r"school|coaching|tuition|academy|institute|training cent(?:er|re)|college|kindergarten|preschool"),
    ("photography", r"photograph|videograph|wedding films|studio for weddings"),
    ("portfolio", r"portfolio|personal (?:website|site)|my resume site|developer site|freelancer"),
    ("startup", r"startup|saas|\bapp\b|software|platform|product launch|landing page for (?:my|our|an?) (?:app|tool|product)"),
    ("shop", r"\bshop\b|\bstore\b|boutique|e-?commerce|clothing|jewell?ery|florist|flower shop|bookstore|grocery|supermarket"),
)

_STYLE_WORDS = r"\b(modern|minimal|minimalist|elegant|luxury|premium|rustic|vintage|playful|bold|dark|light|warm|pastel|colou?rful|vibrant|classic|corporate|cute|fun)\b"
_SKIP_ASKING = re.compile(
    r"\b(go ahead|just build|build it|your (?:choice|call)|you decide|decide yourself|use placeholders?|"
    r"don'?t ask|no questions|skip(?: the)? questions?|as you (?:like|wish|think)|whatever you (?:think|like)|"
    r"surprise me|use (?:sample|dummy|example) (?:data|details|content)|make (?:it|them) up|"
    r"best (?:judg(?:e)?ment|guess))\b", re.IGNORECASE)

EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RX = re.compile(r"(?<![\w])(\+?\d[\d\s().-]{7,}\d)(?![\w])")


@dataclass
class SiteBrief:
    request: str
    kind: str = "business"
    name: str = ""
    location: str = ""              # address or city
    phone: str = ""
    email: str = ""
    hours: str = ""
    offerings: str = ""             # what they sell / signature items, in the owner's words
    style: str = ""
    audience: str = ""
    extra: str = ""                 # anything else the owner told us (story, awards, delivery …)
    skip_questions: bool = False
    asked: bool = False

    @property
    def blueprint(self) -> Blueprint:
        return BLUEPRINTS.get(self.kind, BLUEPRINTS["business"])

    def facts(self) -> Dict[str, str]:
        return {k: v for k, v in (("name", self.name), ("location", self.location), ("phone", self.phone),
                                  ("email", self.email), ("hours", self.hours), ("offerings", self.offerings),
                                  ("style", self.style), ("audience", self.audience), ("extra", self.extra)) if v}

    def summary(self) -> str:
        """What the content writer is told — only facts the owner actually gave."""
        bp = self.blueprint
        lines = [f"Business type: {bp.label}", f"Business name: {self.name or '(not given)'}"]
        for label, value in (("Location", self.location), ("Signature offerings", self.offerings),
                             ("Opening hours", self.hours), ("Audience", self.audience),
                             ("Style", self.style), ("Other details from the owner", self.extra)):
            if value:
                lines.append(f"{label}: {value}")
        lines.append(f"Original request: {self.request}")
        return "\n".join(lines)


# question key → (question text, applies when)
_QUESTIONS: Tuple[Tuple[str, str], ...] = (
    ("name", "What is the business called?"),
    ("location", "Where is it? (full address, or at least the area and city — used for the map and directions)"),
    ("contact", "Which phone number and/or email should customers use? (a WhatsApp number works too)"),
    ("hours", "What are the opening hours? (e.g. Mon–Sat 8 am–9 pm, Sun 9 am–2 pm)"),
    ("offerings", "What do you want to highlight — signature {items}, and prices if you'd like them shown?"),
    ("style", "Any look you want — colours, mood (warm, modern, elegant, playful), or a site you like?"),
)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip(" .,;:-\"'")


def detect_kind(text: str) -> str:
    low = (text or "").lower()
    return next((k for k, rx in _KINDS if re.search(rf"\b(?:{rx})", low)), "business")


def _name_from_request(text: str) -> str:
    # "for Sweet Crumbs bakery", "called 'Sweet Crumbs'", "named Sweet Crumbs"
    m = re.search(r"\b(?:called|named|name is|brand(?:ed)? as)\s+[\"'“]?([A-Z0-9][\w&'’ .-]{1,40}?)[\"'”]?(?=[,.]|\s+(?:in|at|located|which|that|with|for|and)\b|$)",
                  text)
    if m:
        return _clean(m.group(1))
    m = re.search(r"[\"'“]([^\"'”]{2,40})[\"'”]", text)
    if m:
        return _clean(m.group(1))
    # Capitalised words right before the business word: "for Sweet Crumbs Bakery"
    m = re.search(r"\bfor\s+((?:[A-Z][\w&'’-]*\s+){1,4}(?:Bakery|Cafe|Café|Restaurant|Salon|Spa|Gym|Clinic|Hotel|Studio|Academy|Store|Shop|Boutique|Kitchen|Bakes|Cakes))\b",
                  text)
    return _clean(m.group(1)) if m else ""


def _location_from_request(text: str) -> str:
    m = re.search(r"\b(?:in|at|located in|based in)\s+((?:[A-Z][\w.-]*)(?:[ ,]+[A-Z][\w.-]*){0,4})", text)
    if not m:
        return ""
    loc = _clean(m.group(1))
    return "" if loc.lower() in ("english", "telugu", "hindi", "html", "react") else loc


def understand(request: str) -> SiteBrief:
    text = request or ""
    brief = SiteBrief(request=text.strip(), kind=detect_kind(text))
    brief.name = _name_from_request(text)
    brief.location = _location_from_request(text)
    if (m := EMAIL_RX.search(text)):
        brief.email = m.group(0)
    if (m := PHONE_RX.search(text)):
        brief.phone = _clean(m.group(1))
    styles = re.findall(_STYLE_WORDS, text, re.IGNORECASE)
    if styles:
        brief.style = ", ".join(dict.fromkeys(s.lower() for s in styles))
    m = re.search(r"\b(?:sells?|selling|serves?|serving|special(?:ises|izes|ity|ities) in|known for|offers?|offering)\s+(.+?)(?=[.;]|$)",
                  text, re.IGNORECASE)
    if m:
        brief.offerings = _clean(m.group(1))[:300]
    brief.skip_questions = bool(_SKIP_ASKING.search(text))
    return brief


def questions(brief: SiteBrief) -> List[Tuple[str, str]]:
    """What still needs the owner: [(key, question)]. Empty when nothing important is missing."""
    bp = brief.blueprint
    out: List[Tuple[str, str]] = []
    for key, q in _QUESTIONS:
        if key == "name" and brief.name:
            continue
        if key == "location" and (brief.location or not bp.physical):
            continue
        if key == "contact" and (brief.phone or brief.email):
            continue
        if key == "hours" and (brief.hours or not bp.physical):
            continue
        if key == "offerings" and brief.offerings:
            continue
        if key == "style" and brief.style:
            continue
        out.append((key, q.format(items=bp.offer_label.lower())))
    return out


def should_ask(brief: SiteBrief) -> bool:
    """Ask once, before building, when an essential fact is missing and the owner didn't say "go ahead"."""
    if brief.skip_questions or brief.asked:
        return False
    essential = {"name", "contact", "location"}
    return any(k in essential for k, _ in questions(brief))


def question_text(brief: SiteBrief) -> str:
    bp = brief.blueprint
    qs = questions(brief)
    head = (f"I'll build a professional {bp.label} website: "
            + ", ".join(SECTION_NAMES.get(s, s) for s in bp.sections) + ".\n"
            "So the details are real (I won't make up an address, phone number or hours), tell me:\n")
    body = "\n".join(f"  {i}. {q}" for i, (_k, q) in enumerate(qs, 1))
    tail = ("\n\nAnswer in one message — numbered or in your own words. Anything you skip becomes a clearly "
            "marked placeholder you can fill in later. Or say \"go ahead\" and I'll start now.")
    return head + body + tail


SECTION_NAMES = {"hero": "a hero banner", "about": "your story", "offerings": "menu/services",
                 "features": "why choose you", "gallery": "a gallery", "process": "how it works",
                 "order": "an order/booking call to action", "faq": "FAQs", "visit": "hours and a map",
                 "contact": "a contact form"}

_LABELS = {
    "name": r"(?:business |shop |brand |company )?name|called",
    "location": r"address|location|where|area|city|located",
    "contact": r"contact|phone|mobile|whats ?app|number|email|e-mail|mail",
    "hours": r"(?:opening |working |business )?hours|timings?|open",
    "offerings": r"offerings?|menu|products?|services?|special(?:ity|ities)?|items?|highlights?|prices?|sell",
    "style": r"style|look|colou?rs?|theme|mood|design|vibe",
}


def apply_answers(brief: SiteBrief, reply: str) -> SiteBrief:
    """Merge the owner's reply into the brief (numbered answers, "label: value" lines, or free text)."""
    brief.asked = True
    text = (reply or "").strip()
    if _SKIP_ASKING.search(text) and len(text.split()) <= 8:
        brief.skip_questions = True
        return brief
    keys = [k for k, _ in questions(brief)]
    parts: Dict[str, str] = {}
    numbered = re.findall(r"(?:^|\n|\s)(\d{1,2})[.)]\s*(.+?)(?=(?:\n|\s)\d{1,2}[.)]\s|$)", text, re.DOTALL)
    for num, value in numbered:
        i = int(num) - 1
        if 0 <= i < len(keys) and _clean(value) and not re.fullmatch(r"(?i)skip|-|na|n/a|none", _clean(value)):
            parts[keys[i]] = _clean(value)
    if not numbered:
        for line in re.split(r"[\n;]+", text):
            m = re.match(r"\s*([A-Za-z' ]{2,30}?)\s*[:=\-–]\s*(.+)", line)
            if not m:
                continue
            label = m.group(1).lower()
            key = next((k for k, rx in _LABELS.items() if re.search(rf"\b(?:{rx})\b", label)), "")
            if key and _clean(m.group(2)):
                parts[key] = _clean(m.group(2))
    contact = parts.pop("contact", "")
    for key, value in parts.items():
        if key in ("name", "location", "hours", "offerings", "style"):
            setattr(brief, key, value[:400])
    found_text = contact or text
    if not brief.email and (m := EMAIL_RX.search(found_text)):
        brief.email = m.group(0)
    if not brief.phone and (m := PHONE_RX.search(found_text)):
        brief.phone = _clean(m.group(1))
    if not parts and not contact:
        # Free text with no structure: keep it for the writer; the model extracts facts from it.
        brief.extra = _clean(f"{brief.extra} {text}")[:800]
    return brief


def merge_extracted(brief: SiteBrief, data: Optional[Dict[str, object]]) -> SiteBrief:
    """Fill still-empty fields from a model's extraction of a free-text reply (never overwrites)."""
    if not isinstance(data, dict):
        return brief
    for key in ("name", "location", "phone", "email", "hours", "offerings", "style", "audience"):
        value = data.get(key)
        if isinstance(value, str) and _clean(value) and not getattr(brief, key) \
                and _clean(value).lower() not in ("unknown", "not given", "none", "n/a", "null"):
            setattr(brief, key, _clean(value)[:400])
    if brief.email and not EMAIL_RX.fullmatch(brief.email):
        brief.email = ""                                  # never put a malformed address on the site
    return brief
