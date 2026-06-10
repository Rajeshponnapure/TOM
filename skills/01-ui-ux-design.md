# UI/UX Design — Comprehensive Skill Guide

## Table of Contents
1. Color Theory & The 60-30-10 Rule
2. Typography Hierarchy
3. Spacing Systems & 8px Grid
4. Accessibility (WCAG 2.1)
5. Responsive Breakpoints
6. Dark Mode Design
7. Glassmorphism & Neumorphism
8. Design Tokens
9. Atomic Design Methodology
10. F-Pattern & Z-Pattern Layouts
11. Cognitive Load Reduction

---

## 1. Color Theory & The 60-30-10 Rule

The 60-30-10 rule creates visual balance:
- **60%** — Dominant/neutral color (backgrounds, large areas)
- **30%** — Secondary color (headers, navigation, cards)
- **10%** — Accent color (CTAs, links, highlights)

### Color Palette Structure

```css
:root {
  /* Primary (60%) */
  --color-surface: #fafafa;
  --color-background: #ffffff;

  /* Secondary (30%) */
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-text-primary: #1e293b;
  --color-text-secondary: #64748b;

  /* Accent (10%) */
  --color-accent: #f59e0b;
  --color-accent-hover: #d97706;
  --color-danger: #ef4444;
  --color-success: #22c55e;
}
```

### Color Psychology Quick Reference

| Color | Emotion/Association | Common Use Cases |
|-------|-------------------|------------------|
| Blue | Trust, calm, security | Finance, healthcare, tech |
| Red | Urgency, passion, danger | CTAs, errors, sales |
| Green | Growth, health, nature | Finance, environment, success |
| Purple | Luxury, creativity, wisdom | Beauty, spirituality, premium |
| Orange | Energy, enthusiasm, warmth | Fitness, food, entertainment |
| Yellow | Optimism, clarity, caution | Warnings, highlights, children |
| Black | Power, sophistication, prestige | Luxury, fashion, high-end |
| White | Purity, simplicity, cleanliness | Healthcare, minimalism |

### Accessibility-First Color Selection

```css
/* Ensure contrast ratios meet WCAG AA (4.5:1) */
:root {
  --color-text: #1e293b;
  --color-text-on-primary: #ffffff;
  --color-text-on-accent: #1e293b;
  --color-border: #e2e8f0;
}
```

---

## 2. Typography Hierarchy

### Type Scale (Modular Scale 1.25)

```css
:root {
  --text-xs: 0.75rem;    /* 12px */
  --text-sm: 0.875rem;   /* 14px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.125rem;   /* 18px */
  --text-xl: 1.25rem;    /* 20px */
  --text-2xl: 1.5rem;    /* 24px */
  --text-3xl: 1.875rem;  /* 30px */
  --text-4xl: 2.25rem;   /* 36px */
  --text-5xl: 3rem;      /* 48px */
  --text-6xl: 3.75rem;   /* 60px */

  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-serif: 'Merriweather', Georgia, serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  --leading-tight: 1.15;
  --leading-normal: 1.5;
  --leading-relaxed: 1.75;

  --tracking-tight: -0.025em;
  --tracking-normal: 0;
  --tracking-wide: 0.05em;
}
```

### Hierarchy Patterns

```
HEADING 1 (h1) → 3rem, bold, tracking-tight  ← Single per page
  HEADING 2 (h2) → 1.875rem, semibold
    HEADING 3 (h3) → 1.5rem, semibold
      HEADING 4 (h4) → 1.25rem, medium
        Body → 1rem, regular, leading-relaxed
          Caption → 0.875rem, regular
            Small → 0.75rem, medium
```

### Readability Best Practices
- **Line length**: 45–75 characters per line (ideal: 66)
- **Line height**: 1.5 for body, 1.15–1.3 for headings
- **Body font size**: Minimum 16px on desktop
- **Hierarchy contrast**: At least 2 steps between adjacent levels
- **Weight pairing**: Regular (400) + Bold (700) minimum

---

## 3. Spacing Systems & 8px Grid

### 8px Grid Foundation

```css
:root {
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */
  --space-20: 5rem;     /* 80px */
  --space-24: 6rem;     /* 96px */
}
```

### Spacing Golden Rules

| Context | Rule | Example |
|---------|------|---------|
| Inner padding | Fixed 8px multiples | `padding: var(--space-4) var(--space-6)` |
| Between related items | 1× space unit | `gap: var(--space-4)` |
| Between sections | 4×–6× space unit | `margin-top: var(--space-16)` |
| Between unrelated groups | 8×+ space unit | `margin-top: var(--space-24)` |
| Touch targets | Min 44×44px | `min-height: 44px; min-width: 44px` |

### Layout Examples

```css
/* Card component with 8px grid */
.card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);         /* 12px between children */
  padding: var(--space-6);     /* 24px inner padding */
  border-radius: var(--radius-lg);
}

.card__title {
  font-size: var(--text-xl);
  margin-bottom: var(--space-2);  /* 8px below title */
}

.card__description {
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  color: var(--color-text-secondary);
}

.card__actions {
  display: flex;
  gap: var(--space-3);          /* 12px between buttons */
  margin-top: var(--space-4);   /* 16px above actions */
}
```

---

## 4. Accessibility (WCAG 2.1)

### Color Contrast Requirements

| Level | Normal Text | Large Text (≥18px bold or ≥24px) | UI Components |
|-------|-------------|----------------------------------|---------------|
| AA (minimum) | 4.5:1 | 3:1 | 3:1 |
| AAA (enhanced) | 7:1 | 4.5:1 | N/A |

### Focus Indicators

```css
/* Always visible focus rings */
:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
  border-radius: 4px;
}

/* Custom focus ring for components */
.custom-button:focus-visible {
  box-shadow: 0 0 0 3px var(--color-primary), 0 0 0 5px rgba(37, 99, 235, 0.3);
}
```

### ARIA Best Practices

```html
<!-- Navigation landmark -->
<nav aria-label="Main navigation">
  <ul role="list">
    <li><a href="/" aria-current="page">Home</a></li>
  </ul>
</nav>

<!-- Live region for dynamic content -->
<div aria-live="polite" aria-atomic="true">
  <!-- Dynamic updates announced by screen readers -->
</div>

<!-- Error messaging -->
<input
  type="email"
  aria-describedby="email-error"
  aria-invalid="true"
  required
/>
<span id="email-error" role="alert">Please enter a valid email address</span>
```

### Keyboard Navigation

```css
/* Skip to main content */
.skip-link {
  position: absolute;
  top: -100%;
  left: 0;
  z-index: 9999;
  padding: var(--space-3) var(--space-4);
  background: var(--color-primary);
  color: white;
}

.skip-link:focus {
  top: 0;
}
```

### Accessibility Checklist

- [ ] All images have descriptive `alt` text
- [ ] Forms have proper `<label>` elements
- [ ] Color not the sole indicator of meaning
- [ ] Touch targets ≥ 44×44px
- [ ] All functionality available via keyboard
- [ ] Page title is descriptive
- [ ] Heading hierarchy is logical (no jumps)
- [ ] ARIA landmarks used appropriately
- [ ] Focus order matches visual order
- [ ] Reduced motion query respected

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 5. Responsive Breakpoints

### Standard Breakpoint System

```css
:root {
  /* Fluid type scaling */
  --fluid-min: 16px;
  --fluid-max: 21px;
}

/* Mobile-first approach */
/* Base styles = mobile (< 640px) */

/* Tablet (≥ 640px) */
@media (min-width: 640px) {
  /* sm breakpoint */
}

/* Tablet landscape (≥ 768px) */
@media (min-width: 768px) {
  /* md breakpoint */
}

/* Desktop (≥ 1024px) */
@media (min-width: 1024px) {
  /* lg breakpoint */
}

/* Large desktop (≥ 1280px) */
@media (min-width: 1280px) {
  /* xl breakpoint */
}

/* Extra large (≥ 1536px) */
@media (min-width: 1536px) {
  /* 2xl breakpoint */
}
```

### Container Queries (Modern Approach)

```css
/* Define containment context */
.card-grid {
  container-type: inline-size;
  container-name: card-grid;
}

/* Query the container's width */
@container card-grid (min-width: 400px) {
  .card {
    display: grid;
    grid-template-columns: 200px 1fr;
  }
}

@container card-grid (min-width: 600px) {
  .card {
    grid-template-columns: 1fr 1fr;
  }
}
```

### Fluid Typography with `clamp()`

```css
:root {
  --text-fluid-lg: clamp(1.5rem, 1rem + 2vw, 3rem);
  --text-fluid-xl: clamp(2rem, 1.5rem + 3vw, 4.5rem);
  --text-fluid-sm: clamp(0.875rem, 0.75rem + 0.5vw, 1rem);
}

/* Usage */
.hero-title {
  font-size: var(--text-fluid-xl);
  line-height: 1.1;
}
```

---

## 6. Dark Mode Design

### CSS Strategy

```css
/* Light mode (default) */
:root {
  --color-bg: #ffffff;
  --color-bg-secondary: #f8fafc;
  --color-bg-tertiary: #f1f5f9;
  --color-text: #0f172a;
  --color-text-secondary: #475569;
  --color-border: #e2e8f0;
  --color-surface: #ffffff;
  --color-surface-hover: #f8fafc;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.07);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
}

/* Dark mode */
[data-theme="dark"] {
  --color-bg: #0f172a;
  --color-bg-secondary: #1e293b;
  --color-bg-tertiary: #334155;
  --color-text: #f8fafc;
  --color-text-secondary: #94a3b8;
  --color-border: #334155;
  --color-surface: #1e293b;
  --color-surface-hover: #334155;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);
}
```

### Dark Mode Best Practices
- **Avoid pure black (#000)** — use very dark gray (#0f172a)
- **Reduce shadow opacity** — increase it since dark backgrounds don't cast visible shadows
- **Lower color saturation** — oversaturated colors on dark backgrounds cause eye strain
- **Increase contrast on surfaces** — surface colors must be distinguishable from background
- **Images need treatment** — reduce brightness/opacity on images in dark mode

```css
[data-theme="dark"] img {
  filter: brightness(0.8) contrast(1.2);
}

[data-theme="dark"] .card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}
```

### System Preference Detection

```javascript
// Toggle with system preference
const darkModeMedia = window.matchMedia('(prefers-color-scheme: dark)');

darkModeMedia.addEventListener('change', (e) => {
  document.documentElement.setAttribute(
    'data-theme',
    e.matches ? 'dark' : 'light'
  );
});
```

---

## 7. Glassmorphism & Neumorphism

### Glassmorphism

```css
.glass {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

/* Dark mode glass */
[data-theme="dark"] .glass {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
```

**Guidelines:**
- Use on dark/gradient backgrounds for best effect
- Keep text legible — ensure contrast against any background
- Add `background-blur` fallback for Firefox
- Use sparingly — too much glass reduces hierarchy

### Neumorphism (Soft UI)

```css
.neumorphic {
  background: var(--color-bg);
  border-radius: 16px;
  box-shadow:
    8px 8px 16px rgba(0, 0, 0, 0.08),
    -8px -8px 16px rgba(255, 255, 255, 0.7);
}

.neumorphic--pressed {
  box-shadow:
    inset 4px 4px 8px rgba(0, 0, 0, 0.08),
    inset -4px -4px 8px rgba(255, 255, 255, 0.7);
}
```

**Guidelines:**
- Only works with subtle, muted backgrounds
- Poor accessibility — low contrast by nature
- Best for decorative elements, not critical UI
- Not suitable for dark mode without significant adjustment

---

## 8. Design Tokens

### Token Structure

```typescript
// Design Token System
interface DesignTokens {
  color: {
    primary: string;
    primaryHover: string;
    surface: string;
    text: string;
    textSecondary: string;
    border: string;
    danger: string;
    success: string;
    warning: string;
  };
  spacing: {
    xs: string; sm: string; md: string;
    lg: string; xl: string; xxl: string;
  };
  typography: {
    fontFamily: { sans: string; serif: string; mono: string };
    fontSize: Record<string, string>;
    fontWeight: { regular: number; medium: number; bold: number };
    lineHeight: Record<string, number>;
  };
  radius: {
    sm: string; md: string; lg: string; full: string;
  };
  shadow: {
    sm: string; md: string; lg: string;
  };
  animation: {
    duration: { fast: string; normal: string; slow: string };
    easing: { ease: string; bounce: string; spring: string };
  };
}
```

### CSS Variables from Tokens

```css
:root {
  /* Colors */
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-primary-light: #dbeafe;
  --color-surface: #ffffff;
  --color-surface-secondary: #f8fafc;
  --color-text: #0f172a;
  --color-text-secondary: #475569;
  --color-text-tertiary: #94a3b8;
  --color-border: #e2e8f0;
  --color-border-hover: #cbd5e1;
  --color-danger: #ef4444;
  --color-success: #22c55e;
  --color-warning: #f59e0b;

  /* Spacing */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2rem;
  --space-2xl: 3rem;
  --space-3xl: 4rem;

  /* Border radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07);
  --shadow-lg: 0 10px 25px rgba(0,0,0,0.1);

  /* Animation */
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 350ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* Semantic tokens built from primitive tokens */
:root {
  --color-link: var(--color-primary);
  --color-link-hover: var(--color-primary-hover);
  --color-btn-primary-bg: var(--color-primary);
  --color-btn-primary-text: #ffffff;
  --color-btn-primary-hover: var(--color-primary-hover);
  --color-input-bg: var(--color-surface);
  --color-input-border: var(--color-border);
  --color-input-focus: var(--color-primary);
}
```

### Token Organization (Platform-Agnostic)

```yaml
# tokens.yaml - Single source of truth
global:
  color:
    blue-500: { value: "#2563eb" }
    blue-700: { value: "#1d4ed8" }
    gray-50: { value: "#f8fafc" }
    gray-900: { value: "#0f172a" }
  spacing:
    4: { value: "1rem" }
    6: { value: "1.5rem" }
  radius:
    md: { value: "8px" }

# Transformed by Style Dictionary to CSS/JSON/Swift/Kotlin
# Output: variables.css, tokens.json, Colors.swift, Colors.kt
```

---

## 9. Atomic Design Methodology

### The 5 Levels

```
atoms/        → Basic HTML elements (buttons, inputs, labels)
  molecules/   → Groups of atoms (search form, card header)
    organisms/ → Complex sections (header, sidebar, product grid)
      templates/ → Page-level wireframes (layout without content)
        pages/  → Specific instances (Home Page, Product Page)
```

### File Structure

```
src/components/
├── atoms/
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.css
│   │   └── Button.test.tsx
│   ├── Input/
│   ├── Label/
│   ├── Icon/
│   └── Typography/
├── molecules/
│   ├── SearchForm/
│   ├── CardPreview/
│   ├── NavigationItem/
│   └── FormField/
├── organisms/
│   ├── Header/
│   ├── ProductGrid/
│   ├── Sidebar/
│   └── Footer/
├── templates/
│   ├── DefaultLayout/
│   └── MarketingLayout/
└── pages/
    ├── HomePage/
    ├── ProductPage/
    └── AboutPage/
```

### Component Example (Atom → Molecule → Organism)

```tsx
// Atom — Button
function Button({ variant = 'primary', children, ...props }) {
  return (
    <button className={`btn btn--${variant}`} {...props}>
      {children}
    </button>
  );
}

// Molecule — SearchForm
function SearchForm({ onSearch }) {
  return (
    <form className="search-form" onSubmit={onSearch}>
      <Input placeholder="Search..." name="q" />
      <Button type="submit" variant="primary">Search</Button>
    </form>
  );
}

// Organism — Header
function Header() {
  return (
    <header className="header">
      <Logo />
      <Navigation items={navItems} />
      <SearchForm onSearch={handleSearch} />
      <UserMenu user={currentUser} />
    </header>
  );
}
```

---

## 10. F-Pattern & Z-Pattern Layouts

### F-Pattern (Content-Heavy Pages)

```
Line 1: [KEYWORD] — — — — — — — — — [SCAN STOPS]  ← Users read first words
Line 2: [keyword] — — — — — —        ← Less reading
Line 3: [keyword] — —                 ← Even less
Line 4: [keyword]                     ← Minimal
```

**Best for:** Blogs, documentation, search results, news articles

**Design Principles:**
- Place most important info in top-left
- Use bold/color for first 2–3 words of paragraphs
- Short paragraphs (2–3 sentences max)
- Subheaders every 3–4 paragraphs
- Bullet points break the F-pattern for better scanning

### Z-Pattern (Visual/Simplified Pages)

```
Top-Left (Start) → → → Top-Right (Primary CTA)
     ↓                                        ↓
Bottom-Left (Secondary) ← ← ← Bottom-Right (Final CTA)
```

**Best for:** Landing pages, splash screens, marketing sites

**Design Principles:**
- Logo in top-left, nav/actions in top-right
- Center area has the core message/image
- Bottom-left for secondary info, bottom-right for primary CTA
- Each corner should have visual weight
- Scanning path should be clear and unobstructed

### Hybrid Pattern

```css
/* Alternating sections on landing pages */
.section--left-image {
  display: grid;
  grid-template-columns: 1fr 1fr;
  /* Image left, text right — supports Z-pattern flow */
}

.section--right-image {
  display: grid;
  grid-template-columns: 1fr 1fr;
  /* Text left, image right — breaks monotony */
}
```

---

## 11. Cognitive Load Reduction

### Key Principles

| Principle | Application |
|-----------|-------------|
| **Hick's Law** | Fewer choices = faster decisions (limit nav to 5–7 items) |
| **Miller's Law** | Chunk information (7±2 items per group) |
| **Jakob's Law** | Leverage familiar patterns (don't reinvent the wheel) |
| **Law of Proximity** | Group related items together |
| **Law of Similarity** | Similar elements = similar function |
| **Tesler's Law** | Some complexity is essential; keep it in the system |
| **Doherty Threshold** | Respond in < 400ms for flow state |
| **Fitts' Law** | Larger + closer targets = faster interaction |

### Progressive Disclosure

```html
<!-- Show basics first, reveal complexity on demand -->
<details class="advanced-settings">
  <summary>Advanced Settings</summary>
  <div class="settings-panel">
    <!-- Hidden until toggled -->
  </div>
</details>
```

### Form Design for Reduced Load

```css
/* Single-column forms reduce cognitive load */
.form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 400px;
}

/* Group related fields */
.form fieldset {
  border: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.form fieldset legend {
  font-weight: 600;
  margin-bottom: var(--space-2);
}
```

### Visual Hierarchy Principles

1. **Size** — Most important elements are largest
2. **Color** — Bright colors draw attention first
3. **Contrast** — High contrast = high importance
4. **Whitespace** — More space around = more important
5. **Position** — Top-left = primary attention zone
6. **Proximity** — Related things close together

### Loading & Feedback

```css
/* Immediate feedback for every action */
.button:active {
  transform: scale(0.97);
}

/* Optimistic UI updates */
.optimistic-update {
  transition: opacity var(--duration-fast) var(--ease-out);
}

.optimistic-update.syncing {
  opacity: 0.7;
}
```

### Reducing Cognitive Load Checklist

- [ ] Limit navigation items to 5–7
- [ ] Use familiar icons with labels
- [ ] Break long forms into steps (wizard pattern)
- [ ] Show password requirements before submission
- [ ] Use default values where appropriate
- [ ] Provide inline validation (not just on submit)
- [ ] Chunk related information into cards/sections
- [ ] Use progressive disclosure for advanced features
- [ ] Maintain consistent layout across pages
- [ ] Keep CTAs visually prominent and singular per viewport

---

## References & Tools

- **Contrast checker**: WebAIM Contrast Checker
- **Design token tool**: Style Dictionary (Amazon)
- **Accessibility audit**: axe DevTools, Lighthouse
- **Color palette gen**: Coolors, Adobe Color
- **Type scale**: Typescale.com
- **Design system inspo**: Dribbble, Mobbin, Design Systems Repo
- **Spacing calculator**: 8px grid generators
- **Figma plugins**: Design Tokens, Stark, Contrast
