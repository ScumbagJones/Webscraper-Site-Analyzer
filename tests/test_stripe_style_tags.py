#!/usr/bin/env python3
"""Check if Stripe puts hover rules in <style> tags instead of external CSS"""

import asyncio
from playwright.async_api import async_playwright

async def check_style_tags():
    """Check <style> tags for hover rules"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Loading Stripe.com...")
        await page.goto('https://stripe.com', wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(2000)

        # Search <style> tags for hover rules (CSS-in-JS often uses these)
        style_tag_hovers = await page.evaluate('''() => {
            const allStyleTags = document.querySelectorAll('style');
            let hoverRules = [];

            allStyleTags.forEach(tag => {
                const content = tag.textContent;
                // Find hover rules
                const hoverRegex = /([^{}]+):hover\s*{([^}]*)}/g;
                let match;
                while ((match = hoverRegex.exec(content)) !== null && hoverRules.length < 10) {
                    hoverRules.push({
                        selector: match[1].trim(),
                        styles: match[2].trim()
                    });
                }
            });

            return {
                totalStyleTags: allStyleTags.length,
                hoverRulesFound: hoverRules.length,
                samples: hoverRules.slice(0, 5)
            };
        }''')

        print(f"\n✅ RESULTS:")
        print(f"   Total <style> tags: {style_tag_hovers['totalStyleTags']}")
        print(f"   Hover rules in <style> tags: {style_tag_hovers['hoverRulesFound']}")

        if style_tag_hovers['samples']:
            print(f"\n   Sample hover rules:")
            for i, rule in enumerate(style_tag_hovers['samples'], 1):
                print(f"\n   {i}. Selector: {rule['selector'][:60]}")
                print(f"      Styles: {rule['styles'][:100]}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(check_style_tags())
