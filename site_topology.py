"""
Site Topology Analyzer — Information architecture from URL topology.

Answers "how is this site organized?" (sections, hierarchy, content distribution)
as opposed to site_architecture which answers "what is this built with?" (tech stack).

Works with any URL source: Cloudflare crawl, nav discovery, interactive discovery,
or a manually supplied list.  No browser required — pure URL analysis.
"""

import logging
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ── Content-type keywords for section classification ──────────────────
_CONTENT_TYPE_MAP = {
    'documentation': ['docs', 'documentation', 'guide', 'guides', 'reference',
                      'manual', 'handbook', 'tutorial', 'tutorials', 'learn',
                      'getting-started', 'quickstart', 'howto', 'how-to'],
    'blog':          ['blog', 'posts', 'articles', 'news', 'updates',
                      'changelog', 'journal', 'stories', 'editorial'],
    'product':       ['products', 'product', 'shop', 'store', 'pricing',
                      'plans', 'features', 'solutions', 'catalog', 'marketplace'],
    'developer':     ['api', 'developers', 'sdk', 'tools', 'integrations',
                      'webhooks', 'libraries', 'playground', 'console'],
    'corporate':     ['about', 'team', 'careers', 'company', 'press',
                      'investors', 'contact', 'partners', 'legal', 'privacy',
                      'terms', 'security'],
    'community':     ['community', 'forum', 'discussions', 'support', 'help',
                      'faq', 'feedback', 'discord', 'slack'],
    'media':         ['gallery', 'videos', 'podcasts', 'webinars', 'events',
                      'media', 'resources', 'downloads', 'assets'],
}


class SiteTopologyAnalyzer:
    """
    Analyze URL topology from a list of discovered URLs.

    Returns structured evidence about site sections, hierarchy depth,
    URL patterns, and content distribution — all from URLs alone.
    """

    def analyze(
        self,
        urls: List[str],
        base_url: str,
        url_source: str = 'nav_discovery',
    ) -> Dict:
        """
        Main entry point.  Accepts raw URLs, returns topology evidence.

        Args:
            urls: List of absolute or relative URLs
            base_url: The site's root URL (for resolving relative paths)
            url_source: 'cloudflare' | 'nav_discovery' | 'interactive'
        """
        logger.info("Analyzing site topology for %s (%d URLs)", base_url, len(urls))

        # Normalise to paths
        parsed_base = urlparse(base_url)
        base_host = parsed_base.hostname or ''
        paths = self._urls_to_paths(urls, base_host)

        if len(paths) < 3:
            return {
                'pattern': f'Too few URLs for topology ({len(paths)} found)',
                'confidence': 10,
                'total_pages': len(paths),
                'url_source': url_source,
            }

        sections = self._extract_sections(paths)
        hierarchy = self._analyze_hierarchy(paths)
        url_patterns = self._detect_url_templates(paths)
        content_dist = self._classify_content_types(sections)
        confidence = self._calculate_confidence(paths, sections)

        n_sections = len(sections)
        max_d = hierarchy['max_depth']

        return {
            'pattern': (
                f'Site topology: {n_sections} section{"s" if n_sections != 1 else ""}, '
                f'{max_d} level{"s" if max_d != 1 else ""} deep, '
                f'{len(paths)} pages'
            ),
            'confidence': confidence,
            'sections': sections,
            'hierarchy': hierarchy,
            'url_patterns': url_patterns,
            'content_distribution': content_dist,
            'total_pages': len(paths),
            'url_source': url_source,
        }

    # ──────────────────────────────────────────────────────────────────
    # URL normalisation
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _urls_to_paths(urls: List[str], base_host: str) -> List[str]:
        """Convert absolute/relative URLs to deduplicated path list."""
        paths = set()
        for raw in urls:
            if not raw:
                continue
            try:
                parsed = urlparse(raw)
                # Skip external links
                host = parsed.hostname or ''
                if host and host != base_host and not host.endswith('.' + base_host):
                    continue
                path = (parsed.path or '/').rstrip('/')
                if not path:
                    path = '/'
                # Skip common non-page paths
                if any(path.endswith(ext) for ext in ('.png', '.jpg', '.svg', '.css', '.js', '.ico', '.xml', '.json', '.woff', '.woff2')):
                    continue
                paths.add(path)
            except Exception:
                continue
        return sorted(paths)

    # ──────────────────────────────────────────────────────────────────
    # Section extraction
    # ──────────────────────────────────────────────────────────────────

    def _extract_sections(self, paths: List[str]) -> List[Dict]:
        """
        Group URLs by top-level path prefix.
        /docs/api/users and /docs/guides/start → section "/docs".
        """
        section_pages = defaultdict(list)

        for path in paths:
            if path == '/':
                section_pages['/'].append(path)
                continue
            segments = path.strip('/').split('/')
            top = '/' + segments[0]
            section_pages[top].append(path)

        sections = []
        for prefix, pages in sorted(section_pages.items(), key=lambda x: -len(x[1])):
            if prefix == '/':
                continue  # Home page — not a section

            # Calculate max sub-depth within this section
            depths = [p.strip('/').count('/') for p in pages]
            max_sub_depth = max(depths) if depths else 0

            # Detect the dominant template for this section
            template = self._section_template(prefix, pages)

            # Classify content type
            content_type = self._classify_single_section(prefix)

            sections.append({
                'path': prefix,
                'page_count': len(pages),
                'depth': max_sub_depth + 1,
                'template': template,
                'type': content_type,
                'sample_pages': pages[:3],
            })

        return sections

    # ──────────────────────────────────────────────────────────────────
    # URL template detection (statistical)
    # ──────────────────────────────────────────────────────────────────

    def _detect_url_templates(self, paths: List[str]) -> List[Dict]:
        """
        Identify recurring URL structures using positional variance.

        Logic:
          1. Group paths by depth (number of segments)
          2. Within each depth group, check each segment position
          3. A position is "variable" if >3 unique values appear there
             with matching prefix segments
          4. Variable positions become {param} in the template
        """
        # Group by (depth, prefix_through_position_0)
        groups = defaultdict(list)
        for path in paths:
            if path == '/':
                continue
            segments = path.strip('/').split('/')
            depth = len(segments)
            if depth < 2:
                continue  # Single-segment paths don't form templates
            prefix_key = segments[0]
            groups[(depth, prefix_key)].append(segments)

        templates = []
        seen_templates = set()

        for (depth, prefix), segment_lists in groups.items():
            if len(segment_lists) < 3:
                continue  # Need at least 3 pages to detect a pattern

            # For each position, check variance
            template_parts = []
            for pos in range(depth):
                values_at_pos = [segs[pos] for segs in segment_lists if pos < len(segs)]
                unique_count = len(set(values_at_pos))

                if unique_count == 1:
                    # Fixed segment
                    template_parts.append(values_at_pos[0])
                elif unique_count <= 3 and len(values_at_pos) > 5:
                    # Low-variance — still fixed (e.g. /docs/en/... and /docs/fr/...)
                    template_parts.append(values_at_pos[0])
                else:
                    # Variable segment — infer a name
                    param_name = self._infer_param_name(values_at_pos, pos, depth)
                    template_parts.append('{' + param_name + '}')

            template_str = '/' + '/'.join(template_parts)

            # Skip if all segments are fixed (not really a template)
            if '{' not in template_str:
                continue

            if template_str in seen_templates:
                continue
            seen_templates.add(template_str)

            # Find a concrete example
            example = '/' + '/'.join(segment_lists[0])

            templates.append({
                'template': template_str,
                'count': len(segment_lists),
                'example': example,
            })

        # Sort by count descending
        templates.sort(key=lambda t: -t['count'])
        return templates[:10]  # Cap at top 10

    @staticmethod
    def _infer_param_name(values: List[str], pos: int, total_depth: int) -> str:
        """Guess a meaningful parameter name from the values at a position."""
        # Check for numeric patterns
        numeric_count = sum(1 for v in values if v.isdigit())
        if numeric_count > len(values) * 0.8:
            if pos == total_depth - 1:
                return 'id'
            # Could be year/month
            sample_nums = [int(v) for v in values if v.isdigit()]
            if sample_nums:
                avg = sum(sample_nums) / len(sample_nums)
                if 1900 < avg < 2100:
                    return 'year'
                if 1 <= avg <= 12:
                    return 'month'
            return 'id'

        # Check for slug-like patterns (lowercase, hyphens)
        slug_count = sum(1 for v in values if re.match(r'^[a-z0-9][a-z0-9-]*$', v))
        if slug_count > len(values) * 0.7:
            if pos == total_depth - 1:
                return 'slug'
            return 'category'

        # Check for UUID-like
        uuid_count = sum(1 for v in values if re.match(r'^[a-f0-9-]{8,}$', v))
        if uuid_count > len(values) * 0.5:
            return 'uuid'

        # Generic
        if pos == total_depth - 1:
            return 'page'
        return 'segment'

    def _section_template(self, prefix: str, pages: List[str]) -> Optional[str]:
        """Detect the dominant template within a section."""
        if len(pages) < 3:
            return None

        # Strip prefix and analyse remaining structure
        suffixes = []
        for p in pages:
            suffix = p[len(prefix):]
            if suffix:
                suffixes.append(suffix.strip('/'))

        if not suffixes:
            return None

        # Check if most suffixes have the same depth
        depths = Counter(s.count('/') for s in suffixes)
        dominant_depth, count = depths.most_common(1)[0]

        if count < 3:
            return None

        # Build template from dominant-depth suffixes
        matching = [s.split('/') for s in suffixes if s.count('/') == dominant_depth]
        if not matching:
            return None

        parts = [prefix.strip('/')]
        for pos in range(dominant_depth + 1):
            values = [segs[pos] for segs in matching if pos < len(segs)]
            unique = len(set(values))
            if unique <= 2 and len(values) > 3:
                parts.append(values[0])
            else:
                parts.append('{' + self._infer_param_name(values, pos + 1, dominant_depth + 2) + '}')

        return '/' + '/'.join(parts)

    # ──────────────────────────────────────────────────────────────────
    # Hierarchy analysis
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _analyze_hierarchy(paths: List[str]) -> Dict:
        """Calculate depth statistics and classify shape."""
        depths = []
        for p in paths:
            if p == '/':
                depths.append(0)
            else:
                depths.append(p.strip('/').count('/') + 1)

        if not depths:
            return {'max_depth': 0, 'avg_depth': 0, 'shape': 'flat'}

        max_d = max(depths)
        avg_d = round(sum(depths) / len(depths), 1)

        # Count distinct top-level sections
        top_sections = set()
        for p in paths:
            if p != '/':
                top_sections.add(p.strip('/').split('/')[0])

        n_sections = len(top_sections)

        # Shape classification
        if avg_d < 1.5 and n_sections >= 4:
            shape = 'wide-shallow'
            label = 'Wide & shallow — lots of top-level pages, few sub-levels'
        elif avg_d > 3 and n_sections <= 3:
            shape = 'deep-narrow'
            label = 'Deep & narrow — few sections but many sub-levels'
        elif avg_d > 2.5:
            shape = 'deep'
            label = 'Deep hierarchy — content is nested several levels'
        elif n_sections >= 6:
            shape = 'wide'
            label = 'Wide — many distinct sections'
        else:
            shape = 'balanced'
            label = 'Balanced — moderate depth and breadth'

        return {
            'max_depth': max_d,
            'avg_depth': avg_d,
            'shape': shape,
            'label': label,
            'top_level_sections': n_sections,
        }

    # ──────────────────────────────────────────────────────────────────
    # Content-type classification
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _classify_single_section(prefix: str) -> str:
        """Classify a single section path into a content type."""
        slug = prefix.strip('/').split('/')[0].lower()
        for content_type, keywords in _CONTENT_TYPE_MAP.items():
            if slug in keywords:
                return content_type
        return 'other'

    def _classify_content_types(self, sections: List[Dict]) -> Dict:
        """Build content distribution from classified sections."""
        dist = defaultdict(lambda: {'count': 0, 'sections': []})
        total = sum(s['page_count'] for s in sections)

        for s in sections:
            ct = s.get('type', 'other')
            dist[ct]['count'] += s['page_count']
            dist[ct]['sections'].append(s['path'])

        # Add percentages
        for ct in dist:
            dist[ct]['pct'] = round(dist[ct]['count'] / total * 100) if total else 0

        # Sort by count descending, convert to regular dict
        return dict(sorted(dist.items(), key=lambda x: -x[1]['count']))

    # ──────────────────────────────────────────────────────────────────
    # Confidence
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _calculate_confidence(paths: List[str], sections: List[Dict]) -> int:
        """
        Confidence based on URL count and structural signals.
        More URLs + more sections = more confident in the topology picture.
        """
        n = len(paths)
        if n < 5:
            base = 25
        elif n < 10:
            base = 40
        elif n < 30:
            base = 55
        elif n < 50:
            base = 65
        elif n < 100:
            base = 75
        elif n < 200:
            base = 85
        else:
            base = 90

        # Bonus for having multiple sections (signals real structure)
        n_sections = len(sections)
        if n_sections >= 5:
            base = min(base + 10, 95)
        elif n_sections >= 3:
            base = min(base + 5, 95)

        return base
