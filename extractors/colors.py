"""
Color Extractor — Palette extraction, CSS variable detection, intelligent classification.

Extracts color usage counts from computed styles, clusters into palette roles,
and generates visual previews via ColorPalettePreview.
"""

import logging
import re
from typing import Dict
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class ColorExtractor(BaseExtractor):
    name = "colors"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Extracting color palette...")

        color_data = await ctx.page.evaluate('''() => {
            const colorCounts = {};

            // ── Semantic role tracking ──
            // Track WHERE each color is used for role classification
            const roleBuckets = {
                background: {},    // body, main, section bg colors
                text: {},          // body, p, span, li text colors
                heading: {},       // h1-h6 text colors
                link: {},          // <a> text colors
                button_bg: {},     // button background colors
                button_text: {},   // button text colors
                border: {},        // border colors
                accent: {}         // non-white/black button & link colors
            };

            function addToRole(role, color, weight) {
                if (!color || color === 'rgba(0, 0, 0, 0)' || color === 'transparent') return;
                roleBuckets[role][color] = (roleBuckets[role][color] || 0) + (weight || 1);
            }

            // Get all elements with usage counts
            const elements = document.querySelectorAll('*');
            for (const el of elements) {
                const styles = window.getComputedStyle(el);
                const tag = el.tagName.toLowerCase();

                // Count color usage (global)
                [styles.color, styles.backgroundColor, styles.borderColor].forEach(function(color) {
                    if (color && color !== 'rgba(0, 0, 0, 0)') {
                        colorCounts[color] = (colorCounts[color] || 0) + 1;
                    }
                });

                // Role-specific tracking
                const bgColor = styles.backgroundColor;
                const textColor = styles.color;
                const borderColor = styles.borderColor;

                // Background role: body, main, section, div (weighted by area)
                if (tag === 'body' || tag === 'main') {
                    addToRole('background', bgColor, 10);
                } else if (tag === 'section' || tag === 'article' || tag === 'header' || tag === 'footer') {
                    addToRole('background', bgColor, 3);
                } else if (tag === 'div') {
                    addToRole('background', bgColor, 1);
                }

                // Text role: p, span, li
                if (tag === 'p' || tag === 'span' || tag === 'li' || tag === 'td' || tag === 'dd') {
                    addToRole('text', textColor, 2);
                } else if (tag === 'body') {
                    addToRole('text', textColor, 5);
                }

                // Heading role
                if (/^h[1-6]$/.test(tag)) {
                    addToRole('heading', textColor, 3);
                }

                // Link role
                if (tag === 'a') {
                    addToRole('link', textColor, 2);
                }

                // Button role
                if (tag === 'button' || (tag === 'a' && /btn|button/.test((el.className || '').toString().toLowerCase()))) {
                    addToRole('button_bg', bgColor, 3);
                    addToRole('button_text', textColor, 2);
                    // Accent: non-neutral button backgrounds
                    if (bgColor && bgColor !== 'rgba(0, 0, 0, 0)' && bgColor !== 'transparent') {
                        addToRole('accent', bgColor, 3);
                    }
                }

                // Border role
                if (borderColor && borderColor !== 'rgba(0, 0, 0, 0)' && borderColor !== textColor) {
                    addToRole('border', borderColor, 1);
                }
            }

            // Also check CSS variables — both color-named and color-valued
            const rootStyles = window.getComputedStyle(document.documentElement);
            const cssVars = {};
            const colorVarNames = /color|bg|background|accent|primary|secondary|brand|text|link|border|surface|foreground|muted|destructive|warning|success|info|highlight|neutral/i;
            const colorValuePattern = /^(#[0-9a-f]{3,8}|rgb|hsl|oklch|color\(|lab\(|lch\()/i;

            for (let i = 0; i < rootStyles.length; i++) {
                const prop = rootStyles[i];
                if (!prop.startsWith('--')) continue;

                const val = rootStyles.getPropertyValue(prop).trim();
                if (!val) continue;

                // Include if name suggests color OR value is a color
                if (colorVarNames.test(prop) || colorValuePattern.test(val)) {
                    cssVars[prop] = val;
                }
            }

            return {
                color_counts: colorCounts,
                css_variables: cssVars,
                role_buckets: roleBuckets
            };
        }''')

        # Convert RGB/RGBA to hex for clustering
        hex_color_counts = self._convert_to_hex_counts(color_data['color_counts'])

        # ── CSS Variable Intelligence ──
        # CSS custom properties are intentional design tokens — they carry far
        # more signal than computed styles inherited through the cascade.
        css_vars = color_data.get('css_variables', {})
        intentional_colors = self._extract_intentional_colors(css_vars)
        css_var_roles = self._assign_roles_from_var_names(css_vars)
        has_design_tokens = len(css_vars) >= 5  # 5+ color vars = deliberate system

        if intentional_colors:
            logger.info(
                "Found %d intentional colors from %d CSS variables",
                len(intentional_colors), len(css_vars)
            )

        # Intelligent color analysis with clustering
        color_intelligence = None
        try:
            from color_intelligence import extract_color_intelligence
            color_intelligence = extract_color_intelligence(hex_color_counts)
            logger.info(
                "Classified %d color roles",
                len(color_intelligence.get('color_palette', {}))
            )
        except Exception as e:
            logger.warning("Color intelligence failed: %s", str(e)[:100])

        # Basic palette analysis — boosted by intentional colors
        all_colors = list(color_data['color_counts'].keys())
        palette = self._analyze_color_palette(all_colors)

        # Inject intentional colors into primary palette (they ARE the palette)
        if intentional_colors:
            # Intentional colors go first — they're the design tokens
            existing_primary = set(self._extract_hex_colors(palette['primary']))
            boosted = []
            for hex_c in intentional_colors:
                if hex_c not in existing_primary:
                    boosted.append(hex_c)
            palette['intentional'] = intentional_colors
            # Merge: intentional first, then existing (deduped), cap at 8
            merged = intentional_colors + [c for c in palette['primary'] if c not in intentional_colors]
            palette['primary'] = merged[:8]

        # Visual preview (keep existing functionality for UI)
        hex_colors = self._extract_hex_colors(palette['primary'])
        preview_analysis = None
        if hex_colors:
            try:
                from color_palette_preview import ColorPalettePreview
                preview_gen = ColorPalettePreview(hex_colors[:10])
                preview_analysis = preview_gen.analyze_palette()
            except Exception as e:
                logger.warning("Preview generation failed: %s", str(e)[:100])

        # Compute semantic color roles from role buckets
        color_roles = self._compute_semantic_roles(
            color_data.get('role_buckets', {}),
            color_data['color_counts']
        )

        # Layer CSS variable roles on top (higher signal than computed style roles)
        if css_var_roles:
            for role, hex_val in css_var_roles.items():
                if role not in color_roles or has_design_tokens:
                    color_roles[role] = hex_val

        # Enrich with hover color roles from MCP state capture (if available)
        mcp_capture = ctx.evidence.get('_mcp_state_capture')
        if mcp_capture and mcp_capture.get('hover_colors'):
            hover_roles = self._extract_hover_color_roles(mcp_capture['hover_colors'])
            color_roles.update(hover_roles)
            logger.info(f"Added {len(hover_roles)} hover color roles from physical state capture")

        # ── Confidence calculation ──
        # Base from intelligence, boosted by CSS variable evidence
        base_confidence = color_intelligence.get('confidence', 70) if color_intelligence else 70
        if has_design_tokens:
            base_confidence = max(base_confidence, 85)  # Design tokens = high confidence
        if len(css_vars) >= 20:
            base_confidence = min(base_confidence + 5, 95)  # Many vars = very confident
        if intentional_colors:
            base_confidence = max(base_confidence, 80)  # Intentional colors found

        # Combine old and new analysis
        result = {
            'pattern': f"{len(palette['primary'])} primary colors detected",
            'confidence': base_confidence,
            'palette': palette,
            'css_variables': css_vars,
            'code_snippets': self._generate_color_snippets(palette),
            'preview': preview_analysis,
            'color_roles': color_roles
        }

        # Add intelligent analysis if available
        if color_intelligence:
            result['intelligent_palette'] = color_intelligence.get('color_palette', {})
            result['evidence_trail'] = color_intelligence.get('evidence_trail', {})
            result['total_colors_analyzed'] = color_intelligence.get('total_colors_analyzed', 0)

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_color_palette(colors):
        """Simple color grouping"""
        return {
            'primary': colors[:5],
            'secondary': colors[5:10] if len(colors) > 5 else []
        }

    @staticmethod
    def _extract_hex_colors(color_list):
        """Extract hex colors from rgb/rgba strings"""
        hex_colors = []

        for color_str in color_list:
            if not color_str:
                continue

            # If already hex
            if color_str.startswith('#'):
                hex_colors.append(color_str)
                continue

            # Convert rgb/rgba to hex
            rgb_match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color_str)
            if rgb_match:
                r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
                hex_color = f'#{r:02x}{g:02x}{b:02x}'
                hex_colors.append(hex_color)

        return list(set(hex_colors))

    @staticmethod
    def _convert_to_hex_counts(color_counts):
        """Convert RGB/RGBA color counts to hex color counts"""
        hex_counts = {}

        for color_str, count in color_counts.items():
            if not color_str:
                continue

            # If already hex
            if color_str.startswith('#'):
                hex_counts[color_str] = hex_counts.get(color_str, 0) + count
                continue

            # Convert rgb/rgba to hex
            rgb_match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color_str)
            if rgb_match:
                r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
                hex_color = f'#{r:02x}{g:02x}{b:02x}'
                hex_counts[hex_color] = hex_counts.get(hex_color, 0) + count

        return hex_counts

    def _compute_semantic_roles(self, role_buckets: Dict, color_counts: Dict) -> Dict:
        """Pick the top color per semantic role bucket, converting to hex."""
        roles = {}

        # Helper: pick highest-weighted color from a bucket, convert to hex
        def top_color(bucket: Dict) -> str:
            if not bucket:
                return None
            # Sort by weight descending
            sorted_colors = sorted(bucket.items(), key=lambda x: -x[1])
            for color_str, _ in sorted_colors:
                hexes = self._extract_hex_colors([color_str])
                if hexes:
                    return hexes[0]
            return None

        role_map = {
            'background': 'background',
            'text': 'text',
            'heading': 'heading',
            'link': 'link',
            'accent': 'accent',
            'border': 'border',
            'button_bg': 'button_bg',
            'button_text': 'button_text',
        }

        for bucket_key, role_name in role_map.items():
            bucket = role_buckets.get(bucket_key, {})
            color = top_color(bucket)
            if color:
                roles[role_name] = color

        # If accent wasn't found from buttons, try links that aren't pure black/white
        if 'accent' not in roles and 'link' in roles:
            link_hex = roles['link']
            if link_hex not in ('#000000', '#ffffff', '#000', '#fff'):
                roles['accent'] = link_hex

        return roles

    def _extract_hover_color_roles(self, hover_colors: Dict) -> Dict:
        """Extract semantic hover color roles from MCP capture data.

        hover_colors format: { 'button_hover': [{'resting': rgb, 'hover': rgb}, ...], ... }
        Returns: { 'button_bg_hover': '#hex', 'link_text_hover': '#hex', 'focus_ring': '#hex' }
        """
        roles = {}

        role_map = {
            'button_hover': 'button_bg_hover',
            'link_hover': 'link_hover',
            'button_text_hover': 'button_text_hover',
            'link_text_hover': 'link_text_hover',
            'role-button_hover': 'button_bg_hover',
            'role-button_text_hover': 'button_text_hover',
        }

        for capture_key, role_name in role_map.items():
            entries = hover_colors.get(capture_key, [])
            if not entries:
                continue
            # Use the most common hover color
            from collections import Counter
            hover_vals = [e['hover'] for e in entries if e.get('hover')]
            if not hover_vals:
                continue
            most_common = Counter(hover_vals).most_common(1)[0][0]
            hexes = self._extract_hex_colors([most_common])
            if hexes:
                roles[role_name] = hexes[0]

        return roles

    def _extract_intentional_colors(self, css_vars: Dict) -> list:
        """Extract hex colors from CSS custom properties — these are design tokens.

        CSS variables are intentionally declared by the designer/developer,
        so they carry far more signal than computed styles inherited through
        the cascade (which includes browser defaults like black text).
        """
        intentional = []
        seen = set()

        for var_name, var_value in css_vars.items():
            hexes = self._extract_hex_colors([var_value])
            for h in hexes:
                h_lower = h.lower()
                # Skip near-black/white — these are usually defaults, not brand colors
                if h_lower in ('#000000', '#ffffff', '#000', '#fff', '#111', '#111111',
                               '#fefefe', '#fdfdfd', '#fcfcfc', '#f8f8f8', '#f5f5f5',
                               '#eeeeee', '#eee', '#222', '#222222', '#333', '#333333'):
                    continue
                if h_lower not in seen:
                    seen.add(h_lower)
                    intentional.append(h)

        return intentional[:12]  # Cap at 12 unique intentional colors

    @classmethod
    def _assign_roles_from_var_names(cls, css_vars: Dict) -> Dict:
        """Assign semantic color roles from CSS variable names.

        e.g. --color-primary → accent, --bg-surface → background,
             --text-color → text, --link-color → link
        """
        roles = {}

        # Map var name patterns to semantic roles (ordered by specificity)
        ROLE_PATTERNS = [
            (r'primary|brand|accent',     'accent'),
            (r'bg[-_]?color|background',  'background'),
            (r'surface',                  'background'),
            (r'text[-_]?color|foreground', 'text'),
            (r'heading',                  'heading'),
            (r'link',                     'link'),
            (r'border',                   'border'),
            (r'secondary',               'secondary'),
            (r'muted|subtle',            'muted'),
            (r'destructive|error|danger', 'error'),
            (r'success',                 'success'),
            (r'warning',                 'warning'),
        ]

        for var_name, var_value in css_vars.items():
            hexes = cls._extract_hex_colors([var_value])
            if not hexes:
                continue
            hex_val = hexes[0]

            name_lower = var_name.lower()
            for pattern, role in ROLE_PATTERNS:
                if re.search(pattern, name_lower) and role not in roles:
                    roles[role] = hex_val
                    break

        return roles

    @staticmethod
    def _generate_color_snippets(palette):
        return ":root {\n  " + "\n  ".join(
            [f"--color-{i}: {c};" for i, c in enumerate(palette['primary'][:3])]
        ) + "\n}"
