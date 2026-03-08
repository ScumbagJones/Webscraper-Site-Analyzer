"""
Design Debt Analyzer

Ingests DeepEvidenceEngine output and acts as a design linter.
Firecrawl tells you what IS. This tells you what is WRONG.

Three categories of debt:
1. Color orphans    - colors used once that deviate slightly from the palette
2. Scale violations - font sizes that break the detected typographic scale ratio
3. Aria misses      - interactive elements missing accessible labels/roles
4. Spacing noise    - spacing values that fall off the detected base-unit grid

Usage:
    from design_debt_analyzer import DesignDebtAnalyzer

    evidence = engine.extract_all()  # from DeepEvidenceEngine
    analyzer = DesignDebtAnalyzer(evidence)
    report   = analyzer.generate_report()
    print(report['debt_score'])  # 0-100, lower = cleaner
"""

import math
import re
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Color utilities
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> Optional[Tuple[int, int, int]]:
    hex_color = hex_color.lstrip('#').strip()
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        return None
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert sRGB to CIELAB (D65 illuminant). Used for perceptual color diff."""
    r, g, b = r / 255.0, g / 255.0, b / 255.0

    def linearize(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = linearize(r), linearize(g), linearize(b)

    # sRGB -> XYZ (D65)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    # Normalize to D65 white point
    x, y, z = x / 0.95047, y / 1.00000, z / 1.08883

    def f(t):
        return t ** (1/3) if t > 0.008856 else 7.787 * t + 16/116

    fx, fy, fz = f(x), f(y), f(z)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b_ = 200 * (fy - fz)
    return L, a, b_


def _delta_e(c1: str, c2: str) -> float:
    """Perceptual color distance (CIE76 ΔE). <5 is barely noticeable."""
    rgb1 = _hex_to_rgb(c1)
    rgb2 = _hex_to_rgb(c2)
    if rgb1 is None or rgb2 is None:
        return 999.0
    L1, a1, b1 = _rgb_to_lab(*rgb1)
    L2, a2, b2 = _rgb_to_lab(*rgb2)
    return math.sqrt((L2 - L1) ** 2 + (a2 - a1) ** 2 + (b2 - b1) ** 2)


def _normalize_color(c: str) -> str:
    """Strip alpha, lowercase, normalize hex."""
    c = c.strip().lower()
    # rgba/rgb → strip alpha, approximate hex
    if c.startswith('rgba'):
        m = re.match(r'rgba\((\d+),\s*(\d+),\s*(\d+)', c)
        if m:
            return '#{:02x}{:02x}{:02x}'.format(*map(int, m.groups()))
    if c.startswith('rgb'):
        m = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)', c)
        if m:
            return '#{:02x}{:02x}{:02x}'.format(*map(int, m.groups()))
    if c.startswith('#'):
        return c
    return c


# ---------------------------------------------------------------------------
# Typography scale utilities
# ---------------------------------------------------------------------------

COMMON_RATIOS = {
    'minor_second':    1.067,
    'major_second':    1.125,
    'minor_third':     1.200,
    'major_third':     1.250,
    'perfect_fourth':  1.333,
    'augmented_fourth':1.414,
    'perfect_fifth':   1.500,
    'golden_ratio':    1.618,
}


def _detect_scale_ratio(sizes_px: List[float]) -> Tuple[Optional[float], str]:
    """
    Given a list of font sizes, return the best-fit typographic scale ratio
    and its name. Returns (ratio, name) or (None, 'none') if no scale detected.
    """
    if len(sizes_px) < 3:
        return None, 'none'

    sizes = sorted(set(sizes_px))
    best_ratio, best_name, best_score = None, 'custom', 0.0

    for name, ratio in COMMON_RATIOS.items():
        matches = 0
        for i in range(len(sizes) - 1):
            if sizes[i] < 1:
                continue
            actual = sizes[i + 1] / sizes[i]
            if abs(actual - ratio) / ratio < 0.08:  # 8% tolerance
                matches += 1
        score = matches / max(len(sizes) - 1, 1)
        if score > best_score:
            best_score, best_ratio, best_name = score, ratio, name

    return (best_ratio, best_name) if best_score > 0.4 else (None, 'none')


def _snap_to_scale(size: float, base: float, ratio: float) -> float:
    """Find the nearest scale step for a given size."""
    if ratio <= 1 or base <= 0:
        return size
    # Try +/- 4 steps from base
    best = base
    best_dist = abs(size - base)
    for step in range(-4, 5):
        candidate = base * (ratio ** step)
        dist = abs(size - candidate)
        if dist < best_dist:
            best_dist = dist
            best = candidate
    return best


# ---------------------------------------------------------------------------
# Spacing utilities
# ---------------------------------------------------------------------------

def _parse_px(value) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.match(r'([\d.]+)(?:px)?$', value.strip())
        if m:
            return float(m.group(1))
    return None


def _base_unit_from_string(base_unit_str: str) -> float:
    v = _parse_px(base_unit_str)
    return v if v is not None else 4.0


# ---------------------------------------------------------------------------
# Main analyzer
# ---------------------------------------------------------------------------

class DesignDebtAnalyzer:
    """
    Lints a DeepEvidenceEngine evidence dict for design inconsistencies.

    Debt score: 0 = perfectly consistent, 100 = extremely noisy system.
    Typical healthy sites score 0-25. Utility-first CSS sites score 30-60.
    """

    # Color orphan thresholds
    COLOR_ORPHAN_DELTA_E_MIN = 3.0   # below this = likely alias, not orphan
    COLOR_ORPHAN_DELTA_E_MAX = 20.0  # above this = intentionally different color
    COLOR_ORPHAN_USAGE_MAX = 2       # colors used this many times or fewer

    # Type scale thresholds
    SCALE_VIOLATION_TOLERANCE_PCT = 0.12   # 12% deviation from nearest scale step
    SCALE_VIOLATION_MIN_SIZE_PX = 10       # skip tiny sizes (line-height remnants)

    # Spacing deviation threshold
    SPACING_DEVIATION_PCT = 0.25          # 25% off grid = flagged

    def __init__(self, evidence: dict):
        self.evidence = evidence
        self.issues: List[dict] = []

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def generate_report(self) -> dict:
        self.issues = []
        self._detect_color_orphans()
        self._detect_scale_violations()
        self._detect_aria_misses()
        self._detect_spacing_deviations()

        critical   = [i for i in self.issues if i['severity'] == 'critical']
        warnings   = [i for i in self.issues if i['severity'] == 'warning']
        suggestions= [i for i in self.issues if i['severity'] == 'suggestion']

        debt_score = self._calculate_debt_score(critical, warnings, suggestions)

        return {
            'debt_score':        debt_score,
            'debt_grade':        self._debt_grade(debt_score),
            'total_issues':      len(self.issues),
            'summary': {
                'critical':    len(critical),
                'warnings':    len(warnings),
                'suggestions': len(suggestions),
            },
            'color_orphans':      [i for i in self.issues if i['type'] == 'color_orphan'],
            'scale_violations':   [i for i in self.issues if i['type'] == 'scale_violation'],
            'aria_misses':        [i for i in self.issues if i['type'] == 'aria_miss'],
            'spacing_deviations': [i for i in self.issues if i['type'] == 'spacing_deviation'],
            'fix_priority':       self._prioritized_fixes(),
        }

    # -----------------------------------------------------------------------
    # Detector: Color orphans
    # -----------------------------------------------------------------------

    def _detect_color_orphans(self):
        """
        Find colors used rarely that are perceptually close to (but not identical to)
        a primary or secondary palette color.

        These are likely accidental color deviations — e.g. #3B82F7 vs #3B82F6.
        """
        colors = self.evidence.get('colors', {})
        palette = colors.get('palette', {})

        # Build reference set from primary + secondary palette
        reference_colors: List[str] = []
        for group in ('primary', 'secondary', 'intentional'):
            for c in palette.get(group, []):
                norm = _normalize_color(str(c))
                if norm.startswith('#') and len(norm) >= 7:
                    reference_colors.append(norm)

        if not reference_colors:
            return

        # Get all colors with usage counts
        all_colors = colors.get('all_colors', colors.get('raw_values', []))
        usage_counts = colors.get('usage_counts', {})

        # Fallback: treat palette colors as having >1 usage, everything else as 1
        if not all_colors:
            return

        for raw_color in all_colors:
            norm = _normalize_color(str(raw_color))
            if not norm.startswith('#') or len(norm) < 7:
                continue

            usage = usage_counts.get(norm, usage_counts.get(raw_color, 1))
            if usage > self.COLOR_ORPHAN_USAGE_MAX:
                continue  # Used enough to be intentional

            # Check against each reference color
            for ref in reference_colors:
                if norm == ref:
                    break  # Exact match — it IS a palette color
                delta = _delta_e(norm, ref)
                if self.COLOR_ORPHAN_DELTA_E_MIN <= delta <= self.COLOR_ORPHAN_DELTA_E_MAX:
                    self.issues.append({
                        'type':      'color_orphan',
                        'severity':  'warning',
                        'color':     norm,
                        'closest_palette_color': ref,
                        'delta_e':   round(delta, 1),
                        'usage_count': usage,
                        'suggestion': (
                            f"Replace {norm} with {ref} (ΔE={delta:.1f}, "
                            f"barely perceptible difference) or add to palette explicitly."
                        ),
                    })
                    break

    # -----------------------------------------------------------------------
    # Detector: Type scale violations
    # -----------------------------------------------------------------------

    def _detect_scale_violations(self):
        """
        Detect font sizes that don't fit the detected typographic scale.

        Skips sizes < 10px (captions, icons) and the base size itself.
        """
        typography = self.evidence.get('typography', {})

        # Get type scale info
        type_scale = typography.get('type_scale', {})
        sizes_px: List[float] = []

        if isinstance(type_scale, dict):
            raw_sizes = type_scale.get('sizes_px', type_scale.get('all_sizes', []))
            sizes_px = [_parse_px(s) for s in raw_sizes if _parse_px(s) is not None]
            ratio = type_scale.get('ratio')
            if isinstance(ratio, str):
                ratio = COMMON_RATIOS.get(ratio)
        else:
            ratio = None

        # Fallback: try to find sizes from raw typography data
        if not sizes_px:
            raw = typography.get('font_sizes', typography.get('sizes', []))
            sizes_px = [_parse_px(s) for s in raw if _parse_px(s) is not None]

        if not sizes_px:
            return

        # Detect ratio if not provided
        if not ratio:
            ratio, _ = _detect_scale_ratio(sizes_px)
        if not ratio:
            return

        # Base is the most common or median size
        filtered = [s for s in sizes_px if s >= self.SCALE_VIOLATION_MIN_SIZE_PX]
        if not filtered:
            return

        filtered.sort()
        base = filtered[len(filtered) // 2]  # median

        for size in set(filtered):
            snapped = _snap_to_scale(size, base, ratio)
            deviation_pct = abs(size - snapped) / snapped if snapped > 0 else 0

            if deviation_pct > self.SCALE_VIOLATION_TOLERANCE_PCT:
                # Find which scale step it should be
                suggestion_size = round(snapped, 1)
                self.issues.append({
                    'type':           'scale_violation',
                    'severity':       'warning' if deviation_pct < 0.25 else 'critical',
                    'size_px':        round(size, 1),
                    'nearest_scale':  suggestion_size,
                    'deviation_pct':  round(deviation_pct * 100, 1),
                    'scale_ratio':    ratio,
                    'suggestion': (
                        f"Font size {size}px is {deviation_pct*100:.0f}% off the "
                        f"{ratio:.3f} scale. Use {suggestion_size}px instead."
                    ),
                })

    # -----------------------------------------------------------------------
    # Detector: Aria misses
    # -----------------------------------------------------------------------

    def _detect_aria_misses(self):
        """
        Find elements that appear interactive but lack accessible markup.

        Sources: interactions extractor, accessibility extractor.
        """
        interactions = self.evidence.get('interactions', {})
        accessibility = self.evidence.get('accessibility', {})

        # Check reported interactive elements
        interactive_elements = (
            interactions.get('elements', []) +
            interactions.get('interactive_elements', [])
        )

        aria_issues = accessibility.get('missing_labels', [])
        if aria_issues:
            for elem in aria_issues[:20]:  # cap at 20
                self.issues.append({
                    'type':      'aria_miss',
                    'severity':  'critical',
                    'element':   elem.get('selector', elem.get('element', 'unknown')),
                    'element_type': elem.get('type', 'interactive'),
                    'suggestion': (
                        f"Add aria-label or aria-labelledby to "
                        f"{elem.get('selector', 'this element')}. "
                        "Keyboard and screen-reader users cannot identify it."
                    ),
                })

        # Check for buttons/links without text from interaction data
        for elem in interactive_elements[:50]:
            if isinstance(elem, dict):
                label = elem.get('text', elem.get('label', elem.get('aria_label', '')))
                role  = elem.get('role', elem.get('type', ''))
                sel   = elem.get('selector', elem.get('element', ''))
                if not label and role in ('button', 'link', 'menuitem', 'tab', 'checkbox', 'radio'):
                    self.issues.append({
                        'type':      'aria_miss',
                        'severity':  'warning',
                        'element':   sel,
                        'element_type': role,
                        'suggestion': (
                            f"'{sel}' acts as a {role} but has no visible text or aria-label. "
                            "Add aria-label describing its action."
                        ),
                    })

    # -----------------------------------------------------------------------
    # Detector: Spacing deviations
    # -----------------------------------------------------------------------

    def _detect_spacing_deviations(self):
        """
        Find spacing values that don't align to the detected base unit grid.

        If the site uses an 8px grid, values like 7px, 13px, 22px are noise.
        """
        spacing = self.evidence.get('spacing_scale', {})
        base_unit_str = spacing.get('base_unit', '4px')
        base_unit = _base_unit_from_string(str(base_unit_str))

        if base_unit < 1:
            return

        scale_values = spacing.get('scale', spacing.get('values', []))
        if not scale_values:
            return

        for raw_val in scale_values:
            px = _parse_px(raw_val)
            if px is None or px < 4:
                continue  # Skip tiny/zero values

            # Check if it snaps to the grid
            nearest = round(px / base_unit) * base_unit
            if nearest == 0:
                nearest = base_unit

            deviation_pct = abs(px - nearest) / nearest if nearest > 0 else 0

            if deviation_pct > self.SPACING_DEVIATION_PCT and abs(px - nearest) >= 2:
                self.issues.append({
                    'type':          'spacing_deviation',
                    'severity':      'suggestion',
                    'value_px':      px,
                    'base_unit_px':  base_unit,
                    'nearest_grid':  nearest,
                    'deviation_px':  round(abs(px - nearest), 1),
                    'suggestion': (
                        f"{px}px doesn't align to the {base_unit}px grid. "
                        f"Use {nearest}px instead."
                    ),
                })

    # -----------------------------------------------------------------------
    # Scoring
    # -----------------------------------------------------------------------

    def _calculate_debt_score(self, critical, warnings, suggestions) -> int:
        """
        Debt score: 0 = clean, 100 = severe inconsistency.

        Weighting: critical=10pts, warning=4pts, suggestion=1pt.
        Capped at 100. Normalized against page complexity estimate.
        """
        raw = (len(critical) * 10) + (len(warnings) * 4) + (len(suggestions) * 1)
        return min(100, raw)

    def _debt_grade(self, score: int) -> str:
        if score <= 10:  return 'A — Highly consistent'
        if score <= 25:  return 'B — Minor inconsistencies'
        if score <= 45:  return 'C — Noticeable debt'
        if score <= 65:  return 'D — Significant debt'
        return                  'F — Severely inconsistent'

    def _prioritized_fixes(self) -> List[dict]:
        """Return top 5 highest-impact fixes sorted by severity."""
        severity_order = {'critical': 0, 'warning': 1, 'suggestion': 2}
        sorted_issues = sorted(
            self.issues,
            key=lambda i: severity_order.get(i.get('severity', 'suggestion'), 3)
        )
        return [
            {
                'rank':       rank + 1,
                'type':       i['type'],
                'severity':   i['severity'],
                'suggestion': i['suggestion'],
            }
            for rank, i in enumerate(sorted_issues[:5])
        ]
