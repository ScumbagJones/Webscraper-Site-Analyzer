"""
Design System Differ - Compare Two Sites

Analyzes differences between two sites' design systems:
- Typography changes (fonts, sizes, weights)
- Color palette differences
- Spacing system variations
- Layout pattern differences
- Shadow and effects changes

Use cases:
- Compare competitor sites
- Track design evolution over time
- Learn from similar products
- Analyze A/B testing variants

Output: Structured diff with insights
"""

from typing import Dict, List, Optional, Tuple
import statistics
import re


def _extract_fonts(evidence: Dict) -> List[str]:
    """Extract font list from actual evidence schema"""
    return evidence.get('typography', {}).get('details', {}).get('all_fonts', [])


def _extract_sizes(evidence: Dict) -> List:
    """Extract font sizes from actual evidence schema"""
    typo = evidence.get('typography', {})
    intelligent = typo.get('intelligent_typography', {})
    it_scale = intelligent.get('type_scale', {}) if isinstance(intelligent.get('type_scale'), dict) else {}
    sizes = it_scale.get('sizes', [])
    if not sizes:
        raw_sizes = typo.get('details', {}).get('all_sizes', [])
        parsed = []
        for s in raw_sizes:
            if isinstance(s, str):
                m = re.match(r'([\d.]+)', s.strip())
                if m:
                    parsed.append(float(m.group(1)))
        sizes = sorted(set(parsed))
    return sizes


def _extract_weights(evidence: Dict) -> List[int]:
    """Extract font weights from actual evidence schema"""
    raw = evidence.get('typography', {}).get('details', {}).get('all_weights', [])
    weights = []
    for w in raw:
        try:
            weights.append(int(w))
        except (ValueError, TypeError):
            pass
    return sorted(set(weights))


def _extract_color_roles(evidence: Dict) -> Dict:
    """Extract color roles from actual evidence schema"""
    return evidence.get('colors', {}).get('preview', {}).get('color_roles', {})


def _extract_palette_list(evidence: Dict) -> List[str]:
    """Extract flat palette list from actual evidence schema"""
    palette = evidence.get('colors', {}).get('palette', {})
    if isinstance(palette, dict):
        return palette.get('primary', []) + palette.get('secondary', [])
    elif isinstance(palette, list):
        return palette
    return []


def _extract_shadow_levels(evidence: Dict) -> List[Dict]:
    """Extract shadow levels from actual evidence schema"""
    return evidence.get('shadow_system', {}).get('levels', [])


def _extract_hero_detected(evidence: Dict) -> bool:
    """Check if hero section detected"""
    vh = evidence.get('visual_hierarchy', {})
    hero = vh.get('hero_section', vh.get('hero_heading', {}))
    return isinstance(hero, dict) and hero.get('detected', False)


class DesignSystemDiffer:
    """
    Compare two design systems and highlight differences.

    Maps to the ACTUAL evidence schema produced by DeepEvidenceEngine.extract_all().
    """

    def __init__(self, site_a_evidence: Dict, site_b_evidence: Dict,
                 site_a_name: str = "Site A", site_b_name: str = "Site B"):
        self.site_a = site_a_evidence
        self.site_b = site_b_evidence
        self.site_a_name = site_a_name
        self.site_b_name = site_b_name

    def compare(self) -> Dict:
        """Generate complete comparison report"""
        return {
            'typography': self._compare_typography(),
            'colors': self._compare_colors(),
            'spacing': self._compare_spacing(),
            'shadows': self._compare_shadows(),
            'layout': self._compare_layout(),
            'interactions': self._compare_interactions(),
            'summary': self._generate_summary()
        }

    def _compare_typography(self) -> Dict:
        """Compare typography systems"""
        fonts_a = _extract_fonts(self.site_a)
        fonts_b = _extract_fonts(self.site_b)

        sizes_a = _extract_sizes(self.site_a)
        sizes_b = _extract_sizes(self.site_b)

        weights_a = _extract_weights(self.site_a)
        weights_b = _extract_weights(self.site_b)

        diff = {
            'fonts': {
                self.site_a_name: fonts_a,
                self.site_b_name: fonts_b,
                'difference': self._describe_font_diff(fonts_a, fonts_b)
            },
            'type_scale': {
                self.site_a_name: {
                    'sizes': sizes_a,
                    'count': len(sizes_a),
                    'range': f"{min(sizes_a)}px - {max(sizes_a)}px" if sizes_a else "none"
                },
                self.site_b_name: {
                    'sizes': sizes_b,
                    'count': len(sizes_b),
                    'range': f"{min(sizes_b)}px - {max(sizes_b)}px" if sizes_b else "none"
                },
                'difference': self._describe_type_scale_diff(sizes_a, sizes_b)
            },
            'weights': {
                self.site_a_name: weights_a,
                self.site_b_name: weights_b,
                'difference': self._describe_weight_diff(weights_a, weights_b)
            }
        }

        return diff

    def _compare_colors(self) -> Dict:
        """Compare color systems"""
        palette_a = _extract_palette_list(self.site_a)
        palette_b = _extract_palette_list(self.site_b)

        roles_a = _extract_color_roles(self.site_a)
        roles_b = _extract_color_roles(self.site_b)

        diff = {
            'palette_size': {
                self.site_a_name: len(palette_a),
                self.site_b_name: len(palette_b),
                'difference': len(palette_b) - len(palette_a)
            },
            'color_roles': {
                self.site_a_name: list(roles_a.keys()),
                self.site_b_name: list(roles_b.keys()),
                'added_roles': [r for r in roles_b if r not in roles_a],
                'removed_roles': [r for r in roles_a if r not in roles_b],
                'changed_values': self._find_changed_color_values(roles_a, roles_b)
            },
            'shared_colors': list(set(palette_a) & set(palette_b)),
            'unique_to_a': [c for c in palette_a if c not in palette_b][:5],
            'unique_to_b': [c for c in palette_b if c not in palette_a][:5]
        }

        return diff

    def _compare_spacing(self) -> Dict:
        """Compare spacing systems"""
        spacing_a = self.site_a.get('spacing_scale', {}).get('scale', [])
        spacing_b = self.site_b.get('spacing_scale', {}).get('scale', [])

        diff = {
            'scale_size': {
                self.site_a_name: len(spacing_a),
                self.site_b_name: len(spacing_b),
                'difference': len(spacing_b) - len(spacing_a)
            },
            'base_unit': {
                self.site_a_name: spacing_a[0] if spacing_a else None,
                self.site_b_name: spacing_b[0] if spacing_b else None,
                'difference': self._describe_base_unit_diff(
                    spacing_a[0] if spacing_a else None,
                    spacing_b[0] if spacing_b else None
                )
            },
            'max_spacing': {
                self.site_a_name: max(spacing_a) if spacing_a else None,
                self.site_b_name: max(spacing_b) if spacing_b else None
            },
            'average_spacing': {
                self.site_a_name: round(statistics.mean(spacing_a)) if spacing_a else None,
                self.site_b_name: round(statistics.mean(spacing_b)) if spacing_b else None
            }
        }

        return diff

    def _compare_shadows(self) -> Dict:
        """Compare shadow systems"""
        shadows_a = _extract_shadow_levels(self.site_a)
        shadows_b = _extract_shadow_levels(self.site_b)

        diff = {
            'shadow_count': {
                self.site_a_name: len(shadows_a),
                self.site_b_name: len(shadows_b),
                'difference': len(shadows_b) - len(shadows_a)
            },
            'depth_philosophy': {
                self.site_a_name: self._infer_depth_philosophy(shadows_a),
                self.site_b_name: self._infer_depth_philosophy(shadows_b)
            }
        }

        return diff

    def _compare_layout(self) -> Dict:
        """Compare layout patterns"""
        visual_a = self.site_a.get('visual_hierarchy', {})
        visual_b = self.site_b.get('visual_hierarchy', {})

        diff = {
            'has_hero': {
                self.site_a_name: _extract_hero_detected(self.site_a),
                self.site_b_name: _extract_hero_detected(self.site_b)
            },
            'has_navigation': {
                self.site_a_name: visual_a.get('navigation', {}).get('exists', False),
                self.site_b_name: visual_b.get('navigation', {}).get('exists', False)
            },
            'content_groups': {
                self.site_a_name: len(visual_a.get('content_groups', [])),
                self.site_b_name: len(visual_b.get('content_groups', []))
            },
            'reading_pattern': {
                self.site_a_name: visual_a.get('reading_pattern', 'Unknown'),
                self.site_b_name: visual_b.get('reading_pattern', 'Unknown')
            }
        }

        return diff

    def _compare_interactions(self) -> Dict:
        """Compare interaction patterns"""
        interact_a = self.site_a.get('interaction_states', {})
        interact_b = self.site_b.get('interaction_states', {})

        # In the actual schema, interaction_states has computed_states, utility_classes, state_deltas
        # All are typically empty dicts, so we compare confidence and pattern
        conf_a = interact_a.get('confidence', 0)
        conf_b = interact_b.get('confidence', 0)
        pattern_a = interact_a.get('pattern', 'None detected')
        pattern_b = interact_b.get('pattern', 'None detected')

        diff = {
            'confidence': {
                self.site_a_name: conf_a,
                self.site_b_name: conf_b
            },
            'pattern': {
                self.site_a_name: pattern_a,
                self.site_b_name: pattern_b
            },
            'comparison': self._describe_interaction_diff(conf_a, conf_b)
        }

        return diff

    def _generate_summary(self) -> Dict:
        """Generate high-level summary of differences"""
        typo_diff = self._compare_typography()
        color_diff = self._compare_colors()
        spacing_diff = self._compare_spacing()

        key_differences = []

        if typo_diff['fonts']['difference']:
            key_differences.append(typo_diff['fonts']['difference'])

        palette_diff = color_diff['palette_size']['difference']
        if abs(palette_diff) >= 3:
            if palette_diff > 0:
                key_differences.append(f"{self.site_b_name} has {palette_diff} more colors")
            else:
                key_differences.append(f"{self.site_a_name} has {abs(palette_diff)} more colors")

        base_diff = spacing_diff['base_unit']['difference']
        if base_diff:
            key_differences.append(base_diff)

        return {
            'key_differences': key_differences,
            'similarity_score': self._calculate_similarity_score(),
            'recommendation': self._generate_recommendation()
        }

    def _describe_font_diff(self, fonts_a: List[str], fonts_b: List[str]) -> str:
        if not fonts_a and not fonts_b:
            return "Both use system fonts"
        if fonts_a == fonts_b:
            return "Identical font stacks"
        if not fonts_a:
            return f"{self.site_b_name} uses custom fonts ({', '.join(fonts_b[:2])})"
        if not fonts_b:
            return f"{self.site_a_name} uses custom fonts ({', '.join(fonts_a[:2])})"

        # Clean primary font names for comparison
        primary_a = fonts_a[0].split(',')[0].strip().strip('"').strip("'")
        primary_b = fonts_b[0].split(',')[0].strip().strip('"').strip("'")

        if primary_a != primary_b:
            return f"Different primary fonts: {primary_a} vs {primary_b}"

        added = [f for f in fonts_b if f not in fonts_a]
        if added:
            return f"{self.site_b_name} adds: {', '.join(added[:2])}"

        return "Similar font stacks"

    def _describe_type_scale_diff(self, sizes_a: List, sizes_b: List) -> str:
        if not sizes_a or not sizes_b:
            return "Cannot compare (missing data)"

        diff_count = len(sizes_b) - len(sizes_a)

        if abs(diff_count) >= 2:
            if diff_count > 0:
                return f"{self.site_b_name} has {diff_count} more font sizes ({len(sizes_b)} vs {len(sizes_a)})"
            else:
                return f"{self.site_a_name} has {abs(diff_count)} more font sizes"

        max_a = max(sizes_a)
        max_b = max(sizes_b)

        if abs(max_a - max_b) >= 12:
            if max_b > max_a:
                return f"{self.site_b_name} has larger display type (up to {max_b}px vs {max_a}px)"
            else:
                return f"{self.site_a_name} has larger display type"

        return "Similar type scales"

    def _describe_weight_diff(self, weights_a: List, weights_b: List) -> str:
        if not weights_a or not weights_b:
            return "Cannot compare (missing data)"

        added = [w for w in weights_b if w not in weights_a]
        removed = [w for w in weights_a if w not in weights_b]

        if added:
            return f"{self.site_b_name} adds weights: {', '.join(map(str, added))}"
        if removed:
            return f"{self.site_a_name} has weights not in {self.site_b_name}: {', '.join(map(str, removed))}"

        return "Identical font weights"

    def _describe_base_unit_diff(self, base_a: Optional[int], base_b: Optional[int]) -> str:
        if base_a is None or base_b is None:
            return "Cannot compare"
        if base_a == base_b:
            return f"Both use {base_a}px base unit"
        if base_a < base_b:
            return f"{self.site_a_name} is more compact ({base_a}px vs {base_b}px)"
        else:
            return f"{self.site_b_name} is more compact ({base_b}px vs {base_a}px)"

    def _find_changed_color_values(self, roles_a: Dict, roles_b: Dict) -> Dict:
        changed = {}
        for role in set(roles_a.keys()) & set(roles_b.keys()):
            if roles_a[role] != roles_b[role]:
                changed[role] = {
                    self.site_a_name: roles_a[role],
                    self.site_b_name: roles_b[role]
                }
        return changed

    def _infer_depth_philosophy(self, shadows: List) -> str:
        count = len(shadows)
        if count == 0:
            return "Flat design (no shadows)"
        elif count <= 2:
            return "Minimal depth (subtle shadows)"
        elif count <= 4:
            return "Moderate depth (layered elevation)"
        else:
            return "Deep depth hierarchy (strong elevation)"

    def _describe_interaction_diff(self, conf_a: int, conf_b: int) -> str:
        if conf_a <= 30 and conf_b <= 30:
            return "Neither site has reliably detectable interaction states"
        if conf_a > 50 and conf_b <= 30:
            return f"{self.site_a_name} has detectable interaction states, {self.site_b_name} does not"
        if conf_b > 50 and conf_a <= 30:
            return f"{self.site_b_name} has detectable interaction states, {self.site_a_name} does not"
        return "Similar interaction detection confidence"

    def _calculate_similarity_score(self) -> float:
        score = 0
        max_score = 0

        # Typography similarity (30 points)
        fonts_a = _extract_fonts(self.site_a)
        fonts_b = _extract_fonts(self.site_b)

        if fonts_a and fonts_b:
            name_a = fonts_a[0].split(',')[0].strip().strip('"').strip("'").lower()
            name_b = fonts_b[0].split(',')[0].strip().strip('"').strip("'").lower()
            if name_a == name_b:
                score += 15

        sizes_a = _extract_sizes(self.site_a)
        sizes_b = _extract_sizes(self.site_b)

        if sizes_a and sizes_b:
            size_diff = abs(len(sizes_a) - len(sizes_b))
            if size_diff <= 1:
                score += 15

        max_score += 30

        # Color similarity (30 points)
        palette_a = _extract_palette_list(self.site_a)
        palette_b = _extract_palette_list(self.site_b)

        if palette_a and palette_b:
            overlap = len(set(palette_a) & set(palette_b))
            score += min(30, (overlap / max(len(palette_a), len(palette_b))) * 30)

        max_score += 30

        # Spacing similarity (20 points)
        spacing_a = self.site_a.get('spacing_scale', {}).get('scale', [])
        spacing_b = self.site_b.get('spacing_scale', {}).get('scale', [])

        if spacing_a and spacing_b:
            if spacing_a[0] == spacing_b[0]:
                score += 20

        max_score += 20

        # Shadow similarity (20 points)
        shadows_a = len(_extract_shadow_levels(self.site_a))
        shadows_b = len(_extract_shadow_levels(self.site_b))

        shadow_diff = abs(shadows_a - shadows_b)
        if shadow_diff <= 1:
            score += 20
        elif shadow_diff <= 2:
            score += 10

        max_score += 20

        return round((score / max_score) * 100, 1) if max_score > 0 else 0

    def _generate_recommendation(self) -> str:
        similarity = self._calculate_similarity_score()

        if similarity >= 80:
            return "Very similar design systems - likely same brand or design team"
        elif similarity >= 60:
            return "Moderately similar - may share design principles or target audience"
        elif similarity >= 40:
            return "Some similarities - may be in same industry or category"
        else:
            return "Distinct design systems - different design philosophies"
