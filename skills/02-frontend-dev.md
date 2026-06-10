# Frontend Development — Comprehensive Skill Guide

## Table of Contents
1. HTML Semantic Elements
2. CSS Grid Deep Dive
3. Flexbox Patterns
4. Modern CSS Features
5. JavaScript ES2024+
6. TypeScript Advanced Types
7. React 19 Features
8. Next.js 15 (App Router)
9. Performance Optimization
10. State Management Patterns
11. Build Tools

---

## 1. HTML Semantic Elements

### Document Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Page Title — Site Name</title>
  <meta name="description" content="Concise page description under 160 chars" />
  <link rel="canonical" href="https://example.com/page" />
</head>
<body>
  <header>
    <nav aria-label="Primary">
      <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/about">About</a></li>
      </ul>
    </nav>
  </header>

  <main>
    <article>
      <h1>Primary Page Heading</h1>
      <section aria-labelledby="section-1-title">
        <h2 id="section-1-title">Section Title</h2>
        <p>Content here.</p>
      </section>
    </article>

    <aside>
      <h2>Related Content</h2>
    </aside>
  </main>

  <footer>
    <small>&copy; 2026 Company</small>
  </footer>
</body>
</html>
```

### Semantic Elements Cheat Sheet

| Element | Purpose | SEO Impact |
|---------|---------|------------|
| `<header>` | Introductory content, nav | High (site identity) |
| `<nav>` | Navigation links | High (crawl prioritization) |
| `<main>` | Primary page content (1 per page) | High (core content) |
| `<article>` | Self-contained composition | High (rich snippets) |
| `<section>` | Thematic grouping | Medium |
| `<aside>` | Tangentially related content | Low |
| `<figure>` / `<figcaption>` | Media + caption | Medium (image search) |
| `<mark>` | Highlighted text | None |
| `<time>` | Machine-readable dates | Medium (rich results) |
| `<details>` / `<summary>` | Expandable content | None |

---

## 2. CSS Grid Deep Dive

### Grid Terminology
- **Grid Container** — Element with `display: grid`
- **Grid Item** — Direct children of grid container
- **Grid Line** — Dividing lines (numbered starting from 1)
- **Grid Cell** — Intersection of row and column
- **Grid Area** — Rectangular group of cells
- **Gutter** — Gap between tracks

### Grid Template Patterns

```css
/* Holy Grail Layout */
.holy-grail {
  display: grid;
  grid-template:
    "header header header" auto
    "nav    main   aside" 1fr
    "footer footer footer" auto
    / 250px 1fr 200px;
  min-height: 100vh;
  gap: 1rem;
}

/* Auto-fill responsive grid (no media queries) */
.auto-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1.5rem;
}

/* Explicit placement with named areas */
.layout {
  display: grid;
  grid-template-columns: [full-start] 1fr [content-start] minmax(0, 1200px) [content-end] 1fr [full-end];
  gap: 2rem;
}

.layout > * {
  grid-column: content;
}

.layout .full-width {
  grid-column: full;
}

/* Subgrid (inherits parent grid tracks) */
.card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.card {
  display: grid;
  grid-template-rows: subgrid;
  grid-row: span 3;
}
```

### Alignment Properties

```css
.grid-align {
  display: grid;
  grid-template-columns: repeat(3, 100px);
  grid-template-rows: repeat(3, 100px);

  /* Container alignment */
  justify-content: center;  /* horizontal distribution of tracks */
  align-content: center;    /* vertical distribution of tracks */

  /* Item alignment */
  justify-items: center;    /* horizontal alignment of items in cells */
  align-items: center;      /* vertical alignment of items in cells */
}

.grid-item {
  /* Self alignment (overrides container) */
  justify-self: end;
  align-self: start;
}
```

---

## 3. Flexbox Patterns

### Common Layout Recipes

```css
/* Centered content (both axes) */
.center {
  display: flex;
  justify-content: center;
  align-items: center;
}

/* Sticky footer */
.page-wrapper {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.page-wrapper main {
  flex: 1;
}

/* Equal-height columns */
.equal-height {
  display: flex;
  align-items: stretch;
}

.equal-height > * {
  flex: 1;
}

/* Holy Albatross (intrinsic layout) */
.albatross {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.albatross > * {
  flex: 1 1 300px;
}

/* Navbar with logo + links + CTA */
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
}

.navbar__links {
  display: flex;
  gap: 1.5rem;
}

.navbar__cta {
  margin-left: auto;
}
```

### Flexbox Mental Model

```
Main Axis (flex-direction)
  ├── justify-content: flex-start | flex-end | center | space-between | space-around | space-evenly
  ├── flex-wrap: nowrap | wrap | wrap-reverse
  └── gap: row-gap column-gap

Cross Axis (opposite of main)
  ├── align-items: stretch | flex-start | flex-end | center | baseline
  └── align-content: (multi-line only) flex-start | center | space-between | ...

Item Properties
  ├── flex: [flex-grow] [flex-shrink] [flex-basis]
  ├── align-self: overrides align-items
  └── order: -1 | 0 | 1 (default 0)
```

---

## 4. Modern CSS Features

### Container Queries

```css
.card-container {
  container-type: inline-size;
  container-name: card;
}

@container card (min-width: 400px) {
  .card {
    display: grid;
    grid-template-columns: 200px 1fr;
  }
}

@container card (min-width: 600px) {
  .card {
    grid-template-columns: 1fr 1fr 1fr;
  }
}
```

### Cascade Layers

```css
@layer reset, base, components, utilities;

@layer reset {
  * { margin: 0; padding: 0; box-sizing: border-box; }
}

@layer base {
  body { font-family: system-ui; line-height: 1.5; }
}

@layer components {
  .button { padding: 0.5rem 1rem; border-radius: 6px; }
}

@layer utilities {
  .mt-4 { margin-top: 1rem; }
}

/* Lower specificity, higher priority than unlayered styles */
```

### :has() Selector

```css
/* Style parent based on child state */
.card:has(.button--primary) {
  border-color: blue;
}

/* Style preceding siblings */
.form:has(input:invalid) .submit-button {
  opacity: 0.5;
  pointer-events: none;
}

/* Style grid based on number of items */
.grid:has(> :last-child:nth-child(3)) {
  grid-template-columns: repeat(3, 1fr);
}

/* Dark mode toggle detection */
html:has(#dark-toggle:checked) {
  --color-bg: #1a1a2e;
  --color-text: #e0e0e0;
}
```

### Other Modern Features

```css
/* CSS Nesting */
.card {
  background: white;
  border-radius: 8px;

  & h2 { font-size: 1.25rem; }
  & p { color: #666; }
  & .button { margin-top: 1rem; }

  &:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
}

/* Scroll-driven animations */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.animated-section {
  animation: fade-in linear;
  animation-timeline: view();
  animation-range: entry 0% entry 100%;
}

/* Color mixing */
:root {
  --brand: #2563eb;
  --brand-light: color-mix(in srgb, var(--brand) 20%, white);
}
```

---

## 5. JavaScript ES2024+

### New Features

```javascript
// Array Grouping (ES2024)
const items = [
  { type: 'fruit', name: 'apple' },
  { type: 'veg', name: 'carrot' },
  { type: 'fruit', name: 'banana' },
];

const grouped = Object.groupBy(items, ({ type }) => type);
// { fruit: [{...}, {...}], veg: [{...}] }

// Promise.withResolvers()
const { promise, resolve, reject } = Promise.withResolvers();

// Temporal API (replaces Date)
const now = Temporal.Now.plainDateTimeISO();
const birthday = Temporal.PlainDate.from('2026-05-25');
const duration = Temporal.Duration.from({ days: 30 });

// Records & Tuples (immutable data structures)
const user = #{ name: 'Tom', age: 30 };
const scores = #[98, 92, 85];

// Decorators
function logged(target, context) {
  return function (...args) {
    console.log(`Called ${context.name} with`, args);
    return target.call(this, ...args);
  };
}

class Service {
  @logged
  fetchData(id) {
    return fetch(`/api/${id}`);
  }
}
```

### Modern Async Patterns

```javascript
// Top-level await
const response = await fetch('/api/config');
const config = await response.json();

// AbortController patterns
function fetchWithTimeout(url, ms = 5000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ms);
  return fetch(url, { signal: controller.signal })
    .finally(() => clearTimeout(timeoutId));
}

// Async iterators
async function* paginate(url) {
  let page = 1;
  while (true) {
    const res = await fetch(`${url}?page=${page}`);
    const data = await res.json();
    if (data.items.length === 0) break;
    yield data.items;
    page++;
  }
}

for await (const items of paginate('/api/users')) {
  console.log(items);
}
```

---

## 6. TypeScript Advanced Types

### Utility Types Mastery

```typescript
// Template literal types
type EventName = `on${Capitalize<string>}`;
type CSSValue = `${number}px` | `${number}rem` | `${number}%` | 'auto';

// Conditional types with infer
type UnwrapPromise<T> = T extends Promise<infer U> ? U : T;
type UnwrapArray<T> = T extends Array<infer U> ? U : T;

// Mapped types with key remapping
type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K];
};

type Setters<T> = {
  [K in keyof T as `set${Capitalize<string & K>}`]: (value: T[K]) => void;
};

// Satisfies operator
const palette = {
  red: [255, 0, 0],
  green: '#00ff00',
  blue: [0, 0, 255],
} satisfies Record<string, string | number[]>;

// Branded types for type safety
type Brand<T, B> = T & { __brand: B };
type Email = Brand<string, 'Email'>;
type UserId = Brand<number, 'UserId'>;

function sendEmail(to: Email, body: string) {}
sendEmail('user@example.com' as Email, 'Hello');

// Discriminated unions with never
type Shape =
  | { kind: 'circle'; radius: number }
  | { kind: 'rect'; width: number; height: number }
  | { kind: 'triangle'; base: number; height: number };

function assertNever(x: never): never {
  throw new Error(`Unexpected value: ${x}`);
}

function area(s: Shape) {
  switch (s.kind) {
    case 'circle': return Math.PI * s.radius ** 2;
    case 'rect': return s.width * s.height;
    case 'triangle': return (s.base * s.height) / 2;
    default: return assertNever(s);
  }
}
```

### Advanced Patterns

```typescript
// Builder pattern with types
class QueryBuilder<T extends Record<string, unknown>> {
  private filters: Partial<T> = {};

  where<K extends keyof T>(key: K, value: T[K]): this {
    this.filters[key] = value;
    return this;
  }

  build(): Partial<T> {
    return { ...this.filters };
  }
}

// Function overloads with generics
function createEntity<T extends 'user' | 'post'>(type: T):
  T extends 'user' ? User : Post;

// Type-safe event emitter
type EventMap = {
  userLogin: { userId: string; timestamp: number };
  error: { message: string; code: number };
};

class TypedEmitter<T extends Record<string, unknown>> {
  on<K extends keyof T>(event: K, handler: (data: T[K]) => void): void {}
  emit<K extends keyof T>(event: K, data: T[K]): void {}
}
```

---

## 7. React 19 Features

### Actions & useActionState

```tsx
'use client';

import { useActionState } from 'react';

async function submitForm(prevState: any, formData: FormData) {
  const name = formData.get('name');
  // Server action logic
  return { success: true, message: `Hello ${name}!` };
}

function MyForm() {
  const [state, formAction, isPending] = useActionState(submitForm, null);

  return (
    <form action={formAction}>
      <input name="name" required />
      <button type="submit" disabled={isPending}>
        {isPending ? 'Submitting...' : 'Submit'}
      </button>
      {state?.message && <p>{state.message}</p>}
    </form>
  );
}
```

### use() Hook

```tsx
import { use, Suspense } from 'react';

function Comments({ commentsPromise }) {
  const comments = use(commentsPromise);
  return comments.map(c => <Comment key={c.id} {...c} />);
}

function PostPage({ postId }) {
  const commentsPromise = fetchComments(postId);

  return (
    <Suspense fallback={<Spinner />}>
      <Comments commentsPromise={commentsPromise} />
    </Suspense>
  );
}
```

### Other React 19 Features

```tsx
// Ref as prop (no more forwardRef)
function Input({ ref, ...props }) {
  return <input ref={ref} {...props} />;
}

// useOptimistic for optimistic updates
function LikeButton({ likes }) {
  const [optimisticLikes, addOptimistic] = useOptimistic(likes);

  async function handleLike() {
    addOptimistic(likes + 1);
    await fetch('/api/like', { method: 'POST' });
  }

  return <button onClick={handleLike}>{optimisticLikes} ❤️</button>;
}

// useFormStatus for form context
function SubmitButton() {
  const { pending } = useFormStatus();
  return <button disabled={pending}>{pending ? 'Saving...' : 'Save'}</button>;
}

// useDeferredValue for keeping UI responsive
function SearchPage() {
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);

  return (
    <>
      <input value={query} onChange={e => setQuery(e.target.value)} />
      <Suspense fallback={<Spinner />}>
        <SearchResults query={deferredQuery} />
      </Suspense>
    </>
  );
}
```

---

## 8. Next.js 15 (App Router)

### File Conventions

```
app/
├── layout.tsx           → Root layout (required)
├── page.tsx             → Route: /
├── loading.tsx          → Suspense boundary for route segment
├── error.tsx            → Error boundary (catches errors)
├── not-found.tsx        → 404 for route segment
├── global-error.tsx     → Error in root layout
├── template.tsx         → Re-renders on every navigation
├── default.tsx          → Fallback for parallel routes
│
├── blog/
│   ├── layout.tsx       → Blog-specific layout
│   ├── page.tsx         → Route: /blog
│   └── [slug]/
│       └── page.tsx     → Route: /blog/:slug
│
├── api/
│   └── users/
│       └── route.ts     → Route Handler: /api/users
│
└── (marketing)/
    ├── layout.tsx       → Layout for marketing pages
    ├── about/page.tsx   → Route: /about
    └── contact/page.tsx → Route: /contact
```

### Server Components vs Client Components

```tsx
// Server Component (default) — no hooks, no browser APIs
// blog/[slug]/page.tsx
export default async function BlogPost({ params }) {
  const post = await db.post.findUnique({ where: { slug: params.slug } });

  return (
    <article>
      <h1>{post.title}</h1>
      <div dangerouslySetInnerHTML={{ __html: post.content }} />
    </article>
  );
}

// Client Component — interactive, use browser APIs
'use client';

export function LikeButton({ postId }) {
  const [liked, setLiked] = useState(false);

  return (
    <button onClick={() => setLiked(!liked)}>
      {liked ? '❤️' : '🤍'}
    </button>
  );
}
```

### Data Fetching Patterns

```tsx
// Parallel data fetching
async function Page() {
  const [user, posts, settings] = await Promise.all([
    fetch('/api/user').then(r => r.json()),
    fetch('/api/posts').then(r => r.json()),
    fetch('/api/settings').then(r => r.json()),
  ]);

  return <Dashboard user={user} posts={posts} settings={settings} />;
}

// Streaming with Suspense
function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>
      <Suspense fallback={<Skeleton />}>
        <UserProfile />
      </Suspense>
      <Suspense fallback={<PostsSkeleton />}>
        <PostsList />
      </Suspense>
    </div>
  );
}
```

### Middleware

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('session')?.value;
  const isAuthPage = request.nextUrl.pathname.startsWith('/login');

  if (!token && !isAuthPage) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  if (token && isAuthPage) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next|static|favicon.ico).*)'],
};
```

---

## 9. Performance Optimization

### Core Web Vitals

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| LCP (Largest Contentful Paint) | ≤ 2.5s | 2.5s–4s | > 4s |
| FID (First Input Delay) / INP | ≤ 200ms | 200ms–500ms | > 500ms |
| CLS (Cumulative Layout Shift) | ≤ 0.1 | 0.1–0.25 | > 0.25 |

### Optimization Techniques

```typescript
// Intersection Observer for lazy loading
function useIntersectionObserver(ref, options = {}) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setIsVisible(true); },
      { threshold: 0.1, ...options }
    );

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [ref]);

  return isVisible;
}

// Dynamic imports for code splitting
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <Skeleton />,
  ssr: false,
});

// Image optimization
import Image from 'next/image';

<Image
  src="/hero.webp"
  alt="Hero"
  width={1200}
  height={675}
  priority={isAboveFold}
  loading={isAboveFold ? undefined : 'lazy'}
  sizes="(max-width: 768px) 100vw, 1200px"
/>

// Preload critical resources
<link
  rel="preload"
  href="/fonts/inter-var.woff2"
  as="font"
  type="font/woff2"
  crossOrigin="anonymous"
/>
```

### CSS Performance

```css
/* Use content-visibility for below-fold content */
.lazy-section {
  content-visibility: auto;
  contain-intrinsic-size: 500px; /* reserve space */
}

/* Hardware acceleration */
.gpu-accelerated {
  transform: translateZ(0);
  will-change: transform;
}

/* Avoid layout thrashing — batch reads/writes */
/* Bad */
element.style.width = '100px';
const width = element.offsetWidth;

/* Good */
// Batch writes
element.style.width = '100px';
element.style.height = '200px';
// Batch reads
requestAnimationFrame(() => {
  const width = element.offsetWidth;
});
```

---

## 10. State Management Patterns

### When to Use What

| Pattern | Use Case | Library |
|---------|----------|---------|
| **Context** | Low-frequency updates (theme, auth) | React Context |
| **Zustand** | Medium complexity, simple API | zustand |
| **Jotai** | Atomic state, fine-grained reactivity | jotai |
| **TanStack Query** | Server state, caching, refetching | @tanstack/react-query |
| **XState** | Complex state machines, workflows | xstate |
| **URL State** | Shareable state, navigation | useRouter / nuqs |

### Zustand Example

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface CartState {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (id: string) => void;
  total: () => number;
}

const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      addItem: (item) => set((state) => ({
        items: [...state.items, item],
      })),
      removeItem: (id) => set((state) => ({
        items: state.items.filter(i => i.id !== id),
      })),
      total: () => get().items.reduce((sum, i) => sum + i.price, 0),
    }),
    { name: 'cart-storage' }
  )
);
```

### TanStack Query Patterns

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Query configuration
const usePosts = (page: number) =>
  useQuery({
    queryKey: ['posts', page],
    queryFn: () => fetch(`/api/posts?page=${page}`).then(r => r.json()),
    staleTime: 1000 * 60 * 5, // 5 min cache
    gcTime: 1000 * 60 * 30,   // 30 min garbage collection
    placeholderData: keepPreviousData, // maintain scroll position
    refetchOnWindowFocus: false,
  });

// Optimistic mutation
function useAddPost() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (newPost) => fetch('/api/posts', {
      method: 'POST',
      body: JSON.stringify(newPost),
    }).then(r => r.json()),

    onMutate: async (newPost) => {
      await queryClient.cancelQueries({ queryKey: ['posts'] });
      const previous = queryClient.getQueryData(['posts']);

      queryClient.setQueryData(['posts'], (old: any) => ({
        ...old,
        pages: [{ ...newPost, id: 'temp' }, ...old?.pages?.[0]],
      }));

      return { previous };
    },

    onError: (err, newPost, context) => {
      queryClient.setQueryData(['posts'], context.previous);
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['posts'] });
    },
  });
}
```

---

## 11. Build Tools

### Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    target: 'esnext',
    minify: 'esbuild',
    cssMinify: 'lightningcss',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:3000',
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom'],
  },
});
```

### Webpack 5 Optimization

```javascript
// next.config.js
module.exports = {
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.optimization.splitChunks.cacheGroups = {
        default: false,
        vendors: false,
        framework: {
          chunks: 'all',
          name: 'framework',
          test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
          priority: 40,
        },
        lib: {
          test: /[\\/]node_modules[\\/]/,
          name(module) {
            const match = module.context.match(/[\\/]node_modules[\\/](.*?)([\\/]|$)/);
            return match ? `npm.${match[1].replace('@', '')}` : null;
          },
          priority: 30,
        },
      };
    }
    return config;
  },
};
```

### Turbopack (Next.js)

```typescript
// next.config.ts
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Turbopack is the default in Next.js 15 dev mode
  // Experimental features:
  experimental: {
    turbo: {
      rules: {
        '*.svg': ['@svgr/webpack'],
      },
      resolveAlias: {
        '@': './src',
      },
    },
  },
};

export default nextConfig;
```

---

## Performance Checklist

- [ ] Images use next/image or optimized srcset
- [ ] Fonts use font-display: swap
- [ ] Critical CSS inlined in `<head>`
- [ ] JS bundles split by route/page
- [ ] Third-party scripts loaded async/defer
- [ ] No render-blocking resources above fold
- [ ] Lighthouse score ≥ 90 for all categories
- [ ] Bundle analyzer run at least monthly
- [ ] CDN configured for static assets
- [ ] Brotli/Gzip compression active
- [ ] Service worker registered for offline support
