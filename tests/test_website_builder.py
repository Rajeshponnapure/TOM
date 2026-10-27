"""Professional website building (tom_core.website): understand → ask → write → render → verify.

Owner report 2026-10-27: "build a website for my bakery" should produce a professional site, asking
for what it needs instead of inventing it. Before, only the literal words "create website" reached a
single model call that had to return the whole site as one JSON blob.
"""
import asyncio
import json
import os
import re

import pytest

from tom_core import website
from tom_core.website import brief as B
from tools.command_router import CommandRouter

ANSWERS = ("1. Sweet Crumbs Bakery\n2. 12 MG Road, Banjara Hills, Hyderabad\n3. +91 98480 22338, hello@sweetcrumbs.in\n"
           "4. Mon-Sat 8 am - 9 pm, Sun 9 am - 2 pm\n5. sourdough, eggless cakes, croissants\n6. warm and elegant")

CANNED = {
    "top of the home page": {"tagline": "Baked fresh every morning",
                             "hero": {"headline": "Rise and Shine with Sourdough", "subheadline": "Eggless cakes and "
                                      "flaky croissants from our Hyderabad kitchen.", "cta_primary": "Order a cake",
                                      "cta_secondary": "See the menu"},
                             "seo": {"title": "Sweet Crumbs Bakery | Hyderabad", "description": "Sourdough, eggless "
                                     "cakes and croissants baked fresh daily at Sweet Crumbs Bakery in Banjara Hills, "
                                     "Hyderabad. Order a custom cake today.", "keywords": "bakery hyderabad"}},
    "About section": {"heading": "Our story", "paragraphs": [
        "Sweet Crumbs began with one loaf of sourdough and a stubborn belief that bread should taste of time and care, "
        "so every batch is slow fermented and shaped by hand in small numbers each morning before sunrise.",
        "Our eggless cakes mean nobody at the table misses out, and our croissants are laminated by hand over two "
        "days so every layer shatters the way it should when you take the very first bite.",
        "paragraphs"],                                    # a key echoed as an item: must not reach the page
        "highlights": [{"title": "Slow sourdough", "text": "Naturally leavened."},
                       {"title": "Eggless cakes", "text": "For every guest."},
                       {"title": "Hand-laminated", "text": "Flaky croissants."}]},
    "section.": {"heading": "Our Menu", "intro": "Baked fresh every day.", "groups": [
        {"name": "Breads", "items": [{"name": "Country Sourdough", "description": "Slow fermented loaf with a deep, crackling "
                                      "crust and an open, tangy crumb.", "price": "Rs 999"},
                                     {"name": "Multigrain", "description": "Seeded loaf with oats, flax and sunflower "
                                      "for a nutty bite.", "price": ""}]},
        {"name": "Cakes", "items": [{"name": "Eggless Chocolate Truffle", "description": "Dark chocolate sponge layered "
                                     "with silky ganache, fully eggless.", "price": "Rs 1,200"},
                                    {"name": "Red Velvet", "description": "Cocoa sponge with cream cheese frosting.",
                                     "price": ""}]}]},
    "4 reasons": {"heading": "Why Sweet Crumbs", "items": [{"title": t, "text": "Because it matters.", "icon": "leaf"}
                                                          for t in ("Fresh daily", "Eggless options", "Made by hand",
                                                                    "Custom cakes")]},
    "5 FAQs": {"heading": "FAQ", "items": [{"q": f"Question {i}?", "a": "Contact us and we will help."} for i in range(5)]},
    "gallery captions": {"heading": "Gallery", "items": [{"caption": f"Photo {i}"} for i in range(6)]},
    "call-to-action": {"heading": "Order a custom cake", "text": "Tell us the date and flavour.", "button": "Order now",
                       "contact": {"heading": "Say hello", "text": "We reply within a day."}},
}


async def canned_ask(system, user):
    for key, value in CANNED.items():
        if key in user:
            return "```json\n" + json.dumps(value) + "\n```"
    raise AssertionError(f"unexpected prompt: {user[:80]}")


async def broken_ask(system, user):
    return "Sure! Here is your content: {not json"


def _text(folder):
    with open(os.path.join(folder, "index.html"), encoding="utf-8") as fh:
        return fh.read()


# ── understanding and questions ─────────────────────────────────────────

@pytest.mark.parametrize("request_text,kind", [
    ("build a website for my bakery", "bakery"), ("website for my dental clinic in Pune", "dental"),
    ("a landing page for our fitness app", "gym"), ("site for my law firm", "law"),
    ("create a website for my coffee shop", "cafe"), ("make a portfolio website", "portfolio"),
    ("make a website for my business", "business"),
])
def test_the_kind_of_business_picks_the_blueprint(request_text, kind):
    assert website.understand(request_text).kind == kind


def test_missing_essentials_are_asked_for_never_invented():
    b = website.understand("build a professional website for my bakery")
    assert website.should_ask(b)
    q = website.question_text(b)
    for needed in ("called", "address", "phone", "opening hours"):
        assert needed in q
    assert "go ahead" in q


def test_go_ahead_skips_the_questions():
    assert not website.should_ask(website.understand("build a website for my bakery, just build it"))


def test_facts_in_the_request_are_not_asked_again():
    b = website.understand('build a website for my bakery called "Sweet Crumbs" in Hyderabad, call +91 98480 22338')
    assert (b.name, b.location, b.phone) == ("Sweet Crumbs", "Hyderabad", "+91 98480 22338")
    keys = [k for k, _ in website.questions(b)]
    assert "name" not in keys and "location" not in keys and "contact" not in keys


def test_numbered_answers_fill_the_brief():
    b = website.understand("build a website for my bakery")
    website.apply_answers(b, ANSWERS)
    assert b.name == "Sweet Crumbs Bakery"
    assert b.location == "12 MG Road, Banjara Hills, Hyderabad"
    assert b.phone == "+91 98480 22338" and b.email == "hello@sweetcrumbs.in"
    assert b.hours.startswith("Mon-Sat") and "sourdough" in b.offerings and "warm" in b.style


def test_labelled_answers_fill_the_brief():
    b = website.understand("build a website for my bakery")
    website.apply_answers(b, "Name: Crumbs & Co\nAddress: Indiranagar, Bengaluru\nPhone: 080 4123 4567\nHours: 9-9 daily")
    assert (b.name, b.location, b.phone, b.hours) == ("Crumbs & Co", "Indiranagar, Bengaluru", "080 4123 4567", "9-9 daily")


def test_model_extraction_never_overwrites_or_adds_a_bad_email():
    b = website.understand("build a website for my bakery")
    b.name = "Sweet Crumbs"
    B.merge_extracted(b, {"name": "Other", "email": "not an email", "location": "unknown", "hours": "8-8"})
    assert (b.name, b.email, b.location, b.hours) == ("Sweet Crumbs", "", "", "8-8")


# ── building and verification ───────────────────────────────────────────

def test_a_full_build_is_verified_and_uses_only_given_facts(tmp_path):
    b = website.understand("build a website for my bakery")
    website.apply_answers(b, ANSWERS)
    res = asyncio.run(website.build(b, canned_ask, root=str(tmp_path)))
    assert res["status"] == "success", res["message"]
    folder = res["path"]
    for f in ("index.html", "styles.css", "script.js", "favicon.svg", "README.md", os.path.join("images", "README.txt")):
        assert os.path.isfile(os.path.join(folder, f)), f
    page = _text(folder)
    assert res["verification"]["ok"] and not res["verification"]["placeholders"]
    assert "Rise and Shine with Sourdough" in page and "Country Sourdough" in page
    assert ">paragraphs<" not in page                       # echoed key dropped
    assert "Rs 999" not in page and "Rs 1,200" not in page  # the owner gave no prices: none invented
    assert '"@type": "Bakery"' in page and "+91 98480 22338" in page and "hello@sweetcrumbs.in" in page
    assert "maps.google.com/maps?q=12%20MG%20Road" in page
    assert "https://wa.me/919848022338" in page
    assert page.count("<h1") == 1


def test_missing_contact_details_become_visible_placeholders(tmp_path):
    b = website.understand("build a website for my bakery called Sweet Crumbs, go ahead")
    res = asyncio.run(website.build(b, canned_ask, root=str(tmp_path)))
    ph = res["verification"]["placeholders"]
    assert "Add your phone number" in ph and "Add your full address" in ph
    assert "Fill in before publishing" in res["message"]
    assert "tel:" not in _text(res["path"])                  # no made-up number to call


def test_a_failing_model_still_gives_a_complete_checked_site(tmp_path):
    b = website.understand("build a website for my bakery")
    website.apply_answers(b, ANSWERS)
    res = asyncio.run(website.build(b, broken_ask, root=str(tmp_path)))
    assert res["verification"]["checks"] and "sections present" in " ".join(res["verification"]["checks"])
    assert "could not write" in res["message"]
    assert not re.search(r"lorem ipsum", _text(res["path"]), re.IGNORECASE)


def test_verification_catches_a_broken_page(tmp_path):
    b = website.understand("build a website for my bakery, go ahead")
    res = asyncio.run(website.build(b, canned_ask, root=str(tmp_path)))
    os.remove(os.path.join(res["path"], "styles.css"))
    with open(os.path.join(res["path"], "index.html"), "a", encoding="utf-8") as fh:
        fh.write('<a href="#nowhere">x</a>')
    report = website.verify(res["path"], b)
    assert not report["ok"]
    assert any("missing files" in i for i in report["issues"])
    assert any("nowhere" in i for i in report["issues"])


def test_a_second_build_never_overwrites_the_first(tmp_path):
    b = website.understand("build a website for my bakery called Sweet Crumbs, go ahead")
    first = asyncio.run(website.build(b, canned_ask, root=str(tmp_path)))
    second = asyncio.run(website.build(b, canned_ask, root=str(tmp_path)))
    assert first["path"] != second["path"] and os.path.isfile(os.path.join(first["path"], "index.html"))


# ── routing and the conversation in the agent ───────────────────────────

@pytest.mark.parametrize("text", ["build a website for my bakery", "create a website for Sweet Crumbs", "make website",
                                  "I need a professional website for my dental clinic in Pune",
                                  "design a landing page for our app", "build a site for my gym"])
def test_website_requests_reach_the_builder(text):
    assert CommandRouter().route(text).handler == "execute_website_creation"


@pytest.mark.parametrize("text", ["open website youtube.com", "is this website safe example.com",
                                  "create a word document about website design", "make a report on website trends",
                                  "search the web for best website builders", "what is a website"])
def test_other_requests_about_websites_do_not(text):
    assert CommandRouter().route(text).handler != "execute_website_creation"


def _agent(tmp_path):
    from agent import TomAgent

    class Resp:
        def __init__(self, content):
            self.content = content

    async def invoke(prompt, payload, label, llm=None):
        return Resp(await canned_ask(payload.get("system", ""), payload.get("user", "")))

    a = TomAgent.__new__(TomAgent)
    a.command_router = CommandRouter()
    a.file_tools = type("F", (), {"open_file": lambda self, p: None})()
    a._build_memory_context = lambda command: ""
    a._invoke_llm = invoke
    a.llm = a.fast_llm = None
    return a


def test_the_agent_asks_then_builds_from_the_answers(tmp_path):
    a = _agent(tmp_path)
    first = asyncio.run(a.execute_website_creation("build a professional website for my bakery"))
    assert first["status"] == "needs_input" and "opening hours" in first["message"]
    done = asyncio.run(a._answer_pending_site(ANSWERS))       # built in the test session's workspace (conftest)
    assert done["status"] == "success", done["message"]
    assert "Sweet Crumbs Bakery" in _text(done["path"]) and a._pending_site is None
    assert os.path.basename(os.path.dirname(done["path"])) == "websites"


def test_cancel_and_unrelated_requests_leave_the_questions(tmp_path):
    a = _agent(tmp_path)
    asyncio.run(a.execute_website_creation("build a website for my bakery"))
    assert asyncio.run(a._answer_pending_site("cancel"))["status"] == "cancelled"
    asyncio.run(a.execute_website_creation("build a website for my bakery"))
    assert asyncio.run(a._answer_pending_site("open youtube")) is None


def test_website_mode_is_a_quick_action():
    from tom_core import skill_modes
    mode = skill_modes.MODES["website"]
    assert skill_modes.BY_LABEL["Website"] == "website"
    assert skill_modes.compose(mode, "a bakery called Sweet Crumbs") == "Build a professional website for a bakery called Sweet Crumbs"
    assert CommandRouter().route(skill_modes.compose(mode, "my dental clinic")).handler == "execute_website_creation"
