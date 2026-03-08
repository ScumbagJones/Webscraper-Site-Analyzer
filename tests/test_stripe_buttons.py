#!/usr/bin/env python3
"""Investigate how Stripe actually implements hover states"""

import asyncio
from playwright.async_api import async_playwright

async def investigate_stripe():
    """Look at actual button/link elements on Stripe"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Loading Stripe.com...")
        await page.goto('https://stripe.com', wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(2000)

        # Find a button and inspect its hover behavior
        button_info = await page.evaluate('''() => {
            // Find first prominent button
            const button = document.querySelector('a[href*="login"], a[href*="signup"], button');
            if (!button) return null;

            // Get its classes
            const classes = button.className ? button.className.split(' ') : [];

            // Get computed style in normal state
            const normalStyle = window.getComputedStyle(button);

            return {
                tag: button.tagName,
                text: button.textContent.trim().substring(0, 30),
                classes: classes,
                normalBg: normalStyle.backgroundColor,
                normalColor: normalStyle.color,
                hasOnClick: !!button.onclick,
                hasEventListeners: true // Can't detect all listeners easily
            };
        }''')

        print(f"\n📍 Sample Interactive Element Found:")
        print(f"   Tag: {button_info['tag']}")
        print(f"   Text: {button_info['text']}")
        print(f"   Classes: {button_info['classes'][:5]}")
        print(f"   Background: {button_info['normalBg']}")
        print(f"   Has onclick: {button_info['hasOnClick']}")

        # Check for CSS-in-JS
        css_in_js = await page.evaluate('''() => {
            // Look for styled-components, emotion, or similar
            const allStyleTags = document.querySelectorAll('style');
            let hasDataStyledAttr = false;
            let hasEmotionAttr = false;

            document.querySelectorAll('*').forEach(el => {
                if (el.hasAttribute('data-styled') || el.className.includes('sc-')) {
                    hasDataStyledAttr = true;
                }
                if (el.className.match(/css-[a-z0-9]+/)) {
                    hasEmotionAttr = true;
                }
            });

            return {
                styleTags: allStyleTags.length,
                hasStyledComponents: hasDataStyledAttr,
                hasEmotion: hasEmotionAttr,
                firstStyleTagSample: allStyleTags[0] ? allStyleTags[0].textContent.substring(0, 200) : 'none'
            };
        }''')

        print(f"\n🔍 CSS-in-JS Detection:")
        print(f"   Style tags: {css_in_js['styleTags']}")
        print(f"   Styled-components: {css_in_js['hasStyledComponents']}")
        print(f"   Emotion: {css_in_js['hasEmotion']}")
        print(f"   First style sample: {css_in_js['firstStyleTagSample'][:100]}...")

        # Look for any hover-related CSS
        hover_search = await page.evaluate('''() => {
            const allStyleTags = document.querySelectorAll('style');
            let hoverMatches = [];

            allStyleTags.forEach(tag => {
                const content = tag.textContent;
                // Search for hover patterns
                const matches = content.match(/:hover[^}]*/g);
                if (matches) {
                    hoverMatches.push(...matches.slice(0, 3)); // First 3 per tag
                }
            });

            return hoverMatches.slice(0, 5); // Total first 5
        }''')

        print(f"\n🎨 Hover CSS Found in Style Tags:")
        if hover_search:
            for match in hover_search:
                print(f"   {match[:80]}...")
        else:
            print("   None found")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(investigate_stripe())
