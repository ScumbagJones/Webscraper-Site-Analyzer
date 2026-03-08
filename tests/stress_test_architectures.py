"""
Stress Test: High-Contrast Architecture Phenomenology Tests

Three tests to validate the engine across different architectural patterns:
1. SoundCloud - Persistent Audio State (SPA with state preservation)
2. Grailed/SSENSE - E-Commerce Filtering (Faceted search + URL sync)
3. Bloomberg/NYT - Scrollytelling (IntersectionObserver API)

These tests force the engine to detect "mannerisms" beyond standard SSR/SSG patterns.
"""

import asyncio
from pyppeteer import launch
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
from collections import defaultdict
import re


class PersistentStateDetector:
    """
    Test 1: SoundCloud - Detect components that survive navigation

    Mannerisms to find:
    - Player bar persists across route changes
    - pushState API usage without page refresh
    - Audio element continuity
    """

    def __init__(self, page):
        self.page = page
        self.navigation_log = []

    async def detect_persistent_components(self, base_url: str) -> Dict[str, Any]:
        """
        Navigate between pages and identify which DOM elements persist
        """
        print("\n🎵 TEST 1: Persistent State Detection (SoundCloud Pattern)")
        print("="*60)

        # Go to initial page
        print(f"   Navigating to {base_url}")
        await self.page.goto(base_url, {'waitUntil': 'domcontentloaded', 'timeout': 45000})
        await asyncio.sleep(3)  # Let player load

        # Capture initial state
        initial_state = await self._capture_dom_snapshot()
        print(f"   Initial elements: {initial_state['element_count']}")

        # Find player/audio elements
        player_elements = await self.page.evaluate('''() => {
            const audio = document.querySelector('audio, video');
            const playerBar = document.querySelector('[class*="player"], [class*="Player"], [id*="player"]');

            return {
                has_audio: !!audio,
                audio_src: audio ? audio.src : null,
                audio_paused: audio ? audio.paused : null,
                player_html: playerBar ? playerBar.outerHTML.substring(0, 500) : null,
                player_selector: playerBar ? playerBar.className : null
            };
        }''')

        print(f"   Audio element: {'Found' if player_elements['has_audio'] else 'None'}")
        print(f"   Player bar: {'Found' if player_elements['player_html'] else 'None'}")

        # Monitor pushState usage
        await self.page.evaluateOnNewDocument('''() => {
            window._pushStateLog = [];
            const originalPushState = history.pushState;
            history.pushState = function(...args) {
                window._pushStateLog.push({
                    timestamp: Date.now(),
                    url: args[2],
                    state: args[0]
                });
                return originalPushState.apply(this, args);
            };
        }''')

        # Simulate navigation (click a link if available)
        print(f"\n   Attempting internal navigation...")
        links = await self.page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('a[href^="/"]'));
            return links.slice(0, 5).map(a => ({
                href: a.href,
                text: a.innerText.substring(0, 50)
            }));
        }''')

        if links:
            print(f"   Found {len(links)} internal links")
            # Click first link
            try:
                await self.page.click('a[href^="/"]')
                await asyncio.sleep(2)

                # Check if audio/player persisted
                post_nav_state = await self._capture_dom_snapshot()
                post_player = await self.page.evaluate('''() => {
                    const audio = document.querySelector('audio, video');
                    return {
                        has_audio: !!audio,
                        audio_src: audio ? audio.src : null,
                        audio_paused: audio ? audio.paused : null
                    };
                }''')

                # Get pushState log
                push_state_log = await self.page.evaluate('window._pushStateLog || []')

                # Determine if components persisted
                persisted = (
                    post_player['has_audio'] and
                    post_player['audio_src'] == player_elements['audio_src']
                )

                print(f"   ✅ Navigation completed")
                print(f"   Audio persisted: {persisted}")
                print(f"   pushState calls: {len(push_state_log)}")

                return {
                    'pattern': 'Persistent State SPA',
                    'persisted_audio': persisted,
                    'push_state_detected': len(push_state_log) > 0,
                    'push_state_log': push_state_log,
                    'initial_player': player_elements,
                    'post_navigation_player': post_player,
                    'delivery_strategy': 'Client-Side SPA' if persisted else 'Multi-Page App',
                    'phenomenology': 'Persistent component survives route changes' if persisted else 'Full page reloads'
                }

            except Exception as e:
                print(f"   ⚠️  Navigation failed: {e}")
                return {
                    'pattern': 'Unknown',
                    'error': str(e)
                }
        else:
            return {
                'pattern': 'No internal navigation detected',
                'initial_player': player_elements
            }

    async def _capture_dom_snapshot(self) -> Dict[str, Any]:
        """Capture current DOM state"""
        return await self.page.evaluate('''() => ({
            element_count: document.querySelectorAll('*').length,
            url: window.location.href,
            title: document.title
        })''')


class FilteringMannerismDetector:
    """
    Test 2: Grailed/SSENSE - E-Commerce filtering patterns

    Mannerisms to find:
    - URL changes when filters applied (or not)
    - Filter sidebar → Product grid relationship
    - Shadow DOM usage
    - Filter latency measurement
    """

    def __init__(self, page):
        self.page = page
        self.filter_events = []

    async def analyze_filtering_system(self, url: str) -> Dict[str, Any]:
        """
        Interact with filters and measure behavior
        """
        print("\n🛍️  TEST 2: E-Commerce Filtering (Grailed/SSENSE Pattern)")
        print("="*60)

        print(f"   Navigating to {url}")
        await self.page.goto(url, {'waitUntil': 'domcontentloaded', 'timeout': 45000})
        await asyncio.sleep(3)

        # Find filter controls
        filter_controls = await self.page.evaluate('''() => {
            const filters = [];

            // Common filter selectors
            const selectors = [
                'input[type="checkbox"]',
                'select',
                'button[class*="filter"]',
                '[role="button"][class*="filter"]',
                '[data-testid*="filter"]'
            ];

            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                if (elements.length > 0) {
                    filters.push({
                        selector: selector,
                        count: elements.length,
                        sample: Array.from(elements).slice(0, 3).map(el => ({
                            type: el.tagName,
                            class: el.className,
                            text: el.innerText ? el.innerText.substring(0, 30) : ''
                        }))
                    });
                }
            }

            return filters;
        }''')

        print(f"   Filter controls found: {sum(f['count'] for f in filter_controls)}")
        for fc in filter_controls[:3]:
            print(f"     - {fc['selector']}: {fc['count']} controls")

        # Count initial products
        initial_products = await self._count_products()
        initial_url = await self.page.evaluate('window.location.href')

        print(f"   Initial products: {initial_products}")
        print(f"   Initial URL: {initial_url}")

        # Try to interact with a filter
        filter_latency = None
        url_changed = False
        shadow_dom_detected = False

        try:
            # Check for Shadow DOM
            shadow_dom_detected = await self.page.evaluate('''() => {
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    if (el.shadowRoot) return true;
                }
                return false;
            }''')

            print(f"   Shadow DOM: {'Detected' if shadow_dom_detected else 'Not found'}")

            # Try clicking a checkbox filter
            checkbox_exists = await self.page.evaluate('''() => {
                return document.querySelectorAll('input[type="checkbox"]').length > 0;
            }''')

            if checkbox_exists:
                print(f"\n   Interacting with filter...")

                # Measure latency
                start_time = datetime.now()

                # Click first unchecked checkbox
                await self.page.evaluate('''() => {
                    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
                    const unchecked = checkboxes.find(cb => !cb.checked);
                    if (unchecked) unchecked.click();
                }''')

                # Wait for DOM mutation
                await asyncio.sleep(1)

                # Check if products changed
                post_filter_products = await self._count_products()
                post_filter_url = await self.page.evaluate('window.location.href')

                end_time = datetime.now()
                filter_latency = (end_time - start_time).total_seconds()

                url_changed = (post_filter_url != initial_url)

                print(f"   Filter latency: {filter_latency:.2f}s")
                print(f"   URL changed: {url_changed}")
                print(f"   Products before: {initial_products} → after: {post_filter_products}")

                return {
                    'pattern': 'E-Commerce Filtering',
                    'filter_controls': filter_controls,
                    'filter_latency_seconds': filter_latency,
                    'url_sync': url_changed,
                    'shadow_dom': shadow_dom_detected,
                    'initial_products': initial_products,
                    'filtered_products': post_filter_products,
                    'filter_mechanism': 'URL-based' if url_changed else 'Client-side state',
                    'phenomenology': f"Filters {'sync to URL' if url_changed else 'use local state'}, latency={filter_latency:.2f}s"
                }

        except Exception as e:
            print(f"   ⚠️  Filter interaction failed: {e}")

        return {
            'pattern': 'E-Commerce Filtering',
            'filter_controls': filter_controls,
            'shadow_dom': shadow_dom_detected,
            'initial_products': initial_products,
            'phenomenology': 'Unable to test filter interaction'
        }

    async def _count_products(self) -> int:
        """Count product items on page"""
        return await self.page.evaluate('''() => {
            const selectors = [
                '[data-testid*="product"]',
                '[class*="product-card"]',
                '[class*="ProductCard"]',
                'article',
                '[class*="grid"] > div'
            ];

            let maxCount = 0;
            for (const selector of selectors) {
                const count = document.querySelectorAll(selector).length;
                if (count > maxCount) maxCount = count;
            }

            return maxCount;
        }''')


class ScrollytellingDetector:
    """
    Test 3: Bloomberg/NYT - Scrollytelling patterns

    Mannerisms to find:
    - IntersectionObserver usage
    - Trigger points for animations
    - Timeline-based content delivery
    """

    def __init__(self, page):
        self.page = page
        self.scroll_events = []

    async def analyze_scrollytelling(self, url: str) -> Dict[str, Any]:
        """
        Detect scroll-triggered animations and content
        """
        print("\n📰 TEST 3: Scrollytelling Detection (Bloomberg/NYT Pattern)")
        print("="*60)

        print(f"   Navigating to {url}")
        await self.page.goto(url, {'waitUntil': 'domcontentloaded', 'timeout': 45000})
        await asyncio.sleep(2)

        # Inject IntersectionObserver spy
        await self.page.evaluateOnNewDocument('''() => {
            window._observerLog = [];
            window._originalIntersectionObserver = window.IntersectionObserver;

            window.IntersectionObserver = function(callback, options) {
                window._observerLog.push({
                    created_at: Date.now(),
                    options: options
                });
                return new window._originalIntersectionObserver(callback, options);
            };
        }''')

        # Reload to capture observers
        await self.page.reload({'waitUntil': 'domcontentloaded'})
        await asyncio.sleep(2)

        # Check for IntersectionObserver usage
        observer_log = await self.page.evaluate('window._observerLog || []')

        print(f"   IntersectionObserver instances: {len(observer_log)}")

        # Look for scroll-triggered elements
        scroll_triggers = await self.page.evaluate('''() => {
            const triggers = [];

            // Find elements with data-scroll, data-aos, or similar attributes
            const scrollElements = document.querySelectorAll(
                '[data-scroll], [data-aos], [class*="fade"], [class*="animate"]'
            );

            scrollElements.forEach(el => {
                const rect = el.getBoundingClientRect();
                triggers.push({
                    tag: el.tagName,
                    classes: el.className,
                    position_y: rect.top + window.scrollY,
                    viewport_height: window.innerHeight,
                    attributes: Array.from(el.attributes).map(a => `${a.name}=${a.value}`)
                });
            });

            return triggers;
        }''')

        print(f"   Scroll-triggered elements: {len(scroll_triggers)}")

        # Perform scroll test
        print(f"\n   Performing scroll test...")
        scroll_timeline = []

        # Get page height
        page_height = await self.page.evaluate('document.body.scrollHeight')
        viewport_height = await self.page.evaluate('window.innerHeight')

        # Scroll in increments and observe changes
        scroll_positions = [0, viewport_height * 0.5, viewport_height, viewport_height * 2]

        for scroll_pos in scroll_positions:
            if scroll_pos > page_height:
                break

            await self.page.evaluate(f'window.scrollTo(0, {scroll_pos})')
            await asyncio.sleep(0.5)

            # Capture what's visible
            visible_state = await self.page.evaluate(f'''() => {{
                const visible = [];
                const elements = document.querySelectorAll('p, h1, h2, h3, img, video');

                elements.forEach(el => {{
                    const rect = el.getBoundingClientRect();
                    if (rect.top >= 0 && rect.top <= window.innerHeight) {{
                        visible.push({{
                            tag: el.tagName,
                            text: el.innerText ? el.innerText.substring(0, 50) : '',
                            scroll_position: {scroll_pos}
                        }});
                    }}
                }});

                return visible;
            }}''')

            scroll_timeline.append({
                'scroll_position': scroll_pos,
                'visible_elements': len(visible_state),
                'sample_content': visible_state[:3]
            })

            print(f"     Scroll {scroll_pos}px: {len(visible_state)} visible elements")

        # Analyze trigger points
        trigger_points = []
        for i, trigger in enumerate(scroll_triggers[:10]):
            trigger_y = trigger['position_y']
            viewport_h = trigger['viewport_height']

            trigger_points.append({
                'element': f"{trigger['tag']}.{trigger['classes'][:30]}",
                'trigger_y': trigger_y,
                'trigger_percentage': (trigger_y / page_height) * 100 if page_height > 0 else 0
            })

        print(f"\n   ✅ Scrollytelling analysis complete")

        return {
            'pattern': 'Scrollytelling',
            'intersection_observers': len(observer_log),
            'observer_configs': observer_log,
            'scroll_triggered_elements': len(scroll_triggers),
            'trigger_points': trigger_points,
            'scroll_timeline': scroll_timeline,
            'page_height': page_height,
            'phenomenology': f"IntersectionObserver{'s' if len(observer_log) > 1 else ''} detected: {len(observer_log)}, Scroll triggers: {len(scroll_triggers)}"
        }


class ArchitectureStressTest:
    """
    Main test runner for all three architecture patterns
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None

    async def __aenter__(self):
        self.browser = await launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu'
            ]
        )
        self.page = await self.browser.newPage()
        await self.page.setViewport({'width': 1920, 'height': 1080})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()

    async def run_all_tests(self, test_urls: Dict[str, str]) -> Dict[str, Any]:
        """
        Run all three stress tests

        Args:
            test_urls: Dict with keys 'persistent_state', 'filtering', 'scrollytelling'
        """
        results = {
            'test_timestamp': datetime.now().isoformat(),
            'tests': {}
        }

        print("\n" + "="*60)
        print("ARCHITECTURE STRESS TEST SUITE")
        print("="*60)

        # Test 1: Persistent State
        if 'persistent_state' in test_urls:
            detector = PersistentStateDetector(self.page)
            results['tests']['persistent_state'] = await detector.detect_persistent_components(
                test_urls['persistent_state']
            )

        # Test 2: Filtering
        if 'filtering' in test_urls:
            detector = FilteringMannerismDetector(self.page)
            results['tests']['filtering'] = await detector.analyze_filtering_system(
                test_urls['filtering']
            )

        # Test 3: Scrollytelling
        if 'scrollytelling' in test_urls:
            detector = ScrollytellingDetector(self.page)
            results['tests']['scrollytelling'] = await detector.analyze_scrollytelling(
                test_urls['scrollytelling']
            )

        # Generate cross-architecture metrics
        results['metrics'] = self._compute_metrics(results['tests'])

        return results

    def _compute_metrics(self, tests: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute cross-architecture metrics
        """
        metrics = {
            'state_persistence_detected': False,
            'filter_latency_ms': None,
            'intersection_observer_detected': False,
            'phenomenology_summary': []
        }

        # Metric 1: State Persistence
        if 'persistent_state' in tests:
            ps = tests['persistent_state']
            if ps.get('persisted_audio') or ps.get('push_state_detected'):
                metrics['state_persistence_detected'] = True
                metrics['phenomenology_summary'].append(
                    f"State Persistence: {ps.get('phenomenology', 'Unknown')}"
                )

        # Metric 2: Filter Latency
        if 'filtering' in tests:
            ft = tests['filtering']
            if ft.get('filter_latency_seconds'):
                metrics['filter_latency_ms'] = ft['filter_latency_seconds'] * 1000
                metrics['phenomenology_summary'].append(
                    f"Filtering: {ft.get('phenomenology', 'Unknown')}"
                )

        # Metric 3: IntersectionObserver
        if 'scrollytelling' in tests:
            st = tests['scrollytelling']
            if st.get('intersection_observers', 0) > 0:
                metrics['intersection_observer_detected'] = True
                metrics['phenomenology_summary'].append(
                    f"Scrollytelling: {st.get('phenomenology', 'Unknown')}"
                )

        return metrics


async def run_stress_tests():
    """
    Main entry point for stress tests
    """

    # Define test URLs
    test_urls = {
        'persistent_state': 'https://soundcloud.com/discover',  # SPA with audio state
        'filtering': 'https://www.grailed.com/shop',  # E-commerce filtering
        'scrollytelling': 'https://www.nytimes.com'  # Scrollytelling (article pages better)
    }

    print("\n🧪 ARCHITECTURE STRESS TEST")
    print("Testing three high-contrast phenomenologies:\n")
    print("1. Persistent State (SoundCloud-style SPA)")
    print("2. E-Commerce Filtering (Grailed/SSENSE)")
    print("3. Scrollytelling (Bloomberg/NYT)")

    async with ArchitectureStressTest(headless=True) as tester:
        results = await tester.run_all_tests(test_urls)

        # Save results
        output_file = 'data/architecture_stress_test_results.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print("\n" + "="*60)
        print("CROSS-ARCHITECTURE METRICS")
        print("="*60)

        metrics = results['metrics']
        print(f"\n✅ State Persistence: {'DETECTED' if metrics['state_persistence_detected'] else 'NOT FOUND'}")

        if metrics['filter_latency_ms']:
            print(f"✅ Filter Latency: {metrics['filter_latency_ms']:.0f}ms")
        else:
            print(f"⚠️  Filter Latency: NOT MEASURED")

        print(f"✅ IntersectionObserver: {'DETECTED' if metrics['intersection_observer_detected'] else 'NOT FOUND'}")

        print(f"\n📊 PHENOMENOLOGY SUMMARY:")
        for summary in metrics['phenomenology_summary']:
            print(f"   • {summary}")

        print(f"\n💾 Full results saved to: {output_file}")

        return results


if __name__ == "__main__":
    asyncio.run(run_stress_tests())
