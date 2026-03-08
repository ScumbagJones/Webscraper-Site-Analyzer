"""
Metadata MRI Scanner - Graceful Degradation for Bot-Protected Sites

When full browser access fails (403, Cloudflare, paywall), extract what we CAN see:
- HTML meta tags (Open Graph, Twitter Cards, Schema.org)
- External stylesheet references
- CDN/framework signatures
- Basic structural indicators

Philosophy: "Show me the bones, not the flesh"
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger('metadata_mri')

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Optional Scrapling integration (Phase 3) — checked lazily on first use
SCRAPLING_FETCHER_AVAILABLE: Optional[bool] = None  # None = unchecked


class MetadataMRI:
    """
    Metadata-only extraction when full access is blocked
    """

    def __init__(self, url: str, html: Optional[str] = None):
        """
        Args:
            url: Target URL
            html: Optional HTML (if already fetched). If None, will fetch with requests.
        """
        self.url = url
        self.html = html
        self.logger = logging.getLogger('metadata_mri')

    def scan(self) -> Dict:
        """
        Perform metadata MRI scan

        Returns:
            {
                'access_strategy': 'metadata_mri',
                'success': bool,
                'meta_tags': {...},
                'stylesheets': [...],
                'frameworks': [...],
                'cdn_providers': [...],
                'structural_hints': {...},
                'confidence': int,
                'limitations': [...]
            }
        """
        html = self.html
        success = True

        if not html:
            success, html = self._fetch_html()

        if not success or not html:
            return self._failed_scan(html or 'No HTML retrieved')

        if not BS4_AVAILABLE:
            return self._failed_scan('BeautifulSoup not available')

        try:
            soup = BeautifulSoup(html, 'html.parser')
        except Exception as e:
            return self._failed_scan(f'HTML parse error: {e}')

        meta = self._extract_meta_tags(soup)
        stylesheets = self._extract_stylesheets(soup)
        frameworks = self._detect_frameworks(soup, stylesheets)
        cdn_providers = self._detect_cdn(soup, stylesheets)
        structural_hints = self._extract_structural_hints(soup)
        css_vars = self._extract_css_variables(soup)
        confidence = self._calculate_confidence(meta, stylesheets, frameworks, structural_hints)

        return {
            'access_strategy': 'metadata_mri',
            'success': True,
            'meta_tags': meta,
            'stylesheets': stylesheets,
            'frameworks': frameworks,
            'cdn_providers': cdn_providers,
            'structural_hints': structural_hints,
            'css_variables': css_vars,
            'confidence': confidence,
            'limitations': self._list_limitations(),
            'pattern': f"MRI scan: {len(meta)} meta fields, {len(frameworks)} frameworks detected",
        }

    def _fetch_html(self) -> Tuple[bool, str]:
        """
        Fetch HTML with best available transport (no JS execution).

        Cascade:
          1. Scrapling Fetcher — browser-grade TLS fingerprint, stealthy headers
          2. requests.get — basic Python HTTP (easily fingerprinted)

        Returns:
            (success: bool, html_or_error: str)
        """
        # Phase 1: try Scrapling Fetcher (TLS fingerprint impersonation)
        global SCRAPLING_FETCHER_AVAILABLE
        if SCRAPLING_FETCHER_AVAILABLE is None:
            try:
                from scrapling.fetchers import Fetcher as _SF  # noqa: F401
                SCRAPLING_FETCHER_AVAILABLE = True
            except Exception:
                SCRAPLING_FETCHER_AVAILABLE = False
        if SCRAPLING_FETCHER_AVAILABLE:
            try:
                from scrapling.fetchers import Fetcher as ScraplingFetcher
                fetcher = ScraplingFetcher(auto_match=False)
                page = fetcher.get(self.url, timeout=10000, stealthy_headers=True)
                status = getattr(page, 'status', 200)
                html = page.html if hasattr(page, 'html') else str(page)
                if status in (403, 401, 400):
                    self.logger.warning(f'Scrapling Fetcher got {status} for {self.url}, falling through to requests')
                elif status != 200:
                    self.logger.warning(f'Scrapling Fetcher got {status} for {self.url}')
                else:
                    self.logger.info(f'Scrapling Fetcher succeeded for {self.url}')
                    return True, html
            except Exception as e:
                self.logger.debug(f'Scrapling Fetcher failed: {e}')

        # Phase 2: basic requests fallback
        if not REQUESTS_AVAILABLE:
            return False, 'requests library not available'

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            response = requests.get(self.url, headers=headers, timeout=15, allow_redirects=True)
            if 200 <= response.status_code < 400:
                return True, response.text
            return False, f'HTTP {response.status_code}'
        except Exception as e:
            return False, str(e)

    def _failed_scan(self, error_msg: str) -> Dict:
        """Return failed scan result"""
        return {
            'access_strategy': 'metadata_mri',
            'success': False,
            'confidence': 0,
            'limitations': ['Complete access failure'],
            'error': error_msg,
            'pattern': f'MRI scan failed: {error_msg[:100]}',
        }

    def _extract_meta_tags(self, soup) -> Dict:
        """
        Extract valuable meta tags: Open Graph, Twitter Cards, Schema.org
        """
        meta_data = {}

        title_tag = soup.find('title')
        if title_tag:
            meta_data['title'] = title_tag.get_text(strip=True)

        og_tags = {}
        for tag in soup.find_all('meta', property=re.compile(r'^og:')):
            prop = tag.get('property', '')
            content = tag.get('content', '')
            if prop and content:
                key = prop.replace('og:', '')
                og_tags[key] = content
        if og_tags:
            meta_data['open_graph'] = og_tags
            for k in ('description', 'image', 'type', 'site_name'):
                if k in og_tags:
                    meta_data[k] = og_tags[k]

        twitter_tags = {}
        for tag in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
            name = tag.get('name', '')
            content = tag.get('content', '')
            if name and content:
                twitter_tags[name.replace('twitter:', '')] = content
        if twitter_tags:
            meta_data['twitter_card'] = twitter_tags

        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag and 'description' not in meta_data:
            meta_data['description'] = desc_tag.get('content', '')

        schema_tags = soup.find_all('script', type='application/ld+json')
        if schema_tags:
            meta_data['schema_org'] = len(schema_tags)

        return meta_data

    def _extract_stylesheets(self, soup) -> List[Dict]:
        """
        Extract external stylesheet references
        Reveals: design systems, CDNs, frameworks
        """
        stylesheets = []
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if not href:
                continue
            try:
                parsed = urlparse(href)
                domain = parsed.netloc
            except Exception:
                domain = ''
            stylesheet = {
                'href': href,
                'domain': domain,
                'is_cdn': self._is_cdn_domain(domain),
                'framework': self._detect_framework_from_url(href),
            }
            stylesheets.append(stylesheet)
        return stylesheets

    def _detect_frameworks(self, soup, stylesheets: List[Dict]) -> List[str]:
        """
        Detect frameworks from HTML markers
        """
        frameworks = []

        if soup.find(attrs={'data-reactroot': True}) or soup.find(attrs={'data-reactid': True}):
            frameworks.append('React')
        if soup.find(id='root') or soup.find(id='__next') or any('_next' in s.get('href', '') for s in stylesheets):
            if 'React' not in frameworks:
                frameworks.append('React')
            frameworks.append('Next.js')
        if soup.find(attrs={'data-v-': True}) or soup.find(id='app'):
            frameworks.append('Vue.js')
        if soup.find(attrs={'ng-app': True}) or soup.find(attrs={'ng-version': True}):
            frameworks.append('Angular')

        for s in stylesheets:
            fw = s.get('framework')
            if fw and fw not in frameworks:
                frameworks.append(fw)

        return list(dict.fromkeys(frameworks))  # deduplicate, preserve order

    def _detect_cdn(self, soup, stylesheets: List[Dict]) -> List[str]:
        """
        Detect CDN providers from external resources
        """
        cdn_providers = []
        cdn_map = {
            'cloudflare': 'Cloudflare',
            'fastly': 'Fastly',
            'akamai': 'Akamai',
            'amazonaws': 'AWS',
            's3': 'AWS',
        }

        for s in stylesheets:
            domain = s.get('domain', '').lower()
            for key, name in cdn_map.items():
                if key in domain and name not in cdn_providers:
                    cdn_providers.append(name)

        for script in soup.find_all('script', src=True):
            src = script.get('src', '').lower()
            for key, name in cdn_map.items():
                if key in src and name not in cdn_providers:
                    cdn_providers.append(name)

        return cdn_providers

    def _extract_structural_hints(self, soup) -> Dict:
        """
        Extract structural hints from HTML skeleton
        """
        hints = {
            'has_header': bool(soup.find('header')),
            'has_nav': bool(soup.find('nav')),
            'has_main': bool(soup.find('main')),
            'has_footer': bool(soup.find('footer')),
            'has_article': bool(soup.find('article')),
            'semantic_html': False,
        }
        hints['semantic_html'] = any([
            hints['has_header'], hints['has_nav'],
            hints['has_main'], hints['has_footer'],
        ])

        all_classes = []
        for tag in soup.find_all(True):
            all_classes.extend(tag.get('class', []))

        hints['uses_flexbox_grid'] = any(c in ('flex', 'grid') for c in all_classes)
        hints['uses_container_layout'] = any('container' in c or 'row' in c or 'col-' in c for c in all_classes)
        hints['class_pattern'] = self._detect_class_pattern(all_classes)

        return hints

    def _detect_class_pattern(self, classes: List[str]) -> str:
        """
        Detect design system naming convention
        """
        bem_count = sum(1 for c in classes if re.match(r'^[\w-]+__[\w-]+(?:--[\w-]+)?$', c))
        utility_keywords = ('flex', 'grid', 'text-', 'bg-', 'p-', 'm-', 'w-', 'h-', 'border', 'rounded')
        utility_count = sum(
            1 for c in classes
            if any(c.startswith(kw) for kw in utility_keywords)
        )
        if bem_count >= 5:
            return 'BEM (Block Element Modifier)'
        if utility_count >= 10:
            return 'Utility-first (Tailwind-style)'
        smacss_prefixes = ('l-', 'is-', 'has-', 'js-', 'u-')
        if any(c.startswith(p) for c in classes for p in smacss_prefixes):
            return 'SMACSS/OOCSS (Prefixed)'
        return 'Custom'

    def _extract_css_variables(self, soup) -> Dict:
        """
        Extract CSS custom properties (design tokens) from inline <style> blocks.
        """
        style_tags = soup.find_all('style')
        combined_css = '\n'.join(tag.get_text() for tag in style_tags if tag.get_text())

        var_pattern = re.compile(r'(--[\w-]+)\s*:\s*([^;}\n]+)')
        all_vars = var_pattern.findall(combined_css)

        hex_pattern = re.compile(r'^#([0-9a-fA-F]{3,8})$')
        rgb_pattern = re.compile(r'^rgba?\(\s*[\d.,\s%]+\)$')
        hsl_pattern = re.compile(r'^hsla?\(\s*[\d.,\s%]+\)$')
        size_pattern = re.compile(r'^[\d.]+(?:px|rem|em)$')

        colors, fonts, font_sizes, spacing, shadows, breakpoints = [], [], [], [], [], []

        for name, value in all_vars:
            value = value.strip()
            if hex_pattern.match(value) or rgb_pattern.match(value) or hsl_pattern.match(value):
                colors.append({'name': name, 'value': value})
            elif 'font-size' in name and size_pattern.match(value):
                font_sizes.append({'name': name, 'value': value})
            elif any(k in name for k in ('spacing', 'gap', 'padding', 'margin')) and size_pattern.match(value):
                spacing.append({'name': name, 'value': value})
            elif 'shadow' in name:
                shadows.append({'name': name, 'value': value})

        # Detect breakpoints from @media queries
        for m in re.finditer(r'@media[^{]+\((?:max|min)-width:\s*(\d+)px\)', combined_css):
            breakpoints.append(int(m.group(1)))

        token_system = None
        if '--newspack' in combined_css:
            token_system = 'Newspack'
        elif '--wp--preset' in combined_css:
            token_system = 'WordPress'
        elif '--tw-' in combined_css:
            token_system = 'Tailwind'

        return {
            'colors': colors,
            'fonts': fonts,
            'font_sizes': font_sizes,
            'spacing': spacing,
            'shadows': shadows,
            'breakpoints': sorted(set(breakpoints)),
            'token_system': token_system,
        }

    def _is_cdn_domain(self, domain: str) -> bool:
        """Check if domain is a known CDN"""
        cdn_domains = ('cloudflare', 'fastly', 'akamai', 'amazonaws', 'cloudfront', 'jsdelivr', 'unpkg', 'cdnjs')
        return any(cdn in domain.lower() for cdn in cdn_domains)

    def _detect_framework_from_url(self, url: str) -> Optional[str]:
        """Detect framework from stylesheet URL"""
        url_lower = url.lower()
        frameworks = {
            'tailwind': 'Tailwind CSS',
            'bootstrap': 'Bootstrap',
            'bulma': 'Bulma',
            'foundation': 'Foundation',
            'materialize': 'Materialize',
        }
        for key, name in frameworks.items():
            if key in url_lower:
                return name
        return None

    def _calculate_confidence(self, meta: Dict, stylesheets: List, frameworks: List, hints: Dict) -> int:
        """
        Calculate confidence score based on data extracted
        """
        score = 0
        if meta.get('title'):
            score += 10
        if meta.get('description'):
            score += 10
        if meta.get('image'):
            score += 10
        if meta.get('schema_org'):
            score += 15
        if any(s.get('is_cdn') for s in stylesheets):
            score += 20
        if frameworks:
            score += 15
        if hints.get('semantic_html'):
            score += 20
        return min(100, score)

    def _list_limitations(self) -> List[str]:
        """
        List what we CAN'T see in MRI mode
        """
        return [
            'No JavaScript execution — dynamic content invisible',
            'No computed styles — only inline/stylesheet tokens',
            'No network requests — API patterns unavailable',
            'No interaction states — hover/focus not captured',
            'No screenshots — visual output not available',
        ]


if __name__ == '__main__':
    print('=' * 70)
    print(' 🔬 METADATA MRI SCANNER TEST')
    print('=' * 70)
    url = 'https://stripe.com/docs'
    print(f'\n Testing URL: {url}')
    mri = MetadataMRI(url)
    result = mri.scan()
    if result.get('success'):
        print('\n✅ MRI SCAN SUCCESSFUL')
        print(f"   Confidence: {result.get('confidence')}%")
        print(f"   Meta fields: {len(result.get('meta_tags', {}))}")
        print(f"   Frameworks: {result.get('frameworks', [])}")
    else:
        print(f"\n❌ SCAN FAILED: {result.get('error', 'unknown')}")
