"""
Test color intelligence on real website
"""
import asyncio
from playwright.async_api import async_playwright
import re
from color_intelligence import extract_color_intelligence
import json


def convert_to_hex_counts(color_counts):
    """Convert RGB/RGBA color counts to hex for clustering"""
    hex_counts = {}
    for color_str, count in color_counts.items():
        if color_str.startswith('#'):
            hex_counts[color_str] = hex_counts.get(color_str, 0) + count
        else:
            rgb_match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color_str)
            if rgb_match:
                r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
                hex_color = f'#{r:02x}{g:02x}{b:02x}'
                hex_counts[hex_color] = hex_counts.get(hex_color, 0) + count
    return hex_counts


async def test_color_extraction(url='https://stripe.com'):
    """Test color extraction on a real website"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Navigating to {url}...")
        await page.goto(url, wait_until='domcontentloaded', timeout=10000)
        await page.wait_for_timeout(3000)

        print("Extracting color usage...")

        # Use simpler JavaScript with single quotes to avoid escaping issues
        color_data = await page.evaluate("""
            () => {
                const colorCounts = {};
                const elements = document.querySelectorAll('*');

                for (const el of elements) {
                    const styles = window.getComputedStyle(el);
                    const colors = [
                        styles.color,
                        styles.backgroundColor,
                        styles.borderColor
                    ];

                    colors.forEach(color => {
                        if (color && color !== 'rgba(0, 0, 0, 0)' && color !== 'transparent') {
                            colorCounts[color] = (colorCounts[color] || 0) + 1;
                        }
                    });
                }

                return colorCounts;
            }
        """)

        await browser.close()

        print(f"\n📊 Raw color data extracted: {len(color_data)} unique colors")

        # Show top 10 most-used colors
        sorted_colors = sorted(color_data.items(), key=lambda x: x[1], reverse=True)[:10]
        print("\n🎨 Top 10 most-used colors:")
        for color, count in sorted_colors:
            print(f"   {color}: {count} usages")

        # Convert to hex
        hex_counts = convert_to_hex_counts(color_data)
        print(f"\n🔄 Converted to hex: {len(hex_counts)} unique colors")

        # Show top 10 hex colors
        sorted_hex = sorted(hex_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        print("\n🎨 Top 10 hex colors:")
        for color, count in sorted_hex:
            print(f"   {color}: {count} usages")

        # Run color intelligence
        print("\n🧠 Running color intelligence...")
        result = extract_color_intelligence(hex_counts)

        print(f"\n✅ Analysis complete!")
        print(f"   Confidence: {result['confidence']}%")
        print(f"   Clusters: {result['clusters']}")
        print(f"   Colors analyzed: {result['total_colors_analyzed']}")

        print("\n🎨 Intelligent Palette:")
        for role, colors in result['color_palette'].items():
            print(f"\n   {role.upper()}:")
            for color in colors:
                print(f"      {color['hex']} - {color['usage_count']} usages ({color['usage_ratio']*100:.1f}%), {color['variants']} variants")

        print("\n📋 Evidence Trail:")
        print(json.dumps(result['evidence_trail'], indent=2))

        return result


if __name__ == '__main__':
    asyncio.run(test_color_extraction())
