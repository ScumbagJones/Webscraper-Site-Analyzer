"""
W3C Design Tokens Community Group (DTCG) Format Exporter

Exports design tokens in the industry-standard DTCG format:
https://design-tokens.github.io/community-group/format/

Enables interoperability with:
- Figma Variables
- Style Dictionary
- Design system tools
- Token Studio (Figma plugin)

Output: tokens.json in DTCG format
"""

from typing import Dict, List, Optional
import json
import re


class DTCGTokenExporter:
    """
    Export evidence as W3C DTCG-compliant design tokens.

    Maps to the ACTUAL evidence schema produced by DeepEvidenceEngine.extract_all().
    """

    def __init__(self, evidence: Dict):
        self.evidence = evidence

        # --- Normalize typography ---
        typo_raw = evidence.get('typography', {})
        details = typo_raw.get('details', {})
        intelligent = typo_raw.get('intelligent_typography', {})
        it_scale = intelligent.get('type_scale', {}) if isinstance(intelligent.get('type_scale'), dict) else {}

        self.fonts = details.get('all_fonts', [])
        self.font_sizes = it_scale.get('sizes', [])
        if not self.font_sizes:
            raw_sizes = details.get('all_sizes', [])
            self.font_sizes = sorted(set(self._parse_px(s) for s in raw_sizes if self._parse_px(s)))

        raw_weights = details.get('all_weights', [])
        self.font_weights = []
        for w in raw_weights:
            try:
                self.font_weights.append(int(w))
            except (ValueError, TypeError):
                pass

        # Line heights from body + headings
        self.line_heights = []
        body = details.get('body', {})
        body_lh = body.get('lineHeight', '')
        if body_lh:
            parsed = self._parse_number(str(body_lh))
            if parsed:
                self.line_heights.append(parsed)
        for h in details.get('headings', []):
            lh = h.get('lineHeight', '')
            parsed = self._parse_number(str(lh))
            if parsed:
                self.line_heights.append(parsed)

        # --- Normalize colors ---
        colors_raw = evidence.get('colors', {})
        self.color_roles = colors_raw.get('preview', {}).get('color_roles', {})
        palette = colors_raw.get('palette', {})
        if isinstance(palette, dict):
            self.palette_colors = palette.get('primary', []) + palette.get('secondary', [])
        elif isinstance(palette, list):
            self.palette_colors = palette
        else:
            self.palette_colors = []
        self.intelligent_palette = colors_raw.get('intelligent_palette', {})

        # --- Normalize spacing ---
        spacing_raw = evidence.get('spacing_scale', {})
        self.spacing_scale = spacing_raw.get('scale', [])

        # --- Normalize shadows ---
        shadows_raw = evidence.get('shadow_system', {})
        self.shadow_levels = shadows_raw.get('levels', [])

        # --- Normalize border radius ---
        br_raw = evidence.get('border_radius_scale', {})
        self.border_radius_levels = br_raw.get('levels', [])

        # --- Normalize breakpoints ---
        bp_raw = evidence.get('responsive_breakpoints', {})
        self.unique_breakpoints = bp_raw.get('unique_breakpoints', [])

        # --- Normalize motion tokens ---
        motion_raw = evidence.get('motion_tokens', {})
        motion_details = motion_raw.get('details', {})
        self.duration_scale = motion_details.get('duration_scale', {})
        self.easing_palette = motion_details.get('easing_palette', {})
        self.keyframe_animations = motion_details.get('keyframe_animations', [])

    @staticmethod
    def _parse_px(val) -> Optional[float]:
        if not isinstance(val, str):
            return None
        m = re.match(r'([\d.]+)px', val.strip())
        return float(m.group(1)) if m else None

    @staticmethod
    def _parse_number(val) -> Optional[float]:
        if not isinstance(val, str):
            return None
        m = re.match(r'([\d.]+)', val.strip())
        return float(m.group(1)) if m else None

    def export(self) -> Dict:
        """Generate complete DTCG token file"""
        tokens = {}

        color_tokens = self._export_colors()
        if color_tokens:
            tokens['color'] = color_tokens

        typography_tokens = self._export_typography()
        if typography_tokens:
            tokens['typography'] = typography_tokens

        spacing_tokens = self._export_spacing()
        if spacing_tokens:
            tokens['spacing'] = spacing_tokens

        shadow_tokens = self._export_shadows()
        if shadow_tokens:
            tokens['shadow'] = shadow_tokens

        radius_tokens = self._export_border_radius()
        if radius_tokens:
            tokens['border-radius'] = radius_tokens

        breakpoint_tokens = self._export_breakpoints()
        if breakpoint_tokens:
            tokens['breakpoint'] = breakpoint_tokens

        motion_tokens = self._export_motion()
        if motion_tokens:
            tokens['motion'] = motion_tokens

        return tokens

    def _export_colors(self) -> Dict:
        """Export color tokens in DTCG format"""
        color_tokens = {}

        # Color roles (most semantic)
        for role, color_value in self.color_roles.items():
            token_name = role.lower().replace(' ', '-').replace('_', '-')
            color_tokens[token_name] = {
                "$type": "color",
                "$value": color_value,
                "$description": f"{role.replace('_', ' ').title()} color from detected design system"
            }

        # Intelligent palette (semantic categories)
        if not color_tokens and self.intelligent_palette:
            for category, colors in self.intelligent_palette.items():
                if not isinstance(colors, list):
                    continue
                for i, c in enumerate(colors[:3]):
                    if isinstance(c, dict) and 'hex' in c:
                        suffix = f"-{i+1}" if i > 0 else ""
                        color_tokens[f'{category}{suffix}'] = {
                            "$type": "color",
                            "$value": c['hex'],
                            "$description": f"{category.title()} color {i+1}"
                        }

        # Fallback: raw palette colors
        if not color_tokens and self.palette_colors:
            for i, color_value in enumerate(self.palette_colors[:10], 1):
                color_tokens[f'palette-{i}'] = {
                    "$type": "color",
                    "$value": color_value,
                    "$description": f"Color {i} from detected palette"
                }

        return color_tokens

    def _export_typography(self) -> Dict:
        """Export typography tokens in DTCG format"""
        typo_tokens = {}

        # Font family
        if self.fonts:
            primary_name = self.fonts[0].split(',')[0].strip().strip('"').strip("'")
            typo_tokens['font-family'] = {
                'primary': {
                    "$type": "fontFamily",
                    "$value": primary_name,
                    "$description": "Primary typeface"
                }
            }

            if len(self.fonts) > 1:
                secondary_name = self.fonts[1].split(',')[0].strip().strip('"').strip("'")
                typo_tokens['font-family']['secondary'] = {
                    "$type": "fontFamily",
                    "$value": secondary_name,
                    "$description": "Secondary typeface"
                }

        # Font sizes
        if self.font_sizes:
            typo_tokens['font-size'] = {}
            size_names = ['xs', 'sm', 'base', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl', '6xl']
            sorted_sizes = sorted(self.font_sizes)

            for i, size in enumerate(sorted_sizes[:10]):
                name = size_names[i] if i < len(size_names) else f'size-{i}'
                typo_tokens['font-size'][name] = {
                    "$type": "dimension",
                    "$value": f"{size}px",
                    "$description": f"Font size {name}"
                }

        # Font weights
        if self.font_weights:
            typo_tokens['font-weight'] = {}
            weight_names = {
                300: 'light', 400: 'regular', 500: 'medium',
                600: 'semibold', 700: 'bold', 800: 'extrabold'
            }

            for weight in sorted(set(self.font_weights)):
                name = weight_names.get(weight, f'weight-{weight}')
                typo_tokens['font-weight'][name] = {
                    "$type": "fontWeight",
                    "$value": str(weight),
                    "$description": f"Font weight {name}"
                }

        # Line heights
        if self.line_heights:
            typo_tokens['line-height'] = {}
            unique_lh = sorted(set(self.line_heights))

            if len(unique_lh) >= 2:
                typo_tokens['line-height']['tight'] = {
                    "$type": "number",
                    "$value": str(min(unique_lh)),
                    "$description": "Tight line height for headings"
                }
                typo_tokens['line-height']['normal'] = {
                    "$type": "number",
                    "$value": "1.5",
                    "$description": "Normal line height for body text"
                }
                typo_tokens['line-height']['relaxed'] = {
                    "$type": "number",
                    "$value": str(max(unique_lh)),
                    "$description": "Relaxed line height for large text"
                }

        return typo_tokens

    def _export_spacing(self) -> Dict:
        """Export spacing tokens in DTCG format"""
        spacing_tokens = {}

        if self.spacing_scale:
            names = ['xs', 'sm', 'md', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl', '6xl']

            for i, value in enumerate(self.spacing_scale[:10]):
                name = names[i] if i < len(names) else f'space-{i}'
                spacing_tokens[name] = {
                    "$type": "dimension",
                    "$value": f"{value}px",
                    "$description": f"Spacing {name} - {value}px"
                }

        return spacing_tokens

    def _export_shadows(self) -> Dict:
        """Export shadow tokens in DTCG format"""
        shadow_tokens = {}

        if self.shadow_levels:
            names = ['sm', 'md', 'lg', 'xl', '2xl']

            for i, shadow in enumerate(self.shadow_levels[:5]):
                if not isinstance(shadow, dict):
                    continue
                name = names[i] if i < len(names) else f'shadow-{i}'
                shadow_css = shadow.get('css', 'none')
                shadow_name = shadow.get('name', 'general use')

                shadow_tokens[name] = {
                    "$type": "shadow",
                    "$value": shadow_css,
                    "$description": f"Shadow {name} - {shadow_name}"
                }

        return shadow_tokens

    def _export_border_radius(self) -> Dict:
        """Export border radius tokens in DTCG format"""
        radius_tokens = {}

        if self.border_radius_levels:
            names = ['sm', 'md', 'lg', 'xl', 'full']

            # Sort by px value, deduplicate
            seen_values = set()
            sorted_levels = sorted(
                [l for l in self.border_radius_levels if isinstance(l, dict)],
                key=lambda x: x.get('px', 0)
            )

            idx = 0
            for level in sorted_levels:
                value = level.get('value', level.get('display', '0px'))
                px = level.get('px', 0)

                if px in seen_values:
                    continue
                seen_values.add(px)

                name = names[idx] if idx < len(names) else f'radius-{idx}'

                # Handle pill/full
                if px >= 9999 or value in ('50%', '9999px'):
                    name = 'full'

                radius_tokens[name] = {
                    "$type": "dimension",
                    "$value": value if isinstance(value, str) else f"{value}px",
                    "$description": f"Border radius {name}"
                }
                idx += 1
                if idx >= 6:
                    break

        return radius_tokens

    def _export_breakpoints(self) -> Dict:
        """Export breakpoint tokens in DTCG format"""
        breakpoint_tokens = {}

        if self.unique_breakpoints:
            names = ['sm', 'md', 'lg', 'xl', '2xl']
            sorted_bp = sorted(self.unique_breakpoints)

            for i, bp in enumerate(sorted_bp[:5]):
                name = names[i] if i < len(names) else f'breakpoint-{i}'
                bp_val = bp if isinstance(bp, (int, float)) else 0

                breakpoint_tokens[name] = {
                    "$type": "dimension",
                    "$value": f"{bp_val}px",
                    "$description": f"Breakpoint {name} - {bp_val}px and up"
                }

        return breakpoint_tokens

    def _export_motion(self) -> Dict:
        """Export motion tokens in DTCG format (duration + cubicBezier)"""
        motion_tokens = {}

        # Duration tokens from tiers
        tiers = self.duration_scale.get('tiers', {})
        if tiers:
            motion_tokens['duration'] = {}
            for tier_name, tier_data in tiers.items():
                if isinstance(tier_data, dict) and 'ms' in tier_data:
                    motion_tokens['duration'][tier_name] = {
                        "$type": "duration",
                        "$value": f"{tier_data['ms']}ms",
                        "$description": tier_data.get('usage', f'{tier_name} duration')
                    }

        # Easing tokens from roles
        roles = self.easing_palette.get('roles', {})
        if roles:
            motion_tokens['easing'] = {}
            for role_name, easing_value in roles.items():
                if not easing_value:
                    continue
                # Parse cubic-bezier values for DTCG format
                bezier_match = re.match(
                    r'cubic-bezier\(\s*([\d.e-]+)\s*,\s*([\d.e-]+)\s*,\s*([\d.e-]+)\s*,\s*([\d.e-]+)\s*\)',
                    easing_value
                )
                if bezier_match:
                    values = [float(bezier_match.group(i)) for i in range(1, 5)]
                    motion_tokens['easing'][role_name] = {
                        "$type": "cubicBezier",
                        "$value": values,
                        "$description": f"{role_name.replace('_', ' ').title()} easing curve"
                    }
                else:
                    # Named keywords (ease, ease-in-out, linear)
                    keyword_beziers = {
                        'ease': [0.25, 0.1, 0.25, 1],
                        'ease-in': [0.42, 0, 1, 1],
                        'ease-out': [0, 0, 0.58, 1],
                        'ease-in-out': [0.42, 0, 0.58, 1],
                        'linear': [0, 0, 1, 1],
                    }
                    if easing_value in keyword_beziers:
                        motion_tokens['easing'][role_name] = {
                            "$type": "cubicBezier",
                            "$value": keyword_beziers[easing_value],
                            "$description": f"{role_name.replace('_', ' ').title()} easing ({easing_value})"
                        }

        return motion_tokens

    def export_to_json(self, indent: int = 2) -> str:
        """Export as formatted JSON string"""
        tokens = self.export()
        return json.dumps(tokens, indent=indent)

    def export_to_file(self, filepath: str = 'tokens.json'):
        """Export to JSON file"""
        tokens = self.export()
        with open(filepath, 'w') as f:
            json.dump(tokens, f, indent=2)
        return filepath

    def get_token_count(self) -> Dict[str, int]:
        """Get count of tokens by category"""
        tokens = self.export()
        counts = {}
        for category, category_tokens in tokens.items():
            counts[category] = self._count_tokens_recursive(category_tokens)
        counts['total'] = sum(counts.values())
        return counts

    def _count_tokens_recursive(self, obj: Dict) -> int:
        """Recursively count tokens (objects with $value)"""
        count = 0
        for key, value in obj.items():
            if isinstance(value, dict):
                if '$value' in value:
                    count += 1
                else:
                    count += self._count_tokens_recursive(value)
        return count
