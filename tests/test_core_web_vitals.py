"""
Test Core Web Vitals integration
"""
import asyncio
from deep_evidence_engine import DeepEvidenceEngine
import json


async def test_web_vitals(url='https://stripe.com'):
    """Test Core Web Vitals extraction"""

    print("=" * 70)
    print(" CORE WEB VITALS INTEGRATION TEST")
    print("=" * 70)
    print(f"\nURL: {url}\n")

    engine = DeepEvidenceEngine(url)

    try:
        print("Running deep scan...\n")
        result = await engine.extract_all()

        # Check performance
        performance = result.get('performance', {})
        print("⚡ PERFORMANCE:")
        print(f"   Load time: {performance.get('timings', {}).get('load_complete', 0):.0f}ms")

        cwv = performance.get('core_web_vitals')
        if cwv:
            print(f"\n   CORE WEB VITALS:")
            print(f"   LCP: {cwv['lcp']['value']}ms ({cwv['lcp']['rating']})")
            print(f"   FID: {cwv['fid']['value']}ms ({cwv['fid']['rating']})")
            print(f"   INP: {cwv['inp']['value']}ms ({cwv['inp']['rating']})")
            print(f"   CLS: {cwv['cls']['value']} ({cwv['cls']['rating']})")

            summary = cwv['summary']
            print(f"\n   Overall: {summary['overall_rating']}")
            print(f"   Pass rate: {summary['pass_rate']*100:.0f}% ({summary['good_metrics']}/3)")
            print(f"   Confidence: {cwv['confidence']}%")

            # Show evidence trail
            print(f"\n   EVIDENCE TRAIL:")
            trail = cwv['evidence_trail']
            for finding in trail.get('found', [])[:3]:
                print(f"      Found: {finding}")
            for analysis in trail.get('analyzed', [])[:3]:
                print(f"      Analyzed: {analysis}")
            print(f"      Concluded: {trail.get('concluded')}")
        else:
            print("   ⚠️  No Core Web Vitals data")

        print("\n" + "=" * 70)
        print(" TEST COMPLETE")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_web_vitals())
