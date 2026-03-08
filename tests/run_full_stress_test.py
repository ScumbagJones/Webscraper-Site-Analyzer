"""
Full Stress Test Runner

Orchestrates all three architecture tests and generates dashboards.

Usage:
    python run_full_stress_test.py

This will:
1. Run persistent state detection (SoundCloud pattern)
2. Run e-commerce filtering analysis (Grailed/SSENSE pattern)
3. Run scrollytelling detection (Bloomberg/NYT pattern)
4. Generate phenomenology dashboard
5. Generate Figma blueprint
"""

import asyncio
import sys
from pathlib import Path
from stress_test_architectures import ArchitectureStressTest
from phenomenology_dashboard import generate_all_dashboards
import json
from datetime import datetime


# Test configuration
TEST_CONFIGS = {
    # Test 1: Persistent State (SPA with audio/video)
    'persistent_state': {
        'url': 'https://soundcloud.com/discover',
        'description': 'SoundCloud - Persistent audio player across navigation',
        'enabled': True
    },

    # Test 2: E-Commerce Filtering
    'filtering': {
        'url': 'https://www.grailed.com/shop',
        'description': 'Grailed - Faceted search with URL sync',
        'enabled': True
    },

    # Test 3: Scrollytelling
    'scrollytelling': {
        'url': 'https://www.bloomberg.com',
        'description': 'Bloomberg - IntersectionObserver-based scrollytelling',
        'enabled': True
    }
}


class StressTestOrchestrator:
    """
    Orchestrates the full stress test suite
    """

    def __init__(self):
        self.results_dir = Path('data')
        self.results_dir.mkdir(exist_ok=True)

    async def run_full_suite(self, custom_urls: dict = None):
        """
        Run all tests and generate dashboards

        Args:
            custom_urls: Optional dict to override default test URLs
        """
        print("\n" + "="*70)
        print(" 🧪 ARCHITECTURE PHENOMENOLOGY STRESS TEST SUITE")
        print("="*70)

        print("\nThis suite validates the scraping engine across three architectures:")
        print("  1. 🎵 Persistent State (SPA with state preservation)")
        print("  2. 🛍️  E-Commerce Filtering (Faceted search)")
        print("  3. 📰 Scrollytelling (IntersectionObserver API)")

        # Prepare test URLs
        test_urls = {}
        for test_name, config in TEST_CONFIGS.items():
            if config['enabled']:
                url = custom_urls.get(test_name) if custom_urls else config['url']
                test_urls[test_name] = url
                print(f"\n  ✓ {test_name}: {config['description']}")
                print(f"    URL: {url}")

        # Confirm execution
        print("\n" + "-"*70)
        response = input("\nProceed with tests? [Y/n]: ").strip().lower()
        if response and response != 'y':
            print("❌ Tests cancelled")
            return

        # Run tests
        print("\n" + "="*70)
        print(" RUNNING TESTS")
        print("="*70)

        start_time = datetime.now()

        async with ArchitectureStressTest(headless=True) as tester:
            results = await tester.run_all_tests(test_urls)

        duration = (datetime.now() - start_time).total_seconds()

        # Save results
        results_path = self.results_dir / 'architecture_stress_test_results.json'
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n✅ Tests completed in {duration:.1f}s")
        print(f"📊 Results saved to: {results_path}")

        # Generate dashboards
        print("\n" + "="*70)
        print(" GENERATING DASHBOARDS")
        print("="*70)

        await generate_all_dashboards(str(results_path))

        # Display summary
        self._display_summary(results)

        print("\n" + "="*70)
        print(" ✅ STRESS TEST COMPLETE")
        print("="*70)

        print(f"\nNext steps:")
        print(f"  1. Review dashboard: {self.results_dir / 'phenomenology_dashboard.md'}")
        print(f"  2. Review Figma blueprint: {self.results_dir / 'figma_blueprint.md'}")
        print(f"  3. Review raw results: {results_path}")

        return results

    def _display_summary(self, results: dict):
        """
        Display test summary
        """
        print("\n" + "="*70)
        print(" 📊 TEST SUMMARY")
        print("="*70)

        metrics = results.get('metrics', {})

        # Metric 1: State Persistence
        print(f"\n1️⃣  State Persistence Detection")
        if metrics.get('state_persistence_detected'):
            print("   ✅ PASSED - Persistent components detected")
        else:
            print("   ⚠️  NOT DETECTED - May be traditional MPA")

        # Metric 2: Filter Latency
        print(f"\n2️⃣  Filter Latency Measurement")
        if metrics.get('filter_latency_ms'):
            latency = metrics['filter_latency_ms']
            status = "✅ GOOD" if latency < 200 else "⚠️ SLOW"
            print(f"   {status} - {latency:.0f}ms (target: <200ms)")
        else:
            print("   ⚠️  NOT MEASURED - Unable to interact with filters")

        # Metric 3: IntersectionObserver
        print(f"\n3️⃣  IntersectionObserver Detection")
        if metrics.get('intersection_observer_detected'):
            print("   ✅ DETECTED - Modern scrollytelling implementation")
        else:
            print("   ⚠️  NOT DETECTED - Static or legacy scroll handling")

        # Phenomenology summaries
        print(f"\n📋 Phenomenology Insights:")
        for summary in metrics.get('phenomenology_summary', []):
            print(f"   • {summary}")


async def run_with_custom_urls():
    """
    Interactive mode - let user specify custom URLs
    """
    print("\n🎯 CUSTOM URL MODE")
    print("-"*70)

    custom_urls = {}

    for test_name, config in TEST_CONFIGS.items():
        if not config['enabled']:
            continue

        print(f"\n{test_name.upper()}")
        print(f"Default: {config['url']}")
        custom = input("Enter custom URL (or press Enter for default): ").strip()

        if custom:
            custom_urls[test_name] = custom
        else:
            custom_urls[test_name] = config['url']

    orchestrator = StressTestOrchestrator()
    await orchestrator.run_full_suite(custom_urls)


async def run_default():
    """
    Run with default URLs
    """
    orchestrator = StressTestOrchestrator()
    await orchestrator.run_full_suite()


async def run_single_test(test_name: str):
    """
    Run a single test only

    Args:
        test_name: 'persistent_state', 'filtering', or 'scrollytelling'
    """
    if test_name not in TEST_CONFIGS:
        print(f"❌ Unknown test: {test_name}")
        print(f"Available tests: {', '.join(TEST_CONFIGS.keys())}")
        return

    config = TEST_CONFIGS[test_name]

    print(f"\n🎯 Running single test: {test_name}")
    print(f"URL: {config['url']}")

    orchestrator = StressTestOrchestrator()
    await orchestrator.run_full_suite({test_name: config['url']})


def main():
    """
    Main entry point with CLI arguments
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Architecture Phenomenology Stress Test Suite"
    )
    parser.add_argument(
        '--test',
        choices=['persistent_state', 'filtering', 'scrollytelling'],
        help='Run a single test only'
    )
    parser.add_argument(
        '--custom',
        action='store_true',
        help='Enter custom URLs interactively'
    )

    args = parser.parse_args()

    if args.test:
        asyncio.run(run_single_test(args.test))
    elif args.custom:
        asyncio.run(run_with_custom_urls())
    else:
        asyncio.run(run_default())


if __name__ == "__main__":
    main()
