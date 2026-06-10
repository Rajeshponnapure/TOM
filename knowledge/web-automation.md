# Web Automation — Complete Guide

## Table of Contents

1. [Introduction & Tools Overview](#introduction--tools-overview)
2. [Selenium WebDriver](#selenium-webdriver)
3. [Playwright](#playwright)
4. [Browser DevTools Protocol (CDP)](#browser-devtools-protocol-cdp)
5. [Page Analysis Techniques](#page-analysis-techniques)
6. [Form Filling & Clicking Elements](#form-filling--clicking-elements)
7. [Screenshots & Visual Testing](#screenshots--visual-testing)
8. [Network Interception](#network-interception)
9. [Console Log Capture](#console-log-capture)
10. [Full-Page Summarization](#full-page-summarization)
11. [Handling SPAs & Dynamic Content](#handling-spas--dynamic-content)
12. [Infinite Scroll & Lazy Loading](#infinite-scroll--lazy-loading)
13. [Shadow DOM](#shadow-dom)
14. [Iframes](#iframes)
15. [Authentication & Sessions](#authentication--sessions)
16. [Cookies & localStorage](#cookies--localstorage)
17. [Headless Browsers](#headless-browsers)
18. [Multi-Page Crawling](#multi-page-crawling)
19. [Accessibility Tree Extraction](#accessibility-tree-extraction)
20. [Performance Metrics](#performance-metrics)
21. [Best Practices & Anti-Detection](#best-practices--anti-detection)

---

## Introduction & Tools Overview

Web automation encompasses programmatic control of web browsers to perform tasks: scraping data, testing applications, monitoring pages, and orchestrating complex workflows. Three dominant approaches exist:

| Tool | Language Bindings | Protocol | Speed | Use Case |
|------|-------------------|----------|-------|----------|
| Selenium | Python, JS, Java, C#, Ruby, Kotlin | WebDriver (W3C) | Moderate | Cross-browser testing |
| Playwright | Python, JS/TS, Java, .NET | CDP + custom | Fast | Modern web apps, SPAs |
| Puppeteer | JS/TS only | CDP | Fast | Chrome/Chromium only |
| CDP directly | Any (via websocket) | Chrome DevTools Protocol | Fastest | Custom tooling |

### Installation

```python
# Selenium
pip install selenium webdriver-manager

# Playwright
pip install playwright
playwright install  # downloads browser binaries

# CDP
pip install websocket-client
```

---

## Selenium WebDriver

### Basic Setup

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Setup with automatic driver management
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

driver.get("https://example.com")
print(driver.title)
driver.quit()
```

### Locating Elements

```python
# Multiple locator strategies
driver.find_element(By.ID, "search-input")
driver.find_element(By.NAME, "email")
driver.find_element(By.CLASS_NAME, "product-card")
driver.find_element(By.TAG_NAME, "h1")
driver.find_element(By.CSS_SELECTOR, "div.container > button.primary")
driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
driver.find_element(By.LINK_TEXT, "Click Here")
driver.find_element(By.PARTIAL_LINK_TEXT, "Click")

# Multiple elements
elements = driver.find_elements(By.CSS_SELECTOR, ".item")
for el in elements:
    print(el.text)
```

### Waits & Dynamic Content

```python
# Explicit wait — preferred over implicit
wait = WebDriverWait(driver, 10)

# Wait for element to be present
element = wait.until(
    EC.presence_of_element_located((By.ID, "dynamic-content"))
)

# Wait for element to be clickable
button = wait.until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, ".submit-btn"))
)

# Wait for element to be invisible (loading spinner gone)
wait.until(
    EC.invisibility_of_element_located((By.CLASS_NAME, "spinner"))
)

# Wait for text to appear in element
wait.until(
    EC.text_to_be_present_in_element((By.ID, "status"), "Complete")
)

# Wait for number of elements
wait.until(
    EC.visibility_of_all_elements_located((By.CLASS_NAME, "result-item"))
)

# Custom wait condition
def page_loaded(driver):
    return driver.execute_script("return document.readyState") == "complete"

wait.until(page_loaded)
```

### Actions API

```python
from selenium.webdriver.common.action_chains import ActionChains

actions = ActionChains(driver)

# Hover
actions.move_to_element(element).perform()

# Drag and drop
actions.drag_and_drop(source, target).perform()

# Click and hold
actions.click_and_hold(element).pause(2).release().perform()

# Double click
actions.double_click(element).perform()

# Right click
actions.context_click(element).perform()

# Keyboard combinations
actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()

# Scroll to element
actions.move_to_element(element).perform()
driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
```

---

## Playwright

### Basic Setup

```python
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        await page.goto("https://example.com", wait_until="networkidle")
        print(await page.title())
        await browser.close()

asyncio.run(main())
```

### Synchronous API

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://example.com")
    page.screenshot(path="screenshot.png")
    browser.close()
```

### Locators & Interactions

```python
# Playwright locators (auto-waiting)
page.locator("#search-input").fill("query")
page.locator("button.primary").click()
page.get_by_role("button", name="Submit").click()
page.get_by_text("Accept Cookies").click()
page.get_by_placeholder("Enter email").fill("user@example.com")
page.get_by_label("Password").fill("securepass")
page.get_by_test_id("submit-button").click()

# Chaining locators
modal = page.locator(".modal")
modal.locator("input[name='name']").fill("Alice")
modal.locator(".confirm-btn").click()

# Multiple elements
items = page.locator(".item").all()
for item in items:
    print(item.text_content())
```

### Advanced Navigation

```python
# Wait strategies
page.goto("https://example.com", wait_until="load")         # default
page.goto("https://example.com", wait_until="domcontentloaded")
page.goto("https://example.com", wait_until="networkidle")  # no network activity for 500ms
page.goto("https://example.com", wait_until="commit")       # navigation committed

# Navigation events
page.wait_for_url("**/dashboard")
page.wait_for_load_state("networkidle")
page.wait_for_function("window.appLoaded === true")
```

### Browser Contexts (Session Isolation)

```python
# Isolated contexts — no cookies sharing
context1 = await browser.new_context()
context2 = await browser.new_context()

page1 = await context1.new_page()
page2 = await context2.new_page()

await page1.goto("https://example.com")
await page2.goto("https://example.com")

# Context with custom settings
context = await browser.new_context(
    viewport={"width": 390, "height": 844},  # iPhone 14
    device_scale_factor=3,
    is_mobile=True,
    locale="en-US",
    timezone_id="America/New_York",
    permissions=["geolocation"],
    geolocation={"latitude": 40.7128, "longitude": -74.0060},
    color_scheme="dark",
    storage_state="auth.json"  # persist session
)
```

---

## Browser DevTools Protocol (CDP)

### Direct CDP via WebSocket

```python
import asyncio
import json
import websockets

async def cdp_example():
    # Launch browser with remote debugging port
    # chrome.exe --remote-debugging-port=9222

    async with websockets.connect("ws://127.0.0.1:9222/devtools/browser/...") as ws:
        # Send command
        await ws.send(json.dumps({
            "id": 1,
            "method": "Browser.getVersion",
            "params": {}
        }))
        response = await ws.recv()
        print(json.loads(response))

        # Enable network tracking
        await ws.send(json.dumps({
            "id": 2,
            "method": "Network.enable",
            "params": {}
        }))

asyncio.run(cdp_example())
```

### CDP via Selenium (Chrome DevTools)

```python
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome

options = Options()
options.add_experimental_option("w3c", True)
driver = Chrome(options=options)

# Access CDP via execute_cdp_cmd
driver.execute_cdp_cmd("Network.enable", {})
driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})

# Capture performance metrics
metrics = driver.execute_cdp_cmd("Performance.getMetrics", {})
print(metrics)

# Emulate network conditions
driver.execute_cdp_cmd("Network.emulateNetworkConditions", {
    "offline": False,
    "latency": 100,        # ms
    "downloadThroughput": 500 * 1024,   # 500 kbps
    "uploadThroughput": 100 * 1024      # 100 kbps
})

# Geolocation override
driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
    "latitude": 48.8566,
    "longitude": 2.3522,
    "accuracy": 100
})
```

### CDP via Playwright (Direct CDP Session)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    cdp_session = page.context.new_cdp_session(page)

    # Send raw CDP command
    result = cdp_session.send("Performance.enable")
    metrics = cdp_session.send("Performance.getMetrics")
    print(metrics)

    # DOM snapshot
    snapshot = cdp_session.send("DOMSnapshot.captureSnapshot", {
        "computedStyles": ["color", "font-size", "background-color"]
    })
    print(snapshot)

    # Coverage data
    cdp_session.send("Profiler.enable")
    coverage = cdp_session.send("Profiler.getBestEffortCoverage")
    print(coverage)
```

### Key CDP Domains

| Domain | Purpose |
|--------|---------|
| `Page` | Navigation, screenshots, print-to-PDF, lifecycle |
| `DOM` | Document traversal, query selectors, markup |
| `CSS` | Style sheets, computed styles, media queries |
| `Network` | Request/response interception, caching, cookies |
| `Runtime` | JavaScript execution, console, exceptions |
| `Console` | Console message capture |
| `Performance` | Metrics, timeline, memory profiling |
| `Emulation` | Device/geolocation/locale/color-scheme override |
| `Security` | Certificate inspection, mixed content |
| `Input` | Mouse, keyboard, touch events |
| `Accessibility` | Accessibility tree |
| `Storage` | Cookies, cache storage, IndexedDB |
| `Profiler` | CPU/memory profiling |
| `Overlay` | Highlight DOM nodes, show rulers |

---

## Page Analysis Techniques

### Extracting All Text

```python
# Selenium
text = driver.find_element(By.TAG_NAME, "body").text

# Playwright
text = page.locator("body").inner_text()

# Structured extraction — get text with hierarchy
def extract_text_tree(element, depth=0):
    prefix = "  " * depth
    tag = element.tag_name
    text = element.text.strip() if element.text else ""
    children = element.find_elements(By.XPATH, "./*")
    result = [f"{prefix}<{tag}>: {text[:100]}"]
    for child in children:
        result.extend(extract_text_tree(child, depth + 1))
    return result

# Extract all text nodes directly
all_text = driver.execute_script("""
    function walkTextNodes(node) {
        let texts = [];
        if (node.nodeType === 3) {
            let t = node.textContent.trim();
            if (t) texts.push(t);
        } else {
            for (let child of node.childNodes) {
                texts = texts.concat(walkTextNodes(child));
            }
        }
        return texts;
    }
    return walkTextNodes(document.body);
""")
```

### Extracting All Tags

```python
# Get all HTML tags with attributes
def extract_all_tags(driver):
    return driver.execute_script("""
        const all = document.querySelectorAll('*');
        return Array.from(all).map(el => ({
            tag: el.tagName.toLowerCase(),
            id: el.id,
            classes: Array.from(el.classList),
            attributes: Object.fromEntries(
                Array.from(el.attributes).map(a => [a.name, a.value])
            ),
            rect: el.getBoundingClientRect().toJSON(),
            visible: el.offsetParent !== null,
            text: (el.innerText || '').substring(0, 200)
        }));
    """)

tags = extract_all_tags(driver)

# Count by tag name
from collections import Counter
tag_counts = Counter(t["tag"] for t in tags)
print(tag_counts.most_common(20))
```

### Extracting CSS

```python
def extract_all_css(driver):
    return driver.execute_script("""
        const sheets = document.styleSheets;
        let rules = [];
        for (let sheet of sheets) {
            try {
                for (let rule of sheet.cssRules || []) {
                    rules.push({
                        selector: rule.selectorText,
                        css: rule.cssText,
                        sheet: sheet.href || 'inline'
                    });
                }
            } catch (e) {
                // CORS restrictions on external sheets
                rules.push({error: 'CORS blocked', sheet: sheet.href});
            }
        }
        return rules;
    """)

# Get computed styles for all elements
def extract_computed_styles(driver):
    return driver.execute_script("""
        const all = document.querySelectorAll('*');
        const props = ['color', 'font-size', 'font-family', 'background-color',
                       'display', 'visibility', 'opacity', 'position',
                       'width', 'height', 'margin', 'padding', 'border',
                       'box-shadow', 'transform', 'transition', 'animation'];
        return Array.from(all).map(el => {
            const styles = getComputedStyle(el);
            let result = {};
            props.forEach(p => result[p] = styles[p]);
            return {tag: el.tagName, id: el.id, classes: el.className, styles: result};
        });
    """)
```

### Extracting JavaScript

```python
# Get all inline scripts
def extract_inline_scripts(driver):
    return driver.execute_script("""
        return Array.from(document.scripts).map(s => ({
            src: s.src || 'inline',
            type: s.type,
            async: s.async,
            defer: s.defer,
            content: s.textContent.substring(0, 5000),
            length: s.textContent.length
        }));
    """)

# Get all global event listeners (limited)
def get_event_listeners(driver):
    return driver.execute_script("""
        const results = [];
        function getListeners(el) {
            const types = ['click', 'mouseover', 'mouseout', 'change', 'submit',
                          'keydown', 'keyup', 'scroll', 'focus', 'blur', 'load'];
            types.forEach(type => {
                const handler = el['on' + type];
                if (handler) {
                    results.push({
                        tag: el.tagName,
                        id: el.id,
                        classes: el.className,
                        type: type,
                        handler: handler.toString().substring(0, 500)
                    });
                }
            });
            Array.from(el.children).forEach(getListeners);
        }
        getListeners(document.body);
        return results;
    """)
```

### Extracting Animations

```python
def extract_animations(driver):
    return driver.execute_script("""
        // CSS animations
        const sheets = document.styleSheets;
        let animations = [];
        for (let sheet of sheets) {
            try {
                for (let rule of sheet.cssRules || []) {
                    if (rule.type === 7 || rule.type === 12) { // KEYFRAMES_RULE
                        animations.push({
                            name: rule.name,
                            type: 'css-keyframes',
                            css: rule.cssText
                        });
                    }
                }
            } catch(e) {}
        }

        // Running animations
        const running = document.getAnimations();
        running.forEach(anim => {
            animations.push({
                type: 'running',
                target: (anim.effect?.target?.tagName || 'unknown'),
                animationName: anim.animationName || 'Web Animation',
                playbackState: anim.playState,
                currentTime: anim.currentTime,
                duration: anim.effect?.getComputedTiming?.()?.duration || 0
            });
        });

        // requestAnimationFrame loops (approximate)
        const origRAF = window.requestAnimationFrame;
        window.__rafCount = 0;
        window.requestAnimationFrame = function(cb) {
            window.__rafCount++;
            return origRAF.call(window, cb);
        };
        setTimeout(() => {
            animations.push({type: 'raf-detected', count: window.__rafCount});
        }, 100);

        return animations;
    """)
```

### Performance Metrics

```python
# Selenium — Performance Log
def get_performance_log(driver):
    logs = driver.get_log("performance")
    entries = []
    for entry in logs:
        data = json.loads(entry["message"])
        entries.append(data["message"])
    return entries

# Playwright — Performance API
def get_performance_metrics(page):
    metrics = page.evaluate("""() => {
        const perf = performance;
        return {
            navigation: perf.getEntriesByType('navigation')[0],
            paint: perf.getEntriesByType('paint'),
            resources: perf.getEntriesByType('resource').map(r => ({
                name: r.name,
                duration: r.duration,
                transferSize: r.transferSize,
                decodedBodySize: r.decodedBodySize,
                initiatorType: r.initiatorType
            })),
            firstContentfulPaint: perf.getEntriesByName('first-contentful-paint')[0]?.startTime,
            largestContentfulPaint: new Promise(resolve => {
                new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    resolve(entries[entries.length - 1]?.startTime);
                }).observe({type: 'largest-contentful-paint', buffered: true});
            }),
            layoutShift: new Promise(resolve => {
                let cumulative = 0;
                new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        cumulative += entry.value;
                    }
                    resolve(cumulative);
                }).observe({type: 'layout-shift', buffered: true});
            })
        };
    }""")
    return metrics
```

---

## Form Filling & Clicking Elements

### Selenium

```python
def fill_form_selenium(driver, form_data):
    for selector, value in form_data.items():
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            element.clear()
            element.send_keys(value)
        except Exception as e:
            print(f"Failed to fill {selector}: {e}")

# Select dropdown
from selenium.webdriver.support.ui import Select
select = Select(driver.find_element(By.ID, "country"))
select.select_by_visible_text("United States")
select.select_by_value("US")
select.select_by_index(1)

# Checkbox / Radio
checkbox = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
if not checkbox.is_selected():
    checkbox.click()

# File upload
driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys("C:\\path\\to\\file.pdf")

# Date picker (set via JS)
driver.execute_script("arguments[0].value = '2025-12-31';",
    driver.find_element(By.CSS_SELECTOR, "input[type='date']"))

# Submit
driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
```

### Playwright

```python
# Fill form (auto-wait, type character by character)
page.get_by_label("Full Name").fill("John Doe")
page.get_by_placeholder("Email").fill("john@example.com")
page.get_by_role("combobox", name="Country").select_option("US")
page.get_by_label("I agree").check()
page.get_by_text("Male").click()  # radio
page.get_by_role("button", name="Register").click()

# Type slowly (human-like)
page.get_by_label("Search").press_sequentially("search term", delay=100)

# File upload
page.get_by_label("Upload CV").set_input_files("resume.pdf")
page.get_by_label("Upload Photos").set_input_files(["photo1.jpg", "photo2.jpg"])

# Select from custom dropdown
page.locator(".custom-dropdown").click()
page.locator(".dropdown-option:has-text('Option 3')").click()

# Rich text editors
page.frame_locator("#editor_iframe").locator("body").fill("Hello world")

# Force click (bypass actionability checks)
page.locator(".hidden-button").click(force=True)
```

### Clicking Strategies

```python
# Reliable click patterns
def reliable_click(page, selector, retries=3):
    for i in range(retries):
        try:
            locator = page.locator(selector)
            locator.wait_for(state="visible", timeout=5000)
            locator.click()
            return True
        except Exception as e:
            if i == retries - 1:
                # Last resort — JS click
                page.evaluate(f"document.querySelector('{selector}').click()")
                return False

# JavaScript click (bypasses overlays)
driver.execute_script("arguments[0].click();", element)

# Click with offset
page.locator("canvas").click(position={"x": 100, "y": 200})

# Click all matching elements
page.locator(".add-to-cart").all().map(lambda btn: btn.click())
```

---

## Screenshots & Visual Testing

### Full Page Screenshots

```python
# Selenium — full page requires stitching
def full_page_screenshot_selenium(driver, path):
    total_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    driver.set_window_size(1920, total_height)
    driver.find_element(By.TAG_NAME, "body").screenshot(path)
    # Reset window size
    driver.set_window_size(1920, 1080)

# Playwright — native full page
page.screenshot(path="fullpage.png", full_page=True)

# Element screenshot
element = page.locator(".hero-section")
element.screenshot(path="hero.png")

# Screenshot to bytes
screenshot_bytes = page.screenshot(full_page=True)
```

### Visual Comparison

```python
from PIL import Image, ImageChops, ImageDraw
import numpy as np

def compare_screenshots(baseline_path, current_path, diff_path, threshold=10):
    baseline = Image.open(baseline_path)
    current = Image.open(current_path)

    # Ensure same size
    if baseline.size != current.size:
        current = current.resize(baseline.size)

    # Pixel difference
    diff = ImageChops.difference(baseline, current)
    diff_array = np.array(diff)

    # Count changed pixels
    changed_pixels = np.sum(diff_array > threshold) / 3  # 3 channels
    total_pixels = diff_array.shape[0] * diff_array.shape[1]
    change_ratio = changed_pixels / total_pixels

    # Highlight differences
    diff_highlight = Image.fromarray(
        np.where(diff_array > threshold, [255, 0, 0, 255],
                 np.array(current.convert("RGBA")))
    )
    diff_highlight.save(diff_path)

    return change_ratio

# Playwright visual comparison (built-in)
expect(page).to_have_screenshot("baseline.png", threshold=0.2)
```

### PDF Generation

```python
# Playwright PDF
page.pdf(path="page.pdf", format="A4", print_background=True,
         margin={"top": "1cm", "bottom": "1cm"})

# Selenium via CDP
pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
    "printBackground": True,
    "paperWidth": 8.27,
    "paperHeight": 11.69,
    "marginTop": 0.4,
    "marginBottom": 0.4
})
with open("page.pdf", "wb") as f:
    f.write(bytes(pdf_data["data"], "base64"))
```

---

## Network Interception

### Playwright — Intercept Requests

```python
# Block resources
def block_resources(route):
    if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
        route.abort()
    else:
        route.continue_()

page.route("**/*", block_resources)

# Modify request headers
page.route("**/api/*", lambda route: route.continue_(
    headers={**route.request.headers, "Authorization": "Bearer token123"}
))

# Mock API response
page.route("**/api/users", lambda route: route.fulfill(
    status=200,
    content_type="application/json",
    body='[{"id": 1, "name": "Mock User"}]'
))

# Capture request/response details
requests_log = []
def log_request(route):
    request = route.request
    response = page.request.fetch(request)
    requests_log.append({
        "url": request.url,
        "method": request.method,
        "headers": request.headers,
        "status": response.status,
        "body": response.text()[:2000]
    })
    route.continue_()

page.route("**/api/*", log_request)
```

### Selenium — Network Logs

```python
from selenium.webdriver.chrome.options import Options

options = Options()
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
driver = Chrome(options=options)
driver.get("https://example.com")

logs = driver.get_log("performance")
network_entries = []
for entry in logs:
    log_data = json.loads(entry["message"])["message"]
    if log_data["method"] in ["Network.requestWillBeSent",
                               "Network.responseReceived"]:
        network_entries.append(log_data)

# Filter by type
api_calls = [e for e in network_entries if "api" in e.get("params", {}).get("request", {}).get("url", "")]
```

### CDP — Full Network Capture

```python
driver.execute_cdp_cmd("Network.enable", {})
driver.execute_cdp_cmd("Network.setRequestInterception", {
    "patterns": [{"urlPattern": "*", "interceptionStage": "HeadersReceived"}]
})

# Capture HAR-like data
har = {
    "log": {
        "version": "1.2",
        "entries": []
    }
}

# Using Playwright to get HAR
har_path = page.context.tracing.start(name="trace")
page.context.tracing.stop(path="trace.zip")

# Or directly via HAR export
browser = p.chromium.launch()
context = browser.new_context(record_har_path="network.har")
page = context.new_page()
page.goto("https://example.com")
context.close()  # writes HAR
```

---

## Console Log Capture

### Selenium

```python
from selenium.webdriver.chrome.options import Options

options = Options()
options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
driver = Chrome(options=options)
driver.get("https://example.com")

console_logs = driver.get_log("browser")
for log in console_logs:
    print(f"[{log['level']}] {log['message']}")
    # log structure: {level, message, timestamp}
```

### Playwright

```python
# Listen to console messages
console_messages = []
page.on("console", lambda msg: console_messages.append({
    "type": msg.type,
    "text": msg.text,
    "location": msg.location,
    "args": [arg.json_value() if arg.json_value() else str(arg) for arg in msg.args]
}))

page.on("pageerror", lambda err: print(f"Page Error: {err}"))
page.on("dialog", lambda dialog: dialog.accept())

# Filter for specific messages
errors = [m for m in console_messages if m["type"] == "error"]
warnings = [m for m in console_messages if m["type"] == "warning"]

# Capture JS exceptions
page.on("pageerror", lambda err: print(f"Uncaught: {err}"))
```

### CDP Console Capture

```python
driver.execute_cdp_cmd("Console.enable", {})
driver.execute_cdp_cmd("Runtime.enable", {})

# Listen for console messages via CDP events
# Requires a WebSocket listener in production

# Inject console interceptor
driver.execute_script("""
    (function() {
        const originalConsole = {};
        ['log', 'warn', 'error', 'info', 'debug'].forEach(method => {
            originalConsole[method] = console[method];
            console[method] = function(...args) {
                originalConsole[method].apply(console, args);
                window.__consoleLogs = window.__consoleLogs || [];
                window.__consoleLogs.push({
                    method: method,
                    args: args.map(a => {
                        try { return JSON.stringify(a); }
                        catch(e) { return String(a); }
                    }),
                    timestamp: Date.now()
                });
            };
        });
    })();
""")

# Retrieve after page interaction
logs = driver.execute_script("return window.__consoleLogs || []")
```

---

## Full-Page Summarization

### Text Extraction & Summarization

```python
import re
from collections import Counter

def summarize_page(driver):
    # Extract structured content
    content = driver.execute_script("""
        const article = document.querySelector('article') || document.body;

        // Remove scripts, styles, nav, footer, ads
        const clones = article.cloneNode(true);
        ['script', 'style', 'nav', 'footer', 'header',
         '.advertisement', '.sidebar', '.related-posts',
         '.comments', '.social-share'].forEach(sel => {
            clones.querySelectorAll(sel).forEach(el => el.remove());
        });

        return {
            title: document.title,
            meta_description: document.querySelector('meta[name="description"]')?.content || '',
            h1: Array.from(clones.querySelectorAll('h1')).map(h => h.textContent.trim()),
            h2: Array.from(clones.querySelectorAll('h2')).map(h => h.textContent.trim()),
            h3: Array.from(clones.querySelectorAll('h3')).map(h => h.textContent.trim()),
            paragraphs: Array.from(clones.querySelectorAll('p')).map(p => p.textContent.trim()),
            links: Array.from(clones.querySelectorAll('a[href]')).map(a => ({
                text: a.textContent.trim(),
                href: a.href
            })),
            images: Array.from(clones.querySelectorAll('img[src]')).map(img => ({
                alt: img.alt,
                src: img.src
            })),
            code: Array.from(clones.querySelectorAll('code, pre')).map(c => c.textContent.trim()),
            lists: Array.from(clones.querySelectorAll('ul, ol')).map(l => ({
                type: l.tagName,
                items: Array.from(l.querySelectorAll('li')).map(li => li.textContent.trim())
            })),
            tables: Array.from(clones.querySelectorAll('table')).map(t => {
                const rows = t.querySelectorAll('tr');
                return Array.from(rows).map(r =>
                    Array.from(r.querySelectorAll('td, th')).map(c => c.textContent.trim())
                );
            })
        };
    """)

    return content

# Word frequency analysis
def word_frequencies(text, top=50):
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    stopwords = set("the a an and or but in on at to for of with by from as is it was are were be has have do does did will would could should may might must shall".split())
    words = [w for w in words if w not in stopwords]
    return Counter(words).most_common(top)

# Sentence extraction for summary
def extract_key_sentences(text, n=5):
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
    # Score by word frequency importance
    freq = word_frequencies(text, 100)
    important_words = {w for w, _ in freq}

    scored = []
    for s in sentences:
        words = set(re.findall(r'\b[a-z]{3,}\b', s.lower()))
        score = len(words & important_words)
        scored.append((score, s))

    scored.sort(reverse=True)
    return [s for _, s in scored[:n]]
```

### Meta & Open Graph Extraction

```python
def extract_metadata(page):
    return page.evaluate("""() => {
        const getMeta = (name) => {
            const el = document.querySelector(`meta[name="${name}"],
                                                meta[property="${name}"]`);
            return el?.content || null;
        };
        return {
            title: document.title,
            canonical: document.querySelector('link[rel="canonical"]')?.href,
            description: getMeta('description'),
            keywords: getMeta('keywords'),
            og_title: getMeta('og:title'),
            og_description: getMeta('og:description'),
            og_image: getMeta('og:image'),
            og_url: getMeta('og:url'),
            og_type: getMeta('og:type'),
            twitter_card: getMeta('twitter:card'),
            twitter_image: getMeta('twitter:image'),
            json_ld: (() => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                return Array.from(scripts).map(s => {
                    try { return JSON.parse(s.textContent); }
                    catch(e) { return s.textContent; }
                });
            })(),
            charset: document.characterSet,
            viewport: document.querySelector('meta[name="viewport"]')?.content,
            theme_color: document.querySelector('meta[name="theme-color"]')?.content,
            robots: getMeta('robots')
        };
    }""")
```

---

## Handling SPAs & Dynamic Content

### Waiting for SPA Render

```python
# Wait for framework-specific indicators
def wait_for_spa(page):
    # React
    page.wait_for_function(
        """document.querySelector('#root')?.__reactFiber$?.child?.memoizedState"""
    )
    # Vue
    page.wait_for_function("""document.querySelector('#app')?.__vue_app__""")
    # Angular
    page.wait_for_function("""window.ng?.probe""")

    # Or wait for a specific component to render
    page.wait_for_selector("[data-loaded='true']")

    # Wait for all network requests to settle
    page.wait_for_load_state("networkidle")

    # Wait for no mutations for 500ms
    page.wait_for_function("""
        new Promise(resolve => {
            let timeout;
            const observer = new MutationObserver(() => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    observer.disconnect();
                    resolve();
                }, 500);
            });
            observer.observe(document.body, {childList: true, subtree: true});
        })
    """)
```

### Handling Client-Side Navigation

```python
# SPAs use pushState — need to detect route changes
def handle_spa_navigation(page):
    navigated = False

    def on_popstate():
        nonlocal navigated
        navigated = True

    page.evaluate("window.addEventListener('popstate', () => window.__popstate = true)")

    # Click SPA link
    page.locator("a[href='/dashboard']").click()

    # Wait for route change
    page.wait_for_function("window.__popstate === true", timeout=5000)
    page.wait_for_load_state("networkidle")

# Or use URL watcher
def navigate_spa(page, url):
    page.goto(url)
    page.wait_for_load_state("networkidle")

    # Click links and capture resulting state
    links = page.locator("a").all()
    pages_data = []
    for link in links:
        href = link.get_attribute("href")
        if href and not href.startswith(("http", "#", "javascript:")):
            link.click()
            page.wait_for_load_state("networkidle")
            pages_data.append({
                "url": page.url,
                "title": page.title(),
                "content": page.locator("body").inner_text()[:1000]
            })
            page.go_back()
            page.wait_for_load_state("networkidle")
    return pages_data
```

### Virtual Scrolling

```python
def handle_virtual_scroll(page):
    # Detect virtual scroll implementation
    is_virtual = page.evaluate("""
        document.querySelector('[style*="overflow"]') &&
        document.querySelectorAll('[style*="transform"]').length > 50
    """)

    if is_virtual:
        # Scroll to bottom repeatedly to load all items
        prev_count = 0
        while True:
            items = page.locator(".virtual-item").count()
            if items == prev_count:
                break
            prev_count = items
            page.evaluate("""
                const container = document.querySelector('[style*="overflow"]');
                container.scrollTop = container.scrollHeight;
            """)
            page.wait_for_timeout(1000)

    return page.locator(".virtual-item").all_text_contents()
```

---

## Infinite Scroll & Lazy Loading

### Scrolling Techniques

```python
def infinite_scroll_selenium(driver, max_scrolls=50):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(max_scrolls):
        # Scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # wait for lazy load

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("No more content loaded")
            break
        last_height = new_height
    print(f"Scrolled {i+1} times")

def infinite_scroll_playwright(page, max_scrolls=50):
    for i in range(max_scrolls):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        try:
            page.wait_for_function(
                "document.body.scrollHeight > arguments[0]",
                arg=page.evaluate("document.body.scrollHeight"),
                timeout=3000
            )
        except:
            break
        page.wait_for_timeout(1000)

# Progressive scrolling with content detection
def smart_infinite_scroll(page, content_selector=".item", timeout=3):
    previous_count = 0
    max_attempts = 30

    for attempt in range(max_attempts):
        current_count = page.locator(content_selector).count()
        if current_count == previous_count:
            # Try scrolling a bit more
            page.evaluate("window.scrollBy(0, 500)")
            try:
                page.wait_for_function(
                    f"document.querySelectorAll('{content_selector}').length > {current_count}",
                    timeout=timeout * 1000
                )
            except:
                print(f"No new items after {attempt} scrolls")
                break
        previous_count = current_count

    return page.locator(content_selector).all_text_contents()
```

### Lazy-Loaded Images

```python
def ensure_images_loaded(page):
    # Scroll to each lazy image
    images = page.locator("img[loading='lazy'], img[data-src]")
    count = images.count()
    for i in range(count):
        images.nth(i).scroll_into_view_if_needed()
        page.wait_for_timeout(200)

    # Wait for all images to load
    page.wait_for_function("""
        Array.from(document.images).every(img => img.complete)
    """, timeout=10000)

    # Or use IntersectionObserver trigger
    page.evaluate("""
        document.querySelectorAll('img[loading="lazy"]').forEach(img => {
            img.loading = 'eager';
            if (img.dataset.src) {
                img.src = img.dataset.src;
                delete img.dataset.src;
            }
        });
    """)
```

---

## Shadow DOM

### Accessing Shadow DOM

```python
# Selenium — Shadow DOM access via JS
def get_shadow_element(driver, host_selector, shadow_selector):
    return driver.execute_script(f"""
        return document.querySelector('{host_selector}')
            .shadowRoot.querySelector('{shadow_selector}');
    """)

# Playwright — pierce via CSS selector with _pierce_ or >>>
# Playwright pierces shadow DOM automatically by default
shadow_element = page.locator("my-component >> #inner-button")
shadow_element.click()

# Manual shadow DOM traversal
def get_shadow_content(page, host_tag="my-component"):
    return page.evaluate("""() => {
        const host = document.querySelector('my-component');
        if (!host || !host.shadowRoot) return null;
        const root = host.shadowRoot;

        function extractTree(node, depth=0) {
            if (!node || node.nodeType !== 1) return '';
            const tag = node.tagName.toLowerCase();
            const text = node.textContent?.trim() || '';
            const children = Array.from(node.children)
                .map(child => extractTree(child, depth + 1))
                .join('\\n');
            const indent = '  '.repeat(depth);
            return `${indent}<${tag}>${text ? ' ' + text.substring(0, 100) : ''}${children ? '\\n' + children : ''}`;
        }

        return extractTree(root);
    }""")

# Handle nested shadow DOM
def get_nested_shadow_text(page):
    return page.evaluate("""() => {
        function traverseShadow(host, depth=0) {
            if (!host || !host.shadowRoot) return [];
            const results = [];
            const root = host.shadowRoot;
            const all = root.querySelectorAll('*');
            all.forEach(el => {
                if (el.shadowRoot) {
                    results.push({
                        tag: el.tagName,
                        shadowContent: el.shadowRoot.textContent?.trim().substring(0, 200),
                        children: traverseShadow(el, depth+1)
                    });
                }
            });
            return results;
        }
        return traverseShadow(document.body);
    }""")

# Playwright — deep shadow piercing
page.locator("my-component").locator("#shadow-button").click()
# Or with CSS >>> syntax
page.locator("my-component >>> #shadow-button").click()
```

### Closed Shadow DOM (not pierceable via CSS)

```python
# Closed shadow mode — only accessible via JS
def access_closed_shadow(page, host_selector):
    return page.evaluate(f"""() => {{
        const host = document.querySelector('{host_selector}');
        // Cannot access .shadowRoot — closed mode
        // Workaround: monkey-patch attachShadow before creation
        return 'closed shadow — cannot access directly';
    }}""")

# Monkey-patch before navigation
def patch_shadow_before_load(page):
    page.add_init_script("""
        Element.prototype._attachShadow = Element.prototype.attachShadow;
        Element.prototype.attachShadow = function(init) {
            const shadow = this._attachShadow(init);
            this.__openShadow = shadow;  // store reference
            return shadow;
        };
    """)
```

---

## Iframes

### Handling Iframes in Selenium

```python
# Switch to iframe by index
driver.switch_to.frame(0)

# By name or id
driver.switch_to.frame("content-frame")

# By element
iframe = driver.find_element(By.CSS_SELECTOR, "iframe[src*='widget']")
driver.switch_to.frame(iframe)

# Do work inside iframe
content = driver.find_element(By.TAG_NAME, "body").text

# Switch back to main document
driver.switch_to.default_content()

# Nested iframes
driver.switch_to.frame("outer")
driver.switch_to.frame("inner")

# Get all iframes on page
iframes = driver.find_elements(By.TAG_NAME, "iframe")
for i, iframe in enumerate(iframes):
    driver.switch_to.frame(iframe)
    print(f"Iframe {i}: {driver.page_source[:200]}")
    driver.switch_to.default_content()
```

### Handling Iframes in Playwright

```python
# Frame locator — most ergonomic
frame = page.frame_locator("#widget-iframe")
frame.locator("input[name='card-number']").fill("4111111111111111")
frame.locator(".submit-btn").click()

# Get frame by name
frame = page.frame("content-frame")

# Get frame by URL
frame = page.frame(url="https://payments.example.com/form")

# List all frames
all_frames = page.frames
for f in all_frames:
    print(f.name, f.url)

# Nested iframes
inner_frame = page.frame_locator("#outer").frame_locator("#inner")
inner_frame.locator("button").click()

# Cross-origin iframe
# Playwright supports cross-origin iframes natively
page.frame_locator("[src*='analytics']").locator("button").click()
```

---

## Authentication & Sessions

### Basic Auth

```python
# Playwright — built-in
page = browser.new_page()
page.authenticate({
    "username": "admin",
    "password": "password123"
})
page.goto("https://secure-site.example.com")

# Selenium — via URL
driver.get("https://admin:password123@secure-site.example.com")

# Or via CDP
driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
    "headers": {
        "Authorization": "Basic " + base64.b64encode(b"admin:password123").decode()
    }
})
```

### Session Persistence

```python
# Playwright — save & restore storage state
context = browser.new_context()
page = context.new_page()
# ... login ...
context.storage_state(path="auth.json")

# Later — load saved state
context = browser.new_context(storage_state="auth.json")

# Selenium — save cookies
def save_cookies(driver, path):
    import pickle
    with open(path, "wb") as f:
        pickle.dump(driver.get_cookies(), f)

def load_cookies(driver, path):
    import pickle
    with open(path, "rb") as f:
        cookies = pickle.load(f)
    for cookie in cookies:
        driver.add_cookie(cookie)
```

### OAuth / SSO Flows

```python
def handle_oauth(page, provider="google"):
    # Click login with provider
    page.get_by_text("Sign in with Google").click()

    # Wait for popup
    with page.expect_popup() as popup_info:
        page.wait_for_timeout(2000)  # popup may already be opening

    popup = popup_info.value
    popup.wait_for_load_state()

    # Fill credentials
    if provider == "google":
        popup.get_by_label("Email").fill("user@gmail.com")
        popup.get_by_role("button", name="Next").click()
        popup.get_by_label("Password").fill("password")
        popup.get_by_role("button", name="Next").click()

    # Wait for redirect back to main page
    page.wait_for_url("**/dashboard")
    return page.url

# Alternative — intercept OAuth callback
def intercept_oauth_callback(page, expected_code):
    code = None
    def handle_route(route):
        nonlocal code
        if "code=" in route.request.url:
            code = route.request.url.split("code=")[1].split("&")[0]
        route.continue_()

    page.route("**/oauth/callback*", handle_route)
    return code
```

### Multi-Factor Authentication (MFA)

```python
import pyotp

def handle_mfa(page, secret_key):
    totp = pyotp.TOTP(secret_key)
    code = totp.now()
    page.get_by_label("Authentication Code").fill(code)
    page.get_by_role("button", name="Verify").click()

# Or wait for manual input
input("Enter MFA code and press Enter to continue...")
```

---

## Cookies & localStorage

### Cookie Management

```python
# Playwright
cookies = page.context.cookies()
for cookie in cookies:
    print(cookie["name"], cookie["value"])

# Add cookies
page.context.add_cookies([{
    "name": "session_id",
    "value": "abc123",
    "domain": ".example.com",
    "path": "/"
}])

# Delete cookies
page.context.clear_cookies()

# Selenium
cookies = driver.get_cookies()
for cookie in cookies:
    print(f"{cookie['name']}={cookie['value']}")

driver.add_cookie({"name": "token", "value": "xyz789", "domain": ".example.com", "path": "/"})
driver.delete_cookie("token")
driver.delete_all_cookies()
```

### localStorage

```python
# Playwright
local_storage = page.evaluate("JSON.stringify(window.localStorage)")
parsed = json.loads(local_storage)

# Set localStorage
page.evaluate("window.localStorage.setItem('theme', 'dark')")

# Selenium
local_storage = driver.execute_script("return JSON.stringify(window.localStorage)")
driver.execute_script("window.localStorage.setItem('token', 'abc123')")
driver.execute_script("window.localStorage.removeItem('token')")

# Copy localStorage between pages
def copy_localstorage(source_page, target_page):
    data = source_page.evaluate("JSON.stringify(window.localStorage)")
    target_page.evaluate(f"""
        const data = JSON.parse('{data.replace(/'/g, "\\'")}');
        Object.entries(data).forEach(([k, v]) => window.localStorage.setItem(k, v));
    """)

# sessionStorage
session_data = page.evaluate("JSON.stringify(window.sessionStorage)")
```

### IndexedDB

```python
def clear_indexeddb(page):
    page.evaluate("""() => {
        return new Promise((resolve, reject) => {
            const req = indexedDB.deleteDatabase('database_name');
            req.onsuccess = () => resolve();
            req.onerror = () => reject(req.error);
        });
    }""")

def list_indexeddb_databases(page):
    return page.evaluate("""() => {
        return new Promise((resolve) => {
            indexedDB.databases().then(dbs => {
                resolve(dbs.map(d => d.name));
            });
        });
    }""")
```

---

## Headless Browsers

### Configuration Options

```python
# Chrome/Chromium headless
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")  # new headless mode (Chrome 112+)
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

# Playwright
browser = p.chromium.launch(headless=True)

# Firefox
browser = p.firefox.launch(headless=True)

# WebKit (Safari)
browser = p.webkit.launch(headless=True)
```

### Anti-Detection Techniques

```python
def configure_stealth(driver):
    # Remove webdriver flag
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});

            // Override Chrome detection
            window.chrome = {runtime: {}};

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (params) => (
                params.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(params)
            );

            // Override webgl vendor
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(p) {
                if (p === 37445) return 'Intel Inc.';
                if (p === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter(p);
            };
        """
    })

# Playwright stealth
def get_stealth_context(browser):
    return browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        device_scale_factor=1,
        locale="en-US",
        timezone_id="America/New_York",
        permissions=["geolocation"],
        geolocation={"latitude": 40.7128, "longitude": -74.0060},
        color_scheme="dark",
    )
```

### Running Headless in Docker

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_DRIVER=/usr/bin/chromedriver

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .
CMD ["python", "app.py"]
```

---

## Multi-Page Crawling

### Basic Crawler

```python
from urllib.parse import urljoin, urlparse
from collections import deque

class WebCrawler:
    def __init__(self, page, base_url, max_pages=50):
        self.page = page
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.visited = set()
        self.queue = deque([base_url])
        self.results = []

    async def crawl(self):
        while self.queue and len(self.visited) < self.max_pages:
            url = self.queue.popleft()
            if url in self.visited:
                continue

            try:
                await self.page.goto(url, wait_until="networkidle", timeout=30000)
                self.visited.add(url)

                page_data = await self.extract_page_data()
                self.results.append(page_data)

                # Extract links
                links = await self.page.evaluate("""
                    Array.from(document.querySelectorAll('a[href]'))
                        .map(a => a.href)
                        .filter(h => h.startsWith('http'))
                """)

                for link in links:
                    parsed = urlparse(link)
                    if parsed.netloc == self.base_domain and link not in self.visited:
                        self.queue.append(link)

            except Exception as e:
                print(f"Failed {url}: {e}")

        return self.results

    async def extract_page_data(self):
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "h1": await self.page.evaluate(
                "Array.from(document.querySelectorAll('h1')).map(h => h.textContent)"
            ),
            "meta_description": await self.page.evaluate(
                "document.querySelector('meta[name=\"description\"]')?.content || ''"
            ),
            "text_length": len(await self.page.evaluate("document.body.innerText")),
            "links": await self.page.evaluate(
                "document.querySelectorAll('a').length"
            ),
            "images": await self.page.evaluate(
                "document.querySelectorAll('img').length"
            ),
            "status_code": await self.page.evaluate("window.performance.getEntriesByType('navigation')[0]?.responseStatus || 200")
        }

# Usage
async def run_crawler():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        crawler = WebCrawler(page, "https://example.com", max_pages=20)
        results = await crawler.crawl()
        await browser.close()
        return results
```

### Sitemap-Based Crawling

```python
import xml.etree.ElementTree as ET
import requests

def parse_sitemap(url):
    """Parse sitemap and return all URLs"""
    resp = requests.get(url)
    root = ET.fromstring(resp.content)

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text for loc in root.findall(".//sm:loc", ns)]

    # Handle sitemap index
    sitemaps = root.findall(".//sm:sitemap/sm:loc", ns)
    for sm_url in sitemaps:
        urls.extend(parse_sitemap(sm_url))

    return urls

def crawl_sitemap(driver, sitemap_url, max_pages=None):
    urls = parse_sitemap(sitemap_url)
    if max_pages:
        urls = urls[:max_pages]

    results = []
    for url in urls:
        driver.get(url)
        results.append({
            "url": url,
            "title": driver.title,
            "text": driver.find_element(By.TAG_NAME, "body").text[:500]
        })
    return results
```

### Concurrent Crawling

```python
import asyncio
from playwright.async_api import async_playwright

async def crawl_page(browser, url, semaphore):
    async with semaphore:
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            data = {
                "url": url,
                "title": await page.title(),
                "text": await page.evaluate("document.body.innerText")[:2000]
            }
            return data
        except Exception as e:
            return {"url": url, "error": str(e)}
        finally:
            await context.close()

async def concurrent_crawl(urls, concurrency=5):
    semaphore = asyncio.Semaphore(concurrency)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        tasks = [crawl_page(browser, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)
        await browser.close()
        return results
```

---

## Accessibility Tree Extraction

### Playwright Accessibility Snapshot

```python
# Full accessibility tree
def get_accessibility_tree(page):
    snapshot = page.accessibility.snapshot()
    return snapshot

# Detailed tree with all properties
def get_detailed_accessibility_tree(page):
    return page.evaluate("""() => {
        const tree = {};
        function getA11yProps(el) {
            const computed = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return {
                role: el.getAttribute('role') || el.tagName.toLowerCase(),
                label: el.getAttribute('aria-label') || '',
                description: el.getAttribute('aria-description') || '',
                expanded: el.getAttribute('aria-expanded'),
                hidden: el.getAttribute('aria-hidden') === 'true',
                disabled: el.getAttribute('aria-disabled') === 'true',
                checked: el.getAttribute('aria-checked'),
                selected: el.getAttribute('aria-selected'),
                pressed: el.getAttribute('aria-pressed'),
                level: el.getAttribute('aria-level'),
                posinset: el.getAttribute('aria-posinset'),
                setsize: el.getAttribute('aria-setsize'),
                tabindex: el.getAttribute('tabindex'),
                text: el.textContent?.trim()?.substring(0, 100) || '',
                alt: el.getAttribute('alt') || '',
                title: el.getAttribute('title') || '',
                visible: el.offsetParent !== null,
                fontSize: computed.fontSize,
                color: computed.color,
                backgroundColor: computed.backgroundColor,
                contrast_ratio: null,  // would need external calc
                rect: {
                    x: rect.x, y: rect.y, width: rect.width, height: rect.height
                },
                tabStop: el.getAttribute('tabindex') !== '-1'
            };
        }

        function walk(element, depth=0) {
            const a11y = getA11yProps(element);
            const children = [];
            for (let child of element.children) {
                const childData = walk(child, depth+1);
                if (childData) children.push(childData);
            }
            if (children.length > 0) a11y.children = children;
            return a11y;
        }

        return walk(document.body);
    }""")
```

### CDP Accessibility

```python
# Selenium via CDP
def get_accessibility_cdp(driver):
    return driver.execute_cdp_cmd("Accessibility.getFullAXTree", {})

# Parse for structured data
def parse_accessibility_tree(ax_tree):
    nodes = {}
    for node in ax_tree["nodes"]:
        node_id = node["nodeId"]
        properties = {}
        for prop in node.get("properties", []):
            properties[prop["name"]] = prop["value"]["value"] if "value" in prop else None
        nodes[node_id] = {
            "role": node.get("role", {}).get("value", "unknown"),
            "name": properties.get("name", ""),
            "description": properties.get("description", ""),
            "value": properties.get("value", ""),
            "child_ids": node.get("childIds", []),
            "backend_dom_node_id": node.get("backendDOMNodeId")
        }
    return nodes

# Build hierarchy
def build_a11y_hierarchy(nodes, root_id):
    def build(node_id, depth=0):
        node = nodes[node_id]
        prefix = "  " * depth
        result = f"{prefix}{node['role']}: {node['name']}"
        for child_id in node["child_ids"]:
            if child_id in nodes:
                result += "\n" + build(child_id, depth + 1)
        return result
    return build(root_id)
```

### Accessibility Audit (axe-core)

```python
# Run axe-core audit
def run_axe_audit(page):
    # Inject axe-core
    axe_js = """
    // Load axe.min.js content here or from CDN
    """
    page.evaluate(axe_js)

    results = page.evaluate("""() => {
        return new Promise((resolve) => {
            axe.run({
                runOnly: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
            }, (err, results) => {
                if (err) resolve({error: err.message});
                resolve({
                    violations: results.violations.map(v => ({
                        id: v.id,
                        impact: v.impact,
                        description: v.description,
                        help: v.help,
                        helpUrl: v.helpUrl,
                        tags: v.tags,
                        nodes: v.nodes.map(n => ({
                            target: n.target,
                            html: n.html,
                            failureSummary: n.failureSummary
                        }))
                    })),
                    passes: results.passes.length,
                    incomplete: results.incomplete.length
                });
            });
        });
    }""")
    return results
```

### Tab Order Analysis

```python
def analyze_tab_order(page):
    return page.evaluate("""() => {
        const focusable = document.querySelectorAll(
            'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const order = [];
        focusable.forEach((el, i) => {
            const rect = el.getBoundingClientRect();
            order.push({
                index: i,
                tag: el.tagName,
                text: el.textContent?.trim()?.substring(0, 50) || '',
                tabindex: parseInt(el.getAttribute('tabindex')) || 0,
                visible: el.offsetParent !== null,
                rect: {
                    top: rect.top, left: rect.left,
                    bottom: rect.bottom, right: rect.right
                },
                id: el.id,
                classes: el.className
            });
        });
        // Sort by tabindex then DOM order
        order.sort((a, b) => {
            if (a.tabindex !== b.tabindex) return a.tabindex - b.tabindex;
            return a.index - b.index;
        });
        return order;
    }""")
```

---

## Performance Metrics

### Core Web Vitals

```python
def measure_core_web_vitals(page):
    page.goto("https://example.com", wait_until="networkidle")

    metrics = page.evaluate("""() => {
        return new Promise((resolve) => {
            const results = {};

            // First Paint
            const paintEntries = performance.getEntriesByType('paint');
            results.firstPaint = paintEntries
                .find(e => e.name === 'first-paint')?.startTime || null;
            results.firstContentfulPaint = paintEntries
                .find(e => e.name === 'first-contentful-paint')?.startTime || null;

            // LCP
            new PerformanceObserver((list) => {
                const entries = list.getEntries();
                results.largestContentfulPaint = entries[entries.length - 1]?.startTime;
                results.largestContentfulPaintElement = entries[entries.length - 1]?.element?.tagName || '';
            }).observe({type: 'largest-contentful-paint', buffered: true});

            // FID — interactivity
            results.firstInputDelay = new Promise((resolveFID) => {
                new PerformanceObserver((list) => {
                    list.getEntries().forEach(entry => {
                        resolveFID(entry.processingStart - entry.startTime);
                    });
                }).observe({type: 'first-input', buffered: true});
                setTimeout(() => resolveFID(null), 10000);
            });

            // CLS
            let cumulativeLayoutShift = 0;
            new PerformanceObserver((list) => {
                list.getEntries().forEach(entry => {
                    if (!entry.hadRecentInput) {
                        cumulativeLayoutShift += entry.value;
                    }
                });
                results.cumulativeLayoutShift = cumulativeLayoutShift;
            }).observe({type: 'layout-shift', buffered: true});

            // TTFB
            const nav = performance.getEntriesByType('navigation')[0];
            results.timeToFirstByte = nav ? nav.responseStart - nav.requestStart : null;

            // DOM metrics
            results.domContentLoaded = nav ? nav.domContentLoadedEventEnd : null;
            results.domComplete = nav ? nav.domComplete : null;
            results.totalDOMNodes = document.querySelectorAll('*').length;
            results.totalScripts = document.querySelectorAll('script').length;
            results.totalImages = document.querySelectorAll('img').length;
            results.totalCSS = document.querySelectorAll('link[rel="stylesheet"]').length;

            setTimeout(() => resolve(results), 3000);
        });
    }""")

    return metrics
```

### Lighthouse Integration

```python
import subprocess
import json

def run_lighthouse(url, output_path="lighthouse-report.json"):
    result = subprocess.run([
        "lighthouse", url,
        "--output=json",
        "--output-path=" + output_path,
        "--chrome-flags=--headless --no-sandbox"
    ], capture_output=True, text=True)

    with open(output_path) as f:
        report = json.load(f)

    categories = report["categories"]
    audit_refs = report["categoryGroups"]

    return {
        "performance": categories.get("performance", {}).get("score", 0),
        "accessibility": categories.get("accessibility", {}).get("score", 0),
        "best_practices": categories.get("best-practices", {}).get("score", 0),
        "seo": categories.get("seo", {}).get("score", 0),
        "pwa": categories.get("pwa", {}).get("score", 0),
    }
```

### Chrome Tracing

```python
# Capture trace from Playwright
def capture_trace(page, output_path="trace.json"):
    context = page.context
    context.tracing.start(
        screenshots=True,
        snapshots=True,
        sources=True
    )

    page.goto("https://example.com")
    page.click(".some-button")

    context.tracing.stop(path=output_path)

# Analyze trace
def analyze_trace(trace_path):
    import zipfile
    import json

    with zipfile.ZipFile(trace_path) as z:
        with z.open("trace.json") as f:
            trace = json.load(f)

    events = trace.get("traceEvents", [])

    # Parse events
    durations = {}
    for event in events:
        if event.get("ph") == "X":  # Complete event
            name = event.get("name", "unknown")
            dur = event.get("dur", 0)
            if name not in durations:
                durations[name] = []
            durations[name].append(dur)

    # Average durations
    averages = {k: sum(v)/len(v) for k, v in durations.items() if len(v) > 0}
    return sorted(averages.items(), key=lambda x: x[1], reverse=True)[:20]
```

---

## Best Practices & Anti-Detection

### Resource Management

```python
# Set timeouts
page.set_default_timeout(30000)  # 30 seconds

# Context-level timeouts
page.set_default_navigation_timeout(45000)

# Graceful error handling
async def safe_navigate(page, url):
    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
    except TimeoutError:
        print(f"Timeout loading {url}")
    except Exception as e:
        print(f"Error loading {url}: {e}")
    finally:
        # Always try to get current state
        pass
```

### Proxy & Rotation

```python
# Playwright with proxy
browser = await p.chromium.launch(proxy={
    "server": "http://proxy.example.com:8080",
    "username": "user",
    "password": "pass"
})

# Selenium with proxy
options = webdriver.ChromeOptions()
options.add_argument("--proxy-server=http://proxy.example.com:8080")

# Rotating proxies
proxies = [
    "http://proxy1:8080",
    "http://proxy2:8080",
    "http://proxy3:8080",
]
import random

def get_random_proxy():
    return {"server": random.choice(proxies)}
```

### Rate Limiting & Politeness

```python
import asyncio
import random

class PoliteCrawler:
    def __init__(self, min_delay=1.0, max_delay=3.0):
        self.last_request = {}
        self.min_delay = min_delay
        self.max_delay = max_delay

    async def wait_before_request(self, domain):
        if domain in self.last_request:
            elapsed = asyncio.get_event_loop().time() - self.last_request[domain]
            delay = random.uniform(self.min_delay, self.max_delay)
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
        self.last_request[domain] = asyncio.get_event_loop().time()
```

### Human Behavior Simulation

```python
import random

def simulate_human_behavior(page):
    # Random mouse movements
    viewport = page.viewport_size
    for _ in range(random.randint(2, 5)):
        x = random.randint(0, viewport["width"])
        y = random.randint(0, viewport["height"])
        page.mouse.move(x, y, steps=random.randint(5, 20))
        page.wait_for_timeout(random.randint(100, 500))

    # Random scroll
    scroll_amount = random.randint(200, 800)
    page.evaluate(f"window.scrollBy(0, {scroll_amount})")
    page.wait_for_timeout(random.randint(500, 1500))

    # Small random pauses
    page.wait_for_timeout(random.randint(1000, 3000))

# Typing with realistic delays
def human_type(page, selector, text):
    locator = page.locator(selector)
    locator.click()
    page.wait_for_timeout(random.randint(200, 500))
    for char in text:
        locator.press_sequentially(char, delay=random.randint(50, 200))
    page.wait_for_timeout(random.randint(100, 300))
```

### Fingerprint Randomization

```python
def randomize_fingerprint(context):
    context.add_init_script("""
        // Randomize canvas fingerprint
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            const data = originalToDataURL.call(this, type);
            // Add slight noise to fingerprint
            return data.replace(/[a-f0-9]/g, (c) =>
                Math.random() > 0.95
                    ? ((parseInt(c, 16) ^ 1).toString(16))
                    : c
            );
        };

        // Randomize WebGL fingerprint
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(p) {
            if (p === 37445) return randomVendor();
            if (p === 37446) return randomRenderer();
            return getParameter.call(this, p);
        };

        function randomVendor() {
            const vendors = ['Intel Inc.', 'NVIDIA Corporation', 'AMD', 'Apple'];
            return vendors[Math.floor(Math.random() * vendors.length)];
        }

        function randomRenderer() {
            const renderers = [
                'Intel Iris OpenGL Engine',
                'GeForce RTX 3080/PCIe/SSE2',
                'AMD Radeon Pro 5500M',
                'Apple M1'
            ];
            return renderers[Math.floor(Math.random() * renderers.length)];
        }
    """)
```
