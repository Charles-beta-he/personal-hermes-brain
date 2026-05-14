---
name: mlops
description: Use when you need the Mlops workflow umbrella. See references/ for detailed
  guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - mlops
    - workflow
    - umbrella
    - routing
    related_skills:
    - modal-serverless-gpu
    - evaluating-llms-harness
    - weights-and-biases
    - huggingface-hub
    - gguf-quantization
    - guidance
---

# Mlops

## Overview

This umbrella skill is the routing surface for mlops. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside mlops and want the quickest route to the right child skill.
- You are not yet sure which mlops sub-workflow best matches the request.
- You want a compact map of the mlops skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific mlops child skill; load that child skill directly.

## Routing Guide

- `cloud/` family — 1 child skills; start here when the request belongs to this subdomain. Examples: `modal-serverless-gpu`.
- `evaluation/` family — 2 child skills; start here when the request belongs to this subdomain. Examples: `evaluating-llms-harness`, `weights-and-biases`.
- `huggingface-hub` — you need guidance on hugging Face Hub CLI (hf) — search, download, and upload models and datasets, manage repos, query datasets with SQL, deploy inference endpoints, manage Spaces ....
- `inference/` family — 5 child skills; start here when the request belongs to this subdomain. Examples: `gguf-quantization`, `guidance`, `llama-cpp`, `outlines`.
- `models/` family — 5 child skills; start here when the request belongs to this subdomain. Examples: `audiocraft-audio-generation`, `clip`, `segment-anything-model`, `stable-diffusion-image-generation`.
- `research/` family — 1 child skills; start here when the request belongs to this subdomain. Examples: `dspy`.
- `training/` family — 6 child skills; start here when the request belongs to this subdomain. Examples: `axolotl`, `grpo-rl-training`, `peft-fine-tuning`, `pytorch-fsdp`.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## Common Pitfalls

1. Using the mlops umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.

