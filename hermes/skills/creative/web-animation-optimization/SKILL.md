---
name: web-animation-optimization
description: "Optimize web application animations by analyzing reference sites, creating reusable animation utilities (easing curves, RAF-driven animations, spring physics, particles), CSS animation systems, and scroll-triggered effects. Use when enhancing UI/UX with smooth, performant animations."
---

# Web Animation Optimization

Analyze reference sites for animation techniques and implement a comprehensive animation system for React/web projects.

## When to Use

- Enhancing a static-feeling web app with smooth animations
- Adding micro-interactions (hover, click, transitions)
- Implementing scroll-triggered entrance animations
- Creating canvas-based game animations (board games, etc.)
- Optimizing animation performance (GPU acceleration, RAF)

## Reference Site Analysis Pattern

Before implementing, analyze a well-designed reference site:

1. **Browser Console Analysis**:
   ```javascript
   // Check frameworks
   typeof THREE !== 'undefined'  // Three.js
   typeof gsap !== 'undefined'   // GSAP
   
   // Count animated elements
   document.querySelectorAll('[style*="transition"]').length
   
   // Check canvas count
   document.querySelectorAll('canvas').length
   ```

2. **CSS Analysis**:
   ```javascript
   // Count animation rules
   Array.from(document.styleSheets).flatMap(s => 
     Array.from(s.cssRules || []).filter(r => 
       r.cssText?.includes('animation') || r.cssText?.includes('transition')
     )
   ).length
   ```

3. **Identify Patterns**:
   - CSS transitions/animations vs JS-driven
   - RequestAnimationFrame usage
   - Intersection Observer for scroll triggers
   - GPU acceleration (will-change, transform: translateZ(0))

## Animation Utility Library (`animations.js`)

Create a reusable animation library with these components:

### 1. Easing Curves

```javascript
export const easings = {
  bounce: 'cubic-bezier(0.34, 1.56, 0.64, 1)',      // Playful bounce
  smoothIn: 'cubic-bezier(0.4, 0, 0.2, 1)',          // Material Design
  smoothOut: 'cubic-bezier(0, 0, 0.2, 1)',           // Exit animations
  elastic: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)', // Elastic overshoot
  snappy: 'cubic-bezier(0.2, 0, 0, 1)',              // iOS-style
}
```

### 2. RAF-Driven Animation Function

```javascript
export function animate({
  from, to, duration = 250, easing = easings.smoothIn,
  onUpdate, onComplete
}) {
  let startTime = null, rafId = null
  const easeFn = parseEasing(easing)

  function step(timestamp) {
    if (!startTime) startTime = timestamp
    const progress = Math.min((timestamp - startTime) / duration, 1)
    const eased = easeFn(progress)
    onUpdate?.(from + (to - from) * eased, progress)
    
    if (progress < 1) rafId = requestAnimationFrame(step)
    else onComplete?.()
  }
  rafId = requestAnimationFrame(step)
  return () => cancelAnimationFrame(rafId) // Cancel function
}
```

### 3. Spring Physics Animation

```javascript
export function spring({
  from, to, stiffness = 100, damping = 10, mass = 1,
  onUpdate, onComplete, threshold = 0.01
}) {
  let position = from, velocity = 0
  // Physics: F = -kx - cv
  // Acceleration = (springForce + dampingForce) / mass
  // ... RAF loop with deltaTime
}
```

### 4. Stagger Animation

```javascript
export function stagger({ items, delayBetween = 50, animationConfig }) {
  items.forEach((item, index) => {
    setTimeout(() => animate({
      ...animationConfig,
      onUpdate: (value, progress) => 
        animationConfig.onUpdate?.(item, value, progress, index)
    }), index * delayBetween)
  })
}
```

### 5. Particle Effects

```javascript
export function createParticles(container, {
  count = 20, colors, sizeRange = [2, 6],
  duration = 1000, spread = 100
}) {
  // Create DOM particles, animate with CSS transitions
  // Clean up after duration
}
```

### 6. Canvas Animation Helpers

```javascript
export const canvasAnimations = {
  // Draw stone with progress (scale + alpha)
  drawStone(ctx, x, y, radius, color, progress = 1, glowColor) {
    const eased = 1 - Math.pow(1 - progress, 3) // easeOut
    const currentRadius = radius * eased
    // Gradient, highlight, glow effects
  },
  
  // Draw winning line progressively
  drawWinningLine(ctx, points, progress = 1, color) {
    // Interpolate along points based on progress
  }
}
```

## CSS Animation System

### Keyframes

```css
/* Entrance animations */
@keyframes fade-scale-in { /* opacity 0→1, scale 0.9→1 */ }
@keyframes slide-in-up { /* opacity 0→1, translateY 30px→0 */ }
@keyframes slide-in-left { /* opacity 0→1, translateX -30px→0 */ }

/* Interactive animations */
@keyframes stone-drop { /* scale 0→1.1→0.95→1, bounce */ }
@keyframes stone-ripple { /* scale 0.8→2, opacity 0.5→0 */ }
@keyframes breathe { /* box-shadow glow pulse */ }
@keyframes thinking-dot { /* scale/opacity pulse for loading */ }

/* Victory animations */
@keyframes victory-appear { /* scale 0.8→1 */ }
@keyframes victory-spin { /* scale 0→1, rotate -180→0 */ }
```

### Utility Classes

```css
/* Animation classes */
.animate-fade-scale-in { animation: fade-scale-in 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards; }
.animate-slide-in-up { animation: slide-in-up 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards; }
.animate-breathe { animation: breathe 2s ease-in-out infinite; }

/* Stagger delays */
.stagger-1 { animation-delay: 0.05s; }
.stagger-2 { animation-delay: 0.1s; }
/* ... up to .stagger-6 */

/* Transition utilities */
.transition-smooth { transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); }
.transition-bounce { transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }

/* GPU acceleration */
.gpu-accelerated {
  will-change: transform, opacity;
  transform: translateZ(0);
  backface-visibility: hidden;
}

/* Hover effects */
.hover-lift:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(0,0,0,0.15); }
.hover-glow:hover { box-shadow: 0 0 16px var(--accent-primary); }
```

## Scroll-Triggered Animations

### useIntersectionObserver Hook

```javascript
export function useIntersectionObserver({
  threshold = 0.1, rootMargin = '0px', triggerOnce = true
} = {}) {
  const ref = useRef(null)
  const [isVisible, setIsVisible] = useState(false)
  
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsVisible(true)
        if (triggerOnce) observer.unobserve(entry.target)
      }
    }, { threshold, rootMargin })
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [threshold, rootMargin, triggerOnce])
  
  return [ref, isVisible]
}

// Usage: const [ref, visible] = useIntersectionObserver()
// <div ref={ref} className={visible ? 'animate-slide-in-up' : 'opacity-0'}>
```

### useStaggerAnimation Hook

```javascript
export function useStaggerAnimation(count, { baseDelay = 0, staggerDelay = 50 }) {
  const [containerRef, isVisible] = useIntersectionObserver()
  const getItemStyle = (index) => ({
    opacity: isVisible ? 1 : 0,
    transform: isVisible ? 'translateY(0)' : 'translateY(20px)',
    transition: `opacity 0.4s ease ${baseDelay + index * staggerDelay}ms,
                 transform 0.4s cubic-bezier(0.4, 0, 0.2, 1) ${baseDelay + index * staggerDelay}ms`
  })
  return [containerRef, getItemStyle]
}
```

## Canvas Animation Integration

For board games or canvas-based UIs:

1. **OffscreenCanvas Pre-rendering**: Render static elements once, copy to main canvas
2. **Progress-Based Drawing**: Pass animation progress (0→1) to draw functions
3. **RAF Loop with Throttle**: 60fps with 16ms throttle
4. **DPR Support**: Scale for retina displays

```javascript
// BoardCanvas.jsx pattern
const [animProgress, setAnimProgress] = useState(null)

useEffect(() => {
  if (!lastMove) return
  // Trigger animation on lastMove change
  const cancel = animate({
    from: 0, to: 1, duration: 350, easing: easings.bounce,
    onUpdate: (value) => setAnimProgress(value),
    onComplete: () => setAnimProgress(null)
  })
  return cancel
}, [lastMove])

// In drawBoard, use canvasAnimations.drawStone() with progress
```

## Performance Optimization

1. **GPU Acceleration**: `will-change`, `transform: translateZ(0)`, `backface-visibility: hidden`
2. **CSS over JS**: Use CSS animations for simple transitions
3. **RAF Throttle**: Limit to 60fps (16ms)
4. **Intersection Observer**: Only animate visible elements
5. **OffscreenCanvas**: Pre-render static content

## Pitfalls

- **Over-animation**: Too many simultaneous animations feel chaotic
- **Layout thrash**: Avoid reading layout in animation loops
- **Memory leaks**: Cancel RAF callbacks on unmount
- **jank on mobile**: Test on real devices, reduce particle counts
- **CSS specificity**: Utility classes may conflict with component styles

## Verification

After implementing animations:
```bash
pnpm test           # Ensure no regressions
pnpm -F web build   # Verify production build
# Manual: Test each animation in browser, check 60fps in DevTools Performance tab
```
