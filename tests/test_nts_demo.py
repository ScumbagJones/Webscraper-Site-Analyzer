"""
Quick NTS.live Demo Test

Uses existing intelligent_scraper.py to demonstrate what we can already detect.
This is Option C - testing existing capabilities before building new ones.
"""

import asyncio
import sys
import json
from pathlib import Path

# Import existing intelligent scraper
try:
    from intelligent_scraper import IntelligentScraper
    print("✅ Using intelligent_scraper.py")
except ImportError:
    print("❌ intelligent_scraper.py not found")
    print("   This test requires the existing intelligent_scraper.py")
    sys.exit(1)


async def demo_nts_analysis():
    """
    Run existing intelligent scraper on NTS.live to see what we already detect
    """
    print("\n" + "="*70)
    print(" 🎵 NTS.LIVE DEMO - Testing Existing Capabilities")
    print("="*70)

    print("\nThis will use our EXISTING intelligent_scraper.py to analyze NTS.live")
    print("We'll see what patterns we already detect before building new tools.\n")

    # Test URL
    url = 'https://nts.live'

    print(f"Target: {url}")
    print(f"Strategy: content-ready (wait for main content)")
    print(f"Ad blocking: ON\n")

    print("="*70)
    print(" RUNNING ANALYSIS...")
    print("="*70)

    try:
        async with IntelligentScraper(headless=True, block_ads=True) as scraper:
            result = await scraper.scrape_intelligent(
                url,
                wait_strategy='content-ready',
                content_selector='main, article, [class*="player"]',
                timeout=45000
            )

            # Save full result
            output_dir = Path('data')
            output_dir.mkdir(exist_ok=True)

            output_file = output_dir / 'nts_demo_results.json'
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)

            print("\n" + "="*70)
            print(" 📊 ANALYSIS COMPLETE")
            print("="*70)

            # Display key findings
            print(f"\n🔍 FRAMEWORK DETECTION:")
            print(f"   Framework: {result['framework']['framework']}")
            print(f"   Confidence: {result['framework']['confidence']:.0%}")
            if result['framework']['evidence']:
                print(f"   Evidence:")
                for ev in result['framework']['evidence'][:3]:
                    print(f"      • {ev}")

            print(f"\n📦 SSR CONTENT:")
            sources = result['ssr_content']['content_sources']
            print(f"   Sources: {', '.join(sources) if sources else 'None detected'}")

            print(f"\n🔄 GRAPHQL:")
            print(f"   Operations: {result['graphql']['operations_count']}")
            if result['graphql']['inferred_types']:
                print(f"   Types: {list(result['graphql']['inferred_types'].keys())}")

            print(f"\n🎨 COMPONENTS:")
            print(f"   Found: {len(result['components'])} repeating patterns")
            for comp in result['components'][:3]:
                label = comp['semantic_label']
                print(f"      • {label['name']} ({label['confidence']:.0%})")

            print(f"\n🗄️  ENTITIES:")
            entities = result['entities']
            total_entities = sum(len(e) for e in entities.get('entities', {}).values())
            print(f"   Total: {total_entities}")
            print(f"   Relationships: {len(entities.get('relationships', []))}")

            print(f"\n⏱️  PERFORMANCE:")
            print(f"   Load time: {result['duration_seconds']:.2f}s")
            print(f"   HTML size: {result['html_length']:,} characters")

            print(f"\n💾 Full results saved to: {output_file}")

            # Now let's do NTS-specific checks
            print("\n" + "="*70)
            print(" 🎵 NTS-SPECIFIC PATTERN CHECK")
            print("="*70)

            await nts_specific_checks(scraper.page, result)

    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()


async def nts_specific_checks(page, base_result):
    """
    Additional NTS-specific checks on top of the base analysis
    """

    # Check 1: Audio Player Detection
    print("\n1️⃣  AUDIO PLAYER CHECK:")
    try:
        player_info = await page.evaluate('''() => {
            // Look for audio elements
            const audio = document.querySelector('audio');

            // Look for player containers
            const playerClasses = [
                '[class*="player"]',
                '[class*="Player"]',
                '[id*="player"]'
            ];

            let playerContainer = null;
            for (const selector of playerClasses) {
                const found = document.querySelector(selector);
                if (found) {
                    playerContainer = {
                        selector: selector,
                        class: found.className,
                        id: found.id || 'none'
                    };
                    break;
                }
            }

            return {
                has_audio_element: !!audio,
                audio_src: audio ? audio.src : null,
                player_container: playerContainer,
                iframe_count: document.querySelectorAll('iframe').length
            };
        }''')

        if player_info['has_audio_element']:
            print(f"   ✅ Audio element detected")
            print(f"      Source: {player_info['audio_src'][:80] if player_info['audio_src'] else 'None'}")
        else:
            print(f"   ⚠️  No audio element found")

        if player_info['player_container']:
            print(f"   ✅ Player container detected")
            print(f"      Class: {player_info['player_container']['class'][:50]}")
        else:
            print(f"   ⚠️  No player container found")

        print(f"   📊 Iframes on page: {player_info['iframe_count']}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Check 2: Grid Layout Detection
    print("\n2️⃣  LAYOUT SYSTEM CHECK:")
    try:
        layout_info = await page.evaluate('''() => {
            const main = document.querySelector('main, [role="main"], body');
            const computed = getComputedStyle(main);

            return {
                display: computed.display,
                grid_template_columns: computed.gridTemplateColumns,
                grid_template_areas: computed.gridTemplateAreas,
                flex_direction: computed.flexDirection,
                is_grid: computed.display === 'grid',
                is_flex: computed.display === 'flex'
            };
        }''')

        if layout_info['is_grid']:
            print(f"   ✅ CSS Grid detected")
            print(f"      Columns: {layout_info['grid_template_columns'][:80]}")
        elif layout_info['is_flex']:
            print(f"   ✅ Flexbox detected")
            print(f"      Direction: {layout_info['flex_direction']}")
        else:
            print(f"   Display type: {layout_info['display']}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Check 3: SoundCloud Embed Detection
    print("\n3️⃣  SOUNDCLOUD EMBED CHECK:")
    try:
        sc_info = await page.evaluate('''() => {
            const scIframes = Array.from(document.querySelectorAll('iframe'))
                .filter(iframe => iframe.src.includes('soundcloud'));

            if (scIframes.length === 0) {
                return { found: false };
            }

            const firstEmbed = scIframes[0];
            const wrapper = firstEmbed.parentElement;
            const wrapperStyles = getComputedStyle(wrapper);
            const iframeStyles = getComputedStyle(firstEmbed);

            return {
                found: true,
                count: scIframes.length,
                wrapper_class: wrapper.className,
                wrapper_border: wrapperStyles.border,
                iframe_filter: iframeStyles.filter,
                iframe_opacity: iframeStyles.opacity
            };
        }''')

        if sc_info['found']:
            print(f"   ✅ SoundCloud embeds found: {sc_info['count']}")
            print(f"      Wrapper class: {sc_info['wrapper_class'][:50]}")
            print(f"      Wrapper border: {sc_info['wrapper_border']}")
            print(f"      Iframe filter: {sc_info['iframe_filter']}")
        else:
            print(f"   ⚠️  No SoundCloud embeds detected on this page")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Check 4: Tag/Navigation System
    print("\n4️⃣  TAG SYSTEM CHECK:")
    try:
        tag_info = await page.evaluate('''() => {
            const tagSelectors = [
                '[class*="tag"]',
                '[data-tag]',
                'a[href*="tag"]',
                'a[href*="genre"]'
            ];

            let tags = [];
            for (const selector of tagSelectors) {
                const found = Array.from(document.querySelectorAll(selector));
                if (found.length > 0) {
                    tags = found.slice(0, 5).map(el => ({
                        text: el.innerText.substring(0, 30),
                        href: el.href || 'none',
                        class: el.className
                    }));
                    break;
                }
            }

            return {
                found: tags.length > 0,
                count: tags.length,
                samples: tags
            };
        }''')

        if tag_info['found']:
            print(f"   ✅ Tag system detected: {tag_info['count']} tags")
            for tag in tag_info['samples'][:3]:
                print(f"      • {tag['text']}")
        else:
            print(f"   ⚠️  No tag system detected on this page")

    except Exception as e:
        print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    print("\n🎯 NTS.LIVE DEMO TEST")
    print("Testing existing scraper capabilities before building new tools\n")

    try:
        asyncio.run(demo_nts_analysis())
        print("\n✅ Demo complete!")
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
