"""
Test Typography Intelligence integration
"""
import asyncio
from deep_evidence_engine import DeepEvidenceEngine
import json


async def test_typography(url='https://stripe.com'):
    """Test typography extraction with intelligent analysis"""

    print("=" * 70)
    print(" TYPOGRAPHY INTELLIGENCE TEST")
    print("=" * 70)
    print(f"\nURL: {url}\n")

    engine = DeepEvidenceEngine(url)

    try:
        print("Running deep scan...\n")
        result = await engine.extract_all()

        # Check typography
        typography = result.get('typography', {})
        print("🖋️  TYPOGRAPHY:")
        print(f"   Pattern: {typography.get('pattern', 'Unknown')}")

        intelligent = typography.get('intelligent_typography')
        if intelligent:
            primary = intelligent['primary_font']
            scale = intelligent['type_scale']
            weights = intelligent['font_weights']

            print(f"\n   PRIMARY FONT:")
            print(f"   Name: {primary['name']}")
            print(f"   Source: {primary['source'] or 'system/self-hosted'}")
            print(f"   Fallbacks: {', '.join(primary['fallbacks'][:3])}")

            print(f"\n   TYPE SCALE:")
            print(f"   Pattern: {scale['pattern']}")
            print(f"   Ratio: {scale['ratio']}")
            print(f"   Consistency: {scale['confidence']}%")
            print(f"   Sizes: {', '.join(str(int(s)) + 'px' for s in scale['sizes'][:5])}")

            print(f"\n   FONT WEIGHTS:")
            print(f"   Range: {weights['range']} ({weights['min']}-{weights['max']})")
            print(f"   Unique weights: {weights['unique_weights']}")
            print(f"   Has bold: {weights['has_bold']}")
            print(f"   Has semibold: {weights['has_semibold']}")

            print(f"\n   Overall confidence: {intelligent['confidence']}%")

            # Show evidence trail
            print(f"\n   EVIDENCE TRAIL:")
            trail = intelligent['evidence_trail']
            for finding in trail.get('found', [])[:4]:
                print(f"      Found: {finding}")
            for analysis in trail.get('analyzed', [])[:4]:
                print(f"      Analyzed: {analysis}")
            print(f"      Concluded: {trail.get('concluded')}")
        else:
            print("   ⚠️  No intelligent typography data")

        print("\n" + "=" * 70)
        print(" TEST COMPLETE")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_typography())
