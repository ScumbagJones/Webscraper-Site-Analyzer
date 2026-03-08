# Changelog - Web Intelligence Scraper

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2026-02-10] - Motion Token Synthesizer + Auto-Detection Validation

### Added
- **Motion Token Synthesizer** (`motion_token_synthesizer.py`) — NEW MODULE
  - Parses raw CSS transition strings into structured tokens (property, duration_ms, easing, delay)
  - Detects duration scale with semantic tiers (micro/fast/normal/slow/dramatic)
  - Detects easing palette with purpose-based roles (default/entrance/exit/continuous/spring)
  - Matches detected cubic-bezier curves against 30+ known curves from 13 design systems
    (Material Design, Carbon, Polaris, Spectrum, Fluent, Atlassian, Ant Design, etc.)
  - Classifies motion patterns by purpose (hover_feedback, focus_ring, state_change, entrance, emphasis)
  - Integrated into deep_evidence_engine.py as `evidence['motion_tokens']`
- **DTCG Motion Tokens** — duration (`$type: "duration"`) and easing (`$type: "cubicBezier"`) tokens
- **Tailwind Motion Config** — `transitionDuration`, `transitionTimingFunction`, `animation` sections
- **Design Brief Motion Section** — personality inference, known-curve attribution, pattern descriptions
- **Starter Template Motion Vars** — `--motion-duration-*` and `--motion-easing-*` CSS custom properties

### Fixed
- Auto-detection `vh` variable not available in Python scope (was JS-only) — fixed by returning viewport height from evaluate
- Easing role assignment thresholds too tight — relaxed decelerate detection, added keyword shortcuts

### Tested
- Motion tokens on 3 sites: Stripe (95%, 100 transitions, 14 curves), Allbirds (95%, 96 transitions, 18 keyframes), NTS (95%, 82 transitions)
- Auto-detection on 10 new sites: Apple, Bandcamp, Notion, Are.na, Ableton, Figma, Vercel, Craigslist, NYTimes, Linear
  - 10/10 detected navigation correctly
  - 8/10 detected hero sections
  - 9/10 detected footers
- All 12 endpoint tests pass (2 sites × 6 endpoints) with motion tokens in every generator

---

## [2026-02-09] - Component Forensics + Auto-Detection + Spatial Composition

### Added
- **Component Forensics** (`component_ripper.py`)
  - 2-level child traversal via `page.evaluate` — extracts tag, text, href, bounding rect, 14 computed styles per child
  - Functional role classification: branding, navigation_links, action_elements, text_content, layout_group, media
  - Spatial zone detection: groups children into left/center/right zones by position
  - Layout system detection: flex direction, justify-content, align-items, gap
  - `<li>` with link children → navigation_links (ESPN nav fix)
  - Anatomy markdown generation with per-zone breakdowns
  - Tested on ESPN, Allbirds, GOV.UK, Pigeons & Planes, NTS Live
- **Auto-Detection Scoring** (`component_ripper.py` — `_rip_page_sections`)
  - Scoring-based heuristic system replaces simple first-match
  - Category scoring: navigation (links, width, position, nav presence), hero (height, images, buttons), player (play/live/audio signals), footer (tag, links, position)
  - Single `page.evaluate` scans all candidates, Python scores and selects winners
  - `selector="auto"` support in API (`app.py`)
  - Tested on NTS: navigation (header.header, score 230), player (#nts-live-header, score 190), hero (section.mixtape-discovery, score 283)
- **Spatial Composition Analyzer** (`spatial_composition_analyzer.py`)
  - Page structure pattern detection (Landing Page, Marketing, Article, App)
  - Spatial relationships (beside, below, inside, aligned)
  - Component zones with bounding boxes (header, hero, footer)
  - Alignment patterns, whitespace density, above-the-fold layout
  - Container hierarchy (flex/grid nesting)
  - Layout grid detection (12-col, asymmetric, custom)
  - Closes the ~50-60% composition gap in design system extraction

### Fixed
- **All 5 generator modules** rewritten against actual evidence schema
  - `design_brief_generator.py` - Fixed `float` object has no attribute `get`
  - `dtcg_token_exporter.py` - Fixed `unhashable type: slice`
  - `tailwind_config_generator.py` - Fixed `unhashable type: slice`
  - `starter_template_generator.py` - Fixed `float` object has no attribute `get`
  - `design_system_differ.py` - Fixed all schema path mismatches
- **Component Ripper** batch mode - `_rip_component()` using `self.selector` instead of `selector` param (caused empty HTML)
- **querySelector escaping** (`deep_evidence_engine.py`) - `CSS.escape()` for IDs with spaces/newlines in label[for] selectors (Glossier crash fix, 0% → 90% confidence)
- **E-commerce site compatibility** - Glossier, Allbirds now fully analyzed

### Changed
- Validated all generators across 5 diverse sites (Stripe Docs, Blizzard, Shopify, Tailwind UI, Wikipedia)
- 20/20 generator endpoint tests passing
- Project workspace cleanup (archived test artifacts, organized docs)
- Tested component forensics across 7 diverse sites (ESPN, Allbirds, GOV.UK, Pigeons & Planes, NTS Live, Glossier, Craigslist)

---

## [2026-02-07] - 8-Site Validation

### Added
- Comprehensive 8-site test suite (Stripe, Tailwind, Shopify, X.com, Reddit, GitHub, Apple, NYTimes)
- `test_results_2026-02-07.md` with full confidence scores

### Results
- All 8 sites loaded with Full Access (Playwright stealth mode works)
- Typography/Layout: 95% confidence consistently
- CSS variables detected: GitHub=1884, Stripe=436, Apple=94, NYTimes=63

---

## [2026-02-XX] - LLM Integration Release

### Added
- **LLM Helper** in every deep-scan response
  - Auto-suggested next steps with reasoning
  - URL pattern detection
  - Discovered links categorization
- **New API Endpoints**
  - `/api/discover-urls` - Extract and categorize all links
  - `/api/batch-analyze` - Analyze up to 5 URLs in one request
  - `/api/generate-starter-template` - HTML starter template from evidence
  - `/api/generate-design-brief` - Human-readable design brief
  - `/api/export-dtcg-tokens` - W3C DTCG format tokens
  - `/api/export-tailwind-config` - Tailwind CSS config
  - `/api/compare-sites` - Design system diffing
- **Component Map Integration** via website-understanding-sdk bridge
- **Full-Page Screenshots** (full scrollable page, not viewport-only)

---

## [2026-02-XX] - Stealth Mode + Smart Nav

### Added
- **Stealth Mode** with playwright-stealth integration
- **3-Tier Fallback** (Stealth Playwright → Degraded → MRI Mode)
- **Smart Nav Mode** (`analysis_mode: "smart-nav"`)
  - Auto-discovers navigation, selects representative pages
  - Synthesizes cross-page design system patterns

---

## [2026-01-XX] - Initial Release

### Added
- 20+ metric categories (Layout, Typography, Colors, Spacing, Shadows, etc.)
- Core API endpoints (`/api/deep-scan`, `/api/rip-component`, `/api/extract-styles`)
- Web dashboard with interactive metric cards and confidence scoring
- Evidence-based extraction with verifiable results

### Technical
- Python 3.9+ with Flask, Playwright, BeautifulSoup
- Vanilla JS frontend

---

## Roadmap

### Implemented
- [x] Design system diff (compare two sites)
- [x] Spatial composition analysis
- [x] Generator modules (Starter Template, Design Brief, DTCG, Tailwind)
- [x] Component forensics (child traversal, role grouping, zone detection)
- [x] Auto-detection scoring (navigation, hero, player, footer)
- [x] Motion token synthesis (duration scale, easing palette, pattern classification)

### Planned
- [ ] Unit tests for core extractors
- [ ] OpenAPI spec for API endpoints
- [ ] Site mapper with depth limits
- [ ] Component library export (React/Vue templates)
- [ ] Auth support
- [ ] Infinite scroll handling

---

*See `tasks/lessons.md` for detailed engineering lessons learned.*
