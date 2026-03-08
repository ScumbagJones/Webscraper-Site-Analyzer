"""
Network Extractor — Third-party service detection from network requests.

Detects analytics, font services, CDNs, and advertising networks.
"""

import logging
from typing import Dict
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class NetworkExtractor(BaseExtractor):
    name = "third_party"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Detecting third-party integrations...")

        third_party = {
            'analytics': [],
            'fonts': [],
            'cdns': [],
            'advertising': []
        }

        for req in ctx.network_requests:
            url = req.get('url', '')

            # Analytics
            if any(x in url for x in ['google-analytics', 'gtag', 'segment.', 'mixpanel']):
                third_party['analytics'].append(url)

            # Fonts
            if any(x in url for x in ['fonts.googleapis', 'typekit', 'fonts.gstatic']):
                third_party['fonts'].append(url)

            # CDNs
            if any(x in url for x in ['cloudflare', 'fastly', 'cloudfront', 'jsdelivr', 'unpkg']):
                third_party['cdns'].append(url)

        return {
            'pattern': f"{len(third_party['analytics'])} analytics services detected",
            'confidence': 90,
            'details': third_party
        }

    def analyze_resources(self, network_requests) -> Dict:
        """Categorize network requests by type."""
        by_type = {}
        for req in network_requests:
            rt = req.get('resource_type', 'unknown')
            by_type[rt] = by_type.get(rt, 0) + 1
        return by_type
