"""
Web Intelligence Dashboard - Final Version

Features:
- 20+ metrics extraction (layout, typography, colors, animations, accessibility, etc.)
- Article content extraction with confidence scoring
- Markdown export
- Debug view with network traces
- Analytics dashboard
- Figma-style UI
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import asyncio
from pathlib import Path
from deep_evidence_engine import DeepEvidenceEngine
from component_ripper import ComponentRipper
from computed_style_extractor import ComputedStyleExtractor
import json
import os
import traceback
import logging
from datetime import datetime
from urllib.parse import urlparse
import ipaddress
import socket
import anthropic

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max request size

# Restrict CORS to localhost origins only
CORS(app, origins=[
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
])


# ---------------------------------------------------------------------------
# Security: URL validation to prevent SSRF
# ---------------------------------------------------------------------------
BLOCKED_IP_RANGES = [
    ipaddress.ip_network('127.0.0.0/8'),       # Loopback
    ipaddress.ip_network('10.0.0.0/8'),         # Private A
    ipaddress.ip_network('172.16.0.0/12'),      # Private B
    ipaddress.ip_network('192.168.0.0/16'),     # Private C
    ipaddress.ip_network('169.254.0.0/16'),     # Link-local / AWS metadata
    ipaddress.ip_network('0.0.0.0/8'),          # Current network
    ipaddress.ip_network('::1/128'),            # IPv6 loopback
    ipaddress.ip_network('fc00::/7'),           # IPv6 private
    ipaddress.ip_network('fe80::/10'),          # IPv6 link-local
]


def validate_url(url):
    """
    Validate and normalize a user-supplied URL.
    Returns (normalized_url, error_message). error_message is None if valid.
    """
    if not url or not isinstance(url, str):
        return None, 'URL is required'

    url = url.strip()

    # Add protocol if missing
    if not url.startswith('http'):
        url = f'https://{url}'

    try:
        parsed = urlparse(url)
    except Exception:
        return None, 'Invalid URL format'

    # Scheme must be http or https
    if parsed.scheme not in ('http', 'https'):
        return None, f'Invalid URL scheme: {parsed.scheme}. Only http and https are allowed.'

    # Must have a hostname
    hostname = parsed.hostname
    if not hostname:
        return None, 'URL must include a hostname'

    # Block file://, data://, javascript:// etc. (already handled by scheme check)
    # Block obviously dangerous hostnames
    if hostname in ('localhost', '0.0.0.0'):
        return None, 'Scanning localhost or 0.0.0.0 is not allowed'

    # Resolve hostname and check against blocked IP ranges
    try:
        addr_infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in addr_infos:
            ip = ipaddress.ip_address(sockaddr[0])
            for blocked in BLOCKED_IP_RANGES:
                if ip in blocked:
                    return None, f'URL resolves to a private/reserved IP address ({ip}). Scanning internal networks is not allowed.'
    except socket.gaierror:
        return None, f'Could not resolve hostname: {hostname}'

    return url, None


# ---------------------------------------------------------------------------
# Utility: run async coroutine in a fresh event loop
# ---------------------------------------------------------------------------
def run_async(coro):
    """Run an async coroutine in a new event loop. Returns the result."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('web_dashboard.html')


@app.route('/ripper')
def ripper():
    """Component Ripper interface"""
    return render_template('component_ripper_ui.html')


@app.route('/glossary')
def glossary():
    """Glossary and metric explanations"""
    return render_template('glossary.html')


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Server is running'})


@app.route('/api/deep-scan', methods=['POST'])
def deep_scan():
    """Run deep evidence extraction with 20+ metrics"""
    data = request.json
    site_url = data.get('site_url')
    analysis_mode = data.get('analysis_mode', 'single')  # 'single' or 'smart-nav'

    site_url, url_error = validate_url(site_url)
    if url_error:
        return jsonify({'error': url_error}), 400

    try:
        print(f"\n{'='*70}")
        print(f" 🔍 DEEP SCAN: {site_url}")
        print(f" 📊 Mode: {analysis_mode}")
        print('='*70)

        engine = DeepEvidenceEngine(site_url, analysis_mode=analysis_mode)
        evidence = run_async(engine.extract_all())

        print("\n✅ Deep scan complete!")
        print(f"   Extracted {len(evidence)} metric categories")

        # Clean up evidence (remove None values, errors)
        cleaned_evidence = {k: v for k, v in evidence.items() if v is not None}

        return jsonify({
            'success': True,
            'evidence': cleaned_evidence
        })

    except TimeoutError as e:
        print(f"\n⚠️  Timeout error: {str(e)}")
        return jsonify({
            'error': 'Site took too long to load. Try a lighter page or increase timeout.',
            'suggestion': 'Try analyzing a specific page like /about or /contact instead of the homepage.'
        }), 408

    except Exception as e:
        logger.error(f"Error during scan: {e}", exc_info=True)
        return jsonify({
            'error': 'Scan failed. The site may be blocking automated access or is temporarily unavailable.',
            'suggestion': 'Try a different page or check server logs for details.'
        }), 500


@app.route('/api/rip-component', methods=['POST'])
def rip_component():
    """
    Component Ripper - Extract exact blueprint of a specific component

    Request body:
    {
        "site_url": "https://ssense.com/en-us/men",
        "selector": ".product-grid",  # Optional - auto-detect if not provided
        "auth_state": null  # Optional - path to saved auth state
    }
    """
    data = request.json
    site_url = data.get('site_url')
    selector = data.get('selector')  # Optional — use "auto" or omit for auto-detect
    if selector and selector.lower() == 'auto':
        selector = None
    auth_state = data.get('auth_state')  # Optional

    site_url, url_error = validate_url(site_url)
    if url_error:
        return jsonify({'error': url_error}), 400

    try:
        print(f"\n{'='*70}")
        print(f" 🔬 COMPONENT RIPPER: {site_url}")
        if selector:
            print(f"    Target: {selector}")
        else:
            print(f"    Mode: Auto-detect sections")
        print('='*70)

        ripper = ComponentRipper(site_url, selector)
        blueprint = run_async(ripper.rip(auth_state))

        print("\n✅ Component rip complete!")

        return jsonify({
            'success': True,
            'blueprint': blueprint
        })

    except Exception as e:
        logger.error(f"Error during component rip: {e}", exc_info=True)
        return jsonify({
            'error': 'Component extraction failed. Check if the selector exists on the page.',
            'suggestion': 'Try a more specific CSS selector or use auto-detect mode.'
        }), 500


@app.route('/api/extract-styles', methods=['POST'])
def extract_styles():
    """
    Extract computed styles from live elements

    Request body:
    {
        "site_url": "https://nts.live",
        "selector": ".channel-card",  # CSS selector to target
        "mode": "critical"  # "critical" or "full"
    }

    Returns actual pixel values instead of class names:
    - padding: "24px 32px" (not "p-6")
    - background: "#f7f7f7" (not "bg-gray-100")
    """
    data = request.json
    site_url = data.get('site_url')
    selector = data.get('selector', 'nav')  # Default to nav
    mode = data.get('mode', 'critical')  # critical or full

    if not selector:
        return jsonify({'error': 'CSS selector required'}), 400

    site_url, url_error = validate_url(site_url)
    if url_error:
        return jsonify({'error': url_error}), 400

    try:
        print(f"\n{'='*70}")
        print(f" 🎨 COMPUTED STYLE EXTRACTION: {site_url}")
        print(f"    Selector: {selector}")
        print(f"    Mode: {mode}")
        print('='*70)

        async def extract():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                page.set_default_timeout(60000)

                # Load page
                await page.goto(site_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(2)

                # Create extractor
                extractor = ComputedStyleExtractor(page)

                # Extract styles based on mode
                if mode == 'critical':
                    result = await extractor.extract_critical_values(selector)
                else:
                    result = await extractor.extract_computed_styles(selector)

                # Generate CSS if found
                if result.get('found'):
                    css = extractor.generate_copy_paste_css(result)
                    result['generated_css'] = css

                await browser.close()
                return result

        result = run_async(extract())

        print("\n✅ Style extraction complete!")

        return jsonify({
            'success': True,
            'styles': result
        })

    except Exception as e:
        logger.error(f"Error during style extraction: {e}", exc_info=True)
        return jsonify({
            'error': 'Style extraction failed. Check if the selector exists on the page.',
            'suggestion': 'Try inspecting the page first to verify the selector.'
        }), 500


@app.route('/api/discover-urls', methods=['POST'])
def discover_urls():
    """
    Extract all links from a page for LLM navigation planning

    Request body:
    {
        "site_url": "https://pi.fyi"
    }

    Returns:
    {
        "base_url": "https://pi.fyi",
        "navigation_links": [...],
        "article_links": [...],
        "section_links": [...],
        "external_links": [...],
        "total_internal": 47
    }
    """
    data = request.json
    site_url = data.get('site_url')

    site_url, url_error = validate_url(site_url)
    if url_error:
        return jsonify({'error': url_error}), 400

    try:
        print(f"\n{'='*70}")
        print(f" 🔗 URL DISCOVERY: {site_url}")
        print('='*70)

        async def discover():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                page.set_default_timeout(60000)

                # Load page
                await page.goto(site_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(2)

                # Create engine to use link discovery
                engine = DeepEvidenceEngine(site_url)
                links = await engine._discover_links(page, site_url)

                await browser.close()
                return links

        links = run_async(discover())

        print(f"\n✅ Found {len(links.get('all', []))} total links")
        print(f"   Navigation: {len(links.get('navigation', []))}")
        print(f"   Articles: {len(links.get('articles', []))}")
        print(f"   Sections: {len(links.get('sections', []))}")

        return jsonify({
            'success': True,
            'base_url': site_url,
            'discovered_links': links
        })

    except Exception as e:
        logger.error(f"Error during URL discovery: {e}", exc_info=True)
        return jsonify({
            'error': 'URL discovery failed. The site may be blocking automated access.',
            'suggestion': 'Try a different page or check server logs.'
        }), 500


@app.route('/api/batch-analyze', methods=['POST'])
def batch_analyze():
    """
    Analyze multiple URLs in one request (for LLMs)

    Request body:
    {
        "urls": ["https://pi.fyi", "https://pi.fyi/editorial", "https://pi.fyi/p/article"]
    }

    Returns:
    {
        "results": {
            "https://pi.fyi": { ...evidence... },
            "https://pi.fyi/editorial": { ...evidence... }
        }
    }
    """
    data = request.json
    urls = data.get('urls', [])

    if not urls:
        return jsonify({'error': 'URLs array required'}), 400

    # Limit to 5 URLs to prevent overload
    urls = urls[:5]

    # Validate all URLs upfront
    validated_urls = []
    for url in urls:
        valid_url, url_error = validate_url(url)
        if url_error:
            return jsonify({'error': f'Invalid URL "{url}": {url_error}'}), 400
        validated_urls.append(valid_url)

    try:
        print(f"\n{'='*70}")
        print(f" 📊 BATCH ANALYSIS: {len(validated_urls)} URLs")
        print('='*70)

        async def analyze_batch():
            results = {}

            for i, url in enumerate(validated_urls, 1):
                print(f"\n[{i}/{len(validated_urls)}] Analyzing: {url}")

                try:
                    engine = DeepEvidenceEngine(url)
                    evidence = await engine.extract_all()
                    results[url] = evidence
                    print(f"   ✅ Complete")
                except Exception as e:
                    print(f"   ❌ Failed: {str(e)[:100]}")
                    results[url] = {
                        'error': 'Analysis failed for this URL',
                        'success': False
                    }

            return results

        results = run_async(analyze_batch())

        print(f"\n✅ Batch analysis complete!")
        print(f"   Successful: {sum(1 for r in results.values() if not r.get('error'))}/{len(validated_urls)}")

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        logger.error(f"Error during batch analysis: {e}", exc_info=True)
        return jsonify({
            'error': 'Batch analysis failed. Check server logs for details.'
        }), 500


@app.route('/api/export-markdown', methods=['POST'])
def export_markdown():
    """Export analysis as markdown"""
    data = request.json
    evidence = data.get('evidence')

    if not evidence:
        return jsonify({'error': 'No evidence data provided'}), 400

    # Generate markdown
    markdown = generate_markdown_report(evidence)

    return jsonify({
        'success': True,
        'markdown': markdown
    })


def generate_markdown_report(evidence):
    """Generate comprehensive markdown report"""
    md = f"# Website Analysis Report\n\n"
    md += f"**URL:** {evidence.get('meta_info', {}).get('url', 'Unknown')}\n\n"

    # Layout
    if 'layout' in evidence:
        md += f"## 📐 Layout System\n\n"
        md += f"**Pattern:** {evidence['layout']['pattern']}\n"
        md += f"**Confidence:** {evidence['layout']['confidence']}%\n\n"
        if evidence['layout'].get('code_snippets'):
            md += f"```css\n{evidence['layout']['code_snippets']}\n```\n\n"

    # Typography
    if 'typography' in evidence:
        md += f"## 🖋️ Typography\n\n"
        md += f"**Pattern:** {evidence['typography']['pattern']}\n"
        md += f"**Type Scale:** {evidence['typography'].get('type_scale', 'N/A')}\n\n"
        if evidence['typography'].get('code_snippets'):
            md += f"```css\n{evidence['typography']['code_snippets']}\n```\n\n"

    # Accessibility
    if 'accessibility' in evidence:
        md += f"## ♿ Accessibility\n\n"
        md += f"**Score:** {evidence['accessibility'].get('score', 0)}/100\n\n"
        if evidence['accessibility'].get('recommendations'):
            md += f"**Recommendations:**\n"
            for rec in evidence['accessibility']['recommendations']:
                md += f"- {rec}\n"
            md += "\n"

    # Performance
    if 'performance' in evidence:
        md += f"## ⚡ Performance\n\n"
        md += f"**Load Time:** {evidence['performance']['pattern']}\n\n"
        if evidence['performance'].get('recommendations'):
            md += f"**Recommendations:**\n"
            for rec in evidence['performance']['recommendations']:
                md += f"- {rec}\n"
            md += "\n"

    # SEO
    if 'seo' in evidence:
        md += f"## 🔍 SEO\n\n"
        md += f"**Score:** {evidence['seo'].get('score', 0)}/100\n\n"
        seo_details = evidence['seo'].get('details', {})
        md += f"- **Title:** {seo_details.get('title', 'N/A')}\n"
        md += f"- **Description:** {seo_details.get('description', 'N/A')}\n"
        md += f"- **H1 Count:** {seo_details.get('h1_count', 0)}\n\n"

    # Security
    if 'security' in evidence:
        md += f"## 🔒 Security\n\n"
        md += f"**Score:** {evidence['security'].get('score', 0)}/100\n\n"
        if evidence['security'].get('recommendations'):
            md += f"**Recommendations:**\n"
            for rec in evidence['security']['recommendations']:
                md += f"- {rec}\n"
            md += "\n"

    # Articles
    if 'article_content' in evidence and evidence['article_content'].get('articles'):
        md += f"## 📄 Extracted Articles\n\n"
        for article in evidence['article_content']['articles']:
            md += f"### {article['title']}\n\n"
            md += f"- **Author:** {article['author']}\n"
            md += f"- **Date:** {article.get('date', 'N/A')}\n"
            md += f"- **Confidence:** {article['confidence']}%\n"
            md += f"- **Status:** {article['status']}\n"
            md += f"- **Word Count:** {article['word_count']}\n\n"
            md += f"{article['preview']}\n\n"

    # API Patterns
    if 'api_patterns' in evidence:
        md += f"## 📡 API Patterns\n\n"
        md += f"**Pattern:** {evidence['api_patterns']['pattern']}\n"
        if evidence['api_patterns'].get('code_snippets'):
            md += f"\n```javascript\n{evidence['api_patterns']['code_snippets']}\n```\n\n"

    # CSS Tricks
    if 'css_tricks' in evidence and evidence['css_tricks'].get('details', {}).get('custom_properties'):
        md += f"## 🎯 CSS Tricks\n\n"
        md += f"**Custom Properties:** {len(evidence['css_tricks']['details']['custom_properties'])}\n\n"
        if evidence['css_tricks'].get('code_snippets'):
            md += f"```css\n{evidence['css_tricks']['code_snippets']}\n```\n\n"

    # Meta Info
    if 'meta_info' in evidence:
        md += f"## 📊 Technical Summary\n\n"
        md += f"- **Total DOM Nodes:** {evidence['meta_info'].get('total_dom_nodes', 0):,}\n"
        md += f"- **Total Network Requests:** {evidence['meta_info'].get('total_requests', 0)}\n\n"

    md += f"---\n\n"
    md += f"*Report generated by Web Intelligence Dashboard*\n"

    return md


@app.route('/api/generate-summary', methods=['POST'])
def generate_ai_summary():
    """
    Generate plain English summary using Claude API

    Input: Full evidence JSON from deep scan
    Output: 3-5 sentence executive summary
    """
    try:
        evidence = request.json.get('evidence')

        if not evidence:
            return jsonify({'error': 'No evidence provided'}), 400

        # Check if API key is configured
        if not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") == "your_api_key_here":
            return jsonify({
                'error': 'Anthropic API key not configured',
                'summary': '📝 AI summary requires an Anthropic API key. Add ANTHROPIC_API_KEY to your .env file.',
                'generated_at': datetime.now().isoformat()
            }), 400

        # Extract key metrics for summary
        summary_context = {
            'url': evidence.get('meta_info', {}).get('url', 'Unknown'),
            'colors_count': len(evidence.get('colors', {}).get('primary_colors', [])),
            'typography_families': len(evidence.get('typography', {}).get('font_families', [])),
            'typography_sizes': len(evidence.get('typography', {}).get('font_sizes', [])),
            'spacing_scale': evidence.get('spacing_scale', {}).get('scale', []),
            'breakpoints': len(evidence.get('responsive_breakpoints', {}).get('breakpoints', [])),
            'shadow_levels': len(evidence.get('shadow_system', {}).get('elevation_levels', [])),
            'layout_type': evidence.get('layout_system', {}).get('primary_layout_type', 'Unknown'),
            'hero_count': len(evidence.get('visual_hierarchy', {}).get('hero_sections', [])),
            'cta_count': len(evidence.get('visual_hierarchy', {}).get('ctas', [])),
        }

        # Use plain language summaries if available
        summaries_available = []
        if evidence.get('shadow_system', {}).get('summary'):
            summaries_available.append(f"Shadows: {evidence['shadow_system']['summary']['description']}")
        if evidence.get('colors', {}).get('summary'):
            summaries_available.append(f"Colors: {evidence['colors']['summary']['description']}")
        if evidence.get('spacing_scale', {}).get('summary'):
            summaries_available.append(f"Spacing: {evidence['spacing_scale']['summary']['description']}")

        # Build summaries section (avoid backslash in f-string)
        summaries_section = ''
        if summaries_available:
            summaries_section = 'Metric Summaries:\n' + '\n'.join(summaries_available)

        prompt = f"""You are a design system analyst explaining findings to a non-technical audience.

Based on this website analysis:

URL: {summary_context['url']}

Quick Stats:
• Colors: {summary_context['colors_count']} primary colors
• Typography: {summary_context['typography_families']} font families, {summary_context['typography_sizes']} text sizes
• Spacing: {len(summary_context['spacing_scale'])} spacing increments
• Breakpoints: {summary_context['breakpoints']} responsive breakpoints
• Shadows: {summary_context['shadow_levels']} elevation levels
• Layout: {summary_context['layout_type']}
• Visual Hierarchy: {summary_context['hero_count']} hero sections, {summary_context['cta_count']} CTAs

{summaries_section}

Generate a 3-5 sentence summary that:
1. Highlights the most important findings
2. Uses plain language (no jargon like "z-index", "DOM", "heuristics")
3. Mentions design system consistency (strict vs flexible)
4. Includes ONE actionable recommendation

Format:
📝 This site has:
• [Key finding 1]
• [Key finding 2]
• [Key finding 3]

Recommendation: [One actionable insight based on the evidence]

Keep it concise and valuable for designers/PMs."""

        response = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        summary_text = response.content[0].text

        return jsonify({
            'summary': summary_text,
            'generated_at': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"AI summary generation failed: {e}", exc_info=True)
        return jsonify({
            'error': 'Summary generation failed',
            'summary': '📝 AI summary could not be generated. Please check server logs for details.'
        }), 500


@app.route('/api/generate-starter-template', methods=['POST'])
def generate_starter_template():
    """
    Generate starter HTML template from deep scan evidence

    Request body:
    {
        "evidence": {...}  # Evidence from deep-scan endpoint
    }

    Returns: HTML string ready to save as starter.html
    """
    from starter_template_generator import StarterTemplateGenerator

    data = request.json
    evidence = data.get('evidence')

    if not evidence:
        return jsonify({'error': 'Evidence data required'}), 400

    try:
        generator = StarterTemplateGenerator(evidence)
        html = generator.generate()

        return jsonify({
            'success': True,
            'html': html,
            'size': len(html),
            'message': 'Starter template generated successfully'
        })

    except Exception as e:
        logger.error(f"Error generating starter template: {e}", exc_info=True)
        return jsonify({
            'error': 'Starter template generation failed. Check server logs for details.'
        }), 500


@app.route('/api/generate-design-brief', methods=['POST'])
def generate_design_brief():
    """
    Generate design brief from deep scan evidence

    Request body:
    {
        "evidence": {...}  # Evidence from deep-scan endpoint
    }

    Returns: Design brief object with sections
    """
    from design_brief_generator import DesignBriefGenerator

    data = request.json
    evidence = data.get('evidence')

    if not evidence:
        return jsonify({'error': 'Evidence data required'}), 400

    try:
        generator = DesignBriefGenerator(evidence)
        brief = generator.generate()

        return jsonify({
            'success': True,
            'brief': brief,
            'message': 'Design brief generated successfully'
        })

    except Exception as e:
        logger.error(f"Error generating design brief: {e}", exc_info=True)
        return jsonify({
            'error': 'Design brief generation failed. Check server logs for details.'
        }), 500


@app.route('/api/full-analysis', methods=['POST'])
def full_analysis():
    """
    Complete analysis workflow: deep scan + starter template + design brief

    Request body:
    {
        "site_url": "https://stripe.com",
        "analysis_mode": "single"  # or "smart-nav"
    }

    Returns: Evidence + starter HTML + design brief all in one
    """
    from starter_template_generator import StarterTemplateGenerator
    from design_brief_generator import DesignBriefGenerator

    data = request.json
    site_url = data.get('site_url')
    analysis_mode = data.get('analysis_mode', 'single')

    site_url, url_error = validate_url(site_url)
    if url_error:
        return jsonify({'error': url_error}), 400

    try:
        print(f"\n{'='*70}")
        print(f" 🎯 FULL ANALYSIS: {site_url}")
        print(f" 📊 Mode: {analysis_mode}")
        print('='*70)

        async def run_full():
            # Step 1: Deep scan
            print("\n1️⃣  Running deep scan...")
            engine = DeepEvidenceEngine(site_url, analysis_mode=analysis_mode)
            evidence = await engine.extract_all()
            return {k: v for k, v in evidence.items() if v is not None}

        cleaned_evidence = run_async(run_full())

        # Step 2: Generate starter template
        print("2️⃣  Generating starter template...")
        template_generator = StarterTemplateGenerator(cleaned_evidence)
        starter_html = template_generator.generate()

        # Step 3: Generate design brief
        print("3️⃣  Generating design brief...")
        brief_generator = DesignBriefGenerator(cleaned_evidence)
        design_brief = brief_generator.generate()

        print("\n✅ Full analysis complete!")

        return jsonify({
            'success': True,
            'evidence': cleaned_evidence,
            'starter_html': starter_html,
            'design_brief': design_brief,
            'message': 'Complete analysis finished - evidence, starter template, and design brief ready'
        })

    except Exception as e:
        logger.error(f"Error during full analysis: {e}", exc_info=True)
        return jsonify({
            'error': 'Full analysis failed. Check server logs for details.'
        }), 500


@app.route('/api/export-dtcg-tokens', methods=['POST'])
def export_dtcg_tokens():
    """
    Export design tokens in W3C DTCG format

    Request body:
    {
        "evidence": {...}  # Evidence from deep-scan
    }

    Returns: DTCG-compliant JSON tokens
    """
    from dtcg_token_exporter import DTCGTokenExporter

    data = request.json
    evidence = data.get('evidence')

    if not evidence:
        return jsonify({'error': 'Evidence data required'}), 400

    try:
        exporter = DTCGTokenExporter(evidence)
        tokens = exporter.export()
        token_counts = exporter.get_token_count()

        return jsonify({
            'success': True,
            'tokens': tokens,
            'token_counts': token_counts,
            'message': 'DTCG tokens exported successfully'
        })

    except Exception as e:
        logger.error(f"Error exporting DTCG tokens: {e}", exc_info=True)
        return jsonify({'error': 'DTCG token export failed. Check server logs for details.'}), 500


@app.route('/api/export-tailwind-config', methods=['POST'])
def export_tailwind_config():
    """
    Export Tailwind CSS configuration

    Request body:
    {
        "evidence": {...}  # Evidence from deep-scan
    }

    Returns: tailwind.config.js as string
    """
    from tailwind_config_generator import TailwindConfigGenerator

    data = request.json
    evidence = data.get('evidence')

    if not evidence:
        return jsonify({'error': 'Evidence data required'}), 400

    try:
        generator = TailwindConfigGenerator(evidence)
        config = generator.generate()

        return jsonify({
            'success': True,
            'config': config,
            'size': len(config),
            'message': 'Tailwind config generated successfully'
        })

    except Exception as e:
        logger.error(f"Error generating Tailwind config: {e}", exc_info=True)
        return jsonify({'error': 'Tailwind config generation failed. Check server logs for details.'}), 500


@app.route('/api/compare-sites', methods=['POST'])
def compare_sites():
    """
    Compare design systems of two sites

    Request body:
    {
        "site_a": "https://stripe.com",
        "site_b": "https://tailwindcss.com",
        "site_a_name": "Stripe",  # Optional
        "site_b_name": "Tailwind"  # Optional
    }

    Returns: Detailed comparison with differences
    """
    from design_system_differ import DesignSystemDiffer

    data = request.json
    site_a_url = data.get('site_a')
    site_b_url = data.get('site_b')
    site_a_name = data.get('site_a_name', 'Site A')
    site_b_name = data.get('site_b_name', 'Site B')

    site_a_url, err_a = validate_url(site_a_url)
    if err_a:
        return jsonify({'error': f'site_a: {err_a}'}), 400

    site_b_url, err_b = validate_url(site_b_url)
    if err_b:
        return jsonify({'error': f'site_b: {err_b}'}), 400

    try:
        print(f"\n{'='*70}")
        print(f" 🔍 SITE COMPARISON")
        print(f" A: {site_a_url}")
        print(f" B: {site_b_url}")
        print('='*70)

        async def run_compare():
            # Analyze both sites
            print("\n1️⃣  Analyzing Site A...")
            engine_a = DeepEvidenceEngine(site_a_url, analysis_mode='single')
            evidence_a = await engine_a.extract_all()

            print("\n2️⃣  Analyzing Site B...")
            engine_b = DeepEvidenceEngine(site_b_url, analysis_mode='single')
            evidence_b = await engine_b.extract_all()

            return evidence_a, evidence_b

        evidence_a, evidence_b = run_async(run_compare())

        # Compare
        print("\n3️⃣  Comparing design systems...")
        differ = DesignSystemDiffer(evidence_a, evidence_b, site_a_name, site_b_name)
        comparison = differ.compare()

        print("\n✅ Comparison complete!")

        return jsonify({
            'success': True,
            'comparison': comparison,
            'site_a_evidence': evidence_a,
            'site_b_evidence': evidence_b,
            'message': 'Design system comparison complete'
        })

    except Exception as e:
        logger.error(f"Error during comparison: {e}", exc_info=True)
        return jsonify({'error': 'Site comparison failed. Check server logs for details.'}), 500


@app.route('/api/extract-component-library', methods=['POST'])
def extract_component_library():
    """
    Extract multiple components in batch mode

    Request body:
    {
        "site_url": "https://stripe.com",
        "selectors": ["nav", ".hero", "footer", ".pricing-card"]
    }

    Returns: Dictionary of component blueprints
    """
    data = request.json
    site_url = data.get('site_url')
    selectors = data.get('selectors', [])

    site_url, url_error = validate_url(site_url)
    if url_error:
        return jsonify({'error': url_error}), 400

    if not selectors or not isinstance(selectors, list):
        return jsonify({'error': 'selectors must be a non-empty array'}), 400

    try:
        print(f"\n{'='*70}")
        print(f" 🔬 COMPONENT LIBRARY EXTRACTION")
        print(f" URL: {site_url}")
        print(f" Components: {len(selectors)}")
        print('='*70)

        ripper = ComponentRipper(site_url)
        components = run_async(ripper.rip_batch(selectors))

        print("\n✅ Component library extraction complete!")

        return jsonify({
            'success': True,
            'components': components,
            'count': len(components),
            'message': f'Extracted {len(components)} components'
        })

    except Exception as e:
        logger.error(f"Error during component extraction: {e}", exc_info=True)
        return jsonify({'error': 'Component library extraction failed. Check server logs for details.'}), 500


if __name__ == '__main__':
    print("\n" + "="*70)
    print(" 🔍 WEB INTELLIGENCE DASHBOARD")
    print("="*70)
    print("\n   Starting server...")
    print("\n   Open your browser and go to:")
    print("\n   👉 http://localhost:8080")
    print("\n   Features:")
    print("      • 20+ Metric Categories")
    print("      • Layout, Typography, Colors, Animations")
    print("      • Accessibility, Performance, SEO, Security")
    print("      • API Pattern Detection")
    print("      • CSS Tricks & Advanced Techniques")
    print("      • Article Content Extraction")
    print("      • Confidence Scoring")
    print("      • Markdown Export")
    print("      • Debug View with Network Traces")
    print("      • Analytics Dashboard")
    print("\n   Example Sites to Test:")
    print("      • https://nts.live")
    print("      • https://ssense.com")
    print("      • https://stripe.com/docs")
    print("      • https://css-tricks.com/article")
    print("\n" + "="*70 + "\n")

    # Kill old servers
    import subprocess

    logging.basicConfig(level=logging.INFO)

    try:
        subprocess.run(['pkill', '-f', 'web_interface'], check=False)
    except Exception as e:
        logger.debug(f"Could not kill old servers (non-critical): {e}")

    # Bind to localhost only — never expose to network with debug=True
    app.run(debug=True, port=8080, host='127.0.0.1')
