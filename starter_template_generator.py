"""
Starter Template Generator - Transform evidence into working HTML

Generates a clean, semantic HTML starter template with:
- Design tokens as CSS custom properties
- Semantic HTML structure based on detected layout
- Font imports (Google Fonts, etc.)
- Responsive foundation
- Component placeholders

Output: Ready-to-code starter.html file
"""

from typing import Dict, List, Optional
import re


class StarterTemplateGenerator:
    """
    Generate production-ready HTML starter templates from evidence
    """

    def __init__(self, evidence: Dict):
        self.evidence = evidence

        # --- Normalize typography from actual evidence schema ---
        typo_raw = evidence.get('typography', {})
        details = typo_raw.get('details', {})
        intelligent = typo_raw.get('intelligent_typography', {})
        it_scale = intelligent.get('type_scale', {}) if isinstance(intelligent.get('type_scale'), dict) else {}

        self.fonts = details.get('all_fonts', [])
        self.font_sizes = it_scale.get('sizes', [])
        # Fallback: parse sizes from details.all_sizes ("17px" -> 17)
        if not self.font_sizes:
            raw_sizes = details.get('all_sizes', [])
            self.font_sizes = sorted(set(self._parse_px(s) for s in raw_sizes if self._parse_px(s)), reverse=True)

        self.body_style = details.get('body', {})
        self.font_weights = details.get('all_weights', [])

        # --- Normalize colors ---
        colors_raw = evidence.get('colors', {})
        self.color_roles = colors_raw.get('preview', {}).get('color_roles', {})
        palette = colors_raw.get('palette', {})
        self.primary_colors = palette.get('primary', []) if isinstance(palette, dict) else []
        self.secondary_colors = palette.get('secondary', []) if isinstance(palette, dict) else []
        self.intelligent_palette = colors_raw.get('intelligent_palette', {})

        # --- Normalize spacing ---
        spacing_raw = evidence.get('spacing_scale', {})
        self.spacing_scale = spacing_raw.get('scale', [])
        self.spacing_base = spacing_raw.get('base_unit', 8)
        self.spacing_most_common = spacing_raw.get('most_common', {})

        # --- Normalize shadows ---
        shadows_raw = evidence.get('shadow_system', {})
        self.shadow_levels = shadows_raw.get('levels', [])

        # --- Normalize layout ---
        self.layout = evidence.get('layout', {})
        self.breakpoints = evidence.get('responsive_breakpoints', {})
        self.visual_hierarchy = evidence.get('visual_hierarchy', {})
        self.component_map = evidence.get('component_map', {})

        # --- Normalize motion tokens ---
        motion_raw = evidence.get('motion_tokens', {})
        motion_details = motion_raw.get('details', {})
        self.duration_tiers = motion_details.get('duration_scale', {}).get('tiers', {})
        self.easing_roles = motion_details.get('easing_palette', {}).get('roles', {})

    @staticmethod
    def _parse_px(val: str) -> Optional[float]:
        """Parse '17px' to 17.0, return None on failure"""
        if not isinstance(val, str):
            return None
        m = re.match(r'([\d.]+)px', val.strip())
        return float(m.group(1)) if m else None

    def generate(self) -> str:
        """Generate complete starter HTML"""

        html_parts = []
        html_parts.append(self._generate_head())
        html_parts.append(self._generate_css())
        html_parts.append(self._generate_body())
        html_parts.append("\n</body>\n</html>\n")

        return '\n'.join(html_parts)

    def _generate_head(self) -> str:
        """Generate <head> with font imports and meta tags"""

        font_imports = self._generate_font_imports(self.fonts)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Starter Template</title>

{font_imports}

    <style>
"""

    def _generate_font_imports(self, fonts: List[str]) -> str:
        """Generate Google Fonts imports for detected fonts"""

        if not fonts:
            return "    <!-- No custom fonts detected -->"

        system_fonts = {'Arial', 'Helvetica', 'Times', 'Georgia', 'Verdana',
                       'Courier', 'system-ui', 'sans-serif', 'serif', 'monospace',
                       '-apple-system', 'BlinkMacSystemFont', 'Segoe UI'}

        # Clean font names: strip quotes, split compound family strings
        clean_fonts = []
        for f in fonts:
            for part in f.split(','):
                name = part.strip().strip('"').strip("'").strip()
                if name and name not in system_fonts and not name.startswith('-'):
                    clean_fonts.append(name)

        if not clean_fonts:
            return "    <!-- Using system fonts only -->"

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for f in clean_fonts:
            if f.lower() not in seen:
                seen.add(f.lower())
                unique.append(f)

        font_families = '&family='.join([f.replace(' ', '+') for f in unique[:3]])

        return f"""    <!-- Web Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family={font_families}:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
"""

    def _generate_css(self) -> str:
        """Generate CSS with design tokens as custom properties"""

        css_parts = []

        css_parts.append("""        /* ============================================
           Design Tokens (extracted from live site)
           ============================================ */
        :root {""")

        css_parts.append(self._generate_typography_tokens())
        css_parts.append(self._generate_color_tokens())
        css_parts.append(self._generate_spacing_tokens())
        css_parts.append(self._generate_shadow_tokens())
        css_parts.append(self._generate_motion_tokens())

        css_parts.append("        }\n")
        css_parts.append(self._generate_base_styles())
        css_parts.append(self._generate_layout_utilities())
        css_parts.append(self._generate_component_styles())
        css_parts.append("    </style>")

        return '\n'.join(css_parts)

    def _generate_typography_tokens(self) -> str:
        """Generate typography CSS custom properties"""

        tokens = []

        # Font families
        if self.fonts:
            # Clean font name
            primary = self.fonts[0].split(',')[0].strip().strip('"').strip("'")
            tokens.append(f"            --font-primary: '{primary}', sans-serif;")
            if len(self.fonts) > 1:
                secondary = self.fonts[1].split(',')[0].strip().strip('"').strip("'")
                tokens.append(f"            --font-secondary: '{secondary}', sans-serif;")

        # Font sizes from intelligent_typography.type_scale.sizes (descending)
        if self.font_sizes:
            tokens.append("\n            /* Font Sizes */")
            sorted_sizes = sorted(self.font_sizes, reverse=True)
            size_names = ['4xl', '3xl', '2xl', 'xl', 'lg', 'base', 'sm', 'xs']
            for i, size in enumerate(sorted_sizes[:8]):
                name = size_names[i] if i < len(size_names) else f'size-{i}'
                tokens.append(f"            --font-size-{name}: {size}px;")

        # Body typography
        if self.body_style:
            lh = self.body_style.get('lineHeight', '')
            if lh:
                tokens.append(f"\n            --line-height-body: {lh};")

        return '\n'.join(tokens) if tokens else "            /* No typography tokens detected */"

    def _generate_color_tokens(self) -> str:
        """Generate color CSS custom properties"""

        tokens = []

        # Named roles first (most useful)
        if self.color_roles:
            tokens.append("\n            /* Color Roles */")
            for role, color in self.color_roles.items():
                css_name = role.lower().replace(' ', '-').replace('_', '-')
                tokens.append(f"            --color-{css_name}: {color};")

        # Intelligent palette (semantic colors)
        if self.intelligent_palette:
            has_roles = bool(self.color_roles)
            if not has_roles:
                tokens.append("\n            /* Colors */")

            for category, colors in self.intelligent_palette.items():
                if not isinstance(colors, list) or not colors:
                    continue
                for i, c in enumerate(colors[:3]):
                    if isinstance(c, dict) and 'hex' in c:
                        suffix = f"-{i+1}" if i > 0 else ""
                        tokens.append(f"            --color-{category}{suffix}: {c['hex']};")

        # Fallback: raw primary/secondary colors
        if not tokens and self.primary_colors:
            tokens.append("\n            /* Colors */")
            for i, color in enumerate(self.primary_colors[:5]):
                tokens.append(f"            --color-primary-{i+1}: {color};")
            for i, color in enumerate(self.secondary_colors[:3]):
                tokens.append(f"            --color-secondary-{i+1}: {color};")

        return '\n'.join(tokens) if tokens else "            /* No color tokens detected */"

    def _generate_spacing_tokens(self) -> str:
        """Generate spacing CSS custom properties"""

        tokens = []

        if self.spacing_scale:
            tokens.append("\n            /* Spacing Scale */")
            names = ['xs', 'sm', 'md', 'lg', 'xl', '2xl', '3xl', '4xl']
            sorted_scale = sorted(self.spacing_scale)
            for i, value in enumerate(sorted_scale[:8]):
                name = names[i] if i < len(names) else f'space-{i}'
                tokens.append(f"            --space-{name}: {value}px;")
        elif self.spacing_most_common:
            tokens.append("\n            /* Spacing (from most common values) */")
            sorted_vals = sorted(
                [(k, v) for k, v in self.spacing_most_common.items() if k != '0px'],
                key=lambda x: x[1], reverse=True
            )
            names = ['xs', 'sm', 'md', 'lg', 'xl', '2xl']
            for i, (px_val, count) in enumerate(sorted_vals[:6]):
                name = names[i] if i < len(names) else f'space-{i}'
                tokens.append(f"            --space-{name}: {px_val}; /* {count} uses */")

        return '\n'.join(tokens) if tokens else "            /* No spacing tokens detected */"

    def _generate_shadow_tokens(self) -> str:
        """Generate shadow CSS custom properties"""

        tokens = []

        if self.shadow_levels:
            tokens.append("\n            /* Shadows */")
            for level in self.shadow_levels:
                if isinstance(level, dict):
                    name = level.get('name', 'default').lower().replace(' ', '-')
                    css_val = level.get('css', 'none')
                    tokens.append(f"            --shadow-{name}: {css_val};")

        return '\n'.join(tokens) if tokens else "            /* No shadow tokens detected */"

    def _generate_motion_tokens(self) -> str:
        """Generate motion CSS custom properties from synthesized tokens"""

        tokens = []

        if self.duration_tiers:
            tokens.append("\n            /* Motion — Duration Scale */")
            for tier_name, tier_data in sorted(self.duration_tiers.items(), key=lambda x: x[1].get('ms', 0)):
                if isinstance(tier_data, dict) and 'ms' in tier_data:
                    tokens.append(f"            --motion-duration-{tier_name}: {tier_data['ms']}ms;")

        if self.easing_roles:
            tokens.append("\n            /* Motion — Easing Curves */")
            for role_name, easing_value in self.easing_roles.items():
                if easing_value:
                    tokens.append(f"            --motion-easing-{role_name}: {easing_value};")

        return '\n'.join(tokens) if tokens else "            /* No motion tokens detected */"

    def _generate_base_styles(self) -> str:
        """Generate base HTML element styles"""

        # Use actual body style if available
        body_font = self.body_style.get('fontFamily', '')
        body_size = self.body_style.get('fontSize', '')
        body_lh = self.body_style.get('lineHeight', '')
        body_weight = self.body_style.get('fontWeight', '')

        if body_font:
            font_family = f"'{body_font}', sans-serif"
        elif self.fonts:
            primary = self.fonts[0].split(',')[0].strip().strip('"').strip("'")
            font_family = f"'{primary}', sans-serif"
        else:
            font_family = 'system-ui, sans-serif'

        font_size = body_size or 'var(--font-size-base, 16px)'
        line_height = body_lh or 'var(--line-height-body, 1.5)'
        font_weight = body_weight or '400'

        return f"""
        /* Base Styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: {font_family};
            font-size: {font_size};
            line-height: {line_height};
            font-weight: {font_weight};
            color: var(--color-text, var(--color-neutral-dark, #333));
            background-color: var(--color-background, var(--color-neutral-light, #fff));
        }}

        h1, h2, h3, h4, h5, h6 {{
            font-weight: 600;
            line-height: 1.2;
        }}

        h1 {{ font-size: var(--font-size-4xl, 2.5rem); }}
        h2 {{ font-size: var(--font-size-3xl, 2rem); }}
        h3 {{ font-size: var(--font-size-2xl, 1.5rem); }}
        h4 {{ font-size: var(--font-size-xl, 1.25rem); }}

        a {{
            color: var(--color-brand, var(--color-primary-1, #0066cc));
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}
"""

    def _generate_layout_utilities(self) -> str:
        """Generate layout utility classes"""

        return """
        /* Layout */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 var(--space-md, 1rem);
        }

        .flex { display: flex; }
        .flex-col { display: flex; flex-direction: column; }
        .grid { display: grid; }
        .gap-sm { gap: var(--space-sm, 0.5rem); }
        .gap-md { gap: var(--space-md, 1rem); }
        .gap-lg { gap: var(--space-lg, 1.5rem); }
        .items-center { align-items: center; }
        .justify-between { justify-content: space-between; }
        .justify-center { justify-content: center; }
        .text-center { text-align: center; }
"""

    def _generate_component_styles(self) -> str:
        """Generate common component styles"""

        return """
        /* Components */
        .button {
            display: inline-block;
            padding: var(--space-sm, 0.5rem) var(--space-lg, 1.5rem);
            background-color: var(--color-brand, var(--color-primary-1, #0066cc));
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
            transition: all var(--motion-duration-fast, 200ms) var(--motion-easing-default, ease-in-out);
        }

        .button:hover { opacity: 0.85; }

        .button--outline {
            background: transparent;
            color: var(--color-brand, currentColor);
            border: 1px solid currentColor;
        }

        .card {
            background: white;
            border-radius: 8px;
            padding: var(--space-lg, 1.5rem);
            box-shadow: var(--shadow-subtle, 0 2px 8px rgba(0,0,0,0.1));
        }
"""

    def _generate_body(self) -> str:
        """Generate semantic HTML body structure based on detected sections"""

        has_nav = self.visual_hierarchy.get('navigation', {}).get('exists', False)
        hero = self.visual_hierarchy.get('hero_section', {})
        has_hero = hero.get('detected', False) if isinstance(hero, dict) else False
        hero_text = hero.get('text', '').strip() if isinstance(hero, dict) else ''
        cta = self.visual_hierarchy.get('primary_cta', {})
        cta_text = cta.get('text', '').strip() if isinstance(cta, dict) else ''

        # Get discovered nav links
        llm_helper = self.evidence.get('llm_helper', {})
        nav_links = llm_helper.get('discovered_links', {}).get('navigation', [])

        # Get detected sections from component map
        sections = self.component_map.get('sections', [])

        body_parts = []
        body_parts.append("\n</head>\n<body>\n")

        # Navigation
        if has_nav and nav_links:
            link_items = ""
            for link in nav_links[:6]:
                if isinstance(link, str):
                    name = link.rstrip('/').split('/')[-1].replace('-', ' ').title() or 'Home'
                    link_items += f'\n            <li><a href="{link}">{name}</a></li>'
            body_parts.append(f"""    <!-- Navigation -->
    <nav class="flex items-center justify-between container" style="padding: var(--space-md, 1rem) 0;">
        <div class="logo">
            <a href="/"><strong>Logo</strong></a>
        </div>
        <ul class="flex gap-md" style="list-style: none;">{link_items}
        </ul>
    </nav>
""")
        elif has_nav:
            body_parts.append("""    <!-- Navigation -->
    <nav class="flex items-center justify-between container" style="padding: var(--space-md, 1rem) 0;">
        <div class="logo"><a href="/"><strong>Logo</strong></a></div>
        <ul class="flex gap-md" style="list-style: none;">
            <li><a href="#">Link 1</a></li>
            <li><a href="#">Link 2</a></li>
            <li><a href="#">Link 3</a></li>
        </ul>
    </nav>
""")

        # Hero section
        if has_hero:
            h1_text = hero_text if hero_text else "Your Compelling Headline"
            cta_label = cta_text if cta_text else "Get Started"
            body_parts.append(f"""    <!-- Hero Section -->
    <header class="container" style="padding: var(--space-3xl, 4rem) 0;">
        <h1>{h1_text}</h1>
        <p style="font-size: var(--font-size-lg, 1.25rem); margin-top: var(--space-md, 1rem); max-width: 600px;">
            Brief description of your offering.
        </p>
        <div class="flex gap-md" style="margin-top: var(--space-lg, 1.5rem);">
            <a href="#" class="button">{cta_label}</a>
            <a href="#" class="button button--outline">Learn More</a>
        </div>
    </header>
""")

        # Main content with detected section types
        body_parts.append("    <!-- Main Content -->\n    <main class=\"container\">\n")

        for section in sections:
            stype = section.get('type', 'content') if isinstance(section, dict) else 'content'
            if stype in ('nav', 'footer'):
                continue
            if stype == 'card_list':
                body_parts.append("""        <section style="padding: var(--space-2xl, 2rem) 0;">
            <div class="grid gap-lg" style="grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));">
                <div class="card"><h3>Item 1</h3><p>Description</p></div>
                <div class="card"><h3>Item 2</h3><p>Description</p></div>
                <div class="card"><h3>Item 3</h3><p>Description</p></div>
            </div>
        </section>
""")
            elif stype == 'form':
                body_parts.append("""        <section class="text-center" style="padding: var(--space-2xl, 2rem) 0;">
            <h2>Stay Updated</h2>
            <form class="flex gap-sm justify-center" style="margin-top: var(--space-md, 1rem);">
                <input type="email" placeholder="Your email" style="padding: var(--space-sm, 0.5rem) var(--space-md, 1rem); border: 1px solid #ccc; border-radius: 4px;">
                <button class="button" type="submit">Subscribe</button>
            </form>
        </section>
""")
            else:
                body_parts.append("""        <section style="padding: var(--space-2xl, 2rem) 0;">
            <h2>Section Heading</h2>
            <p style="margin-top: var(--space-sm, 0.5rem);">Content goes here.</p>
        </section>
""")

        # If no sections detected, add generic content
        if not [s for s in sections if isinstance(s, dict) and s.get('type') not in ('nav', 'footer')]:
            body_parts.append("""        <section style="padding: var(--space-2xl, 2rem) 0;">
            <h2>Features</h2>
            <div class="grid gap-lg" style="grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); margin-top: var(--space-lg, 1.5rem);">
                <div class="card"><h3>Feature 1</h3><p>Description</p></div>
                <div class="card"><h3>Feature 2</h3><p>Description</p></div>
                <div class="card"><h3>Feature 3</h3><p>Description</p></div>
            </div>
        </section>
""")

        body_parts.append("    </main>\n")

        # Footer
        body_parts.append("""    <!-- Footer -->
    <footer style="background-color: var(--color-neutral, #f5f5f5); padding: var(--space-2xl, 2rem) 0; margin-top: var(--space-3xl, 4rem);">
        <div class="container text-center">
            <p>&copy; 2026 Your Company. All rights reserved.</p>
        </div>
    </footer>
""")

        return '\n'.join(body_parts)
