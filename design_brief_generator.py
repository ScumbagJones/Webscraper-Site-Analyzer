"""
Design Brief Generator - Synthesize evidence into human-readable design descriptions

Transforms raw metrics into natural language descriptions of:
- Visual style and personality
- Layout patterns and grid systems
- Typography philosophy
- Color psychology
- Interaction patterns
- Target audience indicators

Output: LLM-friendly design brief that bridges "what I see" to "what to build"
"""

from typing import Dict, List, Optional
import statistics
import re


class DesignBriefGenerator:
    """
    Generate plain-English design briefs from evidence.

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
            self.font_sizes = sorted(set(self._parse_px(s) for s in raw_sizes if self._parse_px(s)), reverse=True)

        self.type_scale_ratio = it_scale.get('ratio', typo_raw.get('type_scale', None))
        self.type_scale_pattern = it_scale.get('pattern', '')
        self.body_style = details.get('body', {})

        raw_weights = details.get('all_weights', [])
        self.font_weights = []
        for w in raw_weights:
            try:
                self.font_weights.append(int(w))
            except (ValueError, TypeError):
                pass

        # Line heights from body + headings
        self.line_heights = []
        body_lh = self.body_style.get('lineHeight', '')
        if body_lh:
            parsed = self._parse_px(str(body_lh))
            if parsed:
                self.line_heights.append(parsed)
        for h in details.get('headings', []):
            lh = h.get('lineHeight', '')
            parsed = self._parse_px(str(lh))
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
        self.spacing_base = spacing_raw.get('base_unit', 8)

        # --- Normalize shadows ---
        shadows_raw = evidence.get('shadow_system', {})
        self.shadow_levels = shadows_raw.get('levels', [])

        # --- Other evidence ---
        self.layout = evidence.get('layout', {})
        self.visual_hierarchy = evidence.get('visual_hierarchy', {})

        anim_raw = evidence.get('animations', {})
        anim_details = anim_raw.get('details', {})
        self.animations_list = anim_details.get('animations', [])
        self.transitions_list = anim_details.get('transitions', [])

        acc_raw = evidence.get('accessibility', {})
        self.accessibility_details = acc_raw.get('details', {})
        self.accessibility_score = acc_raw.get('score', 0)

        # --- Normalize motion choreography ---
        motion_raw = evidence.get('motion_tokens', {})
        self.motion_choreography = motion_raw.get('choreography', [])
        self.motion_personality_text = motion_raw.get('motion_personality', '')

    @staticmethod
    def _parse_px(val: str) -> Optional[float]:
        if not isinstance(val, str):
            return None
        m = re.match(r'([\d.]+)', val.strip())
        return float(m.group(1)) if m else None

    def generate(self) -> Dict[str, str]:
        """Generate complete design brief"""
        return {
            'overview': self._generate_overview(),
            'visual_style': self._generate_visual_style(),
            'typography_approach': self._generate_typography_approach(),
            'color_strategy': self._generate_color_strategy(),
            'layout_system': self._generate_layout_system(),
            'interaction_patterns': self._generate_interaction_patterns(),
            'target_audience': self._generate_target_audience(),
            'technical_approach': self._generate_technical_approach(),
            'quick_start_guide': self._generate_quick_start_guide()
        }

    def _generate_overview(self) -> str:
        """One-paragraph summary of the design"""
        personality = self._infer_personality()

        # Primary font
        primary_font = None
        if self.fonts:
            primary_font = self.fonts[0].split(',')[0].strip().strip('"').strip("'")

        color_count = len(self.palette_colors)
        has_shadows = len(self.shadow_levels) > 2

        parts = []
        parts.append(f"This is a **{personality}** design")

        if primary_font:
            parts.append(f"using **{primary_font}** for typography")

        if color_count > 5:
            parts.append(f"with a **rich color palette** ({color_count} colors)")
        elif color_count > 0:
            parts.append(f"with a **minimal color palette** ({color_count} colors)")

        if has_shadows:
            parts.append("featuring **elevated depth** through shadows")

        parts.append("The layout emphasizes")

        hero = self.visual_hierarchy.get('hero_section', self.visual_hierarchy.get('hero_heading', {}))
        if isinstance(hero, dict) and hero.get('detected'):
            parts.append("**large hero headlines** and")

        parts.append("**clear content hierarchy**.")

        return ' '.join(parts)

    def _infer_personality(self) -> str:
        """Infer design personality from metrics"""
        avg_spacing = statistics.mean(self.spacing_scale) if self.spacing_scale else 16
        shadow_count = len(self.shadow_levels)
        has_animations = len(self.animations_list) + len(self.transitions_list) > 5

        if avg_spacing > 24 and shadow_count > 3:
            return "modern, premium"
        elif avg_spacing < 12 and shadow_count < 2:
            return "compact, utilitarian"
        elif has_animations:
            return "dynamic, engaging"
        elif shadow_count > 4:
            return "layered, dimensional"
        else:
            return "clean, professional"

    def _generate_visual_style(self) -> str:
        """Describe the overall visual aesthetic"""
        parts = []

        shadow_count = len(self.shadow_levels)
        if shadow_count > 4:
            parts.append("**Deep depth hierarchy** with multiple shadow layers creating strong elevation.")
        elif shadow_count > 2:
            parts.append("**Moderate depth** using subtle shadows for card and button elevation.")
        else:
            parts.append("**Flat design** with minimal or no shadows, emphasizing content over depth.")

        parts.append("\n\n**Corners:** Modern rounded corners for a friendly, approachable feel.")

        if self.spacing_scale:
            base_unit = self.spacing_base if self.spacing_base else (self.spacing_scale[0] if self.spacing_scale else 8)
            if base_unit == 4:
                parts.append(f"\n\n**Spacing system:** 4px base unit (tight, compact design)")
            elif base_unit == 8:
                parts.append(f"\n\n**Spacing system:** 8px base unit (balanced, standard spacing)")
            else:
                parts.append(f"\n\n**Spacing system:** {base_unit}px base unit")

        return ' '.join(parts)

    def _generate_typography_approach(self) -> str:
        """Describe typography philosophy"""
        parts = []

        if self.fonts:
            primary_font = self.fonts[0].split(',')[0].strip().strip('"').strip("'")
            parts.append(f"**Primary typeface:** {primary_font}")

            if any(kw in primary_font.lower() for kw in ['inter', 'roboto', 'sohne', 'sf pro']):
                parts.append("(neutral, highly readable, tech-forward)")
            elif any(kw in primary_font.lower() for kw in ['serif', 'georgia', 'times', 'livory']):
                parts.append("(traditional, authoritative, editorial)")
            elif any(kw in primary_font.lower() for kw in ['mono', 'courier', 'code']):
                parts.append("(technical, developer-focused)")

        # Type scale
        ratio = self.type_scale_ratio
        if isinstance(ratio, (int, float)) and ratio > 0:
            pattern = self.type_scale_pattern or 'Custom'
            parts.append(f"\n\n**Type scale:** {pattern} (ratio: {ratio:.2f})")

            if ratio >= 1.5:
                parts.append("- Creates dramatic size contrast between headings and body")
            elif ratio >= 1.33:
                parts.append("- Provides clear hierarchy without excessive contrast")
            else:
                parts.append("- Subtle size differences, content-focused")

        # Size range
        if self.font_sizes and len(self.font_sizes) > 3:
            numeric = [s for s in self.font_sizes if isinstance(s, (int, float))]
            if numeric:
                min_size = min(numeric)
                max_size = max(numeric)
                parts.append(f"\n\n**Size range:** {min_size}px to {max_size}px")

                if max_size > 48:
                    parts.append("- Features large display typography for hero sections")
                if min_size < 14:
                    parts.append("- Includes small text for captions and metadata")

        return ' '.join(parts)

    def _generate_color_strategy(self) -> str:
        """Describe color usage and psychology"""
        parts = []

        if self.color_roles:
            parts.append("**Color roles:**")
            for role, color in list(self.color_roles.items())[:5]:
                parts.append(f"\n- **{role.replace('_', ' ').title()}:** `{color}`")

        # Intelligent palette categories
        if self.intelligent_palette:
            categories = list(self.intelligent_palette.keys())
            if categories:
                parts.append(f"\n\n**Palette categories:** {', '.join(categories)}")

        palette_size = len(self.palette_colors)
        if palette_size > 10:
            parts.append(f"\n\n**Palette:** Rich and expressive ({palette_size} colors)")
            parts.append("- Supports diverse content types and states")
        elif palette_size > 5:
            parts.append(f"\n\n**Palette:** Balanced and intentional ({palette_size} colors)")
            parts.append("- Provides flexibility without overwhelming")
        elif palette_size > 0:
            parts.append(f"\n\n**Palette:** Minimal and focused ({palette_size} colors)")
            parts.append("- Emphasizes simplicity and brand consistency")

        return ' '.join(parts)

    def _generate_layout_system(self) -> str:
        """Describe layout patterns and grid system"""
        parts = []
        parts.append("**Layout approach:**")

        hero = self.visual_hierarchy.get('hero_section', self.visual_hierarchy.get('hero_heading', {}))
        has_hero = isinstance(hero, dict) and hero.get('detected', False)
        nav = self.visual_hierarchy.get('navigation', {})
        has_nav = isinstance(nav, dict) and nav.get('exists', False)

        if has_nav and has_hero:
            parts.append("\n- Fixed navigation bar at top")
            parts.append("\n- Hero section with large headline and CTA")
            parts.append("\n- Content sections with clear separation")
        elif has_nav:
            parts.append("\n- Navigation-focused header")
            parts.append("\n- Content-first layout with minimal decoration")

        reading_pattern = self.visual_hierarchy.get('reading_pattern', '')
        if reading_pattern:
            parts.append(f"\n- **Reading pattern:** {reading_pattern}")

        parts.append("\n\n**Grid system:**")
        parts.append("\n- Responsive grid using CSS Grid or Flexbox")
        parts.append("\n- Mobile-first approach with breakpoints")
        parts.append("\n- Container max-width for optimal readability (typically 1200-1400px)")

        content_groups = self.visual_hierarchy.get('content_groups', [])
        if content_groups and len(content_groups) > 3:
            parts.append(f"\n\n**Content grouping:** {len(content_groups)} distinct sections")
            parts.append("\n- Likely uses card-based layout for content modules")

        return ' '.join(parts)

    def _generate_interaction_patterns(self) -> str:
        """Describe interactive elements and motion system"""
        primary_cta = self.visual_hierarchy.get('primary_cta', {})
        motion_tokens = self.evidence.get('motion_tokens', {})
        motion_details = motion_tokens.get('details', {})

        parts = []

        if isinstance(primary_cta, dict) and primary_cta.get('detected'):
            parts.append(f"**Primary CTA:** {primary_cta.get('text', 'Call to action')}")
            parts.append("\n- Prominent button with clear action-oriented text")

        # Motion system (from synthesized tokens)
        duration_scale = motion_details.get('duration_scale', {})
        easing_palette = motion_details.get('easing_palette', {})
        motion_patterns = motion_details.get('motion_patterns', [])
        keyframes = motion_details.get('keyframe_animations', [])
        libraries = motion_details.get('libraries', [])

        if duration_scale.get('values_ms'):
            values = duration_scale['values_ms']
            total = duration_scale.get('total_parsed', 0)
            tiers = duration_scale.get('tiers', {})

            # Infer motion personality from tier distribution
            fast_count = sum(t.get('count', 0) for name, t in tiers.items() if name in ('micro', 'fast'))
            slow_count = sum(t.get('count', 0) for name, t in tiers.items() if name in ('slow', 'dramatic'))

            parts.append(f"\n\n**Motion system:** {total} transitions across {len(values)} duration tiers")
            parts.append(f"\n- Duration scale: {', '.join(f'{v}ms' for v in values)}")

            if not self.motion_personality_text:
                if fast_count > slow_count * 2:
                    parts.append("\n- **Personality:** Snappy and responsive — most transitions under 200ms")
                elif slow_count > fast_count:
                    parts.append("\n- **Personality:** Cinematic and deliberate — emphasis on smooth, longer transitions")
                else:
                    parts.append("\n- **Personality:** Balanced — mix of quick feedback and smooth state changes")

        if easing_palette.get('primary'):
            primary_easing = easing_palette['primary']
            curves = easing_palette.get('curves', [])
            parts.append(f"\n\n**Primary easing:** `{primary_easing}`")

            # Attribution for known curves
            for c in curves[:3]:
                if c.get('known_as'):
                    parts.append(f"\n- `{c['value']}` matches **{c['known_as'].replace('-', ' ').replace('_', ' ')}**")

            roles = easing_palette.get('roles', {})
            role_parts = []
            for role, value in roles.items():
                if value:
                    role_parts.append(f"{role}: `{value}`")
            if role_parts:
                parts.append(f"\n- Roles: {', '.join(role_parts)}")

        # Choreography descriptions (human-readable) or fallback to pattern listing
        if self.motion_choreography:
            parts.append("\n\n**Motion choreography** (CSS declarations detected):")
            for entry in self.motion_choreography[:6]:
                parts.append(f"\n- {entry.get('description', '')}")
        elif motion_patterns:
            parts.append("\n\n**Motion patterns:**")
            for p in motion_patterns[:4]:
                name = p.get('name', '').replace('_', ' ')
                dur = p.get('duration_ms', 0)
                count = p.get('element_count', 0)
                parts.append(f"\n- **{name}:** {dur}ms, {count} elements")

        if not self.motion_choreography:
            if keyframes:
                named = [kf['name'] for kf in keyframes if kf.get('name') and kf.get('duration_ms', 0) > 0]
                if named:
                    parts.append(f"\n\n**Keyframe animations:** {', '.join(named[:5])}")

        if libraries:
            parts.append(f"\n\n**Animation libraries:** {', '.join(libraries)}")

        # Motion personality summary
        if self.motion_personality_text:
            parts.append(f"\n\n**Motion personality:** {self.motion_personality_text}")

        # Fallback for sites with no motion data
        if not duration_scale.get('values_ms') and not easing_palette.get('primary'):
            transition_count = len(self.transitions_list)
            if transition_count > 0:
                parts.append(f"\n\n**Transitions:** {transition_count} CSS transitions detected")
            else:
                parts.append("\n\n**Motion:** Minimal — likely uses simple hover/click states")

        if not parts:
            parts.append("**Interactions:** Minimal detected")

        return ' '.join(parts)

    def _generate_target_audience(self) -> str:
        """Infer target audience from design decisions"""
        dom_depth = self.evidence.get('dom_depth', {}).get('max_depth', 10)
        is_complex = dom_depth > 20

        has_custom_fonts = False
        system_fonts = {'arial', 'helvetica', 'times', 'georgia', 'verdana', 'courier',
                       'system-ui', 'sans-serif', 'serif', 'monospace'}
        for f in self.fonts:
            name = f.split(',')[0].strip().strip('"').strip("'").lower()
            if name and name not in system_fonts:
                has_custom_fonts = True
                break

        parts = []
        parts.append("**Likely target audience:**")

        if is_complex and has_custom_fonts:
            parts.append("\n- **B2B/Professional:** Complex architecture suggests enterprise product")
        elif not is_complex:
            parts.append("\n- **Consumer/General:** Simple, accessible design for broad audience")

        if self.accessibility_score > 80:
            parts.append("\n- **Inclusive:** Strong accessibility indicates commitment to all users")

        shadow_count = len(self.shadow_levels)
        if shadow_count > 4:
            parts.append("\n- **Design-conscious:** Premium visual treatment suggests design-savvy audience")

        return ' '.join(parts)

    def _generate_technical_approach(self) -> str:
        """Describe likely technical implementation"""
        parts = []
        parts.append("**Technical implementation:**")

        # Check CSS variables count as framework hint
        css_vars = self.evidence.get('colors', {}).get('css_variables', {})
        css_var_count = len(css_vars) if isinstance(css_vars, dict) else 0

        if css_var_count > 100:
            parts.append(f"\n- **CSS Custom Properties:** {css_var_count} variables (sophisticated design system)")
        elif css_var_count > 0:
            parts.append(f"\n- **CSS Custom Properties:** {css_var_count} variables")

        # Check animation patterns
        if len(self.transitions_list) > 20:
            parts.append("\n- **Rich transitions:** Likely using CSS-in-JS or preprocessor")

        # Responsive
        breakpoints_raw = self.evidence.get('responsive_breakpoints', {})
        unique_bp = breakpoints_raw.get('unique_breakpoints', [])
        media_queries = breakpoints_raw.get('media_queries', [])
        if unique_bp:
            parts.append(f"\n- **Responsive:** {len(unique_bp)} breakpoints for multi-device support")
        elif media_queries:
            parts.append(f"\n- **Responsive:** {len(media_queries)} media queries detected")

        parts.append("\n- **Performance:** Modern loading strategies recommended (lazy loading, code splitting)")

        return ' '.join(parts)

    def _generate_quick_start_guide(self) -> str:
        """Provide actionable next steps"""
        primary_font = 'Inter'
        if self.fonts:
            primary_font = self.fonts[0].split(',')[0].strip().strip('"').strip("'")

        return f"""**Quick start guide:**

1. **Set up fonts:** Import {primary_font} from Google Fonts
2. **Define design tokens:** Use CSS custom properties for colors, spacing, typography
3. **Build component library:** Start with button, card, and navigation components
4. **Implement layout:** Use CSS Grid/Flexbox for responsive structure
5. **Add interactions:** Implement hover states and subtle animations
6. **Test responsiveness:** Verify layout works across mobile, tablet, desktop

**Starter template:** Generated HTML file includes all design tokens wired up and ready to code.
"""
