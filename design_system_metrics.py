"""
Design System Metrics - The Missing Pieces

Extracts system-wide design patterns that are critical for implementation:
1. Spacing Scale Detection - All padding/margin/gap values + pattern detection
2. Responsive Breakpoints - Media queries + layout changes
3. Shadow System - box-shadow scale categorization
4. Z-Index Stack - Stacking context visualization
5. Border Radius Scale - All border-radius values + pattern

These metrics answer: "What design system are they using?"
"""

import asyncio
from playwright.async_api import Page
from typing import Dict, List, Tuple
from collections import Counter
import re
import math


class DesignSystemMetrics:
    """
    Extract design system patterns from live sites
    """

    def __init__(self, page: Page):
        self.page = page

    async def extract_spacing_scale(self) -> Dict:
        """
        Extract all spacing values and detect the scale pattern

        Returns system-wide spacing like:
        - 4px, 8px, 16px, 24px, 32px (powers of 2)
        - 0.25rem, 0.5rem, 1rem, 1.5rem (Tailwind-style)
        """
        print("\n📏 Extracting spacing scale...")

        result = await self.page.evaluate('''() => {
            const spacingValues = {
                padding: [],
                margin: [],
                gap: []
            };

            // Get all elements
            const elements = document.querySelectorAll('*');

            for (const el of elements) {
                const styles = window.getComputedStyle(el);

                // Extract padding values
                const padding = styles.padding;
                if (padding && padding !== '0px') {
                    spacingValues.padding.push(padding);
                }

                // Extract margin values
                const margin = styles.margin;
                if (margin && margin !== '0px') {
                    spacingValues.margin.push(margin);
                }

                // Extract gap values (flexbox/grid)
                const gap = styles.gap;
                if (gap && gap !== 'normal' && gap !== '0px') {
                    spacingValues.gap.push(gap);
                }
            }

            return spacingValues;
        }''')

        # Parse spacing values into pixels
        all_spacing_px = []

        for prop_type, values in result.items():
            for value_str in values:
                # Parse compound values like "16px 24px"
                px_values = re.findall(r'(\d+(?:\.\d+)?)px', value_str)
                all_spacing_px.extend([float(v) for v in px_values])

        # Count occurrences
        spacing_counter = Counter(all_spacing_px)

        # Detect pattern (powers of 2, multiples of 4, etc.)
        pattern = self._detect_spacing_pattern(spacing_counter)

        # Get top values
        top_values = spacing_counter.most_common(10)

        # Calculate detailed confidence
        base_confidence = 40  # Pattern detected
        instance_bonus = min(len(all_spacing_px) // 10, 30)  # Up to +30 for high usage
        pattern_bonus = 15 if pattern['base'] else 0  # +15 if matches known system
        total_confidence = min(base_confidence + instance_bonus + pattern_bonus, 95)

        return {
            'confidence': total_confidence,
            'pattern': pattern['type'],
            'base_unit': pattern['base'],
            'scale': pattern['scale'],
            'most_common': {f'{int(v)}px': count for v, count in top_values},
            'total_instances': len(all_spacing_px),
            'unique_values': len(spacing_counter),
            'evidence': {
                'padding_samples': result['padding'][:5],
                'margin_samples': result['margin'][:5],
                'gap_samples': result['gap'][:5]
            },
            'evidence_trail': {
                'found': [
                    f"{len(all_spacing_px)} total spacing values across padding/margin/gap",
                    f"{len(spacing_counter)} unique values",
                    f"Most common: {', '.join(f'{int(v)}px ({c}×)' for v, c in top_values[:3])}"
                ],
                'analyzed': [
                    f"Checked for powers of 2 pattern",
                    f"Checked for multiples of 8 (Material Design)",
                    f"Checked for multiples of 4 (common systems)"
                ],
                'concluded': f"Pattern identified as '{pattern['type']}' with base unit {pattern['base']}px" if pattern['base'] else f"Custom spacing pattern detected",
                'confidence_breakdown': {
                    'base_detection': base_confidence,
                    'usage_frequency': instance_bonus,
                    'system_match': pattern_bonus,
                    'total': total_confidence
                }
            }
        }

    def _detect_spacing_pattern(self, counter: Counter) -> Dict:
        """
        Detect spacing pattern from observed values

        Heuristic: Checks for common design system patterns:
        1. Powers of 2 (4, 8, 16, 32...) - Common in Tailwind, Bootstrap
        2. Multiples of 8 (8, 16, 24, 32...) - Material Design baseline
        3. Multiples of 4 (4, 8, 12, 16...) - Most design systems

        Confidence calculation:
        - Base 40: Pattern detected
        - +2 per value matching pattern (capped at 95)

        Returns pattern type and base unit for scale generation.
        """
        values = sorted([v for v in counter.keys() if v > 0])

        if not values:
            return {'type': 'No spacing detected', 'base': 0, 'scale': []}

        # Check for powers of 2
        powers_of_2 = [4, 8, 16, 24, 32, 48, 64, 96, 128]
        matches = sum(1 for v in values if v in powers_of_2)
        if matches >= 4:
            scale = [v for v in powers_of_2 if v in values]
            return {
                'type': 'Powers of 2 (Tailwind-style)',
                'base': 4,
                'scale': scale
            }

        # Check for multiples of 8
        multiples_of_8 = all(v % 8 == 0 for v in values[:5])
        if multiples_of_8:
            return {
                'type': '8pt grid system',
                'base': 8,
                'scale': [v for v in values if v % 8 == 0][:8]
            }

        # Check for multiples of 4
        multiples_of_4 = all(v % 4 == 0 for v in values[:5])
        if multiples_of_4:
            return {
                'type': '4pt grid system',
                'base': 4,
                'scale': [v for v in values if v % 4 == 0][:8]
            }

        # Default: custom scale
        return {
            'type': 'Custom spacing (no clear pattern)',
            'base': min(values) if values else 0,
            'scale': values[:8]
        }

    async def extract_responsive_breakpoints(self) -> Dict:
        """
        Extract media query breakpoints and detect responsive strategy
        """
        print("\n📱 Extracting responsive breakpoints...")

        result = await self.page.evaluate('''() => {
            const breakpoints = [];

            // Get all stylesheets
            for (const sheet of document.styleSheets) {
                try {
                    const rules = sheet.cssRules || sheet.rules;
                    for (const rule of rules) {
                        if (rule.type === CSSRule.MEDIA_RULE) {
                            const mediaText = rule.media.mediaText;
                            breakpoints.push(mediaText);
                        }
                    }
                } catch (e) {
                    // CORS or other issues
                }
            }

            // Also check viewport meta tag
            const viewport = document.querySelector('meta[name="viewport"]');
            const viewportContent = viewport ? viewport.content : null;

            return {
                breakpoints: breakpoints,
                viewport: viewportContent,
                current_width: window.innerWidth,
                current_height: window.innerHeight
            };
        }''')

        # Parse breakpoints and preserve media query text
        breakpoint_values = []
        media_queries = []
        for bp in result['breakpoints']:
            # Store the full media query text
            media_queries.append(bp)
            # Extract pixel values from media queries
            matches = re.findall(r'(\d+)px', bp)
            breakpoint_values.extend([int(m) for m in matches])

        # Count and categorize
        bp_counter = Counter(breakpoint_values)
        unique_breakpoints = sorted(set(breakpoint_values))

        # Detect breakpoint strategy
        strategy = self._detect_breakpoint_strategy(unique_breakpoints)

        return {
            'confidence': 95 if breakpoint_values else 60,
            'pattern': strategy['type'],
            'breakpoints': strategy['breakpoints'],
            'total_media_queries': len(result['breakpoints']),
            'unique_breakpoints': unique_breakpoints[:10],
            'media_queries': media_queries[:20],  # Keep first 20 actual media queries
            'viewport_meta': result['viewport'],
            'current_size': {
                'width': result['current_width'],
                'height': result['current_height']
            },
            'evidence': {
                'samples': result['breakpoints'][:5]
            }
        }

    def _detect_breakpoint_strategy(self, breakpoints: List[int]) -> Dict:
        """
        Detect if breakpoints match common frameworks

        Heuristic: Matches observed breakpoints against known framework patterns
        - Tailwind: [640, 768, 1024, 1280, 1536]
        - Bootstrap: [576, 768, 992, 1200, 1400]
        - Material: [600, 960, 1280, 1920]
        - Foundation: [640, 1024, 1200, 1440]

        Confidence: Requires 3+ matching breakpoints to classify as framework
        Rationale: 3 matches indicates intentional pattern, not coincidence

        Failure modes:
        - Custom breakpoints won't match any framework
        - Hybrid systems using multiple frameworks may match incorrectly
        """
        if not breakpoints:
            return {
                'type': 'No responsive design detected',
                'breakpoints': {}
            }

        # Tailwind breakpoints
        tailwind_bp = [640, 768, 1024, 1280, 1536]
        tailwind_matches = sum(1 for bp in breakpoints if bp in tailwind_bp)

        if tailwind_matches >= 3:
            return {
                'type': 'Tailwind CSS breakpoints',
                'breakpoints': {
                    'sm': '640px',
                    'md': '768px',
                    'lg': '1024px',
                    'xl': '1280px',
                    '2xl': '1536px'
                }
            }

        # Bootstrap breakpoints
        bootstrap_bp = [576, 768, 992, 1200, 1400]
        bootstrap_matches = sum(1 for bp in breakpoints if bp in bootstrap_bp)

        if bootstrap_matches >= 3:
            return {
                'type': 'Bootstrap breakpoints',
                'breakpoints': {
                    'sm': '576px',
                    'md': '768px',
                    'lg': '992px',
                    'xl': '1200px',
                    'xxl': '1400px'
                }
            }

        # Custom breakpoints
        labels = ['mobile', 'tablet', 'desktop', 'wide', 'ultra-wide']
        custom_bp = {}
        for i, bp in enumerate(sorted(breakpoints)[:5]):
            custom_bp[labels[i]] = f'{bp}px'

        return {
            'type': 'Custom breakpoints',
            'breakpoints': custom_bp
        }

    async def extract_shadow_system(self) -> Dict:
        """
        Extract box-shadow values with usage counts and element context.

        Returns each unique shadow with:
        - The actual CSS value (copy/paste ready)
        - How many elements use it
        - Sample selectors so you know WHERE it lives
        - A semantic name (Subtle / Elevated / Floating) based on blur
        """
        print("\n☁️  Extracting shadow system...")

        result = await self.page.evaluate("""
            () => {
                const shadowMap = {};
                const elements = document.querySelectorAll('*');

                for (const el of elements) {
                    const styles = window.getComputedStyle(el);
                    const shadow = styles.boxShadow;

                    if (shadow && shadow !== 'none') {
                        if (!shadowMap[shadow]) {
                            shadowMap[shadow] = { count: 0, selectors: [] };
                        }
                        shadowMap[shadow].count += 1;

                        // Grab up to 3 selector examples per shadow
                        if (shadowMap[shadow].selectors.length < 3) {
                            let sel = '';
                            if (el.id) {
                                sel = '#' + el.id;
                            } else if (el.className && typeof el.className === 'string') {
                                sel = '.' + el.className.trim().split(/\\s+/)[0];
                            } else {
                                sel = el.tagName.toLowerCase();
                            }
                            if (sel && !shadowMap[shadow].selectors.includes(sel)) {
                                shadowMap[shadow].selectors.push(sel);
                            }
                        }
                    }
                }

                return shadowMap;
            }
        """)

        if not result:
            return {
                'confidence': 50,
                'pattern': 'No shadows detected',
                'scale': {},
                'levels': [],
                'total_instances': 0,
                'unique_shadows': 0,
                'evidence_trail': {
                    'found': ['No box-shadow values found on any element'],
                    'analyzed': [],
                    'concluded': 'Site uses a flat design with no elevation'
                }
            }

        # Build levelled output: sort by usage, assign semantic names
        total_instances = sum(entry['count'] for entry in result.values())

        # Collect all blur radii for relative naming
        all_blurs = [self._extract_blur(css) for css in result.keys()]

        levels = []
        for css_value, entry in sorted(result.items(), key=lambda x: x[1]['count'], reverse=True):
            blur = self._extract_blur(css_value)
            levels.append({
                'css': css_value,
                'count': entry['count'],
                'usage_pct': round((entry['count'] / total_instances) * 100, 1),
                'selectors': entry['selectors'],
                'blur_radius': blur,
                'name': self._shadow_semantic_name(blur, all_blurs)
            })

        # Build the scale dict keyed by semantic name for the dashboard card
        # (dashboard's createShadowCard iterates scale entries)
        scale = {}
        for lvl in levels:
            name = lvl['name']
            if name not in scale:
                scale[name] = []
            scale[name].append({'shadow': lvl['css'], 'count': lvl['count']})

        unique_count = len(levels)
        confidence = min(40 + (total_instances // 5) + (unique_count * 5), 95)

        return {
            'confidence': confidence,
            'pattern': f'{unique_count} unique shadow{"s" if unique_count != 1 else ""} across {total_instances} elements',
            'scale': scale,
            'levels': levels,          # ← new: ordered list with full context
            'total_instances': total_instances,
            'unique_shadows': unique_count,
            'evidence_trail': {
                'found': [
                    f'{total_instances} elements with box-shadow',
                    f'{unique_count} unique shadow values',
                    f'Most used: {levels[0]["css"][:60]}... ({levels[0]["count"]} uses)' if levels else 'None'
                ],
                'analyzed': [
                    f'Blur radii range: {min(l["blur_radius"] for l in levels)}px – {max(l["blur_radius"] for l in levels)}px' if levels else '',
                    f'Semantic levels detected: {", ".join(set(l["name"] for l in levels))}' if levels else ''
                ],
                'concluded': f'Elevation system with {len(set(l["name"] for l in levels))} distinct levels' if levels else 'No shadows'
            }
        }

    def _extract_blur(self, shadow_css: str) -> int:
        """Pull the blur radius out of a box-shadow string."""
        match = re.search(r'(\d+)px\s+(\d+)px\s+(\d+)px', shadow_css)
        return int(match.group(3)) if match else 0

    def _shadow_semantic_name(self, blur: int, all_blurs: list = None) -> str:
        """Map blur radius → human-readable elevation name.
        Uses relative distribution when multiple shadows exist,
        falls back to absolute thresholds for ≤2 shadows."""
        if all_blurs and len(all_blurs) > 2:
            return self._shadow_name_relative(blur, all_blurs)
        # Absolute fallback for sites with very few shadows
        if blur <= 2:
            return 'Subtle'
        elif blur <= 6:
            return 'Card'
        elif blur <= 15:
            return 'Elevated'
        elif blur <= 30:
            return 'Floating'
        else:
            return 'Deep'

    def _shadow_name_relative(self, blur: int, all_blurs: list) -> str:
        """Assign name based on position within the site's own shadow range.
        Ensures each tier gets a distinct label even when blur values cluster."""
        unique_sorted = sorted(set(all_blurs))
        if len(unique_sorted) <= 1:
            return 'Default'
        rank = unique_sorted.index(blur)
        pct = rank / (len(unique_sorted) - 1)  # 0.0 to 1.0
        if pct <= 0.2:
            return 'Subtle'
        elif pct <= 0.4:
            return 'Card'
        elif pct <= 0.6:
            return 'Elevated'
        elif pct <= 0.8:
            return 'Heavy'
        else:
            return 'Deep'

    async def extract_z_index_stack(self) -> Dict:
        """
        Extract all z-index values and visualize stacking context
        """
        print("\n📚 Extracting z-index stack...")

        result = await self.page.evaluate('''() => {
            const zIndexes = [];
            const elements = document.querySelectorAll('*');

            for (const el of elements) {
                const styles = window.getComputedStyle(el);
                const zIndex = styles.zIndex;

                if (zIndex && zIndex !== 'auto') {
                    // SVG elements have className as SVGAnimatedString
                    const safeClass = (typeof el.className === 'string')
                        ? el.className : (el.className?.baseVal || '');
                    zIndexes.push({
                        z: parseInt(zIndex),
                        tag: el.tagName.toLowerCase(),
                        classes: safeClass,
                        id: el.id || '',
                        role: el.getAttribute('role') || '',
                        ariaLabel: el.getAttribute('aria-label') || '',
                        position: styles.position
                    });
                }
            }

            return zIndexes;
        }''')

        # Categorize z-indexes into layers
        layers = self._categorize_z_indexes(result)

        # Detect conflicts
        conflicts = self._detect_z_conflicts(result)

        # Health summary
        health = self._z_index_health(result)

        return {
            'confidence': 90 if result else 60,
            'pattern': f'{len(layers)} stacking layers detected',
            'layers': layers,
            'health': health,
            'total_elements': len(result),
            'conflicts': conflicts,
            'evidence': {
                'samples': result[:10]
            }
        }

    # Common CSS framework prefixes that obscure meaning
    _FRAMEWORK_PREFIXES = (
        'Mui', 'mui-', 'css-', 'tw-', 'sc-', 'chakra-', 'ant-',
        'v-', 'el-', 'bp3-', 'bp4-', 'mantine-', 'rs-', 'semi-',
    )

    @staticmethod
    def _smart_label(el: Dict) -> str:
        """Generate a human-readable label for a z-index element.
        Priority: aria-label > id > role > first meaningful class > tag.
        Strips common framework prefixes from class names."""
        if el.get('ariaLabel'):
            label = el['ariaLabel']
            return label[:40] if len(label) > 40 else label
        if el.get('id'):
            return f"#{el['id'][:35]}"
        if el.get('role'):
            return f"{el['tag']}[role={el['role']}]"
        classes = el.get('classes', '')
        if classes:
            first_class = classes.split()[0] if isinstance(classes, str) else ''
            if first_class:
                # Strip framework prefixes for cleaner labels
                for prefix in DesignSystemMetrics._FRAMEWORK_PREFIXES:
                    if first_class.startswith(prefix):
                        remainder = first_class[len(prefix):]
                        if remainder:
                            first_class = remainder
                            break
                return f"{el['tag']}.{first_class[:30]}"
        return el.get('tag', 'div')

    def _categorize_z_indexes(self, z_data: List[Dict]) -> Dict:
        """
        Categorize z-indexes into logical layers with smart labels
        """
        if not z_data:
            return {}

        # Get unique z-index values
        z_values = sorted(set(item['z'] for item in z_data))

        layers = {}

        for z in z_values:
            elements = [item for item in z_data if item['z'] == z]

            # Determine layer name based on z-index value
            if z <= 1:
                layer_name = f'Layer {z} (base)'
            elif z <= 10:
                layer_name = f'Layer {z} (dropdowns)'
            elif z <= 100:
                layer_name = f'Layer {z} (modals)'
            elif z <= 1000:
                layer_name = f'Layer {z} (tooltips)'
            else:
                layer_name = f'Layer {z} (top)'

            layers[layer_name] = {
                'z_index': z,
                'count': len(elements),
                'elements': [self._smart_label(e) for e in elements[:5]]
            }

        return layers

    def _z_index_health(self, z_data: List[Dict]) -> Dict:
        """Compute z-index health summary: Clean / Complex / Chaotic"""
        if not z_data:
            return {'level': 'Clean', 'detail': 'No z-index values detected'}
        unique = len(set(item['z'] for item in z_data))
        max_z = max(item['z'] for item in z_data)
        if unique <= 5 and max_z <= 1000:
            return {'level': 'Clean', 'detail': f'{unique} unique values, max z-index {max_z}'}
        elif unique <= 10:
            return {'level': 'Complex', 'detail': f'{unique} unique values, max z-index {max_z}'}
        else:
            return {'level': 'Chaotic', 'detail': f'{unique} unique values, max z-index {max_z} — consider consolidating'}

    def _detect_z_conflicts(self, z_data: List[Dict]) -> List[str]:
        """
        Detect potential z-index conflicts or anti-patterns

        Heuristic: Identifies problematic z-index patterns
        1. Extremely high values (>9999) - indicates z-index wars
        2. Unusual specific values (e.g., 2347) - suggests manual tweaking
        3. Too many layers (>10) - indicates lack of system

        Rationale:
        - Good design systems use 5-8 intentional layers (1, 10, 100, 1000)
        - Random values suggest ad-hoc fixes, not systematic thinking
        - Values >9999 indicate escalating conflicts

        Failure modes:
        - Framework-generated high values may trigger false positives
        - Some libraries use specific values intentionally (e.g., 9999 for modals)
        """
        conflicts = []

        z_values = [item['z'] for item in z_data]

        # Check for random high values
        if any(z > 9999 for z in z_values):
            conflicts.append('⚠️  Extremely high z-index detected (>9999)')

        # Check for odd specific values (anti-pattern)
        weird_values = [z for z in z_values if z > 10 and z % 10 not in [0, 1, 5]]
        if weird_values:
            conflicts.append(f'⚠️  Unusual z-index values: {weird_values[:3]}')

        # Check for too many layers
        unique_z = len(set(z_values))
        if unique_z > 10:
            conflicts.append(f'⚠️  Too many z-index layers ({unique_z})')

        return conflicts if conflicts else ['✅ No conflicts detected']

    async def extract_border_radius_scale(self) -> Dict:
        """
        Extract border-radius values with usage counts and element context.

        Returns each unique radius with:
        - The pixel value
        - How many elements use it
        - Sample selectors (where it lives)
        - A semantic name (Sharp / Subtle / Medium / Pill / Circular)
        """
        print("\n🔘 Extracting border radius scale...")

        result = await self.page.evaluate("""
            () => {
                const radiusMap = {};
                const elements = document.querySelectorAll('*');

                for (const el of elements) {
                    const styles = window.getComputedStyle(el);
                    const radius = styles.borderRadius;

                    if (radius && radius !== '0px') {
                        if (!radiusMap[radius]) {
                            radiusMap[radius] = { count: 0, selectors: [] };
                        }
                        radiusMap[radius].count += 1;

                        if (radiusMap[radius].selectors.length < 3) {
                            let sel = '';
                            if (el.id) {
                                sel = '#' + el.id;
                            } else if (el.className && typeof el.className === 'string') {
                                sel = '.' + el.className.trim().split(/\\s+/)[0];
                            } else {
                                sel = el.tagName.toLowerCase();
                            }
                            if (sel && !radiusMap[radius].selectors.includes(sel)) {
                                radiusMap[radius].selectors.push(sel);
                            }
                        }
                    }
                }

                return radiusMap;
            }
        """)

        if not result:
            return {
                'confidence': 50,
                'pattern': 'No border radius detected',
                'scale': [],
                'levels': [],
                'special_cases': {'circular': 0, 'pill': 0},
                'total_instances': 0,
                'unique_values': 0,
                'evidence_trail': {
                    'found': ['No border-radius found — site uses sharp corners everywhere'],
                    'analyzed': [],
                    'concluded': 'Flat / sharp design language'
                }
            }

        # Parse into structured levels
        total_instances = sum(entry['count'] for entry in result.values())
        levels = []
        special_cases = {'circular': 0, 'pill': 0}
        scale_values = []  # raw px numbers for the old scale field

        for raw_value, entry in result.items():
            # Detect specials
            if '50%' in raw_value:
                special_cases['circular'] += entry['count']
                levels.append({
                    'value': '50%',
                    'display': '50% (Circular)',
                    'count': entry['count'],
                    'usage_pct': round((entry['count'] / total_instances) * 100, 1),
                    'selectors': entry['selectors'],
                    'name': 'Circular'
                })
                continue

            # Extract first numeric px value for classification
            px_match = re.findall(r'(\d+(?:\.\d+)?)px', raw_value)
            if not px_match:
                continue

            first_px = float(px_match[0])

            if first_px >= 999:
                special_cases['pill'] += entry['count']
                name = 'Pill'
                display = f'{int(first_px)}px (Pill)'
            else:
                name = self._radius_semantic_name(first_px)
                display = f'{int(first_px)}px'
                scale_values.append(int(first_px))

            levels.append({
                'value': raw_value,
                'display': display,
                'px': first_px,
                'count': entry['count'],
                'usage_pct': round((entry['count'] / total_instances) * 100, 1),
                'selectors': entry['selectors'],
                'name': name
            })

        # Sort by usage (most common first)
        levels.sort(key=lambda x: x['count'], reverse=True)
        scale_values = sorted(set(scale_values))

        # Detect base pattern
        pattern_type = self._detect_radius_pattern_from_values(scale_values)

        unique_count = len(levels)
        confidence = min(40 + (total_instances // 8) + (unique_count * 4), 95)

        return {
            'confidence': confidence,
            'pattern': f'{unique_count} radius value{"s" if unique_count != 1 else ""} · {pattern_type}',
            'scale': scale_values,           # keep for backwards compat
            'levels': levels,                # ← new: ordered list with context
            'special_cases': special_cases,
            'total_instances': total_instances,
            'unique_values': unique_count,
            'evidence_trail': {
                'found': [
                    f'{total_instances} elements with border-radius',
                    f'{unique_count} unique radius values',
                    f'Most used: {levels[0]["display"]} ({levels[0]["count"]} uses)' if levels else 'None'
                ],
                'analyzed': [
                    f'Scale values: {scale_values}',
                    f'Special cases: {special_cases["pill"]} pills, {special_cases["circular"]} circles'
                ],
                'concluded': f'{pattern_type} — {", ".join(set(l["name"] for l in levels))}' if levels else 'No radius data'
            }
        }

    def _radius_semantic_name(self, px: float) -> str:
        """Map a border-radius pixel value to a human-readable style name."""
        if px == 0:
            return 'Sharp'
        elif px <= 4:
            return 'Subtle'
        elif px <= 8:
            return 'Medium'
        elif px <= 16:
            return 'Rounded'
        else:
            return 'Large'

    def _detect_radius_pattern_from_values(self, values: List[int]) -> str:
        """Classify the radius scale into a human-readable pattern string."""
        if not values:
            return 'No radius scale'
        if all(v % 4 == 0 for v in values[:5]):
            return '4px base system'
        if all(v % 2 == 0 for v in values[:5]):
            return '2px base system'
        return 'Custom scale'


async def demo_design_system_metrics():
    """
    Demo: Extract design system metrics from real sites
    """
    from playwright.async_api import async_playwright

    print("\n" + "="*70)
    print(" 🎨 DESIGN SYSTEM METRICS DEMO")
    print("="*70)

    test_sites = [
        ('https://stripe.com/docs', 'Stripe Docs'),
        ('https://tailwindcss.com', 'Tailwind CSS')
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for url, name in test_sites:
            print(f"\n{'='*70}")
            print(f" Analyzing: {name}")
            print(f" URL: {url}")
            print('='*70)

            page = await browser.new_page()
            page.set_default_timeout(60000)

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(2)

                metrics = DesignSystemMetrics(page)

                # Extract all metrics
                spacing = await metrics.extract_spacing_scale()
                print(f"\n📏 Spacing: {spacing['pattern']} (base: {spacing['base_unit']}px)")
                print(f"   Scale: {spacing['scale']}")

                breakpoints = await metrics.extract_responsive_breakpoints()
                print(f"\n📱 Breakpoints: {breakpoints['pattern']}")
                print(f"   {breakpoints['breakpoints']}")

                shadows = await metrics.extract_shadow_system()
                print(f"\n☁️  Shadows: {shadows['pattern']}")

                z_index = await metrics.extract_z_index_stack()
                print(f"\n📚 Z-Index: {z_index['pattern']}")
                print(f"   {z_index['conflicts'][0]}")

                radius = await metrics.extract_border_radius_scale()
                print(f"\n🔘 Border Radius: {radius['pattern']}")
                print(f"   Scale: {radius['scale']}")

            except Exception as e:
                print(f"   ❌ Error: {str(e)[:100]}")

            await page.close()

        await browser.close()


if __name__ == '__main__':
    asyncio.run(demo_design_system_metrics())
