"""
API Pattern Extractor — REST, GraphQL, WebSocket detection from network requests.
"""

import logging
from typing import Dict
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class APIPatternExtractor(BaseExtractor):
    name = "api_patterns"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Analyzing API patterns...")

        api_requests = [
            r for r in ctx.network_requests
            if r.get('resource_type') in ('xhr', 'fetch')
        ]

        patterns = {
            'rest_apis': [],
            'graphql': [],
            'websockets': [],
            'total_api_calls': len(api_requests)
        }

        for req in api_requests:
            url = req['url']
            if 'graphql' in url.lower():
                patterns['graphql'].append(url)
            elif 'ws://' in url or 'wss://' in url:
                patterns['websockets'].append(url)
            else:
                patterns['rest_apis'].append(url)

        # Generate API relationship map
        relationship_map = None
        if api_requests:
            try:
                from api_relationship_mapper import APIRelationshipMapper
                mapper = APIRelationshipMapper(api_requests)
                relationship_map = mapper.analyze_relationships()
            except Exception as e:
                logger.warning("Relationship mapping failed: %s", str(e)[:100])

        return {
            'pattern': self._determine_api_pattern(patterns),
            'confidence': min(90, 40 + len((relationship_map or {}).get('endpoints', [])) * 5),
            'details': patterns,
            'relationship_map': relationship_map
        }

    @staticmethod
    def _determine_api_pattern(patterns: Dict) -> str:
        if len(patterns['graphql']) > 0:
            return f"GraphQL API ({len(patterns['graphql'])} queries)"
        elif len(patterns['rest_apis']) > 5:
            return f"REST API ({len(patterns['rest_apis'])} endpoints)"
        elif len(patterns['websockets']) > 0:
            return "WebSocket Real-time"
        else:
            return "Static Content"
