"""
Spatial Composition Analyzer

Captures the 50-60% gap: HOW pieces fit together spatially

This bridges the gap between:
- What we have: Design tokens (fonts, colors, spacing)
- What we need: Spatial relationships and layout composition

Extracts:
1. Page Layout Structure - Detects common patterns (hero + 3-col + CTA)
2. Spatial Relationships - Which elements are beside/below/inside each other
3. Component Zones - Semantic regions with bounding boxes
4. Alignment Patterns - Left-aligned, centered, split, etc.
5. Whitespace Analysis - Density and breathing room
6. Above-the-Fold Layout - What users see immediately
7. Container Hierarchies - Flex/Grid parent-child relationships
8. Layout Grid Detection - 12-column, asymmetric, etc.

Philosophy: "How do the pieces fit together?"
"""

from typing import Dict, List, Tuple, Optional
from playwright.async_api import Page
import json


class SpatialCompositionAnalyzer:
    """
    Analyze spatial relationships and layout composition
    """

    def __init__(self):
        self.composition = {}

    async def analyze(self, page: Page) -> Dict:
        """
        Comprehensive spatial composition analysis

        Returns:
            {
                'page_structure': {...},        # Overall layout pattern
                'spatial_relationships': {...}, # Element relationships
                'component_zones': [...],       # Semantic regions
                'alignment_patterns': {...},    # How things align
                'whitespace_analysis': {...},   # Density and spacing
                'above_fold_layout': {...},     # Initial viewport
                'container_hierarchy': {...},   # Flex/grid nesting
                'layout_grid': {...}            # Column system detection
            }
        """
        print("   🗺️  Analyzing spatial composition...")

        # Extract viewport-aware spatial data
        spatial_data = await self._extract_spatial_data(page)

        # Analyze page structure patterns
        page_structure = await self._analyze_page_structure(spatial_data)

        # Extract spatial relationships
        relationships = self._extract_relationships(spatial_data['elements'])

        # Detect component zones
        zones = self._detect_component_zones(spatial_data['elements'])

        # Analyze alignment patterns
        alignment = self._analyze_alignment(spatial_data['elements'])

        # Analyze whitespace
        whitespace = self._analyze_whitespace(spatial_data)

        # Above-fold analysis
        above_fold = self._analyze_above_fold(spatial_data)

        # Container hierarchy
        hierarchy = self._analyze_container_hierarchy(spatial_data['containers'])

        # Layout grid detection
        grid_system = self._detect_layout_grid(spatial_data['elements'])

        return {
            'pattern': f"Spatial composition analyzed: {len(spatial_data['elements'])} elements, {len(zones)} zones",
            'confidence': self._calculate_confidence(spatial_data),
            'page_structure': page_structure,
            'spatial_relationships': relationships,
            'component_zones': zones,
            'alignment_patterns': alignment,
            'whitespace_analysis': whitespace,
            'above_fold_layout': above_fold,
            'container_hierarchy': hierarchy,
            'layout_grid': grid_system,
            'viewport': spatial_data['viewport']
        }

    async def _extract_spatial_data(self, page: Page) -> Dict:
        """
        Extract comprehensive spatial data from the page

        Captures:
        - Element positions, sizes, and visual properties
        - Container relationships (flex/grid parents)
        - Viewport dimensions
        - Semantic HTML structure
        """
        return await page.evaluate('''() => {
            const viewport = {
                width: window.innerWidth,
                height: window.innerHeight
            };

            // Get all visible elements with spatial data
            const elements = [];
            const containers = [];
            const allElements = document.querySelectorAll('body *');

            for (const el of allElements) {
                const rect = el.getBoundingClientRect();
                const styles = window.getComputedStyle(el);

                // Skip invisible elements
                if (rect.width === 0 || rect.height === 0 ||
                    styles.display === 'none' || styles.visibility === 'hidden') {
                    continue;
                }

                // Safe className handling (SVG elements)
                const safeClassName = (typeof el.className === 'string') ?
                    el.className : (el.className?.baseVal || '');

                const elementData = {
                    tag: el.tagName.toLowerCase(),
                    id: el.id || null,
                    className: safeClassName,
                    text: el.textContent?.substring(0, 100) || '',
                    rect: {
                        top: Math.round(rect.top),
                        left: Math.round(rect.left),
                        right: Math.round(rect.right),
                        bottom: Math.round(rect.bottom),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        centerX: Math.round(rect.left + rect.width / 2),
                        centerY: Math.round(rect.top + rect.height / 2)
                    },
                    styles: {
                        display: styles.display,
                        position: styles.position,
                        flexDirection: styles.flexDirection,
                        justifyContent: styles.justifyContent,
                        alignItems: styles.alignItems,
                        gridTemplateColumns: styles.gridTemplateColumns,
                        gridTemplateRows: styles.gridTemplateRows,
                        textAlign: styles.textAlign,
                        margin: {
                            top: parseFloat(styles.marginTop) || 0,
                            bottom: parseFloat(styles.marginBottom) || 0,
                            left: parseFloat(styles.marginLeft) || 0,
                            right: parseFloat(styles.marginRight) || 0
                        }
                    },
                    semantic: {
                        role: el.getAttribute('role'),
                        ariaLabel: el.getAttribute('aria-label'),
                        isLandmark: ['header', 'nav', 'main', 'aside', 'footer', 'section', 'article'].includes(el.tagName.toLowerCase()),
                        landmarkType: el.tagName.toLowerCase()
                    },
                    aboveFold: rect.top < viewport.height,
                    // Track parent-child relationships
                    parentId: el.parentElement ? (el.parentElement.id || el.parentElement.tagName.toLowerCase()) : null
                };

                elements.push(elementData);

                // Track flex/grid containers
                if (styles.display === 'flex' || styles.display === 'grid') {
                    containers.push({
                        ...elementData,
                        children: Array.from(el.children).map(child => ({
                            tag: child.tagName.toLowerCase(),
                            id: child.id || null
                        }))
                    });
                }
            }

            return {
                viewport,
                elements,
                containers,
                totalElements: elements.length
            };
        }''')

    async def _analyze_page_structure(self, spatial_data: Dict) -> Dict:
        """
        Detect common page layout patterns

        Patterns:
        - Hero + Features + CTA (landing page)
        - Header + Content Grid (blog/news)
        - Sidebar + Content (docs/wiki)
        - App Layout (nav + main + sidebar)
        """
        elements = spatial_data['elements']
        viewport = spatial_data['viewport']

        # Find semantic landmarks
        landmarks = [el for el in elements if el['semantic']['isLandmark']]

        # Detect header
        headers = [el for el in landmarks if el['semantic']['landmarkType'] == 'header']
        has_header = len(headers) > 0
        header_height = headers[0]['rect']['height'] if headers else 0

        # Detect navigation
        navs = [el for el in landmarks if el['semantic']['landmarkType'] == 'nav']
        has_nav = len(navs) > 0

        # Detect hero (large element in top 50% of viewport)
        hero_candidates = [
            el for el in elements
            if el['aboveFold'] and
               el['rect']['top'] < viewport['height'] * 0.5 and
               el['rect']['height'] > 200 and
               el['rect']['width'] > viewport['width'] * 0.6
        ]
        has_hero = len(hero_candidates) > 0

        # Detect multi-column layouts (3-col features, etc.)
        multi_col = self._detect_multi_column_sections(elements, viewport)

        # Detect footer
        footers = [el for el in landmarks if el['semantic']['landmarkType'] == 'footer']
        has_footer = len(footers) > 0

        # Classify overall pattern
        pattern = self._classify_layout_pattern({
            'has_header': has_header,
            'has_nav': has_nav,
            'has_hero': has_hero,
            'multi_col_count': len(multi_col),
            'has_footer': has_footer
        })

        return {
            'pattern_type': pattern,
            'landmarks': {
                'header': {'detected': has_header, 'height': header_height},
                'navigation': {'detected': has_nav, 'count': len(navs)},
                'hero': {'detected': has_hero, 'count': len(hero_candidates)},
                'footer': {'detected': has_footer}
            },
            'multi_column_sections': multi_col,
            'structure_summary': self._generate_structure_summary(pattern, landmarks)
        }

    def _detect_multi_column_sections(self, elements: List[Dict], viewport: Dict) -> List[Dict]:
        """
        Detect multi-column sections (e.g., 3-col features, 4-col grid)

        Logic:
        - Find container elements with 2+ children at similar vertical positions
        - Children should have similar widths and be horizontally aligned
        """
        multi_col_sections = []

        # Group elements by vertical position (row detection)
        rows = {}
        for el in elements:
            # Round to nearest 50px to group elements in same row
            row_key = round(el['rect']['top'] / 50) * 50
            if row_key not in rows:
                rows[row_key] = []
            rows[row_key].append(el)

        # Find rows with 2+ elements of similar size
        for row_y, row_elements in rows.items():
            if len(row_elements) < 2:
                continue

            # Check if elements are horizontally aligned and similar size
            widths = [el['rect']['width'] for el in row_elements]
            heights = [el['rect']['height'] for el in row_elements]

            # Similar width? (within 20% variance)
            avg_width = sum(widths) / len(widths)
            width_variance = max(abs(w - avg_width) / avg_width for w in widths) if avg_width > 0 else 1

            # Similar height? (within 30% variance - more lenient)
            avg_height = sum(heights) / len(heights)
            height_variance = max(abs(h - avg_height) / avg_height for h in heights) if avg_height > 0 else 1

            if width_variance < 0.3 and height_variance < 0.5:
                # This looks like a multi-column section
                multi_col_sections.append({
                    'row_position': row_y,
                    'column_count': len(row_elements),
                    'column_width': round(avg_width),
                    'total_width': sum(widths),
                    'pattern': f"{len(row_elements)}-column layout"
                })

        return multi_col_sections[:5]  # Top 5 most prominent

    def _classify_layout_pattern(self, features: Dict) -> str:
        """
        Classify the overall page layout pattern
        """
        if features['has_hero'] and features['multi_col_count'] > 0:
            return "Landing Page (Hero + Features)"
        elif features['has_nav'] and features['multi_col_count'] > 2:
            return "Marketing Site (Nav + Multi-Column)"
        elif features['has_header'] and features['multi_col_count'] == 0:
            return "Article Layout (Single Column)"
        elif features['has_nav'] and not features['has_hero']:
            return "App Layout (Navigation-First)"
        else:
            return "Standard Web Layout"

    def _generate_structure_summary(self, pattern: str, landmarks: List[Dict]) -> str:
        """
        Generate human-readable structure summary
        """
        landmark_names = [l['semantic']['landmarkType'] for l in landmarks if l['semantic']['isLandmark']]
        structure = ' → '.join(landmark_names) if landmark_names else 'unknown'
        return f"{pattern}: {structure}"

    def _extract_relationships(self, elements: List[Dict]) -> Dict:
        """
        Extract spatial relationships between elements

        Relationships:
        - beside (same row, different columns)
        - below (different rows)
        - inside (parent-child)
        - aligned (same left/center/right edge)
        """
        relationships = {
            'beside_pairs': [],
            'below_pairs': [],
            'nested_groups': [],
            'aligned_groups': []
        }

        # Find elements beside each other (same vertical band)
        for i, el1 in enumerate(elements[:50]):  # Limit to first 50 for performance
            for el2 in elements[i+1:min(i+20, len(elements))]:
                # Same row? (within 20px vertical tolerance)
                if abs(el1['rect']['top'] - el2['rect']['top']) < 20:
                    # Not overlapping horizontally?
                    if el1['rect']['right'] < el2['rect']['left'] or el2['rect']['right'] < el1['rect']['left']:
                        relationships['beside_pairs'].append({
                            'el1': f"{el1['tag']}#{el1['id']}" if el1['id'] else el1['tag'],
                            'el2': f"{el2['tag']}#{el2['id']}" if el2['id'] else el2['tag'],
                            'gap': abs(el1['rect']['right'] - el2['rect']['left'])
                        })

        # Find vertical alignment (same left edge)
        left_aligned = {}
        for el in elements[:50]:
            left_key = round(el['rect']['left'] / 10) * 10  # Group within 10px
            if left_key not in left_aligned:
                left_aligned[left_key] = []
            left_aligned[left_key].append(el['tag'])

        # Keep groups with 3+ elements
        for left_pos, tags in left_aligned.items():
            if len(tags) >= 3:
                relationships['aligned_groups'].append({
                    'alignment': 'left',
                    'position': left_pos,
                    'elements': tags[:5]  # First 5
                })

        return {
            'beside_count': len(relationships['beside_pairs']),
            'aligned_groups': len(relationships['aligned_groups']),
            'examples': {
                'beside': relationships['beside_pairs'][:3],  # Top 3 examples
                'aligned': relationships['aligned_groups'][:2]  # Top 2 examples
            }
        }

    def _detect_component_zones(self, elements: List[Dict]) -> List[Dict]:
        """
        Detect semantic component zones with bounding boxes

        Zones:
        - Header/Banner
        - Hero
        - Features
        - Content
        - Footer
        """
        zones = []

        # Header zone (top of page)
        headers = [el for el in elements if el['semantic']['landmarkType'] == 'header']
        if headers:
            header = headers[0]
            zones.append({
                'type': 'header',
                'bbox': header['rect'],
                'elements_inside': len([e for e in elements if self._is_inside(e['rect'], header['rect'])])
            })

        # Hero zone (large element in top 50%)
        heroes = [
            el for el in elements
            if el['aboveFold'] and
               el['rect']['height'] > 300 and
               el['rect']['width'] > 600
        ]
        if heroes:
            hero = heroes[0]
            zones.append({
                'type': 'hero',
                'bbox': hero['rect'],
                'elements_inside': len([e for e in elements if self._is_inside(e['rect'], hero['rect'])])
            })

        # Footer zone (bottom of page)
        footers = [el for el in elements if el['semantic']['landmarkType'] == 'footer']
        if footers:
            footer = footers[0]
            zones.append({
                'type': 'footer',
                'bbox': footer['rect'],
                'elements_inside': len([e for e in elements if self._is_inside(e['rect'], footer['rect'])])
            })

        return zones

    def _is_inside(self, inner_rect: Dict, outer_rect: Dict) -> bool:
        """Check if inner rect is inside outer rect"""
        return (inner_rect['left'] >= outer_rect['left'] and
                inner_rect['right'] <= outer_rect['right'] and
                inner_rect['top'] >= outer_rect['top'] and
                inner_rect['bottom'] <= outer_rect['bottom'])

    def _analyze_alignment(self, elements: List[Dict]) -> Dict:
        """
        Analyze alignment patterns across the page

        Patterns:
        - Left-aligned (text-heavy sites)
        - Center-aligned (landing pages)
        - Split (left nav + right content)
        - Asymmetric (design-forward sites)
        """
        # Count elements by horizontal position
        left_count = len([el for el in elements[:50] if el['rect']['left'] < 200])
        center_count = len([el for el in elements[:50] if 200 <= el['rect']['left'] <= 800])
        right_count = len([el for el in elements[:50] if el['rect']['left'] > 800])

        # Determine dominant pattern
        total = left_count + center_count + right_count
        if total == 0:
            pattern = 'unknown'
        elif left_count / total > 0.7:
            pattern = 'left-aligned'
        elif center_count / total > 0.5:
            pattern = 'center-aligned'
        elif left_count > 0 and right_count > 0:
            pattern = 'split-layout'
        else:
            pattern = 'balanced'

        return {
            'primary_pattern': pattern,
            'distribution': {
                'left': left_count,
                'center': center_count,
                'right': right_count
            },
            'confidence': 75
        }

    def _analyze_whitespace(self, spatial_data: Dict) -> Dict:
        """
        Analyze whitespace and density

        Metrics:
        - Content density (% of viewport filled)
        - Average gaps between elements
        - Breathing room score
        """
        elements = spatial_data['elements']
        viewport = spatial_data['viewport']

        # Calculate total content area
        total_content_area = sum(el['rect']['width'] * el['rect']['height'] for el in elements[:50])
        viewport_area = viewport['width'] * viewport['height']
        density = (total_content_area / viewport_area) * 100 if viewport_area > 0 else 0

        # Calculate average margins
        margins = [el['styles']['margin']['top'] + el['styles']['margin']['bottom'] for el in elements[:30]]
        avg_vertical_margin = sum(margins) / len(margins) if margins else 0

        # Breathing room score (higher margins = more breathing room)
        breathing_room = min(100, avg_vertical_margin * 2)

        return {
            'content_density_pct': round(density, 1),
            'average_vertical_spacing': round(avg_vertical_margin),
            'breathing_room_score': round(breathing_room),
            'interpretation': self._interpret_density(density)
        }

    def _interpret_density(self, density: float) -> str:
        """Interpret content density"""
        if density > 80:
            return 'Dense (text-heavy or crowded)'
        elif density > 50:
            return 'Balanced (moderate spacing)'
        elif density > 30:
            return 'Spacious (generous whitespace)'
        else:
            return 'Minimal (sparse content)'

    def _analyze_above_fold(self, spatial_data: Dict) -> Dict:
        """
        Analyze above-the-fold layout structure

        What users see immediately on page load
        """
        elements = spatial_data['elements']
        viewport = spatial_data['viewport']

        above_fold_elements = [el for el in elements if el['aboveFold']]

        # Categorize by type
        headings = [el for el in above_fold_elements if el['tag'] in ['h1', 'h2', 'h3']]
        images = [el for el in above_fold_elements if el['tag'] == 'img']
        buttons = [el for el in above_fold_elements if el['tag'] == 'button']

        return {
            'total_elements': len(above_fold_elements),
            'element_breakdown': {
                'headings': len(headings),
                'images': len(images),
                'buttons': len(buttons)
            },
            'primary_focus': self._determine_primary_focus(above_fold_elements),
            'viewport_coverage_pct': self._calculate_coverage(above_fold_elements, viewport)
        }

    def _determine_primary_focus(self, elements: List[Dict]) -> str:
        """Determine what the above-fold focuses on"""
        if any(el['tag'] == 'h1' and el['rect']['height'] > 100 for el in elements):
            return 'Hero heading'
        elif any(el['tag'] == 'img' and el['rect']['height'] > 300 for el in elements):
            return 'Large image/visual'
        elif len([el for el in elements if el['tag'] == 'button']) > 2:
            return 'Call-to-action buttons'
        else:
            return 'Mixed content'

    def _calculate_coverage(self, elements: List[Dict], viewport: Dict) -> float:
        """Calculate what % of viewport is covered by content"""
        if not elements:
            return 0
        total_area = sum(el['rect']['width'] * el['rect']['height'] for el in elements)
        viewport_area = viewport['width'] * viewport['height']
        return round((total_area / viewport_area) * 100, 1) if viewport_area > 0 else 0

    def _analyze_container_hierarchy(self, containers: List[Dict]) -> Dict:
        """
        Analyze flex/grid container hierarchies

        Shows parent-child nesting structure
        """
        flex_containers = [c for c in containers if c['styles']['display'] == 'flex']
        grid_containers = [c for c in containers if c['styles']['display'] == 'grid']

        return {
            'flex_containers': {
                'count': len(flex_containers),
                'examples': [
                    {
                        'tag': c['tag'],
                        'direction': c['styles']['flexDirection'],
                        'children': len(c['children'])
                    }
                    for c in flex_containers[:3]
                ]
            },
            'grid_containers': {
                'count': len(grid_containers),
                'examples': [
                    {
                        'tag': c['tag'],
                        'columns': c['styles']['gridTemplateColumns'],
                        'children': len(c['children'])
                    }
                    for c in grid_containers[:3]
                ]
            },
            'total_layout_containers': len(containers)
        }

    def _detect_layout_grid(self, elements: List[Dict]) -> Dict:
        """
        Detect underlying layout grid system

        Common grids:
        - 12-column (Bootstrap, Foundation)
        - 16-column (Material Design)
        - Asymmetric (custom)
        """
        # Analyze horizontal positions to detect column grid
        left_positions = sorted(set(el['rect']['left'] for el in elements[:50]))

        # Calculate gaps between positions
        gaps = [left_positions[i+1] - left_positions[i] for i in range(len(left_positions)-1)]

        # Look for consistent gap pattern
        if not gaps:
            return {'detected': False, 'type': 'unknown'}

        avg_gap = sum(gaps) / len(gaps)
        gap_variance = max(abs(g - avg_gap) / avg_gap for g in gaps) if avg_gap > 0 else 1

        # Consistent gaps = grid system
        if gap_variance < 0.3:
            # Estimate column count
            viewport_width = max(el['rect']['right'] for el in elements[:50])
            estimated_columns = round(viewport_width / avg_gap)

            return {
                'detected': True,
                'type': f'{estimated_columns}-column grid',
                'column_width': round(avg_gap),
                'confidence': 70 if gap_variance < 0.2 else 50
            }
        else:
            return {
                'detected': True,
                'type': 'asymmetric/custom grid',
                'confidence': 40
            }

    def _calculate_confidence(self, spatial_data: Dict) -> int:
        """
        Calculate overall confidence in spatial analysis

        Based on:
        - Number of elements analyzed
        - Presence of semantic landmarks
        - Data completeness
        """
        element_count = len(spatial_data['elements'])
        has_landmarks = any(el['semantic']['isLandmark'] for el in spatial_data['elements'])
        has_containers = len(spatial_data['containers']) > 0

        base_confidence = 50
        if element_count > 20:
            base_confidence += 20
        if has_landmarks:
            base_confidence += 15
        if has_containers:
            base_confidence += 15

        return min(base_confidence, 95)


# Integration test
async def test_spatial_composition():
    """Test spatial composition analysis on a real site"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto('https://stripe.com', wait_until='networkidle')

        analyzer = SpatialCompositionAnalyzer()
        result = await analyzer.analyze(page)

        print("\n" + "="*70)
        print(" 🗺️  SPATIAL COMPOSITION ANALYSIS")
        print("="*70)

        print("\n📐 Page Structure:")
        print(f"   Pattern: {result['page_structure']['pattern_type']}")
        print(f"   Summary: {result['page_structure']['structure_summary']}")

        print("\n🔗 Spatial Relationships:")
        print(f"   Beside pairs: {result['spatial_relationships']['beside_count']}")
        print(f"   Aligned groups: {result['spatial_relationships']['aligned_groups']}")

        print("\n🏢 Component Zones:")
        for zone in result['component_zones']:
            print(f"   {zone['type'].upper()}: {zone['elements_inside']} elements inside")

        print("\n📏 Alignment Pattern:")
        print(f"   Primary: {result['alignment_patterns']['primary_pattern']}")

        print("\n⬜ Whitespace Analysis:")
        print(f"   Density: {result['whitespace_analysis']['content_density_pct']}%")
        print(f"   Interpretation: {result['whitespace_analysis']['interpretation']}")

        print("\n👁️ Above-the-Fold:")
        print(f"   Total elements: {result['above_fold_layout']['total_elements']}")
        print(f"   Primary focus: {result['above_fold_layout']['primary_focus']}")

        print("\n📦 Layout Grid:")
        grid = result['layout_grid']
        if grid['detected']:
            print(f"   Type: {grid['type']}")
            print(f"   Confidence: {grid['confidence']}%")
        else:
            print("   No grid detected")

        await browser.close()

        print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_spatial_composition())
