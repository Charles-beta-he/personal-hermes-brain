---
name: web-animation-patterns
description: Use when you need guidance on web animation patterns and performance optimization techniques.
version: 1.0.0
author: Hermes Agent
license: MIT
category: creative
metadata:
  hermes:
    tags:
    - creative
    - web
    - animation
    - patterns
    - optimization
    related_skills:
    - design
---

# Web Animation Patterns

## Overview


High-performance animation techniques for modern web applications.

## When to Use

- You need guidance on web animation patterns and performance optimization techniques

## Core Technologies

### 1. CSS Animations (Simple → Use CSS)
- `@keyframes` for reusable animations
- `transition` for state changes
- `cubic-bezier` easing curves

### 2. JavaScript RAF (Complex → Use JS)
- `requestAnimationFrame` for 60fps loops
- Time-based animation (not frame-based)
- Throttle to 16ms (~60fps)

### 3. Intersection Observer (Scroll-triggered)
- Lazy-load animations when visible
- `threshold` and `rootMargin` for control
- `triggerOnce` for one-time entrance

## Easing Curves (from Lusion.co)

```javascript
const easings = {
  bounce: 'cubic-bezier(0.34, 1.56, 0.64, 1)',      // Playful bounce
  smoothIn: 'cubic-bezier(0.4, 0, 0.2, 1)',          // Material design
  smoothOut: 'cubic-bezier(0, 0, 0.2, 1)',           // Exit animation
  elastic: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)', // Spring-like
  snappy: 'cubic-bezier(0.2, 0, 0, 1)',              // Quick micro-interactions
}
```

## Performance Optimization

### GPU Acceleration
```css
.gpu-accelerated {
  will-change: transform, opacity;
  transform: translateZ(0);
  backface-visibility: hidden;
}
```

### Rules
1. **Only animate `transform` and `opacity`** - These don't trigger layout/paint
2. **Use `will-change` sparingly** - Memory overhead
3. **Avoid animating width/height/margin/padding** - Causes reflow
4. **Use `transform: translate()` instead of `top/left`**

## Animation Patterns

### Entrance Animations
```css
@keyframes fade-scale-in {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes slide-in-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### Stagger (List Items)
```javascript
items.forEach((item, i) => {
  item.style.transition = `opacity 0.4s ease ${i * 50}ms, transform 0.4s ease ${i * 50}ms`;
});
```

### Spring Physics
```javascript
function spring({ from, to, stiffness = 100, damping = 10, onUpdate }) {
  let pos = from, vel = 0;
  function step() {
    const force = -stiffness * (pos - to) - damping * vel;
    vel += force * dt;
    pos += vel * dt;
    onUpdate(pos);
    if (Math.abs(vel) > 0.01 || Math.abs(pos - to) > 0.01) {
      requestAnimationFrame(step);
    }
  }
  requestAnimationFrame(step);
}
```

### Particles (Victory/Effects)
```javascript
function createParticles(container, { count = 20, spread = 100 }) {
  for (let i = 0; i < count; i++) {
    const particle = document.createElement('div');
    const angle = (Math.PI * 2 * i) / count;
    // ... style particle
    requestAnimationFrame(() => {
      particle.style.transform = `translate(${Math.cos(angle) * spread}px, ${Math.sin(angle) * spread}px)`;
      particle.style.opacity = '0';
    });
  }
}
```

## Common Use Cases

| Pattern | Technology | Duration |
|---------|-----------|----------|
| Button hover | CSS transition | 150-200ms |
| Card entrance | CSS animation | 300-500ms |
| Page transition | CSS/JS mix | 300-400ms |
| Scroll reveal | Intersection Observer | 400-600ms |
| Physics bounce | JS RAF | Variable |
| Particle burst | JS + CSS | 800-1200ms |

## Reference Sites

- **Lusion.co** - WebGL + CSS hybrid, scroll-driven 3D
- **Stripe.com** - Smooth micro-interactions
- **Linear.app** - Minimal, snappy transitions
- **Apple.com** - Scroll-triggered reveals

## React Hook: useIntersectionObserver

```javascript
function useIntersectionObserver({ threshold = 0.1, triggerOnce = true }) {
  const ref = useRef(null);
  const [isVisible, setIsVisible] = useState(false);
  
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsVisible(true);
        if (triggerOnce) observer.unobserve(entry.target);
      }
    }, { threshold });
    
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [threshold, triggerOnce]);
  
  return [ref, isVisible];
}
```

## Common Pitfalls
1. **Don't animate too many elements simultaneously** - Cap at ~50-100
2. **Clean up RAF loops** - Memory leaks from forgotten callbacks
3. **Test on low-end devices** - GPU limitations
4. **Respect `prefers-reduced-motion`** - Accessibility
5. **Avoid layout thrashing** - Don't read/write DOM in loops

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

