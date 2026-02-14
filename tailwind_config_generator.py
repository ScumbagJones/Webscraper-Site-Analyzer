"""
Tailwind CSS Config Generator

Generates tailwind.config.js from extracted design tokens.
Enables immediate integration with Tailwind-based projects.

Output: tailwind.config.js ready to use
"""

from typing import Dict, List, Optional
import json
import re


class TailwindConfigGenerator:
    """
    Generate Tailwind config from evidence.

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

        # Line heights
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
        self.duration_tiers = motion_details.get('duration_scale', {}).get('tiers', {})
        self.easing_roles = motion_details.get('easing_palette', {}).get('roles', {})
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

    def generate(self) -> str:
        """Generate complete tailwind.config.js file"""
        config_parts = []

        config_parts.append(self._generate_header())
        config_parts.append("module.exports = {")
        config_parts.append("  content: [")
        config_parts.append("    './src/**/*.{js,jsx,ts,tsx}',")
        config_parts.append("    './public/index.html',")
        config_parts.append("  ],")
        config_parts.append("  theme: {")
        config_parts.append("    extend: {")

        # Colors
        colors_config = self._generate_colors()
        if colors_config:
            config_parts.append(colors_config)

        # Font family
        fonts_config = self._generate_font_family()
        if fonts_config:
            config_parts.append(fonts_config)

        # Font size
        font_size_config = self._generate_font_size()
        if font_size_config:
            config_parts.append(font_size_config)

        # Font weight
        font_weight_config = self._generate_font_weight()
        if font_weight_config:
            config_parts.append(font_weight_config)

        # Line height
        line_height_config = self._generate_line_height()
        if line_height_config:
            config_parts.append(line_height_config)

        # Spacing
        spacing_config = self._generate_spacing()
        if spacing_config:
            config_parts.append(spacing_config)

        # Box shadow
        shadow_config = self._generate_shadows()
        if shadow_config:
            config_parts.append(shadow_config)

        # Border radius
        radius_config = self._generate_border_radius()
        if radius_config:
            config_parts.append(radius_config)

        # Transition duration
        transition_duration_config = self._generate_transition_duration()
        if transition_duration_config:
            config_parts.append(transition_duration_config)

        # Transition timing function
        transition_timing_config = self._generate_transition_timing()
        if transition_timing_config:
            config_parts.append(transition_timing_config)

        # Keyframe animations
        animation_config = self._generate_animation()
        if animation_config:
            config_parts.append(animation_config)

        # Screens (breakpoints)
        screens_config = self._generate_screens()
        if screens_config:
            config_parts.append(screens_config)

        config_parts.append("    },")
        config_parts.append("  },")
        config_parts.append("  plugins: [],")
        config_parts.append("};")

        return '\n'.join(config_parts)

    def _generate_header(self) -> str:
        return """/** @type {import('tailwindcss').Config} */
/**
 * Tailwind CSS Configuration
 * Generated from design system analysis
 *
 * Customize this file to match your project needs.
 */
"""

    def _generate_colors(self) -> str:
        """Generate colors configuration"""
        lines = []
        lines.append("      colors: {")

        has_content = False

        # Color roles (most semantic)
        if self.color_roles:
            for role, color_value in self.color_roles.items():
                key = role.lower().replace(' ', '-').replace('_', '-')
                lines.append(f"        '{key}': '{color_value}',")
            has_content = True

        # Intelligent palette
        if not has_content and self.intelligent_palette:
            for category, colors in self.intelligent_palette.items():
                if not isinstance(colors, list):
                    continue
                for i, c in enumerate(colors[:3]):
                    if isinstance(c, dict) and 'hex' in c:
                        suffix = f"-{i+1}" if i > 0 else ""
                        lines.append(f"        '{category}{suffix}': '{c['hex']}',")
                        has_content = True

        # Fallback: raw palette
        if not has_content and self.palette_colors:
            for i, color_value in enumerate(self.palette_colors[:10], 1):
                lines.append(f"        'palette-{i}': '{color_value}',")
                has_content = True

        if not has_content:
            return ""

        lines.append("      },")
        return '\n'.join(lines)

    def _generate_font_family(self) -> str:
        """Generate fontFamily configuration"""
        if not self.fonts:
            return ""

        lines = []
        lines.append("      fontFamily: {")

        primary_name = self.fonts[0].split(',')[0].strip().strip('"').strip("'")
        font_stack = self._build_font_stack(primary_name)
        lines.append(f"        'primary': {font_stack},")

        if len(self.fonts) > 1:
            secondary_name = self.fonts[1].split(',')[0].strip().strip('"').strip("'")
            font_stack = self._build_font_stack(secondary_name)
            lines.append(f"        'secondary': {font_stack},")

        lines.append("      },")
        return '\n'.join(lines)

    def _build_font_stack(self, primary_font: str) -> str:
        if 'mono' in primary_font.lower() or 'code' in primary_font.lower():
            fallback = "'Courier New', monospace"
        elif 'serif' in primary_font.lower():
            fallback = "Georgia, 'Times New Roman', serif"
        else:
            fallback = "system-ui, -apple-system, sans-serif"
        return f"['{primary_font}', {fallback}]"

    def _generate_font_size(self) -> str:
        """Generate fontSize configuration"""
        if not self.font_sizes:
            return ""

        lines = []
        lines.append("      fontSize: {")

        size_names = ['xs', 'sm', 'base', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl', '6xl', '7xl', '8xl', '9xl']
        sorted_sizes = sorted(self.font_sizes)

        for i, size in enumerate(sorted_sizes[:13]):
            name = size_names[i] if i < len(size_names) else f'text-{i}'
            line_height = self._calculate_line_height_for_size(size)
            lines.append(f"        '{name}': ['{size}px', '{line_height}'],")

        lines.append("      },")
        return '\n'.join(lines)

    def _calculate_line_height_for_size(self, font_size: float) -> str:
        if font_size < 16:
            return '1.5'
        elif font_size < 24:
            return '1.4'
        elif font_size < 36:
            return '1.3'
        else:
            return '1.2'

    def _generate_font_weight(self) -> str:
        """Generate fontWeight configuration"""
        if not self.font_weights:
            return ""

        lines = []
        lines.append("      fontWeight: {")

        weight_names = {
            100: 'thin', 200: 'extralight', 300: 'light',
            400: 'normal', 500: 'medium', 600: 'semibold',
            700: 'bold', 800: 'extrabold', 900: 'black'
        }

        for weight in sorted(set(self.font_weights)):
            name = weight_names.get(weight, f'weight-{weight}')
            lines.append(f"        '{name}': '{weight}',")

        lines.append("      },")
        return '\n'.join(lines)

    def _generate_line_height(self) -> str:
        """Generate lineHeight configuration"""
        if not self.line_heights:
            return ""

        unique_lh = sorted(set(self.line_heights))
        if len(unique_lh) < 2:
            return ""

        lines = []
        lines.append("      lineHeight: {")
        lines.append(f"        'tight': '{min(unique_lh)}',")
        lines.append("        'normal': '1.5',")
        lines.append(f"        'relaxed': '{max(unique_lh)}',")
        lines.append("      },")

        return '\n'.join(lines)

    def _generate_spacing(self) -> str:
        """Generate spacing configuration"""
        if not self.spacing_scale:
            return ""

        lines = []
        lines.append("      spacing: {")

        names = ['xs', 'sm', 'md', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl', '6xl']
        for i, value in enumerate(self.spacing_scale[:10]):
            name = names[i] if i < len(names) else f'{i}'
            lines.append(f"        '{name}': '{value}px',")

        lines.append("      },")
        return '\n'.join(lines)

    def _generate_shadows(self) -> str:
        """Generate boxShadow configuration"""
        if not self.shadow_levels:
            return ""

        lines = []
        lines.append("      boxShadow: {")

        names = ['sm', 'DEFAULT', 'md', 'lg', 'xl', '2xl']
        for i, shadow in enumerate(self.shadow_levels[:6]):
            if not isinstance(shadow, dict):
                continue
            name = names[i] if i < len(names) else f'shadow-{i}'
            shadow_css = shadow.get('css', 'none')
            lines.append(f"        '{name}': '{shadow_css}',")

        lines.append("      },")
        return '\n'.join(lines)

    def _generate_border_radius(self) -> str:
        """Generate borderRadius configuration"""
        if not self.border_radius_levels:
            return ""

        lines = []
        lines.append("      borderRadius: {")

        names = ['sm', 'DEFAULT', 'md', 'lg', 'xl', 'full']

        # Sort by px value, deduplicate
        seen = set()
        sorted_levels = sorted(
            [l for l in self.border_radius_levels if isinstance(l, dict)],
            key=lambda x: x.get('px', 0)
        )

        idx = 0
        for level in sorted_levels:
            value = level.get('value', level.get('display', '0px'))
            px = level.get('px', 0)

            if px in seen:
                continue
            seen.add(px)

            name = names[idx] if idx < len(names) else f'radius-{idx}'

            if px >= 9999 or value in ('50%', '9999px'):
                name = 'full'

            radius_value = value if isinstance(value, str) else f"{value}px"
            lines.append(f"        '{name}': '{radius_value}',")
            idx += 1
            if idx >= 6:
                break

        lines.append("      },")
        return '\n'.join(lines)

    def _generate_transition_duration(self) -> str:
        """Generate transitionDuration configuration from motion tokens"""
        if not self.duration_tiers:
            return ""

        lines = []
        lines.append("      transitionDuration: {")

        for tier_name, tier_data in sorted(self.duration_tiers.items(), key=lambda x: x[1].get('ms', 0)):
            if isinstance(tier_data, dict) and 'ms' in tier_data:
                lines.append(f"        '{tier_name}': '{tier_data['ms']}ms',")

        lines.append("      },")
        return '\n'.join(lines)

    def _generate_transition_timing(self) -> str:
        """Generate transitionTimingFunction configuration from motion tokens"""
        if not self.easing_roles:
            return ""

        lines = []
        lines.append("      transitionTimingFunction: {")

        for role_name, easing_value in self.easing_roles.items():
            if easing_value:
                lines.append(f"        '{role_name}': '{easing_value}',")

        lines.append("      },")
        return '\n'.join(lines)

    def _generate_animation(self) -> str:
        """Generate animation configuration from keyframe tokens"""
        if not self.keyframe_animations:
            return ""

        # Only include animations that have timing info
        useful = [kf for kf in self.keyframe_animations if kf.get('duration_ms', 0) > 0]
        if not useful:
            return ""

        lines = []
        lines.append("      animation: {")

        for kf in useful[:8]:
            name = kf['name']
            dur = kf.get('duration_ms', 300)
            easing = kf.get('easing', 'ease')
            iteration = kf.get('iteration', '1')
            iter_str = ' infinite' if iteration == 'infinite' else ''
            lines.append(f"        '{name}': '{name} {dur}ms {easing}{iter_str}',")

        lines.append("      },")
        return '\n'.join(lines)

    def _generate_screens(self) -> str:
        """Generate screens (breakpoints) configuration"""
        if not self.unique_breakpoints:
            return ""

        lines = []
        lines.append("    },")  # Close extend
        lines.append("    screens: {")

        names = ['sm', 'md', 'lg', 'xl', '2xl']
        sorted_bp = sorted(self.unique_breakpoints)

        for i, bp in enumerate(sorted_bp[:5]):
            name = names[i] if i < len(names) else f'screen-{i}'
            bp_val = bp if isinstance(bp, (int, float)) else 0
            lines.append(f"      '{name}': '{bp_val}px',")

        return '\n'.join(lines)

    def export_to_file(self, filepath: str = 'tailwind.config.js'):
        """Export to JavaScript file"""
        config = self.generate()
        with open(filepath, 'w') as f:
            f.write(config)
        return filepath
