"""
Security Extractor — HTTPS status, CSP, CORS, and security headers.

Inspects network response headers for the target URL to assess
security posture and produce a score with recommendations.
"""

import logging
from typing import Dict
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class SecurityExtractor(BaseExtractor):
    name = "security"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Checking security...")

        security_data = {
            'https': ctx.url.startswith('https'),
            'csp_header': None,
            'cors_headers': [],
            'security_headers': {}
        }

        # Check response headers
        for resp in ctx.network_responses:
            if resp['url'] == ctx.url:
                headers = resp['headers']
                security_data['csp_header'] = headers.get('content-security-policy')
                security_data['security_headers'] = {
                    'x-frame-options': headers.get('x-frame-options'),
                    'x-content-type-options': headers.get('x-content-type-options'),
                    'strict-transport-security': headers.get('strict-transport-security')
                }
                break

        score = self._calculate_security_score(security_data)

        return {
            'pattern': f"Security Score: {score}/100",
            'confidence': 95,
            'score': score,
            'details': security_data,
            'recommendations': self._generate_security_recommendations(security_data)
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_security_score(data):
        score = 0
        if data['https']:
            score += 40
        if data['csp_header']:
            score += 20
        if data['security_headers'].get('x-frame-options'):
            score += 15
        if data['security_headers'].get('strict-transport-security'):
            score += 25
        return score

    @staticmethod
    def _generate_security_recommendations(data):
        recs = []
        if not data['https']:
            recs.append("Enable HTTPS")
        if not data['csp_header']:
            recs.append("Add Content-Security-Policy header")
        return recs
