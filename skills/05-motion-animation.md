# Motion Design — Comprehensive Skill Guide

## Table of Contents
1. GSAP (GreenSock Animation Platform)
2. Framer Motion
3. CSS Animations
4. Lottie / Bodymovin
5. Rive Interactive Animations
6. Spring Physics
7. Easing Functions
8. FLIP Animations
9. Shared Element Transitions
10. Page Transitions
11. Micro-Interactions
12. Loading Animations
13. Skeleton Screens
14. Principles of Motion

---

## 1. GSAP (GreenSock Animation Platform)

### Core Usage

```javascript
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { MotionPathPlugin } from 'gsap/MotionPathPlugin';
import { TextPlugin } from 'gsap/TextPlugin';

gsap.registerPlugin(ScrollTrigger, MotionPathPlugin, TextPlugin);

// Basic tween
gsap.to('.element', {
  x: 200,
  y: 100,
  rotation: 45,
  scale: 1.5,
  opacity: 0.8,
  duration: 1,
  delay: 0.5,
  ease: 'power3.out',
  onComplete: () => console.log('Done!'),
});

// From state
gsap.from('.element', {
  opacity: 0,
  y: 50,
  duration: 0.8,
  stagger: 0.2,
});

// FromTo (explicit start and end)
gsap.fromTo('.element',
  { opacity: 0, x: -100, scale: 0.8 },
  { opacity: 1, x: 0, scale: 1, duration: 1, ease: 'back.out(1.7)' }
);

// Set (immediate, no animation)
gsap.set('.element', { opacity: 0, x: 50 });
```

### Timelines

```javascript
// Master timeline for complex sequences
const tl = gsap.timeline({
  defaults: { duration: 0.6, ease: 'power2.out' },
  onComplete: () => console.log('Sequence finished'),
  paused: true, // Don't auto-play
});

tl.from('.hero-title', { y: 60, opacity: 0 })
  .from('.hero-subtitle', { y: 30, opacity: 0 }, '-=0.3')
  .from('.hero-cta', { y: 20, opacity: 0 }, '-=0.2')
  .from('.hero-image', { scale: 0.8, opacity: 0 }, '-=0.3')
  .to('.hero-content', { '--progress': '100%' }, 0);

// Control methods
tl.play();
tl.pause();
tl.reverse();
tl.seek(1.5);
tl.timeScale(2); // Double speed
tl.progress(0.5); // Jump to 50%
```

### Stagger Patterns

```javascript
// Grid stagger
gsap.from('.grid-item', {
  scale: 0,
  opacity: 0,
  duration: 0.5,
  stagger: {
    grid: [4, 3],     // 4 columns, 3 rows
    from: 'center',   // 'start', 'end', 'edges', 'random'
    ease: 'power2.out',
    amount: 1.5,      // Total stagger time
  },
});

// Sequential stagger
gsap.from('.list-item', {
  x: -50,
  opacity: 0,
  duration: 0.4,
  stagger: 0.08,     // 80ms between each
});

// With easing on stagger itself
gsap.from('.cards', {
  y: 30,
  opacity: 0,
  stagger: {
    each: 0.1,
    from: 'end',
    ease: 'power1.in',
  },
});
```

### ScrollTrigger

```javascript
// Basic scroll trigger
gsap.to('.parallax-section', {
  yPercent: -30,
  ease: 'none',
  scrollTrigger: {
    trigger: '.parallax-section',
    start: 'top bottom',    // When trigger top hits viewport bottom
    end: 'bottom top',      // When trigger bottom hits viewport top
    scrub: 1,               // Link animation to scroll position (1s lag)
    markers: true,          // Debug markers (remove in production)
    toggleActions: 'play none none reverse',
    onEnter: () => console.log('Entered'),
    onLeave: () => console.log('Left'),
  },
});

// Pin an element
ScrollTrigger.create({
  trigger: '.pin-section',
  start: 'top top',
  end: 'bottom top',
  pin: true,
  pinSpacing: true,
  scrub: 1,
});

// Horizontal scroll
const sections = gsap.utils.toArray('.horizontal-section');
gsap.to(sections, {
  xPercent: -100 * (sections.length - 1),
  ease: 'none',
  scrollTrigger: {
    trigger: '.horizontal-container',
    pin: true,
    scrub: 1,
    snap: 1 / (sections.length - 1),
    end: `+=${(sections.length - 1) * 100}%`,
  },
});

// Scroll-based timeline
const tl = gsap.timeline({
  scrollTrigger: {
    trigger: '.container',
    start: 'top top',
    end: '+=200%',
    scrub: 1,
    pin: true,
    anticipatePin: 1,
  },
});

tl.to('.box', { scale: 2, rotation: 180, borderRadius: '50%' })
  .to('.box', { backgroundColor: '#ff6b6b' })
  .to('.box', { x: 300, scale: 1, rotation: 360 });
```

### MotionPath

```javascript
// Animate along an SVG path
gsap.to('.plane', {
  motionPath: {
    path: '#flight-path',
    align: '#flight-path',
    alignOrigin: [0.5, 0.5],
    autoRotate: true,
    start: 0,
    end: 1,
  },
  duration: 5,
  ease: 'power1.inOut',
  scrollTrigger: {
    trigger: '.map-container',
    scrub: 2,
    start: 'top bottom',
    end: 'bottom top',
  },
});

// Custom path as array
gsap.to('.ball', {
  motionPath: {
    path: [
      { x: 100, y: 200 },
      { x: 300, y: 100 },
      { x: 500, y: 300 },
    ],
    curviness: 1,
  },
  duration: 3,
  ease: 'rough',
});
```

---

## 2. Framer Motion

### Layout Animations

```tsx
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';

// Basic variants
const variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
  exit: { opacity: 0, scale: 0.8 },
};

function AnimatedCard({ item }) {
  return (
    <motion.div
      layout // Animate layout changes
      initial="hidden"
      animate="visible"
      exit="exit"
      variants={variants}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      {item.content}
    </motion.div>
  );
}

// Shared layout animations (FLIP)
function ListGrid({ items, layout }) {
  return (
    <LayoutGroup>
      {items.map(item => (
        <motion.div
          key={item.id}
          layout
          layoutId={item.id}
          className={layout === 'grid' ? 'grid-item' : 'list-item'}
        >
          {item.content}
        </motion.div>
      ))}
    </LayoutGroup>
  );
}
```

### AnimatePresence

```tsx
function AnimatedList({ items }) {
  return (
    <AnimatePresence mode="wait">
      {items.map(item => (
        <motion.div
          key={item.id}
          initial={{ opacity: 0, x: -20, height: 0 }}
          animate={{ opacity: 1, x: 0, height: 'auto' }}
          exit={{ opacity: 0, x: 20, height: 0 }}
          transition={{
            height: { type: 'spring', stiffness: 500, damping: 30 },
            opacity: { duration: 0.2 },
          }}
          layout
        >
          {item.content}
        </motion.div>
      ))}
    </AnimatePresence>
  );
}

// Route transitions
function AnimatedRoutes() {
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Home />
          </motion.div>
        } />
        <Route path="/about" element={
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
          >
            <About />
          </motion.div>
        } />
      </Routes>
    </AnimatePresence>
  );
}
```

### Gesture Animations

```tsx
// Drag with constraints
<motion.div
  drag="x"
  dragConstraints={{ left: -100, right: 100 }}
  dragElastic={0.2}
  onDragEnd={(event, info) => {
    if (info.offset.x > 100) {
      // Swipe right action
    }
  }}
  whileDrag={{ scale: 1.05 }}
/>

// Scroll-driven animations
function useScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useTransform(scrollYProgress, [0, 1], [0, 1]);
  return scaleX;
}

function ProgressBar() {
  const scaleX = useScrollProgress();

  return (
    <motion.div
      className="progress-bar"
      style={{ scaleX, transformOrigin: 'left' }}
    />
  );
}
```

---

## 3. CSS Animations

### Keyframes

```css
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.8; }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  33% {
    transform: translateY(-10px) rotate(1deg);
  }
  66% {
    transform: translateY(5px) rotate(-1deg);
  }
}

.animated-element {
  animation: fadeInUp 0.6s ease-out 0.2s both;
  /*     name       duration  timing  delay   fill-mode */
}

.pulse-element {
  animation: pulse 2s ease-in-out infinite;
}
```

### animation-timeline (Scroll-Driven)

```css
/* Modern scroll-driven CSS animations */
@keyframes fade-in-scroll {
  from { opacity: 0; transform: translateY(50px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes reveal {
  from {
    clip-path: inset(0 100% 0 0);
  }
  to {
    clip-path: inset(0 0 0 0);
  }
}

.scroll-animate {
  animation: fade-in-scroll linear forwards;
  animation-timeline: view();
  animation-range: entry 0% entry 100%;
}

.reveal-text {
  animation: reveal linear forwards;
  animation-timeline: view();
  animation-range: entry 0% cover 50%;
}

/* Range shorthand */
.animate-enter {
  animation: fade-in-scroll linear;
  animation-timeline: view();
  animation-range: entry 0% cover 50%;
}

.animate-exit {
  animation: fade-in-scroll linear reverse;
  animation-timeline: view();
  animation-range: exit 0% exit 100%;
}
```

### view-timeline

```css
/* Named view timelines for coordination */
.element {
  view-timeline-name: --element-timeline;
  view-timeline-axis: block;
}

.target {
  animation: scale-in linear;
  animation-timeline: --element-timeline;
}
```

---

## 4. Lottie / Bodymovin

### Lottie Integration

```javascript
import Lottie from 'lottie-web';

// Load and play
const animation = Lottie.loadAnimation({
  container: document.getElementById('lottie-container'),
  renderer: 'svg',       // 'svg', 'canvas', 'html'
  loop: true,
  autoplay: true,
  path: '/animations/checkmark.json',
  rendererSettings: {
    progressiveLoad: true,
    hideOnTransparent: true,
  },
});

// Control
animation.play();
animation.pause();
animation.stop();
animation.goToAndStop(30, true); // Frame 30
animation.setSpeed(1.5);
animation.setDirection(-1); // Reverse
animation.playSegments([0, 30], true);

// Event listeners
animation.addEventListener('complete', () => console.log('Done'));
animation.addEventListener('loopComplete', () => console.log('Loop'));
animation.addEventListener('enterFrame', (e) => {
  console.log(`Frame: ${e.currentTime}`);
});

// Lottie for React
import Lottie from 'react-lottie';
import checkAnimation from './checkmark.json';

function CheckAnimation({ isVisible }) {
  return (
    <Lottie
      options={{
        animationData: checkAnimation,
        loop: false,
        autoplay: false,
        rendererSettings: { preserveAspectRatio: 'xMidYMid slice' },
      }}
      isStopped={!isVisible}
      isPaused={!isVisible}
    />
  );
}
```

### Performance Tips for Lottie

- Use `canvas` renderer for complex animations (better performance)
- Keep file size under 500KB per animation
- Convert to dotLottie format for smaller files
- Limit to 30fps for web use
- Use `setSubframe(false)` for smoother performance
- Preload critical animations with `<link rel="preload">`

---

## 5. Rive Interactive Animations

```javascript
import Rive from 'rive-js';

// State machine driven animations
const rive = new Rive({
  src: '/animations/button.riv',
  canvas: document.getElementById('rive-canvas'),
  autoplay: true,
  stateMachines: 'State Machine 1',
  onLoad: () => {
    rive.resizeDrawingSurfaceToCanvas();
  },
});

// Trigger inputs
rive.play('click');
rive.setInputState('State Machine 1', 'hover', true);

// Animation inputs
const inputs = rive.stateMachineInputs('State Machine 1');
const slider = inputs.find(i => i.name === 'progress');
slider.value = 0.75;
```

**Rive vs Lottie:**
| Feature | Rive | Lottie |
|---------|------|--------|
| Interactivity | State machines | Playback only |
| File size | Smaller | Larger |
| Runtime editing | Yes | No |
| Complex rigging | Yes | Limited |
| Web support | Canvas only | SVG/Canvas/HTML |

---

## 6. Spring Physics

### Spring Parameters

```javascript
// Framer Motion spring
const spring = {
  type: 'spring',
  stiffness: 300,    // Higher = snappier
  damping: 25,       // Higher = less bounce
  mass: 1,           // Higher = heavier, slower
  velocity: 0,       // Initial velocity
  restSpeed: 0.01,   // When to consider at rest
  restDelta: 0.01,   // Position precision
};

// GSAP spring-like
gsap.to('.element', {
  x: 100,
  ease: 'elastic.out(1, 0.3)',  // amplitude, period
  duration: 2,
});

// Custom spring (GSAP)
gsap.to('.element', {
  motion: {
    type: 'spring',
    stiffness: 100,
    damping: 15,
    mass: 1,
  },
});
```

### Common Spring Configurations

```javascript
const springs = {
  // Very bouncy
  playful: { stiffness: 150, damping: 8 },
  // Smooth and professional
  smooth: { stiffness: 300, damping: 25 },
  // Heavy and deliberate
  heavy: { stiffness: 500, damping: 35, mass: 2 },
  // Snappy with minimal bounce
  snappy: { stiffness: 800, damping: 50 },
  // Gentle float
  gentle: { stiffness: 100, damping: 15, mass: 0.5 },
};
```

---

## 7. Easing Functions

### Common Easings

```css
:root {
  /* CSS built-in */
  --ease-linear: linear;
  --ease-in: ease-in;
  --ease-out: ease-out;
  --ease-in-out: ease-in-out;

  /* Custom cubic-bezier */
  --ease-smooth: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-snappy: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-expo: cubic-bezier(0.19, 1, 0.22, 1);
  --ease-in-expo: cubic-bezier(0.7, 0, 0.84, 0);
  --ease-anticipate: cubic-bezier(0.36, 0, 0.66, -0.56);
  --ease-decelerate: cubic-bezier(0, 0, 0.2, 1);
  --ease-accelerate: cubic-bezier(0.4, 0, 1, 1);
}
```

### Easing Visual Reference

```
ease-in-out    → [0.42, 0, 0.58, 1]    S-curve, starts slow ends slow
ease-out       → [0, 0, 0.2, 1]        Fast start, slows down
ease-in        → [0.4, 0, 1, 1]        Slow start, speeds up
ease-spring    → [0.34, 1.56, 0.64, 1] Overshoots slightly
ease-snappy    → [0.16, 1, 0.3, 1]     Quick start, gentle end
ease-bouncy    → [0.68, -0.55, 0.27, 1.55]  Exaggerated overshoot
```

### GSAP Easings

```javascript
// Power (strength 1-4)
gsap.to(el, { ease: 'power1.out' });  // Gentle
gsap.to(el, { ease: 'power4.out' });  // Strong

// Exponential
gsap.to(el, { ease: 'expo.out' });    // Very smooth
gsap.to(el, { ease: 'expo.inOut' });  // Dramatic

// Elastic
gsap.to(el, { ease: 'elastic.out(1, 0.3)' });

// Back (anticipate)
gsap.to(el, { ease: 'back.out(2)' });  // Overshoot then settle

// Bounce
gsap.to(el, { ease: 'bounce.out' });

// Rough
gsap.to(el, { ease: 'rough({strength: 1, points: 20})' });

// SlowMo
gsap.to(el, { ease: 'slow(0.7, 0.7)' });
```

---

## 8. FLIP Animations

### The FLIP Technique

```javascript
function flipAnimation(element, callback) {
  // F — First: Record initial position
  const first = element.getBoundingClientRect();

  // Apply state change
  callback();

  // L — Last: Record final position
  const last = element.getBoundingClientRect();

  // I — Invert: Calculate differences
  const dx = first.left - last.left;
  const dy = first.top - last.top;
  const dw = first.width / last.width;
  const dh = first.height / last.height;

  // P — Play: Animate from inverted to final
  gsap.fromTo(element,
    {
      x: dx,
      y: dy,
      scaleX: dw,
      scaleY: dh,
      transformOrigin: 'top left',
    },
    {
      x: 0,
      y: 0,
      scaleX: 1,
      scaleY: 1,
      duration: 0.6,
      ease: 'power3.out',
    }
  );
}

// Usage
document.querySelector('.expand-button').addEventListener('click', () => {
  flipAnimation(card, () => {
    card.classList.toggle('expanded');
  });
});
```

### Framer Motion FLIP (Built-in)

```tsx
// Framer Motion handles FLIP automatically with `layout`
function ExpandingCard({ expanded }) {
  return (
    <motion.div
      layout
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      style={{ width: expanded ? 400 : 200, height: expanded ? 300 : 100 }}
    >
      <motion.img
        src={image}
        layoutId="card-image"
        layout="position"
        transition={{ duration: 0.4 }}
      />
      <motion.h2 layout="position">{title}</motion.h2>
    </motion.div>
  );
}
```

---

## 9. Shared Element Transitions

```tsx
// View Transitions API (modern browsers)
function navigateToDetail(item) {
  const transition = document.startViewTransition(() => {
    // Update DOM to show detail
    showDetail(item);
  });
}

// CSS for view transitions
@keyframes fade-in {
  from { opacity: 0; }
}

@keyframes fade-out {
  to { opacity: 0; }
}

@keyframes slide-from-right {
  from { transform: translateX(30px); }
}

@keyframes slide-to-left {
  to { transform: translateX(-30px); }
}

::view-transition-old(root) {
  animation: fade-out 0.2s ease-out, slide-to-left 0.2s ease-out;
}

::view-transition-new(root) {
  animation: fade-in 0.3s ease-out, slide-from-right 0.3s ease-out;
}

/* Shared element */
::view-transition-old(hero-image),
::view-transition-new(hero-image) {
  animation-duration: 0.4s;
  animation-timing-function: cubic-bezier(0.16, 1, 0.3, 1);
}

.hero-image {
  view-transition-name: hero-image;
  contain: layout;
}
```

---

## 10. Page Transitions

```javascript
// GSAP page transition
function pageTransition(toUrl) {
  const tl = gsap.timeline({
    onComplete: () => {
      window.location.href = toUrl;
    },
  });

  tl.to('.page-transition-overlay', {
    scaleY: 1,
    transformOrigin: 'bottom',
    duration: 0.4,
    ease: 'power3.in',
  })
  .set('.page-content', { opacity: 0 })
  .to('.page-transition-overlay', {
    scaleY: 0,
    transformOrigin: 'top',
    duration: 0.4,
    ease: 'power3.out',
  });
}

// React + Framer Motion page transitions
function PageLayout({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 30,
        duration: 0.4,
      }}
    >
      {children}
    </motion.div>
  );
}
```

---

## 11. Micro-Interactions

### Button Feedback

```css
.button {
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease,
    background-color 0.2s ease;
}

.button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.button:active {
  transform: translateY(0) scale(0.98);
}

/* Loading state */
.button--loading {
  pointer-events: none;
  opacity: 0.8;
}

.button--loading .button__text {
  opacity: 0;
}

.button--loading .button__spinner {
  animation: spin 0.6s linear infinite;
}
```

### Input Feedback

```css
.input-wrapper {
  position: relative;
}

.input-wrapper input {
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.input-wrapper input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.input-wrapper label {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  transition: all 0.2s ease;
  pointer-events: none;
}

.input-wrapper input:focus + label,
.input-wrapper input:not(:placeholder-shown) + label {
  top: -8px;
  left: 12px;
  font-size: 12px;
  color: #2563eb;
  background: white;
  padding: 0 4px;
}
```

### Ripple Effect

```javascript
function createRipple(event) {
  const button = event.currentTarget;
  const circle = document.createElement('span');
  const diameter = Math.max(button.clientWidth, button.clientHeight);
  const radius = diameter / 2;

  circle.style.width = circle.style.height = `${diameter}px`;
  circle.style.left = `${event.clientX - button.offsetLeft - radius}px`;
  circle.style.top = `${event.clientY - button.offsetTop - radius}px`;
  circle.classList.add('ripple');

  // Remove after animation
  button.appendChild(circle);
  setTimeout(() => circle.remove(), 600);
}

// CSS
.ripple {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.4);
  transform: scale(0);
  animation: ripple-animate 0.6s ease-out;
  pointer-events: none;
}

@keyframes ripple-animate {
  to {
    transform: scale(4);
    opacity: 0;
  }
}
```

---

## 12. Loading Animations

```css
/* Spinner */
@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

/* Pulsing dots */
@keyframes dot-pulse {
  0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.loading-dots span {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2563eb;
  animation: dot-pulse 1.4s ease-in-out infinite both;
}

.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }
.loading-dots span:nth-child(3) { animation-delay: 0; }

/* Progress bar */
@keyframes progress-indeterminate {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}

.progress-bar {
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar::after {
  content: '';
  display: block;
  width: 25%;
  height: 100%;
  background: linear-gradient(90deg, transparent, #2563eb, transparent);
  animation: progress-indeterminate 1.5s ease-in-out infinite;
}
```

---

## 13. Skeleton Screens

```css
.skeleton {
  background: linear-gradient(
    90deg,
    #e2e8f0 25%,
    #f1f5f9 50%,
    #e2e8f0 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: 4px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Card skeleton */
.skeleton-card {
  padding: 1rem;
  border-radius: 8px;
  background: white;
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin-bottom: 1rem;
}

.skeleton-title {
  width: 60%;
  height: 16px;
  margin-bottom: 0.5rem;
}

.skeleton-text {
  width: 100%;
  height: 12px;
  margin-bottom: 0.25rem;
}

.skeleton-text--short {
  width: 40%;
}
```

---

## 14. Principles of Motion

### The 12 Principles Applied to UI

| Principle | UI Application |
|-----------|---------------|
| **Anticipation** | Button scales down slightly before moving (prepares user) |
| **Follow-Through** | Dropdown menu items continue slightly past target, then settle |
| **Overshoot** | Card snaps past final position and bounces back |
| **Easing** | Objects don't start/stop instantly; use ease-out |
| **Secondary Action** | Progress bar animates while content loads |
| **Staging** | Elements enter sequentially, guiding focus |
| **Timing** | Fast (150ms) for micro-interactions, slow (400ms) for page transitions |
| **Arcs** | Elements follow natural curved paths, not straight lines |
| **Exaggeration** | Pull-to-refresh stretches past threshold before snapping |
| **Squash & Stretch** | Button compresses on press, expands on release |
| **Appeal** | Smooth, natural-feeling animations vs robotic mechanical motion |
| **Solid Drawing** | 3D elements maintain consistent perspective during rotation |

### Duration Guidelines

| Interaction | Duration | Easing |
|-------------|----------|--------|
| Micro-interaction (hover, tap) | 100–200ms | ease-out |
| Element entering/in-view | 300–500ms | ease-out |
| Element exiting | 200–300ms | ease-in |
| Page transition | 300–500ms | ease-in-out |
| Loading animation | 600–1500ms | linear |
| Complex sequence | 1000–3000ms | varied |
| Background/ambient | 3000ms+ | linear |

### Motion Checklist

- [ ] Duration is appropriate for the interaction type
- [ ] Easing curve is natural, not robotic (avoid `linear`)
- [ ] No motion if `prefers-reduced-motion` is set
- [ ] Stagger delays create clear hierarchy
- [ ] Overlapping motion (not sequential) feels smooth
- [ ] Exit animations are as important as entry
- [ ] Motion doesn't block user interaction
- [ ] 60fps maintained for all animations
- [ ] Transform/opacity preferred over layout-triggering properties
- [ ] Consistent timing across similar interactions
