"""
Visual Hierarchy Analyzer

Detects:
1. Hero section (CV-based visual salience + fallback heuristic)
2. Primary CTA (most prominent button)
3. Navigation hierarchy (header → nav → sections)
4. Content groupings (cards, grids, lists)
5. Reading order (F-pattern, Z-pattern detection)
6. Visual weight scoring (computer vision + heuristic fallback)

Philosophy: "What does the eye see first?"

CV Enhancement: Uses OpenCV visual salience detector for robust hero detection
"""

from typing import Dict, List, Tuple

# Import CV detector (graceful fallback if not available)
try:
    from visual_salience_detector import VisualSalienceDetector
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False
    print("⚠️  OpenCV not available - using heuristic hero detection")


class VisualHierarchyAnalyzer:
    """
    Analyze visual hierarchy of a web page
    """

    def __init__(self):
        self.hierarchy = {}

    async def analyze(self, page) -> Dict:
        """
        Comprehensive visual hierarchy analysis

        Returns:
            {
                'hero_section': {...},
                'primary_cta': {...},
                'navigation': {...},
                'content_groups': [...],
                'reading_pattern': 'F-pattern' | 'Z-pattern' | 'Grid',
                'visual_weight_map': [...],
                'attention_flow': [...]
            }
        """
        print("   👁️  Analyzing visual hierarchy...")

        # Extract visual hierarchy data
        hierarchy_data = await page.evaluate('''() => {
            const elements = [...document.querySelectorAll('*')];
            const viewport = {
                width: window.innerWidth,
                height: window.innerHeight
            };

            // Calculate visual weight for each element
            const weightedElements = elements.map(el => {
                const rect = el.getBoundingClientRect();
                const styles = window.getComputedStyle(el);

                // Skip invisible elements
                if (rect.width === 0 || rect.height === 0 || styles.display === 'none' || styles.visibility === 'hidden') {
                    return null;
                }

                // Calculate visual weight score
                const size = rect.width * rect.height;
                const aboveFold = rect.top >= 0 && rect.top < viewport.height;
                const zIndex = parseInt(styles.zIndex) || 0;
                const fontSize = parseFloat(styles.fontSize) || 0;

                // Color contrast (simplified)
                const color = styles.color;
                const bgColor = styles.backgroundColor;

                // Visual weight: size and font are primary signals.
                // z-index is a tiebreaker, not a multiplier — capped and scaled
                // by area so tiny overlays (arrows at z999) don't drown real content.
                const role = el.getAttribute('role');
                const ariaLabel = el.getAttribute('aria-label');
                const tagName = el.tagName.toLowerCase();

                // Nav/header structural elements: cap sizeScore to prevent
                // full-width elements from dominating the visual weight map.
                const isNavStructural = tagName === 'nav' || role === 'navigation' || role === 'banner'
                    || (tagName === 'header' && rect.width > viewport.width * 0.8);
                const sizeScore = isNavStructural ? Math.min(size * 0.0001, 5.0) : size * 0.0001;
                const foldBonus = aboveFold ? 50 : 0;                     // above-fold lift
                const fontScore = fontSize * 3;                           // text size matters
                const zBonus = zIndex > 0 ? Math.min(zIndex, 50) * (size * 0.0005) : 0;  // z-index scaled by size, capped at 50

                // Semantic importance bonus
                let semanticBonus = 0;

                // Navigation elements — structural, not the visual focus
                if (tagName === 'nav' || role === 'navigation' || role === 'banner') {
                    semanticBonus = 200;  // Reduced from 500 — nav is structural, not hero
                }
                // Header elements
                else if (tagName === 'header' && rect.top < viewport.height * 0.2) {
                    semanticBonus = 250;  // Reduced from 400
                }
                // Main content area
                else if (tagName === 'main' || role === 'main') {
                    semanticBonus = 150;  // Increased from 100
                }
                // Article headings (important text)
                else if (tagName.match(/^h[1-3]$/)) {
                    semanticBonus = 120;  // Increased from 80
                }
                // Footer (visible but lower priority)
                else if (tagName === 'footer' || role === 'contentinfo') {
                    semanticBonus = 50;  // Increased from 30
                }

                const weight = sizeScore + foldBonus + fontScore + zBonus + semanticBonus;

                // SVG elements have className as SVGAnimatedString, not a plain string
                const safeClassName = (typeof el.className === 'string') ? el.className : (el.className?.baseVal || '');

                return {
                    tag: el.tagName.toLowerCase(),
                    text: el.textContent?.substring(0, 100) || '',
                    className: safeClassName,
                    id: el.id,
                    weight: weight,
                    isNavStructural: isNavStructural,
                    rect: {
                        top: rect.top,
                        left: rect.left,
                        width: rect.width,
                        height: rect.height
                    },
                    styles: {
                        fontSize: fontSize,
                        color: color,
                        backgroundColor: bgColor,
                        fontWeight: styles.fontWeight,
                        zIndex: zIndex
                    },
                    aboveFold: aboveFold
                };
            }).filter(el => el !== null);

            // Sort by visual weight, excluding nav/header structural elements
            // from the ranked visual hierarchy (they are shown separately)
            const sorted = weightedElements
                .filter(el => !el.isNavStructural)
                .sort((a, b) => b.weight - a.weight);

            // Detect hero section (largest heading + nearby image)
            const heroHeading = sorted.find(el =>
                (el.tag === 'h1' || el.tag === 'h2') &&
                el.aboveFold &&
                el.text.length > 10
            );

            // Detect primary CTA (most prominent button with action-oriented text)
            const buttons = sorted.filter(el =>
                el.tag === 'button' ||
                el.tag === 'a' && (el.className.includes('btn') || el.className.includes('button'))
            );

            // Bug 2 Fix: Score buttons by CTA likelihood
            const actionWords = ['start', 'get', 'try', 'sign up', 'signup', 'buy', 'shop', 'join', 'subscribe', 'download', 'free', 'demo'];
            const scoredButtons = buttons.map(btn => {
                const textLower = btn.text.toLowerCase();
                let ctaScore = btn.weight; // Start with visual weight

                // Boost for action-oriented text
                const hasActionWord = actionWords.some(word => textLower.includes(word));
                if (hasActionWord) {
                    ctaScore += 300; // Significant boost for action words
                }

                // Boost for button tag (more likely CTA than link)
                if (btn.tag === 'button') {
                    ctaScore += 100;
                }

                // Boost for primary/cta class names
                if (btn.className.includes('primary') || btn.className.includes('cta')) {
                    ctaScore += 200;
                }

                return { ...btn, ctaScore };
            });

            // Sort by CTA score instead of just visual weight
            scoredButtons.sort((a, b) => b.ctaScore - a.ctaScore);
            const primaryCTA = scoredButtons[0];

            // Detect navigation
            const nav = elements.find(el => el.tagName.toLowerCase() === 'nav');
            const navData = nav ? {
                exists: true,
                position: window.getComputedStyle(nav).position,
                top: nav.getBoundingClientRect().top
            } : { exists: false };

            // Detect content groupings
            const contentGroups = sorted.filter(el =>
                (el.className.includes('card') ||
                 el.className.includes('grid') ||
                 el.tag === 'article' ||
                 el.tag === 'section') &&
                el.rect.width > 200 &&
                el.rect.height > 100
            ).slice(0, 10);

            return {
                topElements: sorted.slice(0, 20),
                heroHeading: heroHeading,
                primaryCTA: primaryCTA,
                navigation: navData,
                contentGroups: contentGroups,
                viewport: viewport
            };
        }''')

        # Analyze patterns
        reading_pattern = self._detect_reading_pattern(hierarchy_data['topElements'])
        attention_flow = self._calculate_attention_flow(hierarchy_data['topElements'], hierarchy_data['viewport'])

        # Try CV-enhanced hero detection if available
        hero_sections = []
        detection_method = 'heuristic'

        if CV_AVAILABLE:
            try:
                cv_heroes = await self._cv_enhanced_hero_detection(page)
                if cv_heroes and len(cv_heroes) > 0:
                    hero_sections = cv_heroes
                    detection_method = 'computer_vision'
                    print("      ✅ CV hero detection successful")
            except Exception as e:
                print(f"      ⚠️  CV hero detection failed, using heuristic fallback: {str(e)}")
                hero_sections = [hierarchy_data.get('heroHeading')] if hierarchy_data.get('heroHeading') else []
        else:
            hero_sections = [hierarchy_data.get('heroHeading')] if hierarchy_data.get('heroHeading') else []

        return {
            'pattern': f"Visual hierarchy detected: {len(hierarchy_data['topElements'])} key elements",
            'confidence': 90 if detection_method == 'computer_vision' else 85,
            'hero_sections': hero_sections,  # CV returns list of candidates
            'hero_section': self._format_hero_section(hero_sections[0] if hero_sections else None),
            'detection_method': detection_method,
            'primary_cta': self._format_primary_cta(hierarchy_data.get('primaryCTA')),
            'navigation': hierarchy_data['navigation'],
            'content_groups': hierarchy_data['contentGroups'][:5],  # Top 5
            'reading_pattern': reading_pattern,
            'visual_weight_map': hierarchy_data['topElements'][:10],  # Top 10 weighted
            'attention_flow': attention_flow,
            'viewport': hierarchy_data['viewport']
        }

    async def _cv_enhanced_hero_detection(self, page) -> List[Dict]:
        """
        Computer vision-based hero detection

        Uses visual salience detector to find visually prominent elements.
        More robust than heuristics across diverse site types.
        """
        # Take screenshot for CV analysis
        screenshot_bytes = await page.screenshot(full_page=False)  # Above-the-fold only

        # Extract candidate elements with bounding boxes
        elements = await page.evaluate('''() => {
            const candidates = document.querySelectorAll('section, article, div, header, main');
            return Array.from(candidates).map(el => {
                const rect = el.getBoundingClientRect();
                const styles = window.getComputedStyle(el);

                // Filter out invisible/tiny elements
                if (rect.width < 100 || rect.height < 100) return null;
                if (styles.display === 'none' || styles.visibility === 'hidden') return null;

                // Safe className handling (SVG elements have SVGAnimatedString)
                const safeClassName = (typeof el.className === 'string') ?
                    el.className : (el.className?.baseVal || '');

                return {
                    selector: el.tagName.toLowerCase() +
                             (el.id ? '#' + el.id : '') +
                             (safeClassName ? '.' + safeClassName.split(' ')[0] : ''),
                    tag: el.tagName.toLowerCase(),
                    text: el.textContent?.substring(0, 100) || '',
                    className: safeClassName,
                    id: el.id,
                    bbox: {
                        x: Math.round(Math.max(0, rect.x)),
                        y: Math.round(Math.max(0, rect.y)),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    },
                    rect: {
                        top: rect.top,
                        left: rect.left,
                        width: rect.width,
                        height: rect.height
                    }
                };
            }).filter(el => el !== null);
        }''')

        if not elements or len(elements) == 0:
            return []

        # Run computer vision analysis
        detector = VisualSalienceDetector(screenshot_bytes)
        scored_elements = detector.find_hero_elements(elements)

        # Top 3 candidates with score > 400 are considered heroes
        heroes = [
            el for el in scored_elements[:3]
            if el.get('visual_weight', 0) > 400
        ]

        return heroes

    def _format_hero_section(self, hero) -> Dict:
        """Format hero section data"""
        if not hero:
            return {
                'detected': False,
                'message': 'No clear hero section detected'
            }

        return {
            'detected': True,
            'tag': hero['tag'],
            'text': hero['text'][:80] + '...' if len(hero['text']) > 80 else hero['text'],
            'position': f"top: {hero['rect']['top']}px",
            'size': f"{hero['rect']['width']}px × {hero['rect']['height']}px",
            'weight': round(hero['weight'], 1),
            'above_fold': hero['aboveFold']
        }

    def _format_primary_cta(self, cta) -> Dict:
        """Format primary CTA data"""
        if not cta:
            return {
                'detected': False,
                'message': 'No clear primary CTA detected'
            }

        return {
            'detected': True,
            'tag': cta['tag'],
            'text': cta['text'][:50] + '...' if len(cta['text']) > 50 else cta['text'],
            'position': f"top: {cta['rect']['top']}px, left: {cta['rect']['left']}px",
            'size': f"{cta['rect']['width']}px × {cta['rect']['height']}px",
            'weight': round(cta['weight'], 1),
            'className': cta['className']
        }

    def _detect_reading_pattern(self, elements: List[Dict]) -> str:
        """
        Detect reading pattern (F-pattern, Z-pattern, or Grid) based on element positions

        Heuristic: Analyzes spatial distribution of top 10 elements
        - F-pattern: 7+ elements with left < 300px (text-heavy, blog-style)
        - Z-pattern: 5+ elements with left > 500px (horizontal, landing pages)
        - Grid: Balanced distribution (ecommerce, galleries)

        Rationale:
        - F-pattern common in content sites (eyes scan left column)
        - Z-pattern in marketing pages (zigzag across headings/CTAs)
        - Grid for product listings and media galleries

        Confidence: Heuristic-based, not ML - treats as low confidence
        Failure modes:
        - Responsive designs may shift patterns at different breakpoints
        - Mixed layouts (header Z, content F) will classify by dominant pattern
        """
        # Simple heuristic:
        # F-pattern: Elements clustered on left side
        # Z-pattern: Elements spread horizontally
        # Grid: Evenly distributed

        left_heavy = sum(1 for el in elements[:10] if el['rect']['left'] < 300)
        spread = sum(1 for el in elements[:10] if el['rect']['left'] > 500)

        if left_heavy > 7:
            return 'F-pattern (Left-heavy, text-focused)'
        elif spread > 5:
            return 'Z-pattern (Horizontal spread)'
        else:
            return 'Grid layout (Balanced distribution)'

    def _calculate_attention_flow(self, elements: List[Dict], viewport: Dict = None) -> List[str]:
        """
        Calculate likely attention flow based on visual weight.
        Skips structural containers (html, body, div wrappers) that span
        the full page — those aren't what the eye actually lands on.

        Bug 3 Fix: Deduplicates nested elements by detecting text overlap.
        """
        # Tags that are pure layout containers, not visual targets
        SKIP_TAGS = {'html', 'body', 'head', 'script', 'style', 'noscript'}

        # Semantic tags that should ALWAYS be included (navigation, headers, main content)
        SEMANTIC_TAGS = {'nav', 'header', 'main', 'article', 'aside'}

        # Use real viewport or fall back to standard desktop
        vp_w = (viewport or {}).get('width', 1920)
        vp_h = (viewport or {}).get('height', 1080)

        flow = []
        added_texts = set()  # Track text content to avoid duplicates

        for el in elements:
            if len(flow) >= 10:  # Increased from 5 to 10 to ensure nav gets included
                break
            # Skip structural containers
            if el['tag'] in SKIP_TAGS:
                continue
            # Skip any element that spans >80% viewport width AND >200% viewport height —
            # UNLESS it's a semantic tag (nav, header, etc.)
            if el['tag'] not in SEMANTIC_TAGS:
                if el['rect']['width'] > vp_w * 0.8 and el['rect']['height'] > vp_h * 2:
                    continue

            # Bug 3 Fix: Skip if we've already added an element with same/similar text
            el_text = el['text'][:40].strip().lower()
            if el_text and len(el_text) > 3:  # Only check non-trivial text
                # Check if this text is a substring of any previously added text, or vice versa
                is_duplicate = False
                for added_text in added_texts:
                    if el_text in added_text or added_text in el_text:
                        # This is likely a nested element (parent/child)
                        is_duplicate = True
                        break

                if is_duplicate:
                    continue  # Skip this duplicate

                added_texts.add(el_text)

            step = f"{len(flow)+1}. {el['tag'].upper()}"
            if el['text']:
                step += f" - '{el['text'][:40]}...'"
            step += f" (weight: {round(el['weight'], 1)})"
            flow.append(step)

        return flow


# Integration test
async def test_visual_hierarchy():
    """Test visual hierarchy analysis"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto('https://stripe.com', wait_until='networkidle')

        analyzer = VisualHierarchyAnalyzer()
        result = await analyzer.analyze(page)

        print("\n" + "="*70)
        print(" 👁️  VISUAL HIERARCHY ANALYSIS")
        print("="*70)

        print("\n🦸 Hero Section:")
        hero = result['hero_section']
        if hero['detected']:
            print(f"   Tag: {hero['tag']}")
            print(f"   Text: {hero['text']}")
            print(f"   Position: {hero['position']}")
            print(f"   Weight: {hero['weight']}")
        else:
            print(f"   {hero['message']}")

        print("\n🎯 Primary CTA:")
        cta = result['primary_cta']
        if cta['detected']:
            print(f"   Tag: {cta['tag']}")
            print(f"   Text: {cta['text']}")
            print(f"   Position: {cta['position']}")
        else:
            print(f"   {cta['message']}")

        print(f"\n🧭 Navigation: {'✅ Detected' if result['navigation']['exists'] else '❌ Not found'}")

        print(f"\n📖 Reading Pattern: {result['reading_pattern']}")

        print("\n👀 Attention Flow (Top 5):")
        for step in result['attention_flow']:
            print(f"   {step}")

        print(f"\n📦 Content Groups: {len(result['content_groups'])} detected")

        await browser.close()

        print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_visual_hierarchy())
