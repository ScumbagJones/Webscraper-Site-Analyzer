"""
Test scraper against boilerroom.tv
"""

from scraper import WebScraper
from database import DatabaseManager
import json

def test_boilerroom():
    """Test scraping boilerroom.tv"""

    print("Testing boilerroom.tv scraping...")
    print("="*60)

    with WebScraper(headless=False) as scraper:  # Set to False to see what's happening
        try:
            # Try scraping the main page
            print("\n1. Testing main page scrape...")
            soup = scraper.scrape_dynamic(
                "https://boilerroom.tv",
                wait_for_selector="body",
                wait_time=15
            )

            print(f"   - Page title: {soup.title.string if soup.title else 'No title'}")
            print(f"   - Content length: {len(soup.get_text())} characters")

            # Look for video elements
            videos = soup.find_all(['video', 'iframe'])
            print(f"   - Video/iframe elements found: {len(videos)}")

            # Look for links
            links = scraper.extract_links(soup, "https://boilerroom.tv")
            print(f"   - Links found: {len(links)}")

            # Look for common data attributes
            print("\n2. Analyzing page structure...")

            # Check for React/Next.js
            react_elements = soup.find_all(attrs={"data-reactroot": True})
            next_data = soup.find(id="__NEXT_DATA__")

            if next_data:
                print("   - Next.js detected! Found __NEXT_DATA__ script")
                try:
                    next_json = json.loads(next_data.string)
                    print(f"   - Next.js data keys: {list(next_json.keys())}")
                except:
                    print("   - Could not parse Next.js data")

            if react_elements:
                print(f"   - React elements found: {len(react_elements)}")

            # Look for API endpoints in scripts
            print("\n3. Looking for API endpoints...")
            scripts = soup.find_all('script')
            api_patterns = []

            for script in scripts:
                if script.string:
                    if 'api' in script.string.lower() or 'endpoint' in script.string.lower():
                        # Extract potential API URLs
                        import re
                        urls = re.findall(r'https?://[^\s<>"\']+', script.string)
                        api_patterns.extend(urls)

            unique_apis = list(set(api_patterns))[:10]  # First 10 unique
            if unique_apis:
                print(f"   - Potential API endpoints found: {len(unique_apis)}")
                for api in unique_apis[:5]:
                    print(f"     * {api}")

            # Look for event listings
            print("\n4. Looking for event/video content...")

            # Common selectors for video/event sites
            selectors_to_check = [
                ('article', 'Articles'),
                ('.video', 'Video classes'),
                ('.event', 'Event classes'),
                ('[data-testid*="video"]', 'Video test IDs'),
                ('[data-testid*="event"]', 'Event test IDs'),
                ('h1, h2, h3', 'Headings')
            ]

            for selector, name in selectors_to_check:
                elements = soup.select(selector)
                if elements:
                    print(f"   - {name}: {len(elements)} found")
                    if len(elements) > 0 and len(elements) < 20:
                        for i, elem in enumerate(elements[:3]):
                            text = elem.get_text().strip()[:60]
                            print(f"     [{i+1}] {text}...")

            # Save to database
            print("\n5. Saving to database...")
            db = DatabaseManager()
            page = db.save_scraped_page(
                url="https://boilerroom.tv",
                title=soup.title.string if soup.title else "Boiler Room",
                content=soup.get_text()[:1000],  # First 1000 chars
                html=str(soup)[:5000],  # First 5000 chars of HTML
                scraper_type="dynamic",
                metadata={
                    "links_found": len(links),
                    "videos_found": len(videos),
                    "has_nextjs": next_data is not None,
                    "potential_apis": len(unique_apis)
                }
            )
            print(f"   - Saved to database with ID: {page.id}")

            print("\n" + "="*60)
            print("✓ Test complete!")

        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_boilerroom()
