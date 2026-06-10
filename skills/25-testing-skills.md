# Testing Skills — Comprehensive Guide

## 1. Testing Pyramid

```
         /\           E2E (Cypress, Playwright)
        /  \          Slow, expensive, few tests
       /    \
      /      \        Integration (service-level, API)
     /        \       Moderate speed, medium count
    /          \
   /____________\     Unit (pytest, Jest, vitest)
                      Fast, cheap, many tests
```

| Level | Speed | Scope | Cost | Brittle? |
|---|---|---|---|---|
| Unit | Milliseconds | Single function/class | Cheap | No |
| Integration | Seconds | Module boundaries, DB, network | Medium | Sometimes |
| E2E | Minutes | Full user flows | Expensive | Yes |

### Test Distribution Guideline

- **70%** Unit tests — pure logic, edge cases
- **20%** Integration tests — API, database, service level
- **10%** E2E tests — critical user journeys only

## 2. pytest — Deep Dive

### Installation

```bash
pip install pytest pytest-cov pytest-mock pytest-xdist hypothesis
```

### Basic Structure

```python
# test_calculator.py
import pytest
from calculator import Calculator

# Fixture
@pytest.fixture
def calc():
    return Calculator()

# Basic test
def test_add(calc):
    assert calc.add(2, 3) == 5

# Parametrized test
@pytest.mark.parametrize("a,b,expected", [
    (2, 3, 5),
    (0, 0, 0),
    (-1, 1, 0),
    (1.5, 2.5, 4.0),
])
def test_add_parametrized(calc, a, b, expected):
    assert calc.add(a, b) == expected
```

### Fixture Scopes

```python
import pytest

@pytest.fixture(scope="session")
def db_connection():
    """Set up database connection once per session."""
    conn = create_db_connection()
    yield conn
    conn.close()

@pytest.fixture(scope="module")
def module_data(db_connection):
    """Load common data for all tests in this module."""
    return db_connection.fetch_all("SELECT * FROM test_data")

@pytest.fixture(scope="class")
def class_data():
    """One instance per test class."""
    return {"counter": 0}

@pytest.fixture(scope="function", autouse=True)
def reset_state():
    """Run before every test automatically."""
    clear_database()
    yield
    # teardown happens here
```

### Fixture Factories

```python
import pytest

@pytest.fixture
def make_user():
    """Fixture factory — returns a function that creates users."""
    users_created = []

    def _make_user(name="default", email=None, **kwargs):
        user = User(name=name, email=email or f"{name}@test.com", **kwargs)
        users_created.append(user)
        return user

    yield _make_user

    # Cleanup all users created by this fixture
    for user in users_created:
        user.delete()

def test_user_creation(make_user):
    user = make_user(name="Alice", email="alice@test.com")
    assert user.name == "Alice"

def test_multiple_users(make_user):
    users = [make_user() for _ in range(5)]
    assert len(users) == 5
```

### Mocks with pytest-mock

```python
# test_service.py
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

def test_get_user(mocker):
    """Mock an external API call."""
    # Arrange
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 1, "name": "Alice", "email": "alice@test.com"
    }
    mocker.patch("requests.get", return_value=mock_response)

    # Act
    from services import UserService
    result = UserService().get_user(1)

    # Assert
    assert result.name == "Alice"
    requests.get.assert_called_once_with(
        "https://api.example.com/users/1",
        headers={"Authorization": "Bearer test-token"},
        timeout=10
    )

def test_send_email_failure(mocker):
    """Mock and verify error handling."""
    mock_smtp = mocker.patch("smtplib.SMTP")
    mock_smtp.side_effect = ConnectionError("SMTP server unavailable")

    from services import NotificationService
    with pytest.raises(NotificationError, match="Failed to send email"):
        NotificationService().send_email("test@test.com", "Hello")

def test_database_call(mocker):
    """Mock database cursor."""
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchall.return_value = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]
    mock_conn = mocker.patch("database.get_connection")
    mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor

    result = get_all_users()
    assert len(result) == 2
```

### Monkeypatch

```python
import pytest
import os

def test_env_variable(monkeypatch):
    """Set environment variables without affecting real env."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("API_KEY", "test-key-123")

    assert os.environ["DATABASE_URL"] == "sqlite:///test.db"

def test_monkeypatch_dict(monkeypatch):
    """Patch dict-like objects."""
    monkeypatch.setitem(__builtins__, "input", lambda _: "42")
    assert input("What number?") == "42"

def test_monkeypatch_attribute(monkeypatch):
    """Patch object attributes."""
    monkeypatch.setattr("time.time", lambda: 1234567890.0)
    import time
    assert time.time() == 1234567890.0
```

### Test Organization

```python
# tests/conftest.py — shared fixtures
import pytest
import tempfile
import json

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp

@pytest.fixture
def sample_data():
    return {
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ]
    }

@pytest.fixture
def temp_json_file(temp_dir, sample_data):
    path = f"{temp_dir}/data.json"
    with open(path, "w") as f:
        json.dump(sample_data, f)
    return path
```

```python
# tests/test_api/
#   conftest.py  (fixtures specific to API tests)
#   test_handlers.py
#   test_middleware.py
#
# tests/test_services/
#   test_user_service.py
#   test_order_service.py
#
# tests/test_integration/
#   test_database.py
#   test_redis.py

# Markers for categorization
# pytest.ini:
#   markers =
#       slow: marks tests as slow (deselect with '-m "not slow"')
#       integration: integration tests
#       smoke: critical path tests

import pytest

@pytest.mark.slow
def test_large_dataset():
    ...

@pytest.mark.integration
def test_database_read_write():
    ...

@pytest.mark.smoke
def test_health_check():
    ...
```

### Coverage

```bash
# Run with coverage
pytest --cov=src --cov-report=term-missing --cov-report=html tests/

# Minimum coverage threshold
pytest --cov=src --cov-fail-under=80 tests/

# Combine multiple runs
coverage combine
coverage report
coverage html

# .coveragerc
# [run]
# source = src
# omit = */tests/*, */migrations/*
# [report]
# fail_under = 85
# exclude_lines =
#     pragma: no cover
#     def __repr__
#     raise NotImplementedError
#     if __name__ == .__main__.:
```

### Hypothesis — Property-Based Testing

```python
from hypothesis import given, strategies as st, assume
from hypothesis import HealthCheck, settings

@given(st.integers(), st.integers())
def test_addition_commutative(a, b):
    assert a + b == b + a

@given(st.lists(st.integers()))
def test_sorting_is_idempotent(lst):
    sorted_once = sorted(lst)
    sorted_twice = sorted(sorted_once)
    assert sorted_once == sorted_twice

@given(st.text(min_size=1, max_size=100))
def test_reverse_reverse(s):
    assert s[::-1][::-1] == s

# Custom strategies
email_strategy = st.emails()
username_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('Ll', 'Lu', 'Nd')
    ),
    min_size=3,
    max_size=20
)

@given(email=email_strategy, username=username_strategy)
def test_user_creation(email, username):
    assume(username not in ["admin", "root"])
    user = User(username=username, email=email)
    assert user.is_valid()

# Stateful testing
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

class CounterTest(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.counter = 0

    @rule(value=st.integers(min_value=1, max_value=100))
    def increment(self, value):
        self.counter += value

    @rule(value=st.integers(min_value=1, max_value=100))
    def decrement(self, value):
        self.counter -= value

    @invariant()
    def never_negative(self):
        assume(self.counter >= 0)
        assert self.counter >= 0

TestCounter = CounterTest.TestCase

# Profile slow tests
settings(deadline=500, suppress_health_check=[HealthCheck.too_slow])
```

### Tmp_path & Capsys

```python
def test_file_writing(tmp_path):
    """tmp_path provides a unique temp directory per test."""
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "hello.txt"
    p.write_text("Hello, world!")
    assert p.read_text() == "Hello, world!"
    assert len(list(tmp_path.iterdir())) == 1

def test_capsys(capsys):
    """Capture stdout/stderr."""
    print("Hello", end="")
    captured = capsys.readouterr()
    assert captured.out == "Hello"
    assert captured.err == ""

def test_capfd(capfd):
    """Capture file descriptors (including C-level output)."""
    import os
    os.write(1, b"FD output")
    captured = capfd.readouterr()
    assert captured.out == "FD output"
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_service():
    result = await fetch_data()
    assert result["status"] == "ok"

@pytest.mark.asyncio
async def test_concurrent_requests():
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            fetch_user(session, 1),
            fetch_user(session, 2),
        )
    assert len(results) == 2

@pytest.fixture
async def db_session():
    session = await get_db_session()
    yield session
    await session.close()
```

## 3. Playwright — E2E Testing

### Installation

```bash
npm init playwright@latest
# or
yarn create playwright
pip install pytest-playwright
```

### Basic Test

```typescript
// tests/example.spec.ts
import { test, expect } from '@playwright/test';

test('user can log in', async ({ page }) => {
    await page.goto('https://example.com/login');

    await page.fill('#email', 'user@example.com');
    await page.fill('#password', 'correct-horse-battery-staple');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('.welcome')).toHaveText('Welcome, User!');
});
```

### Locator Strategies

```typescript
// Recommended: use role, text, and test IDs over CSS/XPath

// By role (best — accessible)
page.getByRole('button', { name: 'Submit' })
page.getByRole('link', { name: 'Home' })
page.getByRole('heading', { name: 'Welcome' })
page.getByRole('textbox', { name: 'Email' })
page.getByRole('combobox', { name: 'Country' })
page.getByRole('listitem')

// By text
page.getByText('Hello world')
page.getByText(/welcome/i)

// By test ID
page.getByTestId('submit-button')

// By label
page.getByLabel('Email address')

// By placeholder
page.getByPlaceholder('Enter your email')

// Chaining
page.getByRole('form').getByRole('button', { name: 'Submit' })

// CSS/XPath (fallback only)
page.locator('button.primary')
page.locator('xpath=//button[contains(text(), "Submit")]')
```

### Assertions

```typescript
import { expect } from '@playwright/test';

// Visibility
await expect(page.locator('.status')).toBeVisible();
await expect(page.locator('.hidden')).toBeHidden();
await expect(page.locator('.spinner')).not.toBeVisible();

// Text
await expect(page.locator('.title')).toHaveText('Dashboard');
await expect(page.locator('.items')).toContainText('Item 1');
await expect(page.locator('.input')).toHaveValue('test@test.com');

// Attributes
await expect(page.locator('img')).toHaveAttribute('src', /logo/);
await expect(page.locator('a')).toHaveAttribute('href', '/dashboard');
await expect(page.locator('button')).toBeEnabled();
await expect(page.locator('button')).toBeDisabled();

// Count
await expect(page.locator('.item')).toHaveCount(3);
await expect(page.locator('.item')).not.toHaveCount(0);

// URL
await expect(page).toHaveURL(/\/dashboard/);
await expect(page).toHaveTitle(/My App/);

// CSS
await expect(page.locator('.error')).toHaveCSS('color', 'rgb(255, 0, 0)');
```

### Fixtures & Page Object Model

```typescript
// pages/LoginPage.ts
import type { Page, Locator } from '@playwright/test';

export class LoginPage {
    readonly page: Page;
    readonly emailInput: Locator;
    readonly passwordInput: Locator;
    readonly submitButton: Locator;

    constructor(page: Page) {
        this.page = page;
        this.emailInput = page.getByLabel('Email');
        this.passwordInput = page.getByLabel('Password');
        this.submitButton = page.getByRole('button', { name: 'Sign In' });
    }

    async goto() {
        await this.page.goto('/login');
    }

    async login(email: string, password: string) {
        await this.emailInput.fill(email);
        await this.passwordInput.fill(password);
        await this.submitButton.click();
    }
}
```

```typescript
// fixtures.ts
import { test as base } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { api } from './helpers/api';

type MyFixtures = {
    loginPage: LoginPage;
    dashboardPage: DashboardPage;
    authenticatedPage: Page;
};

export const test = base.extend<MyFixtures>({
    loginPage: async ({ page }, use) => {
        const loginPage = new LoginPage(page);
        await use(loginPage);
    },

    dashboardPage: async ({ page }, use) => {
        await use(new DashboardPage(page));
    },

    authenticatedPage: async ({ browser }, use) => {
        const context = await browser.newContext({
            storageState: 'storageState.json'
        });
        const page = await context.newPage();
        await use(page);
        await context.close();
    },
});

export { expect } from '@playwright/test';
```

```typescript
// tests/login.spec.ts
import { test, expect } from '../fixtures';

test('successful login', async ({ loginPage }) => {
    await loginPage.goto();
    await loginPage.login('admin@test.com', 'password123');
    await expect(loginPage.page).toHaveURL(/\/dashboard/);
});

test('empty email validation', async ({ loginPage }) => {
    await loginPage.goto();
    await loginPage.login('', 'password');
    await expect(loginPage.page.getByText('Email is required')).toBeVisible();
});
```

### Network Interception

```typescript
import { test, expect } from '@playwright/test';

test('mock API response', async ({ page }) => {
    // Mock entire endpoint
    await page.route('**/api/users/**', async route => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                id: 1, name: 'Mocked User', email: 'mock@test.com'
            })
        });
    });

    await page.goto('/profile/1');
    await expect(page.getByText('Mocked User')).toBeVisible();
});

test('intercept and modify response', async ({ page }) => {
    await page.route('**/api/products', async route => {
        const response = await route.fetch();
        const body = await response.json();
        // Add an item
        body.push({ id: 999, name: 'Synthetic Product' });
        await route.fulfill({ response, body: JSON.stringify(body) });
    });
});

test('block analytics', async ({ page }) => {
    await page.route('**/analytics/**', route => route.abort());
    await page.route('**/facebook.net/**', route => route.abort());
    await page.goto('/');
});

test('wait for network idle', async ({ page }) => {
    await page.goto('/search');
    await page.fill('#search', 'playwright');
    // Wait for API response
    const response = await page.waitForResponse('**/api/search**');
    const data = await response.json();
    expect(data.results.length).toBeGreaterThan(0);
});
```

### Visual Regression Testing

```typescript
import { test, expect } from '@playwright/test';

test('homepage visual comparison', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveScreenshot('homepage.png', {
        fullPage: true,
        maxDiffPixelRatio: 0.01,
        threshold: 0.2,
    });
});

test('component visual test', async ({ page }) => {
    await page.goto('/components/button');
    const button = page.getByRole('button', { name: 'Primary' });
    await expect(button).toHaveScreenshot('primary-button.png');

    // Hover state
    await button.hover();
    await expect(button).toHaveScreenshot('primary-button-hover.png');

    // Focus state
    await button.focus();
    await expect(button).toHaveScreenshot('primary-button-focus.png');

    // Disabled state
    await page.getByRole('button', { name: 'Disabled' }).screenshot();
});
```

### Mobile Emulation

```typescript
import { test, expect, devices } from '@playwright/test';

test.use({ ...devices['iPhone 14 Pro'] });

test('mobile viewport test', async ({ page }) => {
    await page.goto('/');
    // Hamburger menu should be visible
    await expect(page.getByTestId('mobile-menu')).toBeVisible();
    await expect(page.getByTestId('desktop-nav')).toBeHidden();
});

test('touch interactions', async ({ page }) => {
    await page.goto('/gallery');
    // Swipe gesture
    await page.touchscreen.swipe(600, 300, 100, 300);
    // Pinch zoom
    await page.touchscreen.pinch(300, 300, 50);
});

test('geolocation', async ({ page, context }) => {
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: 48.8566, longitude: 2.3522 });
    await page.goto('/nearby');
    await expect(page.getByText('Paris')).toBeVisible();
});
```

### Component Testing (Playwright CT)

```typescript
// Button.test.tsx
import { test, expect } from '@playwright/experimental-ct-react';
import Button from './Button';

test('renders with correct label', async ({ mount }) => {
    const component = await mount(<Button label="Click me" />);
    await expect(component).toContainText('Click me');
});

test('calls onClick when clicked', async ({ mount }) => {
    const clicks: string[] = [];
    const component = await mount(
        <Button label="Submit" onClick={() => clicks.push('clicked')} />
    );
    await component.click();
    expect(clicks).toContain('clicked');
});

test('applies disabled state', async ({ mount }) => {
    const component = await mount(<Button label="Disabled" disabled />);
    await expect(component).toBeDisabled();
});
```

### Playwright Config

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './tests',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 4 : undefined,
    reporter: [
        ['html'],
        ['json', { outputFile: 'test-results.json' }],
        ['junit', { outputFile: 'junit.xml' }],
    ],
    use: {
        baseURL: process.env.BASE_URL || 'http://localhost:3000',
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
        video: 'retain-on-failure',
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
        {
            name: 'firefox',
            use: { ...devices['Desktop Firefox'] },
        },
        {
            name: 'webkit',
            use: { ...devices['Desktop Safari'] },
        },
        {
            name: 'mobile-chrome',
            use: { ...devices['Pixel 7'] },
        },
        {
            name: 'mobile-safari',
            use: { ...devices['iPhone 14'] },
        },
    ],
    webServer: {
        command: 'npm run dev',
        url: 'http://localhost:3000',
        reuseExistingServer: !process.env.CI,
    },
});
```

## 4. TDD (Test-Driven Development)

### Red-Green-Refactor Cycle

```
1. RED   — Write a failing test (define expected behavior)
2. GREEN — Write minimal code to make it pass
3. REFACTOR — Clean up code while keeping tests green
```

### TDD Example — FizzBuzz

```python
# Step 1: RED — write the test first
def test_fizzbuzz():
    assert fizzbuzz(1) == "1"
    assert fizzbuzz(3) == "Fizz"
    assert fizzbuzz(5) == "Buzz"
    assert fizzbuzz(15) == "FizzBuzz"
    assert fizzbuzz(7) == "7"

# Step 2: GREEN — minimal implementation
def fizzbuzz(n):
    if n % 15 == 0:
        return "FizzBuzz"
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    return str(n)

# Step 3: REFACTOR (if needed)
def fizzbuzz(n):
    result = ""
    if n % 3 == 0: result += "Fizz"
    if n % 5 == 0: result += "Buzz"
    return result or str(n)
```

### TDD for a Class

```python
# test_shopping_cart.py — RED phase
import pytest
from shopping_cart import ShoppingCart

def test_empty_cart_has_zero_total():
    cart = ShoppingCart()
    assert cart.total == 0

def test_add_item_increases_total():
    cart = ShoppingCart()
    cart.add_item("Apple", 1.50)
    assert cart.total == 1.50

def test_add_multiple_items():
    cart = ShoppingCart()
    cart.add_item("Apple", 1.50)
    cart.add_item("Banana", 0.75)
    assert cart.total == 2.25

def test_cart_contains_item():
    cart = ShoppingCart()
    cart.add_item("Apple", 1.50)
    assert "Apple" in cart

def test_remove_item():
    cart = ShoppingCart()
    cart.add_item("Apple", 1.50)
    cart.add_item("Banana", 0.75)
    cart.remove_item("Apple")
    assert cart.total == 0.75
    assert "Apple" not in cart

def test_clear_cart():
    cart = ShoppingCart()
    cart.add_item("Apple", 1.50)
    cart.clear()
    assert cart.total == 0
    assert len(cart.items) == 0

def test_discount_applied():
    cart = ShoppingCart()
    cart.add_item("Expensive Item", 100.00)
    cart.apply_discount(10)  # 10% off
    assert cart.total == 90.00
```

```python
# shopping_cart.py — GREEN phase
from dataclasses import dataclass, field

@dataclass
class CartItem:
    name: str
    price: float

class ShoppingCart:
    def __init__(self):
        self.items: list[CartItem] = []

    @property
    def total(self) -> float:
        return round(sum(item.price for item in self.items), 2)

    def add_item(self, name: str, price: float) -> None:
        self.items.append(CartItem(name=name, price=price))

    def remove_item(self, name: str) -> None:
        self.items = [item for item in self.items if item.name != name]

    def clear(self) -> None:
        self.items.clear()

    def apply_discount(self, percent: float) -> None:
        factor = (100 - percent) / 100
        for item in self.items:
            item.price = round(item.price * factor, 2)

    def __contains__(self, name: str) -> bool:
        return any(item.name == name for item in self.items)
```

### TDD Best Practices

| Practice | Why |
|---|---|
| One assertion per test (ideally) | Clear failure messages |
| Test behavior, not implementation | Refactoring-safe |
| Avoid testing private methods | Test through public API |
| Descriptive test names | Test name == documentation |
| Arrange-Act-Assert pattern | Consistent structure |
| Tests should be fast | Developer will run them often |
| Never depend on test execution order | Isolation |
| Avoid shared mutable state | Flaky tests |

## 5. Contract Testing with Pact

### Consumer-Driven Contracts

```
Consumer (frontend)                Provider (API)
    |                                  |
    | --- 1. Define expectations ----> |
    | <-- 2. Return mock response --- |
    |                                  |
    | 3. Pact file generated           |
    |                                  |
    | 4. Pact file published to broker |
    |                                  |
    | 5. Broker ---> Pact file ------> |
    |                                  |
    | 6. Verify contract               |
    | <-- 7. Verification result ----- |
```

### Python Pact (Consumer)

```python
# consumer/test_user_client.py
import atexit
from pact import Consumer, Provider

# Create Pact
pact = Consumer('FrontendApp').has_pact_with(
    Provider('UserService'),
    pact_dir='./pacts',
    port=1234,
    host_name='localhost'
)
pact.start_service()
atexit.register(pact.stop_service)

def test_get_user():
    # Define expected interaction
    expected = {
        'id': 1,
        'name': 'Alice',
        'email': 'alice@example.com'
    }

    (pact
     .given('user exists')
     .upon_receiving('a request for user 1')
     .with_request('GET', '/users/1')
     .will_respond_with(200, body=expected))

    # Execute (against mock provider)
    with pact:
        import requests
        result = requests.get('http://localhost:1234/users/1')
        assert result.status_code == 200
        assert result.json() == expected
```

### Pact Provider Verification

```python
# provider/test_provider.py
from pact.verifier import Verifier
import os

def test_verify_user_service():
    verifier = Verifier(provider='UserService',
                        provider_base_url='http://localhost:8080')

    # Read pacts from broker or local
    success, logs = verifier.verify_pacts(
        './pacts/FrontendApp-UserService.json',
        provider_states_setup_url='http://localhost:8080/_pact/provider-states',
        verbose=False,
    )

    assert success == 0, f"Pact verification failed: {logs}"
```

## 6. Performance Testing

### k6 (Load Testing)

```javascript
// k6-script.js
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');
const successfulRequests = new Counter('successful_requests');

export const options = {
    stages: [
        { duration: '2m', target: 100 },  // Ramp up
        { duration: '5m', target: 100 },  // Stay at peak
        { duration: '2m', target: 0 },    // Ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'],  // 95% of requests under 500ms
        http_req_failed: ['rate<0.01'],    // < 1% error rate
        errors: ['rate<0.05'],            // Custom error rate < 5%
    },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';

export default function () {
    group('user API', () => {
        // GET users
        const getUsers = http.get(`${BASE_URL}/api/users`, {
            headers: { 'Content-Type': 'application/json' },
        });

        apiLatency.add(getUsers.timings.duration);
        check(getUsers, {
            'status is 200': (r) => r.status === 200,
            'response time < 200ms': (r) => r.timings.duration < 200,
        }) ? successfulRequests.add(1) : errorRate.add(1);

        sleep(1);

        // POST user
        const payload = JSON.stringify({
            name: `User ${Math.random().toString(36).substring(7)}`,
            email: `test${Date.now()}@test.com`,
        });

        const createUser = http.post(`${BASE_URL}/api/users`, payload, {
            headers: { 'Content-Type': 'application/json' },
        });

        check(createUser, {
            'created status is 201': (r) => r.status === 201,
            'has user id': (r) => JSON.parse(r.body).id !== undefined,
        }) ? successfulRequests.add(1) : errorRate.add(1);

        sleep(1);
    });
}
```

```bash
# Run k6 test
k6 run --vus 50 --duration 60s k6-script.js
k6 run --out json=results.json k6-script.js
k6 run --out influxdb=http://localhost:8086/k6 k6-script.js
```

### Locust

```python
# locustfile.py
from locust import HttpUser, task, between, tag
import json

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)  # Think time between requests

    def on_start(self):
        """Login once per user."""
        self.client.post("/login", {
            "username": "test_user",
            "password": "test_pass"
        })

    @task(3)
    @tag('read')
    def view_products(self):
        with self.client.get(
            "/api/products",
            catch_response=True,
            name="list_products"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")

    @task(2)
    @tag('read')
    def view_product_detail(self):
        product_id = 42
        self.client.get(f"/api/products/{product_id}",
                        name="product_detail")

    @task(1)
    @tag('write')
    def create_order(self):
        self.client.post("/api/orders", json={
            "product_id": 42,
            "quantity": 1,
            "shipping_address": "123 Test St"
        })

    @task(1)
    @tag('search')
    def search_products(self):
        for query in ["shirt", "shoes", "hat"]:
            self.client.get(f"/api/products?search={query}",
                          name="search_products")
            self.wait()
```

```bash
locust -f locustfile.py --host=http://localhost:3000 --headless -u 100 -r 10 --run-time 5m
locust -f locustfile.py --host=http://localhost:3000 --web-host=0.0.0.0 --web-port=8089
```

## 7. Accessibility Testing (axe-core)

### Integration with Playwright

```typescript
// playwright-axe.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('homepage should not have accessibility violations', async ({ page }) => {
    await page.goto('/');

    const results = await new AxeBuilder({ page })
        .include('main')
        .exclude('.advertisement')
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .options({
            runOnly: {
                type: 'tag',
                values: ['wcag2a', 'wcag2aa'],
            },
        })
        .analyze();

    expect(results.violations).toEqual([]);
});

test('check specific rules', async ({ page }) => {
    await page.goto('/login');

    const results = await new AxeBuilder({ page })
        .withRules(['color-contrast', 'label', 'button-name'])
        .analyze();

    for (const violation of results.violations) {
        console.log(`Violation: ${violation.id} — ${violation.description}`);
    }

    expect(results.violations.length).toBeLessThanOrEqual(3);
});
```

### axe-core with pytest

```python
# test_a11y.py
import pytest
from axe_selenium_python import Axe
from selenium import webdriver

@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def test_accessibility(driver):
    driver.get("https://example.com/login")
    axe = Axe(driver)
    axe.inject()

    results = axe.run()
    violations = results["violations"]

    if violations:
        print(f"Found {len(violations)} violations:")
        for v in violations:
            print(f"  - {v['id']}: {v['description']}")

    assert len(violations) == 0, \
        f"Accessibility violations found: {[v['id'] for v in violations]}"
```

### Continuous Accessibility Testing

```yaml
# .github/workflows/a11y.yml
name: Accessibility Tests
on: [push, pull_request]
jobs:
  a11y:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run build
      - run: npx playwright install --with-deps
      - run: npx playwright test --project=chromium --grep @a11y
      - uses: dequelabs/axe-api-report@v3
        if: failure()
```

## 8. Mutation Testing

### What Is Mutation Testing?

Mutants are small changes to your code (e.g., changing `>` to `>=`, flipping a boolean). Mutation testing checks if your test suite catches these changes.

```
Original code:          if (age >= 18)
Mutant 1:               if (age > 18)    # KILLED (test caught it)
Mutant 2:               if (age < 18)    # KILLED
Mutant 3:               if (true)        # SURVIVED (no test caught it!)
```

### Mutmut (Python)

```python
# Install
# pip install mutmut

# Run mutation testing
# mutmut run --paths-to-mutate src/ --tests-dir tests/

# See surviving mutants
# mutmut results

# Show specific mutant
# mutmut show 5
```

```python
# Example target code
def is_adult(age: int) -> bool:
    return age >= 18

def can_drive(age: int, has_license: bool) -> bool:
    return is_adult(age) and has_license

def get_discount(price: float, is_member: bool) -> float:
    if is_member:
        return price * 0.9
    return price
```

```python
# Tests that must catch all mutations
def test_is_adult():
    assert is_adult(18) == True   # Without this, >= could become >
    assert is_adult(17) == False
    assert is_adult(99) == True

def test_can_drive():
    assert can_drive(18, True) == True
    assert can_drive(17, True) == False   # Catches is_adult mutation
    assert can_drive(18, False) == False  # Catches 'and' -> 'or' mutation

def test_get_discount():
    assert get_discount(100, True) == 90.0
    assert get_discount(100, False) == 100.0  # Catches removed 'if' mutation
```

## 9. Test Doubles Reference

| Double | Description | When to Use |
|---|---|---|
| **Dummy** | Passed but never used | Filling parameter lists |
| **Fake** | Working implementation but simplified | In-memory database |
| **Stub** | Returns canned answers | When you need specific return values |
| **Spy** | Records calls made | Verifying side effects |
| **Mock** | Pre-programmed expectations | Behavior verification |

### Python Examples

```python
# Dummy
user_service = UserService(
    email_client=DummyEmailClient(),  # interface but no behavior
    db=DummyDB()
)

# Fake
class FakeDatabase:
    """Simple in-memory dict instead of real DB."""
    def __init__(self):
        self._data = {}
        self._id_counter = 0

    def insert(self, table, record):
        self._id_counter += 1
        record['id'] = self._id_counter
        self._data.setdefault(table, {})[self._id_counter] = record
        return record

    def find(self, table, id):
        return self._data.get(table, {}).get(id)

# Stub
class WeatherStub:
    """Returns fixed weather data regardless of input."""
    def get_forecast(self, city, country):
        return {"temp": 22, "condition": "sunny", "humidity": 45}

# Spy
class EmailSpy:
    """Records all sent emails for later assertion."""
    def __init__(self):
        self.sent_emails = []

    def send(self, to, subject, body):
        self.sent_emails.append({
            'to': to, 'subject': subject, 'body': body
        })

# Mock (using pytest-mock)
def test_notification(mocker):
    mock_email = mocker.patch('services.email_client')
    notification_service.send_welcome_email('alice@test.com')
    mock_email.send.assert_called_once_with(
        'alice@test.com',
        'Welcome!',
        'Thanks for joining'
    )
```

## 10. Testing Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| Testing implementation details | Tests break on refactor | Test observable behavior |
| Excessive mocking | Tests pass, system fails | Prefer real objects, mock boundaries |
| Flaky tests | Random failures | Fix timing, isolation, ordering |
| Slow tests | Developers skip running them | Move to higher pyramid level |
| Tests that don't assert | No value provided | Remove or add assertions |
| DRY in tests | Tests harder to understand | Repeat yourself in tests |
| Testing private methods | Brittle, over-specified | Test through public API |
| Too many assertions per test | Unclear which failed | One logical assertion per test |
| Shared state between tests | Order-dependent failures | Fresh state per test |
| Snapshot everything | Blind approval, subtle bugs | Targeted snapshots for stable UI |
