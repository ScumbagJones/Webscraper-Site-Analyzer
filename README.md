# 🔍 Web Intelligence Scraper

A comprehensive web scraping and design analysis system that extracts design systems, layout patterns, and site architecture in a way that is legible to humans and LLMs.

---

## 🤖 FOR LLMs (Claude Code, GPT, etc.)

**Looking to analyze sites programmatically?** Read the **[LLM Usage Guide](LLM_USAGE_GUIDE.md)** for:
- API endpoints (`/api/discover-urls`, `/api/batch-analyze`)
- Common workflows (site architecture, design systems)
- What the scraper CAN and CANNOT do
- Example analysis flows

---

## 🎯 What This Tool Does

This is **not a content crawler**—it's an **evidence engine** for structural understanding.

**It extracts:**
- Design systems (typography, colors, spacing, shadows)
- Layout patterns (Grid, Flexbox, positioning)
- Site architecture (navigation, URL patterns, templates)
- Visual hierarchy (hero sections, CTAs, content groups)
- Component structures (with CSS selectors)

**Primary users:**
- Designers learning from real-world sites
- Developers extracting reusable patterns
- LLMs (Claude Code, GPT) performing architectural analysis

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd /Users/jarradjones/Desktop/Webscraper
pip install -r requirements.txt
playwright install chromium
```

### 2. Install SDK Dependencies

```bash
cd website-understanding-sdk
npm install
cd ..
```

### 3. Start the Server

```bash
python3 app.py
```

Server runs at **http://localhost:8080**

---

## 📡 API Endpoints

### Complete Site Analysis
```bash
POST /api/deep-scan
{
  "site_url": "https://example.com",
  "analysis_mode": "single"  # or "smart-nav"
}
```

**Returns:** 20+ metrics including layout, typography, colors, component map, and LLM helper suggestions.

### Discover All Links
```bash
POST /api/discover-urls
{"site_url": "https://example.com"}
```

**Returns:** Categorized links (navigation, articles, sections, external)

### Batch Analysis
```bash
POST /api/batch-analyze
{"urls": ["url1", "url2", "url3"]}  # max 5
```

**Returns:** Full analysis for multiple URLs in one request

### Extract Component
```bash
POST /api/rip-component
{"site_url": "...", "selector": ".nav"}
```

**Returns:** HTML + CSS blueprint for specific component

### Get Computed Styles
```bash
POST /api/extract-styles
{"site_url": "...", "selector": ".card", "mode": "critical"}
```

**Returns:** Real pixel values (not Tailwind classes)

---

## 🧠 Key Features

### 20+ Metric Categories
1. Layout System (Grid/Flexbox)
2. Typography (fonts, sizes, type scale)
3. Color Palette (with visual previews)
4. Spacing System (margin/padding scale)
5. Responsive Breakpoints (actual media queries)
6. Shadow System (elevation levels)
7. Border Radius (rounding patterns)
8. Z-Index Stack (layering)
9. Animations (CSS + JS libraries)
10. Accessibility Score
11. Performance Metrics
12. SEO Analysis
13. Security Headers
14. API Patterns
15. CSS Tricks
16. Interactive Elements
17. Third-Party Integrations
18. Visual Hierarchy
19. Component Map (with CSS selectors)
20. DOM Depth

### LLM-Friendly Features
- **Auto-suggestions:** Every analysis includes `llm_helper` with next steps
- **URL discovery:** Automatic link categorization
- **Batch analysis:** Compare multiple pages at once
- **URL pattern detection:** Identifies templates (`/p/{slug}`)
- **Context-specific tips:** Guidance based on page type

### Special Capabilities
- **Stealth Mode:** Bypasses bot protection (works on pi.fyi, etc.)
- **Full-Page Screenshots:** Captures entire scrollable content
- **Smart Nav Mode:** Auto-discovers and analyzes 3 representative pages
- **Component Extraction:** CSS selectors for all page sections
- **Actual Media Queries:** Shows real CSS, not inferred breakpoints

---

## 🏗️ Architecture

### Tech Stack
- **Backend:** Python 3.9+ with Flask
- **Browser Automation:** Playwright (Chromium)
- **HTML Parsing:** BeautifulSoup
- **Component Analysis:** website-understanding-sdk (Node.js bridge)
- **Frontend:** Vanilla JavaScript

### Core Files
- `app.py` - Flask server and API routing
- `deep_evidence_engine.py` - Main analysis orchestrator (20+ metrics)
- `component_mapper.py` - Bridge to component detection SDK
- `design_system_metrics.py` - Typography, colors, spacing, shadows
- `visual_hierarchy_analyzer.py` - Hero sections, CTAs, content groups
- `screenshot_annotator.py` - Full-page screenshots with overlays
- `content_extractor.py` - Page type classification
- `api_relationship_mapper.py` - API endpoint detection
- `component_ripper.py` - HTML + CSS extraction

---

## 🎨 Philosophy

This tool treats **websites as systems, not pages**.

**Core principles:**
- Every extraction must be **verifiable** (traceable to DOM/CSS/network)
- Every metric must be **defensible** (confidence scores based on evidence)
- Every feature must **minimize hallucination risk** for LLM consumers

**Output contract:**
- Structured, deterministic JSON
- No metric without traceable evidence
- Explicit confidence scores
- Clear failure modes

---

## 🧩 Known Limitations

**By design, this tool does NOT:**
- ❌ Click buttons (provide direct URLs instead)
- ❌ Handle auth walls (credentials not supported)
- ❌ Infinite scroll (only initial page load)
- ❌ Solve CAPTCHAs (stealth mode instead)
- ❌ Maintain browser sessions (isolated requests)

**Workarounds:**
- Use `/api/discover-urls` to map site structure
- Analyze specific pages with direct URLs
- Stealth mode bypasses most bot detection

---

## 📚 Documentation

- **[LLM_USAGE_GUIDE.md](LLM_USAGE_GUIDE.md)** - Complete guide for LLMs
- **[SYSTEM.md](SYSTEM.md)** - Engineering philosophy and workflow doctrine
- **[claude.md](claude.md)** - Quick project context for AI agents
- **[tasks/lessons.md](tasks/lessons.md)** - Captured corrections and patterns

---

## 🛠️ Common Tasks

### Testing the Server
```bash
# Health check
curl http://localhost:8080/health

# Analyze a site
curl -X POST http://localhost:8080/api/deep-scan \
  -H "Content-Type: application/json" \
  -d '{"site_url": "https://example.com"}'
```

### Debugging
```bash
# Check server logs
tail -f server.log

# View recent errors
grep "ERROR" server.log | tail -20
```

### Adding New Metrics
1. Add extraction method to `design_system_metrics.py`
2. Call it in `deep_evidence_engine.py` → `_analyze_single_page()`
3. Add display logic to `templates/web_dashboard.html`
4. Document in `metric_explanations.py`

---

## 💡 Example Workflows

### For Designers: Extract Design System
```bash
# 1. Analyze homepage
POST /api/deep-scan {"site_url": "https://stripe.com"}

# 2. Extract design tokens from response
typography.fonts → ["Inter", ...]
color_palette.palette.primary → ["#635BFF", ...]
spacing.spacing_scale → [4, 8, 16, 24, 32, ...]
responsive_breakpoints.media_queries → [...]

# 3. Compare with another page
POST /api/batch-analyze {"urls": ["homepage", "docs page"]}
```

### For Developers: Understand Architecture
```bash
# 1. Discover site structure
POST /api/discover-urls {"site_url": "https://example.com"}

# 2. Batch analyze key pages
POST /api/batch-analyze {"urls": [discovered navigation links]}

# 3. Compare component_map across pages
# Identify consistent patterns (nav, footer)
# Find variations (different article templates)
```

### For LLMs: Site Analysis
```bash
# 1. Deep scan with auto-suggestions
POST /api/deep-scan {"site_url": "https://example.com"}

# 2. Follow llm_helper.suggested_next_steps
# Check url_patterns for templates
# Read analysis_tips for context

# 3. Batch analyze suggested URLs
POST /api/batch-analyze {"urls": [from suggestions]}
```

---

## 🔧 Configuration

### Environment Variables
- `PORT` - Server port (default: 8080)
- `DEBUG` - Debug mode (default: True)

### Analysis Modes
- `single` - Analyze one page (default)
- `smart-nav` - Auto-discover and analyze 3 pages

### Timeouts
- Page load: 60 seconds
- JavaScript render: 3 seconds
- Network idle: 60 seconds

---

## 🚨 Troubleshooting

### Server Won't Start
```bash
# Kill existing process
lsof -ti:8080 | xargs kill -9

# Restart
python3 app.py
```

### Bot Detection Blocking
- Stealth mode activates automatically
- Check logs for "🥷 Stealth mode enabled"
- If still blocked, site may require manual access

### Empty Analysis Results
- Check `server.log` for errors
- Verify URL is accessible in browser
- Try with `analysis_mode: "single"` first

---

## 📊 Output Structure

Every analysis returns:

```json
{
  "layout": {"pattern": "...", "confidence": 95, ...},
  "typography": {"fonts": [...], "type_scale": [...], ...},
  "color_palette": {"palette": {"primary": [...], ...}, ...},
  "component_map": {
    "page_type": "home",
    "sections": [{"type": "nav", "selector": "nav.main"}],
    "elements": {"buttons": [...], "links": [...]}
  },
  "llm_helper": {
    "discovered_links": {...},
    "suggested_next_steps": [...],
    "url_patterns": {...},
    "analysis_tips": [...]
  },
  "meta_info": {
    "url": "...",
    "total_requests": 47,
    "access_strategy": "playwright_full"
  }
}
```

---

## 🤝 Contributing

This is a workflow-driven project. Before contributing:

1. Read **[SYSTEM.md](SYSTEM.md)** for engineering philosophy
2. Create a plan in **tasks/todo.md** for non-trivial changes
3. Document lessons in **tasks/lessons.md** after corrections
4. Ensure all metrics have verifiable evidence

**Quality standards:**
- No silent failures (always log exceptions)
- No metric without traceable evidence
- Confidence scores must be defensible
- Test on 3+ real sites before shipping

---

## 📄 License

MIT License - See LICENSE file for details

---

*This scraper is not a toy, crawler, or black box. It is a workflow-driven evidence system designed to survive contact with real websites and real LLM usage.*
