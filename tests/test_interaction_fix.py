#!/usr/bin/env python3
"""Test the fixed interaction states extraction on Stripe.com"""

import asyncio
import json
from playwright.async_api import async_playwright

async def test_interaction_states():
    """Test interaction states detection on Stripe"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Loading Stripe.com...")
        await page.goto('https://stripe.com', wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(2000)

        print("\nExtracting interaction states with new dual-strategy approach...")

        # Run the exact code from the fixed method
        from collections import defaultdict

        # Strategy 1: Traditional CSS
        traditional_rules = await page.evaluate('''() => {
            const results = [];
            const pseudos = [':hover', ':focus', ':active', ':focus-within', ':focus-visible'];
            try {
                for (const sheet of document.styleSheets) {
                    let rules;
                    try { rules = sheet.cssRules || sheet.rules; }
                    catch(e) { continue; }
                    if (!rules) continue;
                    for (const rule of rules) {
                        if (!rule.selectorText) continue;
                        const sel = rule.selectorText;
                        const matchedPseudo = pseudos.find(p => sel.includes(p));
                        if (!matchedPseudo) continue;
                        const base = sel.replace(matchedPseudo, '').replace(/::before|::after/g, '').trim();
                        if (!base || base.length > 120) continue;
                        const props = {};
                        for (let i = 0; i < rule.style.length; i++) {
                            const prop = rule.style[i];
                            props[prop] = rule.style.getPropertyValue(prop);
                        }
                        if (Object.keys(props).length === 0) continue;
                        results.push({ base, pseudo: matchedPseudo, props });
                    }
                }
            } catch(e) {}
            return results;
        }''')

        # Strategy 2: Utility classes
        utility_classes = await page.evaluate('''() => {
            const allElements = document.querySelectorAll('*');
            const interactionClasses = {
                hover: [],
                focus: [],
                active: [],
                disabled: []
            };

            allElements.forEach(el => {
                if (!el.className || typeof el.className !== 'string') return;
                const classes = el.className.split(' ').filter(c => c.trim());
                classes.forEach(c => {
                    if (c.startsWith('hover:')) interactionClasses.hover.push(c);
                    else if (c.startsWith('focus:')) interactionClasses.focus.push(c);
                    else if (c.startsWith('active:')) interactionClasses.active.push(c);
                    else if (c.startsWith('disabled:')) interactionClasses.disabled.push(c);
                });
            });

            return {
                hover: [...new Set(interactionClasses.hover)],
                focus: [...new Set(interactionClasses.focus)],
                active: [...new Set(interactionClasses.active)],
                disabled: [...new Set(interactionClasses.disabled)]
            };
        }''')

        total_traditional = len(traditional_rules) if traditional_rules else 0
        total_utility = sum(len(v) for v in utility_classes.values())

        print(f"\n✅ RESULTS:")
        print(f"   Traditional CSS rules: {total_traditional}")
        print(f"   Utility classes: {total_utility}")
        print(f"   Total detections: {total_traditional + total_utility}")

        if utility_classes['hover']:
            print(f"\n   Sample hover classes (first 10):")
            for cls in utility_classes['hover'][:10]:
                print(f"      - {cls}")

        if utility_classes['focus']:
            print(f"\n   Sample focus classes (first 5):")
            for cls in utility_classes['focus'][:5]:
                print(f"      - {cls}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_interaction_states())
