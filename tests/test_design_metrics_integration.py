"""
Quick test to verify design system metrics integration

Tests that all 5 new metrics are properly extracted and returned
"""

import asyncio
from deep_evidence_engine import DeepEvidenceEngine


async def test_integration():
    print("\n" + "="*70)
    print(" 🧪 DESIGN METRICS INTEGRATION TEST")
    print("="*70)

    test_url = 'https://stripe.com/docs'
    print(f"\n Testing URL: {test_url}")
    print("="*70)

    engine = DeepEvidenceEngine(test_url)
    evidence = await engine.extract_all()

    print("\n✅ Evidence extraction complete!")
    print(f"   Total categories: {len(evidence)}")

    # Check for new design system metrics
    new_metrics = [
        'spacing_scale',
        'responsive_breakpoints',
        'shadow_system',
        'z_index_stack',
        'border_radius_scale'
    ]

    print("\n🎨 Design System Metrics Check:")
    for metric in new_metrics:
        if metric in evidence:
            data = evidence[metric]
            print(f"   ✅ {metric}:")
            print(f"      - Pattern: {data.get('pattern', 'N/A')}")
            print(f"      - Confidence: {data.get('confidence', 0)}%")
        else:
            print(f"   ❌ {metric}: MISSING")

    # Show sample data
    if 'spacing_scale' in evidence:
        spacing = evidence['spacing_scale']
        print(f"\n📏 Spacing Scale Details:")
        print(f"   Base unit: {spacing.get('base_unit')}px")
        print(f"   Scale: {spacing.get('scale', [])}")
        print(f"   Total instances: {spacing.get('total_instances', 0)}")

    if 'responsive_breakpoints' in evidence:
        bp = evidence['responsive_breakpoints']
        print(f"\n📱 Breakpoints Details:")
        print(f"   Breakpoints: {bp.get('breakpoints', {})}")
        print(f"   Media queries: {bp.get('total_media_queries', 0)}")

    print("\n" + "="*70)
    print(" ✅ TEST COMPLETE")
    print("="*70)
    print("\n Next step: Run web interface to see visual cards")
    print("   python3 app.py")
    print("   http://localhost:8080")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    asyncio.run(test_integration())
