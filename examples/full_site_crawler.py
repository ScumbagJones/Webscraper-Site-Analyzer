"""
Full Site Crawler - Python Version
Crawls multiple pages (not just homepage) with intelligent limits
Inspired by Screaming Frog and siteCrawler.js
"""

import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
from typing import Set, List, Dict
from tqdm import tqdm
from colorama import Fore, init
import pandas as pd
from collections import defaultdict
import jmespath
from pydantic import BaseModel, HttpUrl
from datetime import datetime

init(autoreset=True)


class PageAnalysis(BaseModel):
    """Validated page analysis result"""
    url: HttpUrl
    depth: int
    title: str = ""
    h1_count: int = 0
    word_count: int = 0
    image_count: int = 0
    link_count: int = 0
    content_type: str = "unknown"
    has_video: bool = False
    has_audio: bool = False
    discovered_links: int = 0
    error: str = None


class SiteCrawler:
    """
    Full site crawler with intelligent limits

    Features:
    - Respects robots.txt (conceptually)
    - Stays on same domain
    - Smart depth and page limits
    - Progress tracking
    - Parquet export
    """

    def __init__(
        self,
        max_pages: int = 50,
        max_depth: int = 3,
        same_origin_only: bool = True
    ):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.same_origin_only = same_origin_only
        self.visited: Set[str] = set()
        self.queue: List[Dict] = []
        self.results: List[Dict] = []
        self.base_url = None

    async def extract_links(self, page, current_url: str) -> List[str]:
        """
        Extract all internal links from page
        """
        links = await page.evaluate("""(baseUrl) => {
            const links = new Set();
            const origin = new URL(baseUrl).origin;

            document.querySelectorAll('a[href]').forEach(a => {
                try {
                    const url = new URL(a.href, baseUrl);

                    // Only same-origin links
                    if (url.origin === origin) {
                        // Normalize URL (remove hash)
                        url.hash = '';
                        links.add(url.href);
                    }
                } catch (e) {
                    // Invalid URL, skip
                }
            });

            return Array.from(links);
        }""", current_url)

        return links

    async def analyze_page(self, page, url: str, depth: int) -> Dict:
        """
        Analyze a single page
        """
        print(f"{Fore.CYAN}  📄 Analyzing [depth {depth}]: {url}")

        try:
            response = await page.goto(
                url,
                wait_until='networkidle',
                timeout=30000
            )

            if not response:
                return {'url': url, 'depth': depth, 'error': 'No response'}

            # Extract page data
            page_data = await page.evaluate("""() => {
                return {
                    title: document.title,
                    h1: Array.from(document.querySelectorAll('h1')).map(h => h.innerText.trim()),
                    links: document.querySelectorAll('a').length,
                    images: document.querySelectorAll('img').length,
                    wordCount: document.body.innerText.split(/\\s+/).length,
                    hasVideo: !!document.querySelector('video'),
                    hasAudio: !!document.querySelector('audio'),
                    contentType: (() => {
                        // Detect content type
                        if (document.querySelector('article')) return 'article';
                        if (document.querySelector('[class*="product"]')) return 'product';
                        if (document.querySelector('[class*="blog"]')) return 'blog';
                        if (document.querySelector('nav')) return 'navigation';
                        return 'unknown';
                    })()
                };
            }""")

            # Extract links for further crawling
            links = await self.extract_links(page, url)

            return {
                'url': url,
                'depth': depth,
                'title': page_data['title'],
                'h1_count': len(page_data['h1']),
                'word_count': page_data['wordCount'],
                'image_count': page_data['images'],
                'link_count': page_data['links'],
                'content_type': page_data['contentType'],
                'has_video': page_data['hasVideo'],
                'has_audio': page_data['hasAudio'],
                'discovered_links': len(links),
                'links': links
            }

        except Exception as e:
            print(f"{Fore.RED}  ❌ Failed: {str(e)[:50]}")
            return {
                'url': url,
                'depth': depth,
                'error': str(e)
            }

    async def crawl(self, start_url: str) -> Dict:
        """
        Crawl entire site
        """
        print(f"\n{Fore.MAGENTA}{'='*70}")
        print(f"{Fore.MAGENTA}  🕷️  FULL SITE CRAWLER")
        print(f"{Fore.MAGENTA}{'='*70}\n")
        print(f"{Fore.CYAN}Starting: {start_url}")
        print(f"{Fore.CYAN}Max pages: {self.max_pages}")
        print(f"{Fore.CYAN}Max depth: {self.max_depth}\n")

        parsed = urlparse(start_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Initialize queue
        self.queue.append({'url': start_url, 'depth': 0})

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.newPage()

            with tqdm(
                total=self.max_pages,
                desc=f"{Fore.GREEN}Crawling",
                ncols=70
            ) as pbar:
                while self.queue and len(self.results) < self.max_pages:
                    item = self.queue.pop(0)
                    url = item['url']
                    depth = item['depth']

                    # Skip if visited
                    if url in self.visited:
                        continue

                    # Skip if too deep
                    if depth > self.max_depth:
                        continue

                    # Mark as visited
                    self.visited.add(url)

                    # Analyze page
                    page_data = await self.analyze_page(page, url, depth)
                    self.results.append(page_data)
                    pbar.update(1)

                    # Add discovered links to queue
                    if depth < self.max_depth and 'links' in page_data:
                        for link in page_data['links']:
                            if link not in self.visited and \
                               not any(q['url'] == link for q in self.queue):
                                self.queue.append({
                                    'url': link,
                                    'depth': depth + 1
                                })

                    print(f"{Fore.GREEN}  ✅ Progress: {len(self.results)}/{self.max_pages}")

            await browser.close()

        print(f"\n{Fore.GREEN}✅ Crawl complete: {len(self.results)} pages analyzed\n")

        return self.generate_site_map()

    def generate_site_map(self) -> Dict:
        """
        Generate site map from crawl results
        """
        site_map = {
            'base_url': self.base_url,
            'total_pages': len(self.results),
            'max_depth': max((r.get('depth', 0) for r in self.results), default=0),
            'content_types': defaultdict(int),
            'pages_by_depth': defaultdict(list),
            'structure': []
        }

        # Count content types
        for page in self.results:
            content_type = page.get('content_type', 'unknown')
            site_map['content_types'][content_type] += 1

        # Group by depth
        for page in self.results:
            depth = page.get('depth', 0)
            site_map['pages_by_depth'][depth].append({
                'url': page['url'],
                'title': page.get('title', ''),
                'type': page.get('content_type', 'unknown')
            })

        # Create structure
        site_map['structure'] = [
            {
                'url': page['url'],
                'title': page.get('title', ''),
                'depth': page.get('depth', 0),
                'type': page.get('content_type', 'unknown'),
                'word_count': page.get('word_count', 0),
                'links': page.get('link_count', 0),
                'images': page.get('image_count', 0),
                'has_video': page.get('has_video', False),
                'has_audio': page.get('has_audio', False),
                'error': page.get('error')
            }
            for page in self.results
        ]

        # Convert to regular dict
        site_map['content_types'] = dict(site_map['content_types'])
        site_map['pages_by_depth'] = dict(site_map['pages_by_depth'])

        return site_map

    def export_to_parquet(self, filename: str = 'site_crawl_results.parquet'):
        """
        Export results to Parquet
        """
        df = pd.DataFrame(self.results)

        # Remove 'links' column (too large)
        if 'links' in df.columns:
            df = df.drop('links', axis=1)

        df.to_parquet(filename, compression='snappy')
        print(f"{Fore.GREEN}✅ Exported to {filename}")

        return filename


class TechnicalSEOAnalyzer:
    """
    Technical SEO analysis inspired by Screaming Frog
    """

    async def analyze(self, url: str) -> Dict:
        """
        Run technical SEO analysis
        """
        print(f"\n{Fore.MAGENTA}{'='*70}")
        print(f"{Fore.MAGENTA}  🔍 TECHNICAL SEO ANALYSIS")
        print(f"{Fore.MAGENTA}{'='*70}\n")
        print(f"{Fore.CYAN}Analyzing: {url}\n")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.newPage()

            # Track resources
            resources = []

            async def handle_response(response):
                resources.append({
                    'url': response.url,
                    'status': response.status,
                    'content_type': response.headers.get('content-type', ''),
                    'size': response.headers.get('content-length', 0)
                })

            page.on('response', handle_response)

            await page.goto(url, wait_until='networkidle', timeout=60000)

            # Analyze page
            analysis = await page.evaluate("""() => {
                const issues = [];

                // Meta tags
                const metaTitle = document.querySelector('title')?.innerText;
                const metaDescription = document.querySelector('meta[name="description"]')?.content;

                if (!metaTitle) issues.push({ type: 'error', message: 'Missing title tag' });
                if (metaTitle && metaTitle.length > 60) issues.push({ type: 'warning', message: 'Title too long (>60 chars)' });
                if (!metaDescription) issues.push({ type: 'warning', message: 'Missing meta description' });

                // Headings
                const h1s = document.querySelectorAll('h1');
                if (h1s.length === 0) issues.push({ type: 'error', message: 'No H1 tags found' });
                if (h1s.length > 1) issues.push({ type: 'warning', message: 'Multiple H1 tags found' });

                // Images
                const images = document.querySelectorAll('img');
                let imagesWithoutAlt = 0;
                images.forEach(img => {
                    if (!img.alt) imagesWithoutAlt++;
                });
                if (imagesWithoutAlt > 0) {
                    issues.push({ type: 'warning', message: `${imagesWithoutAlt} images missing alt text` });
                }

                // Links
                const links = document.querySelectorAll('a');
                let brokenLinks = 0;
                links.forEach(link => {
                    if (!link.href || link.href === '#') brokenLinks++;
                });
                if (brokenLinks > 0) {
                    issues.push({ type: 'warning', message: `${brokenLinks} empty or # links` });
                }

                // Mobile viewport
                const viewport = document.querySelector('meta[name="viewport"]');
                if (!viewport) {
                    issues.push({ type: 'error', message: 'Missing mobile viewport meta tag' });
                }

                // Frameworks
                const hasReact = !!(window.React || window.ReactDOM || document.querySelector('[data-reactroot]'));
                const hasVue = !!(window.Vue || document.querySelector('[data-v-]'));
                const hasAngular = !!(window.angular || document.querySelector('[ng-version]'));

                return {
                    meta: {
                        title: metaTitle,
                        titleLength: metaTitle?.length || 0,
                        description: metaDescription,
                        descriptionLength: metaDescription?.length || 0,
                        hasViewport: !!viewport
                    },
                    headings: {
                        h1Count: h1s.length,
                        h2Count: document.querySelectorAll('h2').length,
                        h3Count: document.querySelectorAll('h3').length
                    },
                    content: {
                        wordCount: document.body.innerText.split(/\\s+/).length,
                        imageCount: images.length,
                        imagesWithoutAlt: imagesWithoutAlt,
                        linkCount: links.length,
                        brokenLinks: brokenLinks
                    },
                    frameworks: {
                        react: hasReact,
                        vue: hasVue,
                        angular: hasAngular
                    },
                    issues: issues
                };
            }""")

            # Analyze resources
            js_files = [r for r in resources if 'javascript' in r['content_type']]
            css_files = [r for r in resources if 'css' in r['content_type']]
            image_files = [r for r in resources if 'image' in r['content_type']]

            analysis['resources'] = {
                'total': len(resources),
                'javascript': len(js_files),
                'css': len(css_files),
                'images': len(image_files),
                'errors': len([r for r in resources if r['status'] >= 400])
            }

            await browser.close()

        return analysis


# Demo usage
async def demo():
    """
    Demonstrate full site crawling
    """
    # Test site (change to your target)
    url = 'https://www.theringer.com'

    # Option 1: Full site crawl
    crawler = SiteCrawler(
        max_pages=20,  # Analyze 20 pages
        max_depth=2    # Go 2 levels deep
    )

    site_map = await crawler.crawl(url)

    # Display results
    print(f"\n{Fore.YELLOW}SITE MAP SUMMARY:")
    print(f"{Fore.CYAN}  Total pages: {site_map['total_pages']}")
    print(f"{Fore.CYAN}  Max depth: {site_map['max_depth']}")
    print(f"\n{Fore.YELLOW}Content Types:")
    for content_type, count in site_map['content_types'].items():
        print(f"{Fore.GREEN}  {content_type}: {count}")

    print(f"\n{Fore.YELLOW}Pages by Depth:")
    for depth, pages in site_map['pages_by_depth'].items():
        print(f"{Fore.CYAN}  Depth {depth}: {len(pages)} pages")

    # Export to Parquet
    crawler.export_to_parquet('theringer_crawl.parquet')

    # Option 2: Technical SEO analysis
    seo_analyzer = TechnicalSEOAnalyzer()
    seo_analysis = await seo_analyzer.analyze(url)

    print(f"\n{Fore.YELLOW}SEO ANALYSIS:")
    print(f"{Fore.CYAN}  Title: {seo_analysis['meta']['title']}")
    print(f"{Fore.CYAN}  H1 count: {seo_analysis['headings']['h1Count']}")
    print(f"{Fore.CYAN}  Word count: {seo_analysis['content']['wordCount']}")

    if seo_analysis['issues']:
        print(f"\n{Fore.YELLOW}Issues Found:")
        for issue in seo_analysis['issues']:
            color = Fore.RED if issue['type'] == 'error' else Fore.YELLOW
            print(f"{color}  [{issue['type']}] {issue['message']}")


if __name__ == '__main__':
    asyncio.run(demo())
