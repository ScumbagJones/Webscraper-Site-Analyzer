"""
Intelligent Site Mapper
Crawls multiple pages and infers site structure from content types

This goes beyond article-centric thinking to understand:
- E-commerce catalogs (products → categories → checkout)
- Music platforms (albums → artists → playlists)
- Documentation sites (guides → API reference → tutorials)
- Portfolios (projects → case studies → about)
- And ANY other site structure
"""

import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
from typing import Set, List, Dict
from tqdm import tqdm
from colorama import Fore, init
import pandas as pd
from collections import defaultdict, Counter
import sys
import os

# Add parent directory to path to import universal_content_detector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from universal_content_detector import UniversalContentDetector, ContentType

init(autoreset=True)


class IntelligentSiteMapper:
    """
    Maps entire site structure by understanding content types

    Instead of just "crawling pages", this:
    1. Detects what type of content each page has
    2. Understands relationships between pages
    3. Infers site structure (catalog → product, blog → article, etc.)
    4. Cross-references with API calls to understand data flow
    5. Generates intelligent site map with content hierarchy
    """

    def __init__(
        self,
        max_pages: int = 50,
        max_depth: int = 3
    ):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.visited: Set[str] = set()
        self.queue: List[Dict] = []
        self.pages: List[Dict] = []
        self.base_url = None
        self.api_calls: List[Dict] = []

    async def map_site(self, start_url: str) -> Dict:
        """
        Map entire site structure

        Returns comprehensive site map with:
        - Content type distribution
        - Page hierarchy
        - Navigation patterns
        - API endpoints discovered
        - Inferred site architecture
        """
        print(f"\n{Fore.MAGENTA}{'='*70}")
        print(f"{Fore.MAGENTA}  🗺️  INTELLIGENT SITE MAPPER")
        print(f"{Fore.MAGENTA}{'='*70}\n")
        print(f"{Fore.CYAN}Target: {start_url}")
        print(f"{Fore.CYAN}Max pages: {self.max_pages}")
        print(f"{Fore.CYAN}Max depth: {self.max_depth}\n")

        parsed = urlparse(start_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Initialize
        self.queue.append({'url': start_url, 'depth': 0, 'parent': None})

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Track API calls
            async def handle_response(response):
                url = response.url
                content_type = response.headers.get('content-type', '')

                # Track API responses
                if any(x in content_type for x in ['json', 'application/json']):
                    self.api_calls.append({
                        'url': url,
                        'method': response.request.method,
                        'status': response.status,
                        'from_page': page.url
                    })

            page.on('response', handle_response)

            # Crawl with progress bar
            with tqdm(
                total=self.max_pages,
                desc=f"{Fore.GREEN}Mapping site",
                ncols=70
            ) as pbar:
                while self.queue and len(self.pages) < self.max_pages:
                    item = self.queue.pop(0)
                    url = item['url']
                    depth = item['depth']
                    parent = item['parent']

                    # Skip if visited or too deep
                    if url in self.visited or depth > self.max_depth:
                        continue

                    self.visited.add(url)

                    # Analyze page
                    page_data = await self._analyze_page(page, url, depth, parent)

                    if page_data:
                        self.pages.append(page_data)
                        pbar.update(1)

                        # Add discovered links (intelligent filtering)
                        if depth < self.max_depth and 'links' in page_data:
                            relevant_links = self._filter_relevant_links(
                                page_data['links'],
                                page_data['content_type']
                            )

                            for link in relevant_links:
                                if link not in self.visited and \
                                   not any(q['url'] == link for q in self.queue):
                                    self.queue.append({
                                        'url': link,
                                        'depth': depth + 1,
                                        'parent': url
                                    })

            await browser.close()

        print(f"\n{Fore.GREEN}✅ Mapping complete: {len(self.pages)} pages analyzed\n")

        # Generate intelligent site map
        return self._generate_intelligent_map()

    async def _analyze_page(self, page, url: str, depth: int, parent: str) -> Dict:
        """
        Analyze page with universal content detection
        """
        print(f"{Fore.CYAN}  📄 [{depth}] {url[:60]}...")

        try:
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            if not response or response.status >= 400:
                return None

            # Universal content detection
            detector = UniversalContentDetector(page)
            content_analysis = await detector.detect_content_type()

            # Extract links
            links = await self._extract_links(page, url)

            # Page metrics
            metrics = await page.evaluate("""() => {
                return {
                    title: document.title,
                    wordCount: document.body.innerText.split(/\\s+/).length,
                    imageCount: document.querySelectorAll('img').length,
                    linkCount: document.querySelectorAll('a').length,
                    hasVideo: !!document.querySelector('video'),
                    hasAudio: !!document.querySelector('audio'),
                };
            }""")

            return {
                'url': url,
                'depth': depth,
                'parent': parent,
                'title': metrics['title'],
                'content_type': content_analysis['primary_type'].value,
                'content_confidence': content_analysis['confidence'],
                'all_content_types': [
                    {
                        'type': score.type.value,
                        'score': score.score,
                        'confidence': score.confidence
                    }
                    for score in content_analysis['all_types'][:5]
                ],
                'is_multi_type': content_analysis['is_multi_type'],
                'extracted_content': content_analysis['extracted_content'],
                'metrics': metrics,
                'links': links,
                'api_calls_on_load': len([
                    call for call in self.api_calls
                    if call['from_page'] == url
                ])
            }

        except Exception as e:
            print(f"{Fore.RED}  ❌ Error: {str(e)[:50]}")
            return None

    async def _extract_links(self, page, current_url: str) -> List[str]:
        """Extract internal links"""
        links = await page.evaluate("""(baseUrl) => {
            const links = new Set();
            const origin = new URL(baseUrl).origin;

            document.querySelectorAll('a[href]').forEach(a => {
                try {
                    const url = new URL(a.href, baseUrl);
                    if (url.origin === origin) {
                        url.hash = '';
                        links.add(url.href);
                    }
                } catch (e) {}
            });

            return Array.from(links);
        }""", current_url)

        return links

    def _filter_relevant_links(self, links: List[str], content_type: str) -> List[str]:
        """
        Intelligently filter links based on current page content type

        E.g., if on product listing page, prioritize product detail pages
        If on artist page, prioritize album pages
        """
        # Limit to prevent queue explosion
        MAX_LINKS = 20

        # Filter patterns based on content type
        if content_type == 'productListing':
            # Prioritize product pages
            patterns = ['/product/', '/item/', '/p/']
        elif content_type == 'musicAlbum':
            # Prioritize album and artist pages
            patterns = ['/album/', '/release/', '/artist/', '/music/']
        elif content_type == 'blogPost':
            # Prioritize other blog posts
            patterns = ['/blog/', '/post/', '/article/', '/20']  # 20 for dates like 2024
        elif content_type == 'documentation':
            # Prioritize doc pages
            patterns = ['/docs/', '/api/', '/guide/', '/tutorial/']
        elif content_type == 'portfolio':
            # Prioritize project pages
            patterns = ['/project/', '/work/', '/case-study/']
        elif content_type == 'videoGallery':
            # Prioritize video pages
            patterns = ['/video/', '/watch/', '/v/']
        else:
            # Generic - take everything
            return links[:MAX_LINKS]

        # Filter links matching patterns
        relevant = [
            link for link in links
            if any(pattern in link.lower() for pattern in patterns)
        ]

        # If too few, add some non-matching links
        if len(relevant) < 5:
            non_relevant = [link for link in links if link not in relevant]
            relevant.extend(non_relevant[:MAX_LINKS - len(relevant)])

        return relevant[:MAX_LINKS]

    def _generate_intelligent_map(self) -> Dict:
        """
        Generate intelligent site map with content hierarchy
        """
        # Content type distribution
        content_types = Counter(page['content_type'] for page in self.pages)

        # Depth distribution
        depth_distribution = defaultdict(list)
        for page in self.pages:
            depth_distribution[page['depth']].append({
                'url': page['url'],
                'type': page['content_type'],
                'title': page['title']
            })

        # Identify site architecture pattern
        architecture = self._infer_architecture(content_types, depth_distribution)

        # Content hierarchy (parent-child relationships)
        hierarchy = self._build_content_hierarchy()

        # API endpoints discovered
        api_summary = self._summarize_api_calls()

        # Page types by confidence
        high_confidence = [
            p for p in self.pages
            if p['content_confidence'] == 'high'
        ]
        medium_confidence = [
            p for p in self.pages
            if p['content_confidence'] == 'medium'
        ]
        low_confidence = [
            p for p in self.pages
            if p['content_confidence'] == 'low'
        ]

        return {
            'base_url': self.base_url,
            'total_pages': len(self.pages),
            'max_depth_reached': max((p['depth'] for p in self.pages), default=0),

            # Content analysis
            'content_type_distribution': dict(content_types),
            'depth_distribution': dict(depth_distribution),
            'architecture_pattern': architecture,

            # Confidence breakdown
            'confidence_breakdown': {
                'high': len(high_confidence),
                'medium': len(medium_confidence),
                'low': len(low_confidence)
            },

            # Content hierarchy
            'content_hierarchy': hierarchy,

            # API discovery
            'api_summary': api_summary,

            # All pages
            'pages': self.pages,

            # Key insights
            'insights': self._generate_insights(content_types, architecture)
        }

    def _infer_architecture(self, content_types: Counter, depth_dist: Dict) -> Dict:
        """
        Infer site architecture pattern from content types

        Examples:
        - E-commerce: Landing → Product Listing → Product → Checkout
        - Music: Landing → Artist → Album → Tracks
        - Blog: Homepage → Category → Article
        - Documentation: Home → Section → Guide → API Reference
        """
        primary_type = content_types.most_common(1)[0][0] if content_types else 'unknown'

        patterns = {
            'productListing': {
                'pattern': 'E-commerce Catalog',
                'structure': 'Homepage → Category → Product → Checkout',
                'depth_0': 'Storefront/Collections',
                'depth_1': 'Product Categories',
                'depth_2': 'Individual Products',
                'depth_3': 'Product Details/Reviews'
            },
            'musicAlbum': {
                'pattern': 'Music Platform',
                'structure': 'Homepage → Artists/Albums → Tracks/Details',
                'depth_0': 'Music Discovery',
                'depth_1': 'Artist/Album Listings',
                'depth_2': 'Album/Track Details',
                'depth_3': 'Extended Info'
            },
            'blogPost': {
                'pattern': 'Editorial/Blog',
                'structure': 'Homepage → Category → Article',
                'depth_0': 'Blog Homepage',
                'depth_1': 'Categories/Tags',
                'depth_2': 'Individual Articles',
                'depth_3': 'Related Articles'
            },
            'documentation': {
                'pattern': 'Documentation Site',
                'structure': 'Docs Home → Section → Guide → Reference',
                'depth_0': 'Documentation Hub',
                'depth_1': 'Major Sections',
                'depth_2': 'Guides/Tutorials',
                'depth_3': 'API Reference/Examples'
            },
            'portfolio': {
                'pattern': 'Portfolio Site',
                'structure': 'Homepage → Projects → Case Studies',
                'depth_0': 'Portfolio Homepage',
                'depth_1': 'Project Listings',
                'depth_2': 'Project Details',
                'depth_3': 'About/Contact'
            },
            'pricing': {
                'pattern': 'SaaS Marketing',
                'structure': 'Landing → Features → Pricing → Signup',
                'depth_0': 'Marketing Landing',
                'depth_1': 'Feature Pages',
                'depth_2': 'Pricing Details',
                'depth_3': 'Signup/Trial'
            }
        }

        return patterns.get(primary_type, {
            'pattern': 'Generic Website',
            'structure': 'Undetermined',
            'depth_0': 'Homepage',
            'depth_1': 'Second-level pages',
            'depth_2': 'Third-level pages',
            'depth_3': 'Deep pages'
        })

    def _build_content_hierarchy(self) -> Dict:
        """
        Build parent-child content relationships

        Shows how different content types relate:
        - Product Listings contain Products
        - Artist pages link to Albums
        - Category pages link to Blog Posts
        """
        hierarchy = defaultdict(lambda: {'children': Counter(), 'examples': []})

        for page in self.pages:
            if page['parent']:
                # Find parent page
                parent_pages = [p for p in self.pages if p['url'] == page['parent']]

                if parent_pages:
                    parent = parent_pages[0]
                    parent_type = parent['content_type']
                    child_type = page['content_type']

                    hierarchy[parent_type]['children'][child_type] += 1

                    # Store example
                    if len(hierarchy[parent_type]['examples']) < 3:
                        hierarchy[parent_type]['examples'].append({
                            'parent_url': parent['url'],
                            'parent_title': parent['title'],
                            'child_url': page['url'],
                            'child_title': page['title']
                        })

        # Convert to regular dict
        return {
            parent_type: {
                'children': dict(data['children']),
                'examples': data['examples']
            }
            for parent_type, data in hierarchy.items()
        }

    def _summarize_api_calls(self) -> Dict:
        """
        Summarize API calls discovered during crawl

        Groups by:
        - Endpoint patterns
        - Methods used
        - Which pages trigger which APIs
        """
        if not self.api_calls:
            return {'total': 0, 'endpoints': {}}

        # Group by endpoint pattern
        endpoints = defaultdict(lambda: {
            'calls': 0,
            'methods': Counter(),
            'triggered_by_pages': set()
        })

        for call in self.api_calls:
            url = call['url']
            # Extract pattern (e.g., /api/products/123 → /api/products/:id)
            pattern = self._extract_api_pattern(url)

            endpoints[pattern]['calls'] += 1
            endpoints[pattern]['methods'][call['method']] += 1
            endpoints[pattern]['triggered_by_pages'].add(call['from_page'])

        # Convert to serializable format
        summary = {
            'total': len(self.api_calls),
            'unique_endpoints': len(endpoints),
            'endpoints': {
                pattern: {
                    'calls': data['calls'],
                    'methods': dict(data['methods']),
                    'triggered_by': list(data['triggered_by_pages'])[:5]
                }
                for pattern, data in list(endpoints.items())[:20]
            }
        }

        return summary

    def _extract_api_pattern(self, url: str) -> str:
        """
        Extract API pattern from URL

        /api/products/123 → /api/products/:id
        /api/users/abc123/posts → /api/users/:id/posts
        """
        import re

        # Remove query params
        url = url.split('?')[0]

        # Replace UUIDs/IDs with :id
        url = re.sub(r'/[a-f0-9]{8,}', '/:id', url)
        url = re.sub(r'/\d+', '/:id', url)

        return url

    def _generate_insights(self, content_types: Counter, architecture: Dict) -> List[str]:
        """
        Generate human-readable insights about the site
        """
        insights = []

        total_pages = sum(content_types.values())
        primary_type = content_types.most_common(1)[0] if content_types else ('unknown', 0)

        # Primary content type
        insights.append(
            f"Primary content type: {primary_type[0]} "
            f"({primary_type[1]}/{total_pages} pages, "
            f"{primary_type[1]/total_pages*100:.0f}%)"
        )

        # Architecture pattern
        if architecture.get('pattern'):
            insights.append(f"Site architecture: {architecture['pattern']}")

        # Multi-type pages
        multi_type_pages = [p for p in self.pages if p.get('is_multi_type')]
        if multi_type_pages:
            insights.append(
                f"{len(multi_type_pages)} pages have multiple content types "
                f"(mixed content)"
            )

        # API-driven
        if self.api_calls:
            insights.append(
                f"API-driven site: {len(self.api_calls)} API calls detected "
                f"across {len(set(c['from_page'] for c in self.api_calls))} pages"
            )

        # Content depth
        max_depth = max((p['depth'] for p in self.pages), default=0)
        if max_depth >= 3:
            insights.append(
                f"Deep site structure: content goes {max_depth} levels deep"
            )

        return insights


# Demo
async def demo():
    """
    Demonstrate intelligent site mapping on different site types
    """
    # Test different site architectures
    test_sites = [
        'https://www.theringer.com',  # Editorial
        # 'https://www.ninaprotocol.com',  # Music platform
        # 'https://stripe.com/docs',  # Documentation
    ]

    for url in test_sites:
        mapper = IntelligentSiteMapper(max_pages=20, max_depth=2)
        site_map = await mapper.map_site(url)

        # Display results
        print(f"\n{Fore.YELLOW}{'='*70}")
        print(f"{Fore.YELLOW}SITE MAP SUMMARY")
        print(f"{Fore.YELLOW}{'='*70}\n")

        print(f"{Fore.CYAN}Base URL: {site_map['base_url']}")
        print(f"{Fore.CYAN}Total Pages: {site_map['total_pages']}")
        print(f"{Fore.CYAN}Max Depth: {site_map['max_depth_reached']}\n")

        print(f"{Fore.GREEN}Content Type Distribution:")
        for content_type, count in site_map['content_type_distribution'].items():
            pct = count / site_map['total_pages'] * 100
            print(f"  {content_type}: {count} ({pct:.0f}%)")

        print(f"\n{Fore.GREEN}Architecture Pattern:")
        arch = site_map['architecture_pattern']
        print(f"  Pattern: {arch.get('pattern', 'Unknown')}")
        print(f"  Structure: {arch.get('structure', 'Unknown')}")

        print(f"\n{Fore.GREEN}Confidence Breakdown:")
        conf = site_map['confidence_breakdown']
        print(f"  High: {conf['high']} pages")
        print(f"  Medium: {conf['medium']} pages")
        print(f"  Low: {conf['low']} pages")

        if site_map['api_summary']['total'] > 0:
            print(f"\n{Fore.GREEN}API Discovery:")
            print(f"  Total API calls: {site_map['api_summary']['total']}")
            print(f"  Unique endpoints: {site_map['api_summary']['unique_endpoints']}")

        print(f"\n{Fore.MAGENTA}Key Insights:")
        for insight in site_map['insights']:
            print(f"  • {insight}")

        # Export to Parquet
        df = pd.DataFrame(site_map['pages'])
        filename = f"{urlparse(url).netloc.replace('.', '_')}_sitemap.parquet"
        df.to_parquet(filename, compression='snappy')
        print(f"\n{Fore.GREEN}✅ Exported to {filename}")


if __name__ == '__main__':
    asyncio.run(demo())
