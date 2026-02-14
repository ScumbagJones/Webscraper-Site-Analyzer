"""
Component Mapper - Bridge to Website Understanding SDK

Uses the website-understanding-sdk to identify page components with CSS selectors.
Provides section identification and element mapping for component extraction.
"""

import subprocess
import json
from typing import Dict, List, Optional
from pathlib import Path


class ComponentMapper:
    """
    Bridge to website-understanding-sdk for component identification
    """

    def __init__(self):
        self.bridge_script = Path(__file__).parent / "analyze_page_bridge.js"

    def analyze_page(self, html_content: str) -> Dict:
        """
        Analyze HTML and extract component structure with selectors

        Args:
            html_content: Raw HTML string

        Returns:
            {
                'page_type': 'product' | 'article' | 'search' | 'list' | 'login' | 'home' | 'unknown',
                'sections': [
                    {'type': 'navigation', 'selector': 'nav.main-nav'},
                    {'type': 'hero', 'selector': 'section.hero'},
                    {'type': 'footer', 'selector': 'footer#site-footer'}
                ],
                'elements': {
                    'inputs': ['input.search', 'input#email'],
                    'buttons': ['button.cta', 'button.submit'],
                    'links': ['a.nav-link'],
                    'images': ['img.hero-image']
                },
                'metadata': {
                    'title': 'Page Title',
                    'description': 'Page description',
                    'url': 'https://example.com'
                }
            }
        """
        try:
            print("   🗺️  Mapping page components...")

            # Call Node.js bridge script
            result = subprocess.run(
                ['node', str(self.bridge_script)],
                input=html_content,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"   ⚠️  SDK analysis failed: {result.stderr[:100]}")
                return self._empty_result()

            # Parse JSON output
            component_map = json.loads(result.stdout)

            # Log results
            page_type = component_map.get('page_type', 'unknown')
            sections = component_map.get('sections', [])
            elements = component_map.get('elements', {})

            print(f"   📄 Page type: {page_type}")
            print(f"   📦 Sections: {len(sections)}")
            print(f"   🎯 Interactive elements: {sum(len(v) for v in elements.values())}")

            return component_map

        except subprocess.TimeoutExpired:
            print("   ⚠️  SDK analysis timeout")
            return self._empty_result()
        except json.JSONDecodeError as e:
            print(f"   ⚠️  SDK output parse error: {str(e)[:100]}")
            return self._empty_result()
        except Exception as e:
            print(f"   ⚠️  Component mapping error: {str(e)[:100]}")
            return self._empty_result()

    def _empty_result(self) -> Dict:
        """Return empty result structure on error"""
        return {
            'page_type': 'unknown',
            'sections': [],
            'elements': {
                'inputs': [],
                'buttons': [],
                'links': [],
                'images': []
            },
            'metadata': {
                'title': None,
                'description': None,
                'url': None
            }
        }

    def format_component_tree(self, component_map: Dict) -> str:
        """
        Format component map as a visual tree structure

        Returns:
            String representation like:
            Page Structure:
            ├─ Navigation (nav.main-header)
            │  ├─ 12 links
            │  └─ 1 search input
            ├─ Hero Section (section.hero-banner)
            │  ├─ 2 buttons
            │  └─ 1 image
            └─ Footer (footer#site-footer)
        """
        sections = component_map.get('sections', [])
        elements = component_map.get('elements', {})

        if not sections:
            return "No sections detected"

        tree = ["Page Structure:"]

        for i, section in enumerate(sections):
            is_last = (i == len(sections) - 1)
            prefix = "└─" if is_last else "├─"
            section_type = section.get('type', 'unknown')
            selector = section.get('selector', 'N/A')

            tree.append(f"{prefix} {section_type.title()} ({selector})")

            # Add element counts for this section
            # (Note: SDK doesn't provide per-section element counts,
            # so we show total counts as a rough indicator)
            if i == 0 and elements:
                sub_prefix = "   " if is_last else "│  "
                if elements.get('links'):
                    tree.append(f"{sub_prefix}├─ {len(elements['links'])} links")
                if elements.get('buttons'):
                    tree.append(f"{sub_prefix}├─ {len(elements['buttons'])} buttons")
                if elements.get('inputs'):
                    tree.append(f"{sub_prefix}├─ {len(elements['inputs'])} inputs")
                if elements.get('images'):
                    tree.append(f"{sub_prefix}└─ {len(elements['images'])} images")

        return "\n".join(tree)


# Test
async def test_component_mapper():
    """Test component mapper with sample HTML"""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <nav class="main-nav">
            <a href="/">Home</a>
            <a href="/about">About</a>
        </nav>
        <section class="hero">
            <h1>Welcome</h1>
            <button class="cta">Get Started</button>
        </section>
        <footer id="site-footer">
            <p>Copyright 2024</p>
        </footer>
    </body>
    </html>
    """

    mapper = ComponentMapper()
    result = mapper.analyze_page(sample_html)

    print("\n" + "="*70)
    print(" 🗺️  COMPONENT MAPPER TEST")
    print("="*70)

    print(f"\nPage Type: {result['page_type']}")
    print(f"\nSections:")
    for section in result['sections']:
        print(f"  - {section['type']}: {section['selector']}")

    print(f"\nElements:")
    for elem_type, selectors in result['elements'].items():
        print(f"  {elem_type}: {len(selectors)}")

    print(f"\n{mapper.format_component_tree(result)}")

    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_component_mapper())
