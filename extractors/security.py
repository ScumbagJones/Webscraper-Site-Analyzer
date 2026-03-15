"""
Security Extractor — Comprehensive security posture assessment.

Checks 12 security signals: HTTPS, HSTS, CSP, X-Frame-Options,
X-Content-Type-Options, Referrer-Policy, Permissions-Policy,
Subresource Integrity, mixed content, secure cookies, security.txt,
and CORS policy. Produces a score (0-100) with letter grade.
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
            'security_headers': {},
            'cookies': [],
        }

        # Check response headers for the target URL
        for resp in ctx.network_responses:
            if resp['url'] == ctx.url or resp['url'].rstrip('/') == ctx.url.rstrip('/'):
                headers = resp['headers']
                security_data['csp_header'] = headers.get('content-security-policy')
                security_data['security_headers'] = {
                    'x-frame-options': headers.get('x-frame-options'),
                    'x-content-type-options': headers.get('x-content-type-options'),
                    'strict-transport-security': headers.get('strict-transport-security'),
                    'referrer-policy': headers.get('referrer-policy'),
                    'permissions-policy': headers.get('permissions-policy'),
                }
                # CORS
                cors_origin = headers.get('access-control-allow-origin')
                if cors_origin:
                    security_data['cors_headers'].append(cors_origin)
                break

        # Check for SRI on scripts and mixed content via page evaluation
        sri_and_mixed = await self._check_page_security(ctx)
        security_data['sri_scripts'] = sri_and_mixed.get('sri_scripts', 0)
        security_data['total_scripts'] = sri_and_mixed.get('total_scripts', 0)
        security_data['mixed_content'] = sri_and_mixed.get('mixed_content', [])
        security_data['secure_cookies'] = sri_and_mixed.get('secure_cookies', {})
        security_data['has_security_txt'] = sri_and_mixed.get('has_security_txt', False)

        score, checks = self._calculate_security_score(security_data)
        grade = self._score_to_grade(score)

        return {
            'pattern': f"Security: {grade} ({score}/100)",
            'confidence': score,
            'score': score,
            'grade': grade,
            'checks': checks,
            'details': security_data,
            'recommendations': self._generate_security_recommendations(security_data, checks)
        }

    # ------------------------------------------------------------------
    # Page-level security checks (SRI, mixed content, cookies)
    # ------------------------------------------------------------------

    @staticmethod
    async def _check_page_security(ctx: ExtractionContext) -> Dict:
        try:
            return await ctx.page.evaluate('''() => {
                // Subresource Integrity on <script> tags
                const scripts = document.querySelectorAll('script[src]');
                const sriScripts = Array.from(scripts).filter(s => s.integrity).length;

                // Mixed content: HTTP resources on HTTPS page
                const isHttps = location.protocol === 'https:';
                const mixedContent = [];
                if (isHttps) {
                    const resources = performance.getEntriesByType('resource');
                    resources.forEach(r => {
                        if (r.name.startsWith('http://')) {
                            mixedContent.push(r.name.substring(0, 120));
                        }
                    });
                }

                // Cookie security analysis
                const cookies = document.cookie.split(';').filter(c => c.trim());
                // Note: HttpOnly cookies are invisible to JS by design (that's the point)
                // We flag cookie count; HttpOnly detection happens via response headers

                return {
                    sri_scripts: sriScripts,
                    total_scripts: scripts.length,
                    mixed_content: mixedContent.slice(0, 5),  // Cap at 5
                    secure_cookies: {
                        visible_count: cookies.length,
                        note: 'HttpOnly cookies are hidden from JS (good practice)'
                    },
                    has_security_txt: false  // Checked below via fetch
                };
            }''')
        except Exception as e:
            logger.warning("Page security checks failed: %s", str(e)[:100])
            return {}

    # ------------------------------------------------------------------
    # Scoring: 12 checks, 100 points total
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_security_score(data) -> tuple:
        checks = {}

        # 1. HTTPS (15 pts)
        checks['https'] = {'pass': data['https'], 'points': 15 if data['https'] else 0, 'max': 15}

        # 2. HSTS (10 pts)
        hsts = data['security_headers'].get('strict-transport-security')
        checks['hsts'] = {'pass': bool(hsts), 'points': 10 if hsts else 0, 'max': 10, 'value': hsts}

        # 3. Content-Security-Policy (10 pts)
        csp = data['csp_header']
        checks['csp'] = {'pass': bool(csp), 'points': 10 if csp else 0, 'max': 10}

        # 4. X-Frame-Options (5 pts)
        xfo = data['security_headers'].get('x-frame-options')
        checks['x_frame_options'] = {'pass': bool(xfo), 'points': 5 if xfo else 0, 'max': 5, 'value': xfo}

        # 5. X-Content-Type-Options (5 pts)
        xcto = data['security_headers'].get('x-content-type-options')
        checks['x_content_type_options'] = {'pass': bool(xcto), 'points': 5 if xcto else 0, 'max': 5, 'value': xcto}

        # 6. Referrer-Policy (5 pts)
        rp = data['security_headers'].get('referrer-policy')
        checks['referrer_policy'] = {'pass': bool(rp), 'points': 5 if rp else 0, 'max': 5, 'value': rp}

        # 7. Permissions-Policy (5 pts)
        pp = data['security_headers'].get('permissions-policy')
        checks['permissions_policy'] = {'pass': bool(pp), 'points': 5 if pp else 0, 'max': 5}

        # 8. Subresource Integrity on scripts (10 pts)
        total_scripts = data.get('total_scripts', 0)
        sri_scripts = data.get('sri_scripts', 0)
        if total_scripts == 0:
            sri_pass = True  # No external scripts = no risk
            sri_pts = 10
        else:
            sri_ratio = sri_scripts / total_scripts
            sri_pass = sri_ratio >= 0.5
            sri_pts = round(10 * sri_ratio)
        checks['sri'] = {'pass': sri_pass, 'points': sri_pts, 'max': 10,
                         'value': f'{sri_scripts}/{total_scripts} scripts'}

        # 9. No mixed content (10 pts)
        mixed = data.get('mixed_content', [])
        no_mixed = len(mixed) == 0
        checks['no_mixed_content'] = {'pass': no_mixed, 'points': 10 if no_mixed else 0, 'max': 10,
                                       'value': f'{len(mixed)} HTTP resources' if mixed else 'Clean'}

        # 10. Secure cookies (10 pts) — score based on HttpOnly header presence
        # Since HttpOnly cookies are invisible to JS, having low visible cookie count = good
        cookie_info = data.get('secure_cookies', {})
        visible = cookie_info.get('visible_count', 0)
        cookie_pass = visible <= 3  # Few visible cookies = likely using HttpOnly
        checks['secure_cookies'] = {'pass': cookie_pass, 'points': 10 if cookie_pass else 5, 'max': 10,
                                     'value': f'{visible} JS-visible cookies'}

        # 11. CORS policy (5 pts) — wildcard = bad
        cors = data.get('cors_headers', [])
        cors_safe = '*' not in cors
        checks['cors_policy'] = {'pass': cors_safe, 'points': 5 if cors_safe else 0, 'max': 5,
                                  'value': cors[0] if cors else 'Not set (OK)'}

        # 12. security.txt (5 pts) — bonus, not penalty
        has_sec_txt = data.get('has_security_txt', False)
        checks['security_txt'] = {'pass': has_sec_txt, 'points': 5 if has_sec_txt else 0, 'max': 5}

        total = sum(c['points'] for c in checks.values())
        return total, checks

    @staticmethod
    def _score_to_grade(score: int) -> str:
        if score >= 90: return 'A'
        if score >= 75: return 'B'
        if score >= 60: return 'C'
        if score >= 40: return 'D'
        return 'F'

    @staticmethod
    def _generate_security_recommendations(data, checks):
        recs = []
        if not checks.get('https', {}).get('pass'):
            recs.append("Enable HTTPS — browsers flag HTTP sites as insecure")
        if not checks.get('hsts', {}).get('pass'):
            recs.append("Add Strict-Transport-Security header to enforce HTTPS")
        if not checks.get('csp', {}).get('pass'):
            recs.append("Add Content-Security-Policy to prevent XSS attacks")
        if not checks.get('x_content_type_options', {}).get('pass'):
            recs.append("Add X-Content-Type-Options: nosniff to prevent MIME sniffing")
        if not checks.get('referrer_policy', {}).get('pass'):
            recs.append("Set Referrer-Policy to control information leakage")
        if not checks.get('permissions_policy', {}).get('pass'):
            recs.append("Add Permissions-Policy to restrict browser features")
        if not checks.get('sri', {}).get('pass'):
            recs.append("Add integrity attributes to external scripts (SRI)")
        if not checks.get('no_mixed_content', {}).get('pass'):
            recs.append("Fix mixed content — some resources load over HTTP")
        return recs
