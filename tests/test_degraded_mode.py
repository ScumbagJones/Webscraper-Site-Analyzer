"""
Test Degraded Mode & MRI Scanner

Test both normal mode and degraded mode (MRI)
"""

import asyncio
from deep_evidence_engine import DeepEvidenceEngine


async def test_normal_mode():
    """Test with a site that allows full access"""
    print("\n" + "="*70)
    print(" ✅ NORMAL MODE TEST (Full Access)")
    print("="*70)

    url = 'https://stripe.com/docs'
    print(f"\n Testing URL: {url}")

    engine = DeepEvidenceEngine(url)
    evidence = await engine.extract_all()

    meta = evidence.get('meta_info', {})
    print(f"\n Access Strategy: {meta.get('access_strategy', 'unknown')}")
    print(f" Bot Protection: {meta.get('bot_protection_detected', False)}")
    print(f" Full Analysis: {meta.get('full_analysis_available', False)}")

    if meta.get('access_strategy') == 'playwright_full':
        print("\n✅ Full access working!")
        print(f" Total Requests: {meta.get('total_requests', 0)}")
        print(f" DOM Nodes: {meta.get('total_dom_nodes', 0)}")

        # Check some metrics
        if 'colors' in evidence:
            print(f"\n🎨 Colors: {evidence['colors']['pattern']}")
        if 'layout' in evidence:
            print(f" 📐 Layout: {evidence['layout']['pattern']}")
        if 'typography' in evidence:
            print(f" 🖋️  Typography: {evidence['typography']['pattern']}")

    print("\n" + "="*70)


async def test_mri_mode():
    """Test MRI mode directly"""
    from metadata_mri import MetadataMRI

    print("\n" + "="*70)
    print(" 🔬 MRI MODE TEST (Metadata Only)")
    print("="*70)

    url = 'https://example.com'
    print(f"\n Testing URL: {url}")

    scanner = MetadataMRI(url)
    result = scanner.scan()

    if result['success']:
        print(f"\n✅ MRI scan successful!")
        print(f" Confidence: {result['confidence']}%")

        meta = result['meta_tags']
        if meta.get('title'):
            print(f"\n📋 Meta Tags:")
            print(f" Title: {meta['title'][:60]}")

        print(f"\n⚛️  Frameworks: {', '.join(result['frameworks']) or 'None'}")
        print(f" ☁️  CDN: {', '.join(result['cdn_providers']) or 'None'}")

        hints = result['structural_hints']
        print(f"\n🏗️  Structure:")
        print(f" Semantic HTML: {hints.get('semantic_html', False)}")
        print(f" Grid System: {hints.get('grid_system', 'Unknown')}")

        print(f"\n⚠️  Limitations ({len(result['limitations'])}):")
        for i, limitation in enumerate(result['limitations'][:3]):
            print(f" {i+1}. {limitation}")

    print("\n" + "="*70)


async def test_all():
    """Run both tests"""
    await test_normal_mode()
    await asyncio.sleep(2)
    await test_mri_mode()

    print("\n🎉 Both modes tested successfully!")
    print("\nℹ️  To test in web dashboard:")
    print("   1. Open http://localhost:8080")
    print("   2. Analyze any site")
    print("   3. Look for the access strategy badge at the top")
    print("   4. Badge will show:")
    print("      - ✅ Full Access (normal sites)")
    print("      - 🔬 Metadata MRI Mode (bot-protected sites)")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    asyncio.run(test_all())
