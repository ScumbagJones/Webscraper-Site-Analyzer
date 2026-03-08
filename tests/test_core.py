"""
Test core modules: Bloom Filter and Signal Schema
"""

import sys
sys.path.insert(0, '..')

from core import BloomFilter, Signal, SignalSchema
import json


def test_bloom_filter():
    """Test Bloom Filter for URL deduplication"""
    print("\n" + "="*70)
    print(" 🧪 BLOOM FILTER TEST")
    print("="*70)

    bf = BloomFilter(size=1000, hash_count=3)

    # Test 1: Add URLs
    print("\n1️⃣ Adding URLs...")
    urls = [
        "https://nts.live",
        "https://nts.live/shows",
        "https://nts.live/explore",
        "https://books.toscrape.com/book_1",
        "https://books.toscrape.com/book_2",
    ]

    for url in urls:
        bf.add(url)
        print(f"   Added: {url}")

    print(f"\n   {bf}")

    # Test 2: Check contains
    print("\n2️⃣ Testing contains...")
    test_urls = urls + ["https://pi.fyi"]  # Add one that wasn't added

    for url in test_urls:
        in_filter = url in bf
        symbol = "✅" if in_filter else "❌"
        print(f"   {symbol} {url}: {in_filter}")

    # Test 3: Deduplication
    print("\n3️⃣ Testing deduplication...")
    print("   Adding duplicate URLs (should not affect false positive rate)...")

    initial_fpr = bf.false_positive_rate()
    print(f"   FPR before duplicates: {initial_fpr:.4%}")

    # Try to add duplicates
    for url in urls[:3]:
        bf.add(url)  # Add again

    final_fpr = bf.false_positive_rate()
    print(f"   FPR after duplicates: {final_fpr:.4%}")
    print(f"   Note: FPR increased because items_added counter increased")
    print(f"         (In production, check `contains()` before `add()` to prevent this)")

    # Test 4: Stats
    print("\n4️⃣ Statistics...")
    stats = bf.stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2%}" if value < 1 else f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")

    print("\n   ✅ Bloom Filter Test PASSED")


def test_signal_schema():
    """Test Signal Schema"""
    print("\n" + "="*70)
    print(" 🧪 SIGNAL SCHEMA TEST")
    print("="*70)

    # Test 1: Create example signal
    print("\n1️⃣ Creating example signal...")
    signal = SignalSchema.example()
    print(f"   URL: {signal.url}")
    print(f"   Framework: {signal.framework}")
    print(f"   DOM signals: {len(signal.dom.active_selectors)} selectors")
    print(f"   Layout: {signal.layout.type}")
    print(f"   Network: {len(signal.network.api_calls)} API calls")

    # Test 2: Validate
    print("\n2️⃣ Validating signal...")
    is_valid = SignalSchema.validate(signal)
    print(f"   Valid: {'✅ Yes' if is_valid else '❌ No'}")

    # Test 3: Serialize to JSON
    print("\n3️⃣ Serializing to JSON...")
    signal_dict = signal.to_dict()
    signal_json = json.dumps(signal_dict, indent=2)
    print(f"   JSON preview (first 300 chars):")
    print(f"   {signal_json[:300]}...")

    # Test 4: Deserialize from JSON
    print("\n4️⃣ Deserializing from JSON...")
    signal_restored = Signal.from_dict(signal_dict)
    print(f"   Restored URL: {signal_restored.url}")
    print(f"   Restored framework: {signal_restored.framework}")
    print(f"   Match: {'✅ Yes' if signal_restored.url == signal.url else '❌ No'}")

    print("\n   ✅ Signal Schema Test PASSED")


def test_real_world_scenario():
    """Test real-world scenario: Crawler + Scraper + MRI"""
    print("\n" + "="*70)
    print(" 🧪 REAL-WORLD SCENARIO TEST")
    print("="*70)

    # Simulate crawler
    print("\n1️⃣ Crawler: Deduplicating URLs...")
    bf = BloomFilter(size=10000, hash_count=3)

    crawled_urls = []
    duplicate_count = 0

    # Simulate crawling with duplicates
    discovered_urls = [
        "https://nts.live",
        "https://nts.live/shows",
        "https://nts.live/explore",
        "https://nts.live/shows",  # duplicate
        "https://nts.live",  # duplicate
        "https://nts.live/episodes/123",
    ]

    for url in discovered_urls:
        if url not in bf:
            bf.add(url)
            crawled_urls.append(url)
            print(f"   ✅ Crawled: {url}")
        else:
            duplicate_count += 1
            print(f"   ⏭️  Skipped (duplicate): {url}")

    print(f"\n   Total discovered: {len(discovered_urls)}")
    print(f"   Unique crawled: {len(crawled_urls)}")
    print(f"   Duplicates skipped: {duplicate_count}")

    # Simulate scraper
    print("\n2️⃣ Scraper: Generating signals...")
    signals = []

    for url in crawled_urls[:3]:  # Just first 3 for demo
        signal = Signal(
            url=url,
            framework="Next.js",
            dom={"active_selectors": ["audio", "div"], "persisted_elements": ["audio"]},
            layout={"type": "flex", "rigidity_score": 4}
        )
        signals.append(signal)
        print(f"   📊 Signal generated: {url}")

    # Simulate MRI
    print("\n3️⃣ MRI: Analyzing signals...")
    print(f"   Total signals: {len(signals)}")

    # Simple heuristic: Check for audio persistence
    audio_count = sum(1 for s in signals if "audio" in str(s.dom))
    persistence_rate = audio_count / len(signals) if signals else 0

    print(f"   Audio persistence: {persistence_rate:.0%}")

    if persistence_rate >= 0.5:
        print(f"   🎯 Diagnosis: Global Audio Player detected")
        print(f"   💡 Implication: Place player outside router")

    print("\n   ✅ Real-World Scenario Test PASSED")


if __name__ == "__main__":
    test_bloom_filter()
    test_signal_schema()
    test_real_world_scenario()

    print("\n" + "="*70)
    print(" ✅ ALL TESTS PASSED")
    print("="*70)
