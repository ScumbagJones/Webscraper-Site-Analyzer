"""
Test full integration: Color extraction → Contrast checking → Accessibility scoring
"""
import asyncio
from deep_evidence_engine import DeepEvidenceEngine
import json


async def test_full_integration(url='https://stripe.com'):
    """Test the full pipeline: color extraction → contrast checking"""

    print("=" * 70)
    print(" FULL INTEGRATION TEST")
    print("=" * 70)
    print(f"\nURL: {url}\n")

    engine = DeepEvidenceEngine(url)

    try:
        # Run analysis
        print("Running deep scan...\n")
        result = await engine.extract_all()
        evidence = result

        # Check colors
        colors = evidence.get('evidence', {}).get('colors', {})
        print("🎨 COLOR ANALYSIS:")
        print(f"   Confidence: {colors.get('confidence', 0)}%")

        intelligent_palette = colors.get('intelligent_palette', {})
        if intelligent_palette:
            print(f"   Brand colors: {len(intelligent_palette.get('brand', []))}")
            print(f"   Text colors: {len(intelligent_palette.get('text', []))}")
            print(f"   Background colors: {len(intelligent_palette.get('background', []))}")
        else:
            print("   ⚠️  No intelligent palette")

        # Check accessibility
        accessibility = evidence.get('evidence', {}).get('accessibility', {})
        print(f"\n♿ ACCESSIBILITY:")
        print(f"   Score: {accessibility.get('score', 0)}/100")

        contrast = accessibility.get('contrast_analysis')
        if contrast:
            summary = contrast.get('summary', {})
            print(f"\n   CONTRAST ANALYSIS:")
            print(f"   Total pairs checked: {summary.get('total_pairs', 0)}")
            print(f"   WCAG AA pass: {summary.get('aa_pass', 0)} ({summary.get('aa_pass_rate', 0)*100:.1f}%)")
            print(f"   WCAG AAA pass: {summary.get('aaa_pass', 0)} ({summary.get('aaa_pass_rate', 0)*100:.1f}%)")

            best = summary.get('best_contrast', {})
            worst = summary.get('worst_contrast', {})
            print(f"\n   Best: {best.get('foreground')} on {best.get('background')}: {best.get('contrast_ratio')}:1")
            print(f"   Worst: {worst.get('foreground')} on {worst.get('background')}: {worst.get('contrast_ratio')}:1")

            # Show all pairs
            print(f"\n   ALL TEXT/BACKGROUND PAIRS:")
            for pair in contrast.get('text_background_pairs', []):
                status = "✅ AA" if pair['wcag_aa'] else "❌ Fail"
                aaa = "AAA ✅" if pair['wcag_aaa'] else ""
                print(f"      {pair['foreground']} on {pair['background']}: {pair['contrast_ratio']}:1 {status} {aaa}")

            # Show evidence trail
            print(f"\n   EVIDENCE TRAIL:")
            trail = contrast.get('evidence_trail', {})
            for finding in trail.get('found', []):
                print(f"      Found: {finding}")
            for analysis in trail.get('analyzed', []):
                print(f"      Analyzed: {analysis}")
            print(f"      Concluded: {trail.get('concluded')}")
        else:
            print("   ⚠️  No contrast analysis")

        # Check recommendations
        recommendations = accessibility.get('recommendations', [])
        if recommendations:
            print(f"\n   RECOMMENDATIONS:")
            for rec in recommendations:
                print(f"      • {rec}")

        print("\n" + "=" * 70)
        print(" TEST COMPLETE")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_full_integration())
