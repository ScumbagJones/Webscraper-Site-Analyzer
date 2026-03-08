"""
Test Color Palette Preview Integration

Quick test to verify the color preview feature is properly integrated
"""

import asyncio
from deep_evidence_engine import DeepEvidenceEngine


async def test_color_preview():
    print("\n" + "="*70)
    print(" 🎨 COLOR PALETTE PREVIEW INTEGRATION TEST")
    print("="*70)

    # Test with a colorful site
    test_url = 'https://stripe.com/docs'
    print(f"\n Testing URL: {test_url}")
    print("="*70)

    engine = DeepEvidenceEngine(test_url)
    evidence = await engine.extract_all()

    print("\n✅ Evidence extraction complete!")
    print(f"   Total categories: {len(evidence)}")

    # Check if colors extracted
    if 'colors' in evidence:
        colors_data = evidence['colors']
        print("\n🎨 Color Palette Data:")
        print(f"   Pattern: {colors_data.get('pattern', 'N/A')}")
        print(f"   Confidence: {colors_data.get('confidence', 0)}%")

        # Check for preview data
        if 'preview' in colors_data and colors_data['preview']:
            preview = colors_data['preview']
            print("\n✅ PREVIEW DATA FOUND!")
            print(f"   Color Roles: {list(preview.get('color_roles', {}).keys())}")
            print(f"   Accessible Pairs: {len(preview.get('accessible_pairs', []))}")
            print(f"   WCAG AA: {preview.get('wcag_compliance', {}).get('aa_percentage', 0)}%")
            print(f"   WCAG AAA: {preview.get('wcag_compliance', {}).get('aaa_percentage', 0)}%")

            # Show color roles
            if preview.get('color_roles'):
                print("\n   Detected Color Roles:")
                for role, color in preview['color_roles'].items():
                    print(f"      {role}: {color}")

            # Show accessible pairs (top 3)
            if preview.get('accessible_pairs'):
                print("\n   Top Accessible Pairs:")
                for i, (c1, c2, ratio, level) in enumerate(preview['accessible_pairs'][:3]):
                    print(f"      {c1} on {c2}: {ratio}:1 ({level})")

            # Check export formats
            if preview.get('export_formats'):
                exports = preview['export_formats']
                print("\n   Export Formats Available:")
                if exports.get('css_variables'):
                    print("      ✅ CSS Variables")
                if exports.get('tailwind_config'):
                    print("      ✅ Tailwind Config")
                if exports.get('figma_palette'):
                    print("      ✅ Figma Palette")

            print("\n✅ INTEGRATION TEST PASSED!")
            print("   Color preview data is being extracted successfully")
        else:
            print("\n⚠️  No preview data found")
            print("   Preview generation may have failed")
    else:
        print("\n❌ No color data found in evidence")

    print("\n" + "="*70)
    print(" 🌐 WEB DASHBOARD TEST")
    print("="*70)
    print("\n Server running at: http://localhost:8080")
    print("\n To test the UI:")
    print("   1. Open http://localhost:8080 in your browser")
    print("   2. Enter URL: https://stripe.com/docs")
    print("   3. Click 'Analyze URL'")
    print("   4. Look for the 'Color Palette' card")
    print("   5. Click the '🎨 Preview Colors' button")
    print("   6. Modal should show:")
    print("      - Color swatches with role labels")
    print("      - WCAG compliance percentages")
    print("      - Accessible color pairs")
    print("      - Live component previews")
    print("      - Export buttons (CSS, Tailwind, Figma)")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    asyncio.run(test_color_preview())
