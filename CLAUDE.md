Web Intelligence Scraper

Project Context

A comprehensive web scraping and design analysis system built with Python (Flask) and Playwright, designed to extract design systems, layout patterns, and site architecture in a way that is legible to humans and LLMs.

🎯 Project Purpose

The Web Intelligence Scraper exists to make how websites are constructed legible.

It enables users to:

Understand how real-world sites are built (learning + inspiration)

Extract reusable design systems (typography, color, spacing, layout)

Analyze site structure (navigation, templates, URL patterns)

Compare multiple pages to identify systemic consistency vs variance

Primary users

Designers

Developers

LLMs (Claude Code, GPT, etc.) performing architectural analysis

This is not a crawler for scraping content at scale—it is an evidence engine for structural understanding.

🧠 Editorial + Engineering Philosophy

This tool treats websites as systems, not pages.

As such:

Every extraction must be verifiable

Every metric must be defensible

Every feature must minimize hallucination risk for LLM consumers

To enforce this, the project follows a strict Workflow Orchestration doctrine.

🔁 Workflow Orchestration (Core Operating Doctrine)
1. Plan Mode (Default)

Any non-trivial change requires planning first.

Applies to:

Adding new metrics

Modifying extraction logic

Extending analysis modes (e.g. Smart Nav)

LLM-facing output changes

Rules:

Enter plan mode for tasks with 3+ steps or architectural impact

If extraction results drift or regress: STOP and re-plan

Planning is required for verification, not just implementation

Specs must describe:

What evidence is collected

How confidence is calculated

Failure modes

2. Subagent Strategy (Parallel Analysis)

This project is inherently parallel by design.

Use subagents to:

Explore unknown site behaviors

Compare scraping strategies

Validate metrics against real-world sites

Audit LLM outputs for ambiguity

Rules:

One task per subagent

Offload research, exploration, and comparisons

Complex sites justify more compute—not rushed logic

3. Self-Improvement Loop

This scraper is designed to learn from its own failures.

After any correction:

Update tasks/lessons.md with the pattern, not just the fix

Convert mistakes into rules

Re-review lessons at the start of related work

Applies to:

Misclassified layouts

Incorrect CSS extraction

LLM confusion

Bot-detection failures

The goal is error-rate collapse over time.

4. Verification Before "Done"

No analysis is complete unless it can be proven.

Required checks:

Evidence exists in the DOM / CSS / network

Metrics match screenshots and raw values

Behavior is consistent across reloads

Output would be trusted by a senior engineer or designer

Ask explicitly:

"Would a staff-level engineer accept this metric?"

If not, it is incomplete.

5. Demand Elegance (Balanced)

Elegance is mandatory—but not at the cost of clarity.

Rules:

For non-trivial changes, pause and ask:

"Is there a simpler, more general solution?"

If a fix feels hacky, re-implement the elegant version

Skip elegance checks for obvious, contained fixes

Do not over-engineer abstractions prematurely

In this system, elegance means:

Fewer heuristics

Clear evidence trails

Predictable failure modes

6. Autonomous Bug Fixing

Bug reports should not require user babysitting.

Rules:

Fix the issue directly

Identify logs, errors, or failing evidence

Resolve without requesting extra context

CI, regressions, or broken metrics should be fixed proactively

🏗️ Architecture Overview
Tech Stack

Backend: Python 3.9+ with Flask

Browser Automation: Playwright (Chromium)

HTML Parsing: BeautifulSoup

Component Analysis: website-understanding-sdk (Node.js bridge)

Frontend: Vanilla JS (no framework)

Core Engine

app.py — Flask server and API routing

deep_evidence_engine.py — Main analysis orchestrator (20+ metrics)

component_mapper.py — Bridge to semantic component detection SDK

Extractors

design_system_metrics.py — Typography, color, spacing, shadows

visual_hierarchy_analyzer.py — Heroes, CTAs, content grouping

**spatial_composition_analyzer.py** — Page structure, spatial relationships, zones **(NEW)**

screenshot_annotator.py — Full-page screenshots + overlays

content_extractor.py — Page-type classification

api_relationship_mapper.py — API detection

component_ripper.py — HTML + CSS component extraction

UI

templates/web_dashboard.html

templates/component_ripper_ui.html

templates/glossary.html

SDK Bridge

analyze_page_bridge.js

website-understanding-sdk/ (npm-only dependency)

📡 API Endpoints
1. Deep Scan

POST /api/deep-scan

Analyzes a single page or smart-nav set and returns full evidence.

2. Discover URLs

POST /api/discover-urls

Extracts and categorizes all links for LLM-driven workflows.

3. Batch Analyze

POST /api/batch-analyze

Compare up to 5 URLs in a single request.

4. Rip Component

POST /api/rip-component

Extract HTML + CSS for a specific selector.

5. Extract Styles

POST /api/extract-styles

Returns computed CSS values (real pixels, not framework abstractions).

🧠 Key Features (System-Level)

20+ metric categories

Evidence-backed design system extraction

**Spatial composition analysis** (NEW - Feb 2026)

LLM-helper with suggested next steps

URL pattern detection

Stealth mode for bot protection

Full-page screenshots

Smart Nav multi-page synthesis

Real media queries (not inferred breakpoints)

🔄 Analysis Flow
Single Page

Load with Playwright

Apply stealth (if required)

Wait for JS render

Run metric extraction in parallel

Generate LLM helper guidance

Return structured evidence

Smart Nav

Analyze homepage

Discover navigation

Select representative pages

Analyze each

Synthesize cross-page patterns

Return unified insights

🗺️ Spatial Composition Analysis (NEW - Feb 2026)

**The Missing 50-60%: How Pieces Fit Together**

Prior to this feature, the scraper extracted comprehensive design tokens (fonts, colors, spacing) but was missing spatial composition — **"how the pieces fit together"** on the page.

### What It Captures

1. **Page Structure Patterns** — Detects common layouts:
   - Landing Page (Hero + Features + CTA)
   - Marketing Site (Nav + Multi-Column)
   - Article Layout (Single Column)
   - App Layout (Navigation-First)

2. **Spatial Relationships** — How elements relate:
   - Beside (horizontal adjacency + gaps)
   - Below (vertical stacking)
   - Inside (parent-child nesting)
   - Aligned (shared left/center/right edges)

3. **Component Zones** — Semantic regions with bounding boxes:
   - Header/Banner
   - Hero Section
   - Features
   - Content
   - Footer

4. **Alignment Patterns** — How content is distributed:
   - Left-aligned (text-heavy)
   - Center-aligned (landing pages)
   - Split-layout (nav + content)
   - Balanced (distributed)

5. **Whitespace Analysis** — Density and breathing room:
   - Content density (% of viewport filled)
   - Average vertical spacing
   - Breathing room score
   - Interpretation (dense/balanced/spacious/minimal)

6. **Above-the-Fold Layout** — Initial viewport:
   - Element breakdown (headings, images, buttons)
   - Primary focus (hero, CTA, visual)
   - Viewport coverage percentage

7. **Container Hierarchy** — Flex/Grid nesting:
   - Flex container counts and direction
   - Grid container counts and columns
   - Children per container

8. **Layout Grid Detection** — Underlying column system:
   - 12-column grid (Bootstrap, Foundation)
   - 16-column grid (Material Design)
   - Asymmetric/custom grids

### Evidence Output

Accessible via `evidence['spatial_composition']`:

```python
{
  'pattern': 'Spatial composition analyzed: 391 elements, 3 zones',
  'confidence': 85,
  'page_structure': {
    'pattern_type': 'Landing Page (Hero + Features)',
    'landmarks': {...},
    'multi_column_sections': [...]
  },
  'spatial_relationships': {
    'beside_count': 419,
    'aligned_groups': 5,
    'examples': {...}
  },
  'component_zones': [...],
  'alignment_patterns': {...},
  'whitespace_analysis': {...},
  'above_fold_layout': {...},
  'container_hierarchy': {...},
  'layout_grid': {...}
}
```

### Confidence Scoring

Based on:
- Element count (20+ elements = +20%)
- Semantic landmarks (header/nav/main/footer = +15%)
- Layout containers (flex/grid = +15%)
- Base: 50%

Typical scores: 85-95% for well-structured sites

### Impact

**Before:** Design tokens only (fonts, colors, spacing) — missing composition
**After:** Full spatial understanding (page structure, zones, relationships)
**Gap closed:** ~50-60% → ~10-15%

See `tasks/SPATIAL_COMPOSITION_COMPLETE.md` for full documentation.

🛠️ Task Management (Required)

Write plans to tasks/todo.md

Verify plan before implementation

Track progress incrementally

Summarize changes clearly

Document results

Capture lessons after corrections

🧩 Known Limitations

**Validation Status:** ✅ Tested across 5 diverse sites (Feb 2026)
- Stripe Docs, Blizzard, Shopify, Tailwind UI, Wikipedia
- 69% average confidence across all metrics
- 74% of metrics scored ≥80% confidence

### Framework Constraints

**✅ Works Best With:**
- Semantic CSS (BEM, SMACSS, CSS custom properties)
- Marketing sites (Stripe, Blizzard)
- Documentation sites (Stripe Docs, Wikipedia)
- E-commerce platforms (Shopify themes)

**⚠️ Works With Limitations:**
- **Utility-first CSS (Tailwind, Tachyons):**
  - Detects values but loses semantic names
  - Color detection drops to 25% confidence (vs 80-90% on semantic CSS)
  - Spacing/typography still work (computed styles)
  - Recommendation: Document as known constraint

**❌ Does Not Work With:**
- Shadow DOM / Web Components (cannot access encapsulated styles)
- Aggressive bot protection (Cloudflare Turnstile, PerimeterX)
- Sites requiring authentication (no login support)
- Infinite scroll content (only analyzes initial DOM)

### Metric Reliability (5-Site Test Results)

**Perfect Stability (0% variance across sites):**
- Typography: 95% avg confidence
- Spacing Scale: 85% avg confidence
- Z-Index Stack: 90% avg confidence
- Visual Hierarchy: 85% avg confidence

**High Reliability (low variance):**
- Shadow System: 73% avg, 12% std dev
- Responsive Breakpoints: 88% avg, 16% std dev
- Interaction States: 81% avg, 15% std dev

**Framework-Dependent:**
- Colors: 69% avg, 26% std dev (drops to 25% on Tailwind)

**Not Implemented:**
- Content Structure: 0% (planned, not built)
- Third-Party Services: 0% (planned, not built)

### Explicitly Non-Goals

These are intentional design decisions, not bugs:

- No button clicking (analysis only, no interaction)
- No auth walls (public sites only)
- No infinite scroll (initial DOM only)
- No CAPTCHA solving (use MRI mode fallback)
- No persistent browser sessions (stateless by design)

### MRI Mode (Graceful Degradation)

When Playwright is blocked:
- Falls back to HTTP + BeautifulSoup
- ~70% accuracy vs full Playwright scan
- Loses: JS-rendered content, computed styles, interaction states
- Keeps: HTML structure, inline styles, CSS custom properties

### Honest Documentation Philosophy

**We document failures, not hide them:**
- Low confidence scores are displayed, not filtered
- Unimplemented features return 0% confidence
- Framework-specific issues are called out explicitly
- Test results validate claims (see docs/test_results_2026-02-07.md)

This increases credibility over "documentation theater."

🎨 Design Decisions (Rationale)

Playwright over Selenium: speed, JS reliability, stealth

Full-page screenshots: system-level visibility

Node SDK bridge: keep Python primary, reuse npm ecosystem

Batch limit of 5: performance + predictability

🚨 Important Notes

Restart server after core changes

Inspect server.log first

LLM users should:

Read docs/LLM_USAGE_GUIDE.md

Use /api/discover-urls before scanning

Trust llm_helper.suggested_next_steps

📊 Output Contract

Evidence objects are structured, deterministic, and LLM-safe.
No metric exists without traceable evidence.

💡 Future Enhancements (Optional)

Site mapper with depth limits

Component library export

Video flow capture

Auth support

Infinite scroll handling

Bottom line

This scraper is not a toy, crawler, or black box.
It is a workflow-driven evidence system designed to survive contact with real websites and real LLM usage.
