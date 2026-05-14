---
name: creative
description: Use when you need the Creative workflow umbrella. See references/ for
  detailed guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - creative
    - workflow
    - umbrella
    - routing
    related_skills:
    - architecture-diagram
    - ascii-art
    - baoyu-comic
    - baoyu-infographic
    - claude-design
    - comfyui
---

# Creative

## Overview

This umbrella skill is the routing surface for creative. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside creative and want the quickest route to the right child skill.
- You are not yet sure which creative sub-workflow best matches the request.
- You want a compact map of the creative skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific creative child skill; load that child skill directly.

## Routing Guide

- `architecture-diagram` — you need to generate dark-themed SVG diagrams of software systems and cloud infrastructure as standalone HTML files with inline SVG graphics.
- `ascii-art` — you need to generate ASCII art using pyfiglet (571 fonts), cowsay, boxes, toilet, image-to-ascii, remote APIs (asciified, ascii.co.uk), and LLM fallback.
- `baoyu-comic` — user asks to create "知识漫画", "教育漫画", "biography comic", "tutorial comic", or "Logicomix-style comic".
- `baoyu-infographic` — user asks to create "infographic", "visual summary", "信息图", "可视化", or "高密度信息大图".
- `claude-design` — you need to design one-off HTML artifacts (landing, deck, prototype).
- `comfyui` — you need to generate images, video, and audio with ComfyUI — install, launch, manage nodes/models, run workflows with parameter injection.
- `ideation` — the user says 'I want to build something', 'give me a project idea', 'I'm bored', 'what should I make', 'inspire me', or any variant of 'I have tools but no direction'. Works for c....
- `design-md` — building a design system, porting style rules between projects, generating UI with consistent brand, or auditing accessibility/contrast.
- `excalidraw` — you need to create hand-drawn style diagrams using Excalidraw JSON format.
- `humanizer` — you need guidance on humanize text: strip AI-isms and add real voice.
- `manim-video` — users request: animated explanations, math animations, concept visualizations, algorithm walkthroughs, technical explainers, 3Blue1Brown style videos, or any programmatic animation....
- `p5js` — users request: p5.js sketches, creative coding, generative art, interactive visualizations, canvas animations, browser-based visual art, data viz, shader effects, or any p5.js proj....
- `popular-web-designs` — you need guidance on 54 production-quality design systems extracted from real websites.
- `pretext` — building creative browser demos with @chenglou/pretext — DOM-free text layout for ASCII art, typographic flow around obstacles, text-as-geometry games, kinetic typography, and text....
- `sketch` — you need guidance on throwaway HTML mockups: 2-3 design variants to compare.
- `songwriting-and-ai-music` — you need guidance on songwriting craft, AI music generation prompts (Suno focus), parody/adaptation techniques, phonetic tricks, and lessons learned.
- `touchdesigner-mcp` — you need to control a running TouchDesigner instance via twozero MCP — create operators, set parameters, wire connections, execute Python, build real-time visuals.
- `web-animation-optimization` — enhancing UI/UX with smooth, performant animations.
- `web-animation-patterns` — you need guidance on web animation patterns and performance optimization techniques.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## Common Pitfalls

1. Using the creative umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.

