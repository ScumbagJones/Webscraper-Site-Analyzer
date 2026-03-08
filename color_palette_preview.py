"""
Color Palette Preview - RealTimeColors-Style Live Previews

Enhancements:
1. Live UI component previews (buttons, cards, inputs)
2. WCAG contrast ratio calculator
3. Color role detection (primary, secondary, accent, neutral)
4. Accessible pairing suggestions
5. Export to CSS vars, Tailwind, Figma

Use case: Instead of just showing hex codes, show HOW they'd look in a real UI
"""

import math
from typing import Dict, List, Tuple


class ColorPalettePreview:
    """
    Generate live previews and accessibility analysis for color palettes
    """

    def __init__(self, colors: List[str]):
        """
        Args:
            colors: List of hex color codes (e.g., ['#0066ff', '#00ff88'])
        """
        self.colors = colors

    def analyze_palette(self) -> Dict:
        """
        Comprehensive palette analysis with live previews

        Returns:
            {
                'color_roles': {'primary': '#0066ff', 'success': '#00ff88', ...},
                'contrast_matrix': [[7.2, 3.1, ...], ...],
                'accessible_pairs': [('#0066ff', '#ffffff'), ...],
                'preview_components': {...},
                'export_formats': {...}
            }
        """
        contrast_matrix = self._calculate_contrast_matrix()
        accessible_pairs = self._find_accessible_pairs(contrast_matrix)
        preview_components = self._generate_component_previews()
        export_formats = self._generate_export_formats()

        return {
            'color_roles': self._detect_color_roles(),
            'contrast_matrix': contrast_matrix,
            'accessible_pairs': accessible_pairs,
            'preview_components': preview_components,
            'export_formats': export_formats,
            'wcag_compliance': self._check_wcag_compliance(contrast_matrix),
        }

    def _detect_color_roles(self) -> Dict:
        """
        Detect which color is primary, secondary, accent, etc.
        Based on HSL values and common color theory
        """
        roles = {}
        for color in self.colors:
            try:
                h, s, l = self._hex_to_hsl(color)
                if 180 <= h <= 240 and s >= 0.5 and 0.4 <= l <= 0.6:
                    roles.setdefault('primary', color)
                elif 90 <= h <= 150:
                    roles.setdefault('success', color)
                elif 30 <= h <= 60:
                    roles.setdefault('warning', color)
                elif h <= 20 or h >= 340:
                    roles.setdefault('error', color)
                elif l >= 0.85:
                    roles.setdefault('neutral_light', color)
                elif l <= 0.2:
                    roles.setdefault('neutral_dark', color)
            except Exception:
                pass
        return roles

    def _calculate_contrast_matrix(self) -> List[List[float]]:
        """
        Calculate WCAG contrast ratios between all color pairs
        """
        matrix = []
        for color1 in self.colors:
            row = []
            for color2 in self.colors:
                try:
                    ratio = round(self._calculate_contrast_ratio(color1, color2), 2)
                except Exception:
                    ratio = 1.0
                row.append(ratio)
            matrix.append(row)
        return matrix

    def _calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """
        Calculate WCAG 2.1 contrast ratio between two colors

        Formula: (L1 + 0.05) / (L2 + 0.05)
        where L1 is lighter, L2 is darker
        """
        l1 = self._get_relative_luminance(color1)
        l2 = self._get_relative_luminance(color2)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    def _get_relative_luminance(self, hex_color: str) -> float:
        """
        Calculate relative luminance for WCAG contrast
        https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
        """
        r, g, b = self._hex_to_rgb(hex_color)

        def transform(c):
            c = c / 255
            if c <= 0.03928:
                return c / 12.92
            return ((c + 0.055) / 1.055) ** 2.4

        return 0.2126 * transform(r) + 0.7152 * transform(g) + 0.0722 * transform(b)

    def _find_accessible_pairs(self, contrast_matrix: List[List[float]]) -> List:
        """
        Find color pairs that meet WCAG AA or AAA standards

        Returns list of (color1, color2, ratio, level)
        """
        pairs = []
        for i, color1 in enumerate(self.colors):
            for j, color2 in enumerate(self.colors):
                if i == j:
                    continue
                ratio = contrast_matrix[i][j]
                if ratio >= 7.0:
                    pairs.append((color1, color2, ratio, 'AAA'))
                elif ratio >= 4.5:
                    pairs.append((color1, color2, ratio, 'AA'))
                elif ratio >= 3.0:
                    pairs.append((color1, color2, ratio, 'AA Large'))
        return sorted(pairs, key=lambda x: x[2], reverse=True)

    def _generate_component_previews(self) -> Dict:
        """
        Generate HTML for live UI component previews
        """
        previews = {}
        roles = self._detect_color_roles()

        primary = roles.get('primary', self.colors[0] if self.colors else '#0066ff')
        previews['button_primary'] = self._generate_button_html(primary, 'Sign Up Now')

        success = roles.get('success', '#00ff88')
        if success:
            previews['alert_success'] = self._generate_alert_html(success, '✓ Payment Successful')

        bg = roles.get('neutral_light', '#f7f7f7')
        text = roles.get('neutral_dark', '#1a1a1a')
        previews['card'] = self._generate_card_html(bg, text)

        return previews

    def _get_best_text_color(self, bg_color: str) -> str:
        """
        Determine if white or black text has better contrast on bg_color
        """
        white_contrast = self._calculate_contrast_ratio(bg_color, '#ffffff')
        black_contrast = self._calculate_contrast_ratio(bg_color, '#000000')
        return '#ffffff' if white_contrast >= black_contrast else '#000000'

    def _generate_button_html(self, bg: str, text: str) -> str:
        """Generate button preview HTML"""
        text_color = self._get_best_text_color(bg)
        return (
            '<button style="background: ' + bg +
            '; color: ' + text_color +
            '; padding: 12px 24px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">' +
            text + '</button>'
        )

    def _generate_alert_html(self, theme_color: str, message: str) -> str:
        """Generate alert preview HTML"""
        try:
            bg = self._lighten_color(theme_color, 0.9)
            border = theme_color
            text = self._darken_color(theme_color, 0.3)
        except Exception:
            bg, border, text = theme_color, theme_color, '#000000'
        return (
            '<div style="background: ' + bg +
            '; border-left: 4px solid ' + border +
            '; color: ' + text +
            '; padding: 16px; border-radius: 8px;">' +
            message + '</div>'
        )

    def _generate_card_html(self, bg: str, text: str) -> str:
        """Generate card preview HTML"""
        return (
            '<div style="background: ' + bg +
            '; color: ' + text +
            '; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">'
            '<h3 style="margin: 0 0 8px 0;">Card Title</h3>'
            '<p style="margin: 0; opacity: 0.8;">Card content goes here</p></div>'
        )

    def _generate_export_formats(self) -> Dict:
        """
        Generate export formats: CSS vars, Tailwind, Figma
        """
        exports = {}
        roles = self._detect_color_roles()

        css_vars = ':root {\n'
        for role, color in roles.items():
            key = role.replace('_', '-')
            css_vars += f'  --color-{key}: {color};\n'
        css_vars += '}'
        exports['css_variables'] = css_vars

        tailwind_colors = ',\n  '.join(
            [f"'{k}': '{v}'" for k, v in roles.items()]
        )
        exports['tailwind_config'] = f'colors: {{\n  {tailwind_colors}\n}}'

        exports['figma_palette'] = [
            {'name': role.replace('_', ' ').title(), 'color': color}
            for role, color in roles.items()
        ]

        return exports

    def _check_wcag_compliance(self, contrast_matrix: List[List[float]]) -> Dict:
        """
        Check overall WCAG compliance of the palette
        """
        total_pairs = 0
        aa_compliant = 0
        aaa_compliant = 0
        for i in range(len(self.colors)):
            for j in range(len(self.colors)):
                if i == j:
                    continue
                total_pairs += 1
                ratio = contrast_matrix[i][j]
                if ratio >= 4.5:
                    aa_compliant += 1
                if ratio >= 7.0:
                    aaa_compliant += 1
        denom = total_pairs or 1
        return {
            'total_pairs': total_pairs,
            'aa_compliant': aa_compliant,
            'aaa_compliant': aaa_compliant,
            'aa_pass_rate': round(aa_compliant / denom * 100, 1),
            'aaa_pass_rate': round(aaa_compliant / denom * 100, 1),
        }

    # ── Color math utilities ─────────────────────────────────────────────

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex to RGB"""
        h = hex_color.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """Convert RGB to hex"""
        return '#' + f'{r:02x}{g:02x}{b:02x}'

    def _hex_to_hsl(self, hex_color: str) -> Tuple[float, float, float]:
        """Convert hex to HSL"""
        r, g, b = self._hex_to_rgb(hex_color)
        r, g, b = r / 255, g / 255, b / 255
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        l = (max_c + min_c) / 2
        if max_c == min_c:
            return 0, 0, l
        d = max_c - min_c
        s = d / (2 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)
        if max_c == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif max_c == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        return h * 360 / 6, s, l

    def _lighten_color(self, hex_color: str, amount: float) -> str:
        """Lighten a color by amount (0-1)"""
        h, s, l = self._hex_to_hsl(hex_color)
        return self._hsl_to_hex(h, s, min(1.0, l + amount * (1.0 - l)))

    def _darken_color(self, hex_color: str, amount: float) -> str:
        """Darken a color by amount (0-1)"""
        h, s, l = self._hex_to_hsl(hex_color)
        return self._hsl_to_hex(h, s, max(0.0, l * (1.0 - amount)))

    def _hsl_to_hex(self, h: float, s: float, l: float) -> str:
        """Convert HSL to hex"""
        h = h / 360

        def hue_to_rgb(p, q, t):
            if t < 0: t += 1
            if t > 1: t -= 1
            if t < 1/6: return p + (q - p) * 6 * t
            if t < 0.5: return q
            if t < 2/3: return p + (q - p) * (2/3 - t) * 6
            return p

        if s == 0:
            r = g = b = l
        else:
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue_to_rgb(p, q, h + 1/3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1/3)

        return self._rgb_to_hex(round(r * 255), round(g * 255), round(b * 255))


if __name__ == '__main__':
    colors = ['#0066ff', '#00ff88', '#ff6b6b', '#f7f7f7', '#1a1a1a']
    preview = ColorPalettePreview(colors)
    analysis = preview.analyze_palette()

    print('\n🎨 COLOR PALETTE ANALYSIS\n')
    print('Color Roles:')
    for role, color in analysis['color_roles'].items():
        print(f'  {role}: {color}')
    print(f"\nAccessible pairs: {len(analysis['accessible_pairs'])}")
    print(f"WCAG AA pass rate: {analysis['wcag_compliance']['aa_pass_rate']}%")
