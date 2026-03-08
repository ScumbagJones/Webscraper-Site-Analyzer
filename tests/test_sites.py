"""
Test scraper on pi.fyi and vogue.com to see what works
"""

from scraper import WebScraper
import time
from bs4 import BeautifulSoup


def test_site(url, name):
    """Test scraping a site"""
    print(f"\n{'='*60}")
    print(f"Testing: {name} ({url})")
    print('='*60)

    try:
        with WebScraper(headless=True) as scraper:
            start = time.time()
            soup = scraper.scrape_dynamic(url, wait_for_selector='body', wait_time=15)
            duration = time.time() - start

            # Analyze content
            text = soup.get_text().strip()
            text_length = len(text)
            images = len(soup.find_all('img'))
            links = len(soup.find_all('a'))
            buttons = len(soup.find_all('button'))
            scripts = len(soup.find_all('script'))

            print(f"\n✅ Success!")
            print(f"⏱️  Duration: {duration:.2f}s")
            print(f"📄 Content length: {text_length:,} chars")
            print(f"🖼️  Images: {images}")
            print(f"🔗 Links: {links}")
            print(f"🎯 Buttons: {buttons}")
            print(f"📜 Scripts: {scripts}")

            # Check if content looks empty (JS didn't render)
            if text_length < 500:
                print("\n⚠️  WARNING: Very little content - likely JS not fully rendered")
                print(f"First 300 chars of text:\n{text[:300]}")
            else:
                print("\n✅ Good amount of content - JS likely rendered")
                print(f"First 300 chars:\n{text[:300]}")

            # Framework detection
            html_str = str(soup)
            frameworks = []

            if '__NEXT_DATA__' in html_str:
                frameworks.append('Next.js')
            if 'data-reactroot' in html_str or 'data-reactid' in html_str:
                frameworks.append('React')
            if '__nuxt' in html_str.lower():
                frameworks.append('Nuxt.js')
            if 'ng-version' in html_str:
                frameworks.append('Angular')
            if '_next' in html_str:
                frameworks.append('Next.js build')

            if frameworks:
                print(f"\n🔍 Detected frameworks: {', '.join(set(frameworks))}")
            else:
                print("\n🔍 No major JS framework detected (or static site)")

            # Check for anti-bot measures
            if 'cloudflare' in html_str.lower():
                print("🛡️  Cloudflare detected")
            if 'captcha' in html_str.lower():
                print("🛡️  CAPTCHA detected")

            # Complexity score
            complexity = 0
            if text_length < 1000:
                complexity += 3  # Likely needs better JS handling
            if scripts > 20:
                complexity += 2
            if frameworks:
                complexity += 2
            if 'cloudflare' in html_str.lower():
                complexity += 2

            print(f"\n📊 Complexity Score: {complexity}/10")

            if complexity >= 7:
                print("🚨 RECOMMENDATION: Use Hyperbrowser or HasData")
                print("   Reason: Very complex, local Playwright likely insufficient")
            elif complexity >= 4:
                print("⚠️  RECOMMENDATION: Consider Hyperbrowser or Browserless")
                print("   Reason: Moderate complexity, may timeout with local")
            else:
                print("✅ RECOMMENDATION: Local Playwright should work fine")

            return {
                'success': True,
                'duration': duration,
                'text_length': text_length,
                'complexity': complexity,
                'frameworks': frameworks
            }

    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()

        print("\n🚨 RECOMMENDATION: This site definitely needs premium service")
        print("   Try: Hyperbrowser (most reliable) or HasData")

        return {
            'success': False,
            'error': str(e)
        }


if __name__ == "__main__":
    print("\n🧪 Testing scraper on real sites...")

    # Test pi.fyi
    pi_result = test_site('https://pi.fyi', 'Pi.fyi (AI assistant)')

    # Test vogue.com
    vogue_result = test_site('https://vogue.com', 'Vogue (editorial)')

    # Summary
    print(f"\n\n{'='*60}")
    print("📊 SUMMARY")
    print('='*60)

    if pi_result.get('success'):
        print(f"\n✅ Pi.fyi: Success")
        print(f"   Duration: {pi_result['duration']:.2f}s")
        print(f"   Content: {pi_result['text_length']:,} chars")
        print(f"   Complexity: {pi_result['complexity']}/10")
    else:
        print(f"\n❌ Pi.fyi: Failed - {pi_result.get('error')}")

    if vogue_result.get('success'):
        print(f"\n✅ Vogue: Success")
        print(f"   Duration: {vogue_result['duration']:.2f}s")
        print(f"   Content: {vogue_result['text_length']:,} chars")
        print(f"   Complexity: {vogue_result['complexity']}/10")
    else:
        print(f"\n❌ Vogue: Failed - {vogue_result.get('error')}")

    print("\n" + "="*60)
