"""
NTS.live Demo Test - Playwright Version

Quick demo to see what we can already detect about NTS.live
using Playwright (more stable than Pyppeteer).

This is Option C - testing existing capabilities before building new tools.
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


async def analyze_nts():
    """
    Analyze NTS.live architecture patterns
    """
    print("\n" + "="*70)
    print(" 🎵 NTS.LIVE ARCHITECTURE DEMO")
    print("="*70)

    url = 'https://nts.live'

    print(f"\nTarget: {url}")
    print(f"Method: Playwright async")
    print(f"Focus: Audio player, layout, embeds, tags\n")

    print("="*70)
    print(" 🚀 LAUNCHING BROWSER...")
    print("="*70)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"   ✅ Browser launched")

        # Navigate to NTS
        print(f"\n📍 Navigating to {url}...")
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)

        # Wait for main content
        try:
            await page.wait_for_selector('main, [class*="player"]', timeout=10000)
            print(f"   ✅ Content loaded")
        except:
            print(f"   ⚠️  Main content selector not found, continuing...")

        # Get page title
        title = await page.title()
        print(f"   📄 Page title: {title}")

        # =================================================================
        # ANALYSIS 1: FRAMEWORK DETECTION
        # =================================================================
        print("\n" + "="*70)
        print(" 1️⃣  FRAMEWORK DETECTION")
        print("="*70)

        framework_data = await page.evaluate('''() => {
            const hints = {
                react: !!document.querySelector('[data-reactroot], [data-reactid]') ||
                       window.React !== undefined,
                next: !!document.querySelector('#__next, #__NEXT_DATA__') ||
                      window.__NEXT_DATA__ !== undefined,
                vue: !!document.querySelector('[data-v-]') ||
                     window.__VUE__ !== undefined,
                angular: !!document.querySelector('[ng-version]') ||
                         window.ng !== undefined
            };

            // Check for meta tags
            const metaFramework = document.querySelector('meta[name="generator"]');

            return {
                hints: hints,
                meta_generator: metaFramework ? metaFramework.content : null,
                next_data_present: !!document.querySelector('#__NEXT_DATA__')
            };
        }''')

        if framework_data['hints']['next']:
            print(f"   ✅ Framework: Next.js")
        elif framework_data['hints']['react']:
            print(f"   ✅ Framework: React")
        elif framework_data['hints']['vue']:
            print(f"   ✅ Framework: Vue")
        elif framework_data['hints']['angular']:
            print(f"   ✅ Framework: Angular")
        else:
            print(f"   ⚠️  Framework: Unknown/Custom")

        if framework_data['meta_generator']:
            print(f"   Meta generator: {framework_data['meta_generator']}")

        # =================================================================
        # ANALYSIS 2: AUDIO PLAYER DETECTION
        # =================================================================
        print("\n" + "="*70)
        print(" 2️⃣  AUDIO PLAYER DETECTION (Persistent State Check)")
        print("="*70)

        player_data = await page.evaluate('''() => {
            // Find audio elements
            const audio = document.querySelector('audio, video');

            // Find player containers
            const playerSelectors = [
                '[class*="player"]',
                '[class*="Player"]',
                '[id*="player"]',
                '[data-player]'
            ];

            let playerContainer = null;
            let playerSelector = null;

            for (const selector of playerSelectors) {
                const found = document.querySelector(selector);
                if (found) {
                    playerContainer = {
                        selector: selector,
                        class: found.className,
                        id: found.id || 'none',
                        tag: found.tagName
                    };
                    playerSelector = selector;
                    break;
                }
            }

            return {
                has_audio: !!audio,
                audio_src: audio ? audio.src : null,
                audio_paused: audio ? audio.paused : null,
                player_container: playerContainer,
                player_selector: playerSelector,
                iframe_count: document.querySelectorAll('iframe').length
            };
        }''')

        if player_data['has_audio']:
            print(f"   ✅ Audio element found")
            print(f"      Source: {player_data['audio_src'][:80] if player_data['audio_src'] else 'Empty'}")
            print(f"      Paused: {player_data['audio_paused']}")
        else:
            print(f"   ⚠️  No <audio> element found")

        if player_data['player_container']:
            print(f"   ✅ Player container found")
            print(f"      Selector: {player_data['player_selector']}")
            print(f"      Element: <{player_data['player_container']['tag']}>")
            print(f"      Class: {player_data['player_container']['class'][:60]}")
        else:
            print(f"   ⚠️  No player container detected")

        print(f"   📊 Iframes on page: {player_data['iframe_count']}")

        # =================================================================
        # ANALYSIS 3: LAYOUT SYSTEM
        # =================================================================
        print("\n" + "="*70)
        print(" 3️⃣  LAYOUT SYSTEM DETECTION")
        print("="*70)

        layout_data = await page.evaluate('''() => {
            const mainContainers = [
                document.querySelector('main'),
                document.querySelector('[role="main"]'),
                document.body
            ].filter(Boolean);

            const main = mainContainers[0];
            const computed = getComputedStyle(main);

            return {
                element: main.tagName,
                display: computed.display,
                grid_template_columns: computed.gridTemplateColumns,
                grid_template_rows: computed.gridTemplateRows,
                grid_gap: computed.gridGap || computed.gap,
                flex_direction: computed.flexDirection,
                flex_wrap: computed.flexWrap,
                is_grid: computed.display.includes('grid'),
                is_flex: computed.display.includes('flex')
            };
        }''')

        if layout_data['is_grid']:
            print(f"   ✅ Layout: CSS Grid")
            print(f"      Columns: {layout_data['grid_template_columns'][:80]}")
            if layout_data['grid_gap'] and layout_data['grid_gap'] != 'normal':
                print(f"      Gap: {layout_data['grid_gap']}")
        elif layout_data['is_flex']:
            print(f"   ✅ Layout: Flexbox")
            print(f"      Direction: {layout_data['flex_direction']}")
            print(f"      Wrap: {layout_data['flex_wrap']}")
        else:
            print(f"   Layout: {layout_data['display']}")

        # =================================================================
        # ANALYSIS 4: SOUNDCLOUD EMBED DETECTION
        # =================================================================
        print("\n" + "="*70)
        print(" 4️⃣  SOUNDCLOUD EMBED DETECTION (Visual Integration)")
        print("="*70)

        sc_data = await page.evaluate('''() => {
            const scIframes = Array.from(document.querySelectorAll('iframe'))
                .filter(iframe => iframe.src && iframe.src.includes('soundcloud'));

            if (scIframes.length === 0) {
                return { found: false };
            }

            const embed = scIframes[0];
            const wrapper = embed.parentElement;

            return {
                found: true,
                count: scIframes.length,
                embed_src: embed.src.substring(0, 80),
                wrapper_tag: wrapper.tagName,
                wrapper_class: wrapper.className,
                wrapper_id: wrapper.id,
                wrapper_styles: {
                    border: getComputedStyle(wrapper).border,
                    borderRadius: getComputedStyle(wrapper).borderRadius,
                    padding: getComputedStyle(wrapper).padding,
                    background: getComputedStyle(wrapper).backgroundColor
                },
                iframe_styles: {
                    filter: getComputedStyle(embed).filter,
                    opacity: getComputedStyle(embed).opacity,
                    border: getComputedStyle(embed).border
                }
            };
        }''')

        if sc_data['found']:
            print(f"   ✅ SoundCloud embeds found: {sc_data['count']}")
            print(f"      Source: {sc_data['embed_src']}")
            print(f"      Wrapper: <{sc_data['wrapper_tag']}> class=\"{sc_data['wrapper_class'][:50]}\"")
            print(f"\n   🎨 Visual Styling:")
            print(f"      Wrapper border: {sc_data['wrapper_styles']['border']}")
            print(f"      Wrapper border-radius: {sc_data['wrapper_styles']['borderRadius']}")
            print(f"      Iframe filter: {sc_data['iframe_styles']['filter']}")
            print(f"      Iframe opacity: {sc_data['iframe_styles']['opacity']}")
        else:
            print(f"   ⚠️  No SoundCloud embeds on this page")
            print(f"      (May be on show-specific pages)")

        # =================================================================
        # ANALYSIS 5: TAG/GENRE SYSTEM
        # =================================================================
        print("\n" + "="*70)
        print(" 5️⃣  TAG/GENRE SYSTEM (API Reactivity)")
        print("="*70)

        tag_data = await page.evaluate('''() => {
            const tagSelectors = [
                'a[href*="genre"]',
                'a[href*="tag"]',
                '[class*="tag"]',
                '[class*="genre"]',
                '[data-tag]',
                '[data-genre]'
            ];

            let tags = [];
            let foundSelector = null;

            for (const selector of tagSelectors) {
                const found = Array.from(document.querySelectorAll(selector));
                if (found.length > 0) {
                    tags = found.slice(0, 5).map(el => ({
                        text: el.innerText ? el.innerText.substring(0, 30).trim() : '',
                        href: el.href || 'none',
                        class: el.className
                    })).filter(t => t.text);

                    foundSelector = selector;
                    break;
                }
            }

            return {
                found: tags.length > 0,
                selector: foundSelector,
                count: tags.length,
                samples: tags
            };
        }''')

        if tag_data['found']:
            print(f"   ✅ Tag/Genre system detected")
            print(f"      Selector: {tag_data['selector']}")
            print(f"      Found: {tag_data['count']} tags")
            print(f"\n   Sample tags:")
            for tag in tag_data['samples'][:5]:
                if tag['text']:
                    print(f"      • {tag['text']}")
        else:
            print(f"   ⚠️  No tag system detected on homepage")

        # =================================================================
        # ANALYSIS 6: COMPONENT PATTERNS
        # =================================================================
        print("\n" + "="*70)
        print(" 6️⃣  REPEATING COMPONENT PATTERNS")
        print("="*70)

        component_data = await page.evaluate('''() => {
            const patterns = [];

            // Common card/item selectors
            const selectors = [
                'article',
                '[class*="card"]',
                '[class*="Card"]',
                '[class*="item"]',
                '[class*="Item"]',
                '[class*="show"]',
                '[class*="Show"]'
            ];

            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                if (elements.length >= 3) {
                    const sample = elements[0];
                    patterns.push({
                        selector: selector,
                        count: elements.length,
                        tag: sample.tagName,
                        class: sample.className,
                        has_image: !!sample.querySelector('img'),
                        has_link: !!sample.querySelector('a')
                    });
                }
            }

            return patterns;
        }''')

        if len(component_data) > 0:
            print(f"   ✅ Found {len(component_data)} repeating patterns")
            for pattern in component_data[:3]:
                print(f"\n      Pattern: {pattern['selector']}")
                print(f"         Count: {pattern['count']} instances")
                print(f"         Element: <{pattern['tag']}>")
                print(f"         Has image: {pattern['has_image']}")
                print(f"         Has link: {pattern['has_link']}")
        else:
            print(f"   ⚠️  No obvious repeating patterns detected")

        # =================================================================
        # SAVE RESULTS
        # =================================================================
        print("\n" + "="*70)
        print(" 💾 SAVING RESULTS")
        print("="*70)

        results = {
            'url': url,
            'title': title,
            'framework': framework_data,
            'audio_player': player_data,
            'layout': layout_data,
            'soundcloud_embeds': sc_data,
            'tag_system': tag_data,
            'component_patterns': component_data
        }

        output_dir = Path('data')
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / 'nts_demo_playwright_results.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"   ✅ Results saved to: {output_file}")

        # =================================================================
        # GENERATE "MRI REPORT"
        # =================================================================
        print("\n" + "="*70)
        print(" 🏥 ARCHITECTURE MRI REPORT")
        print("="*70)

        report = generate_mri_report(results)

        report_file = output_dir / 'nts_mri_report.md'
        with open(report_file, 'w') as f:
            f.write(report)

        print(report)
        print(f"\n   ✅ MRI report saved to: {report_file}")

        await browser.close()


def generate_mri_report(results):
    """
    Generate user-friendly "MRI Report"
    """
    report = []

    report.append("# 🏥 NTS.LIVE Architecture MRI Report\n")
    report.append(f"**Site:** {results['url']}\n")
    report.append(f"**Title:** {results['title']}\n")

    # Framework verdict
    framework = results['framework']
    if framework['hints']['next']:
        fw_name = "Next.js (React Framework)"
        verdict = "✅ High-Performance SSR/SSG"
    elif framework['hints']['react']:
        fw_name = "React"
        verdict = "✅ Modern SPA"
    else:
        fw_name = "Unknown/Custom"
        verdict = "⚠️ Unable to determine"

    report.append(f"\n**Verdict:** {verdict}\n")
    report.append(f"\n---\n")

    # Audio
    report.append("\n## 🎵 Audio Architecture\n")
    player = results['audio_player']
    if player['has_audio']:
        report.append(f"- **Status:** ✅ Audio element present\n")
        report.append(f"- **Persistence:** To be tested (requires navigation)\n")
        if player['player_container']:
            report.append(f"- **Container:** `{player['player_selector']}`\n")
            report.append(f"- **Implementation Hint:** Likely global component in root layout\n")
    else:
        report.append(f"- **Status:** ⚠️ No audio element on homepage\n")
        report.append(f"- **Note:** May be present on show pages\n")

    # Layout
    report.append("\n## 📐 Layout System\n")
    layout = results['layout']
    if layout['is_grid']:
        report.append(f"- **Type:** CSS Grid\n")
        report.append(f"- **Columns:** `{layout['grid_template_columns'][:80]}`\n")
        report.append(f"- **Recommendation:** Use `display: grid` for main layout\n")
    elif layout['is_flex']:
        report.append(f"- **Type:** Flexbox\n")
        report.append(f"- **Direction:** {layout['flex_direction']}\n")
        report.append(f"- **Recommendation:** Use `display: flex` for main layout\n")

    # SoundCloud
    report.append("\n## 🎨 SoundCloud Integration\n")
    sc = results['soundcloud_embeds']
    if sc['found']:
        report.append(f"- **Status:** ✅ Detected ({sc['count']} embeds)\n")
        report.append(f"- **Wrapper:** `<{sc['wrapper_tag']}>`\n")
        report.append(f"- **Visual Masking:** {sc['wrapper_styles']['border']}\n")
        report.append(f"- **Design Secret:** Custom wrapper to match site aesthetic\n")
    else:
        report.append(f"- **Status:** ⚠️ Not detected on homepage\n")

    # Tags
    report.append("\n## ⚡ Tag/Genre System\n")
    tags = results['tag_system']
    if tags['found']:
        report.append(f"- **Status:** ✅ Detected\n")
        report.append(f"- **Count:** {tags['count']} tags\n")
        report.append(f"- **Reactivity:** To be tested (requires click interaction)\n")
    else:
        report.append(f"- **Status:** ⚠️ Not detected on homepage\n")

    # Components
    report.append("\n## 🧩 Component Patterns\n")
    patterns = results['component_patterns']
    if len(patterns) > 0:
        report.append(f"- **Repeating patterns:** {len(patterns)}\n")
        for p in patterns[:3]:
            report.append(f"  - `{p['selector']}`: {p['count']} instances\n")
    else:
        report.append(f"- **Status:** No obvious patterns detected\n")

    report.append("\n---\n")
    report.append("\n## 📋 Next Steps for Full Analysis\n")
    report.append("1. Test audio persistence by navigating between pages\n")
    report.append("2. Click tags to test API reactivity\n")
    report.append("3. Visit show pages to analyze SoundCloud embed styling\n")
    report.append("4. Measure filter/tag latency\n")

    return ''.join(report)


if __name__ == "__main__":
    print("\n🎯 NTS.LIVE ARCHITECTURE DEMO")
    print("Testing EXISTING capabilities with Playwright\n")

    try:
        asyncio.run(analyze_nts())
        print("\n✅ Demo complete!")
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
