"""
Performance Extractor — Load timing, Core Web Vitals, resource analysis,
transfer sizes, render-blocking detection, and Web Vitals grading.

Measures navigation timing, LCP, FID, CLS, INP, resource transfer
sizes, render-blocking scripts/stylesheets, and third-party script
impact. Generates a composite grade and plain-English summary.
"""

import logging
from typing import Dict
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class PerformanceExtractor(BaseExtractor):
    name = "performance"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Measuring performance...")

        perf_data = await ctx.page.evaluate('''() => {
            const perf = performance.getEntriesByType('navigation')[0];

            // Core Web Vitals - LCP, FID, CLS
            let lcp = 0;
            let fid = 0;
            let cls = 0;
            let inp = 0;

            // LCP (Largest Contentful Paint)
            const lcpEntry = performance.getEntriesByType('largest-contentful-paint');
            if (lcpEntry.length > 0) {
                lcp = lcpEntry[lcpEntry.length - 1].renderTime || lcpEntry[lcpEntry.length - 1].loadTime;
            }

            // FID (First Input Delay) - requires user interaction, may be 0
            const fidEntry = performance.getEntriesByType('first-input');
            if (fidEntry.length > 0) {
                fid = fidEntry[0].processingStart - fidEntry[0].startTime;
            }

            // CLS (Cumulative Layout Shift)
            const clsEntries = performance.getEntriesByType('layout-shift');
            clsEntries.forEach(entry => {
                if (!entry.hadRecentInput) {
                    cls += entry.value;
                }
            });

            // INP (Interaction to Next Paint) - approximate from event timing
            const eventEntries = performance.getEntriesByType('event');
            if (eventEntries.length > 0) {
                const durations = eventEntries.map(e => e.duration);
                inp = Math.max(...durations);
            }

            // Transfer sizes by type
            const resources = performance.getEntriesByType('resource');
            const sizes = { css: 0, js: 0, image: 0, font: 0, other: 0, total: 0 };
            resources.forEach(r => {
                const bytes = r.transferSize || 0;
                sizes.total += bytes;
                if (r.initiatorType === 'css' || r.name.match(/\\.css/)) sizes.css += bytes;
                else if (r.initiatorType === 'script' || r.name.match(/\\.js/)) sizes.js += bytes;
                else if (r.initiatorType === 'img' || r.name.match(/\\.(png|jpg|jpeg|gif|webp|avif|svg)/i)) sizes.image += bytes;
                else if (r.name.match(/\\.(woff2?|ttf|otf|eot)/i)) sizes.font += bytes;
                else sizes.other += bytes;
            });

            // Convert to KB
            Object.keys(sizes).forEach(k => { sizes[k] = Math.round(sizes[k] / 1024); });

            // Render-blocking resources
            const headScripts = document.querySelectorAll('head script[src]:not([async]):not([defer]):not([type="module"])');
            const headStylesheets = document.querySelectorAll('link[rel="stylesheet"]');

            // Third-party scripts
            const currentHost = location.hostname;
            const thirdPartyScripts = Array.from(document.querySelectorAll('script[src]')).filter(s => {
                try { return new URL(s.src).hostname !== currentHost; } catch { return false; }
            });
            const thirdPartyDomains = [...new Set(thirdPartyScripts.map(s => {
                try { return new URL(s.src).hostname; } catch { return 'unknown'; }
            }))];

            // Page load timeline
            const pageLoadMs = perf ? perf.loadEventEnd - perf.fetchStart : 0;
            const ttfb = perf ? perf.responseStart - perf.requestStart : 0;
            const domReady = perf ? perf.domContentLoadedEventEnd - perf.fetchStart : 0;

            return {
                dom_content_loaded: perf?.domContentLoadedEventEnd - perf?.domContentLoadedEventStart,
                load_complete: pageLoadMs,
                dom_interactive: perf?.domInteractive - perf?.fetchStart,
                total_resources: resources.length,
                // Core Web Vitals
                lcp: lcp,
                fid: fid,
                inp: inp,
                cls: Math.round(cls * 1000) / 1000,
                // Supporting metrics
                ttfb: ttfb,
                fcp: performance.getEntriesByType('paint').find(e => e.name === 'first-contentful-paint')?.startTime || 0,
                dom_ready_ms: domReady,
                // Transfer sizes (KB)
                transfer_sizes: sizes,
                // Render blocking
                render_blocking: {
                    scripts: headScripts.length,
                    stylesheets: headStylesheets.length
                },
                // Third party
                third_party: {
                    script_count: thirdPartyScripts.length,
                    domains: thirdPartyDomains.slice(0, 10)
                }
            };
        }''')

        # Analyze resource counts
        resource_summary = self._analyze_resources(ctx)

        # Grade Core Web Vitals against Google thresholds
        cwv_grade, cwv_details = self._grade_web_vitals(perf_data)

        # Generate plain-English speed summary
        load_ms = perf_data.get('load_complete', 0)
        speed_label = self._speed_label(load_ms)

        # Analyze Core Web Vitals (legacy integration)
        core_web_vitals = None
        try:
            from core_web_vitals import analyze_core_web_vitals
            vitals_data = {
                'lcp': perf_data.get('lcp', 0),
                'fid': perf_data.get('fid', 0),
                'inp': perf_data.get('inp', 0),
                'cls': perf_data.get('cls', 0),
                'ttfb': perf_data.get('ttfb', 0),
                'fcp': perf_data.get('fcp', 0)
            }
            core_web_vitals = analyze_core_web_vitals(vitals_data)
            logger.info("Core Web Vitals: %s", core_web_vitals['summary']['overall_rating'])
        except Exception as e:
            logger.warning("Core Web Vitals module: %s", str(e)[:100])

        result = {
            'pattern': f"{speed_label} — loads in {load_ms / 1000:.1f}s" if load_ms else "Performance measured",
            'confidence': 95,
            'speed_label': speed_label,
            'timings': perf_data,
            'transfer_sizes': perf_data.get('transfer_sizes', {}),
            'render_blocking': perf_data.get('render_blocking', {}),
            'third_party': perf_data.get('third_party', {}),
            'resources': resource_summary,
            'web_vitals_grade': cwv_grade,
            'web_vitals_details': cwv_details,
            'recommendations': self._generate_perf_recommendations(perf_data, resource_summary)
        }

        if core_web_vitals:
            result['core_web_vitals'] = core_web_vitals

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_resources(ctx):
        by_type = {}
        for req in ctx.network_requests:
            rt = req['resource_type']
            if rt not in by_type:
                by_type[rt] = 0
            by_type[rt] += 1
        return by_type

    @staticmethod
    def _speed_label(load_ms: float) -> str:
        """Plain-English speed description — no jargon."""
        if load_ms <= 0:
            return "Speed not measured"
        if load_ms < 1000:
            return "Very fast"
        if load_ms < 2500:
            return "Fast"
        if load_ms < 4000:
            return "Average"
        if load_ms < 7000:
            return "Slow"
        return "Very slow"

    @staticmethod
    def _grade_web_vitals(perf) -> tuple:
        """Grade Core Web Vitals against Google's thresholds.
        Returns (grade: str, details: dict)."""
        details = {}

        # LCP: Good <2.5s, Needs Work <4s, Poor >=4s
        lcp = perf.get('lcp', 0)
        if lcp > 0:
            if lcp < 2500:
                details['lcp'] = {'rating': 'Good', 'value_ms': round(lcp), 'label': f'{lcp/1000:.1f}s'}
            elif lcp < 4000:
                details['lcp'] = {'rating': 'Needs work', 'value_ms': round(lcp), 'label': f'{lcp/1000:.1f}s'}
            else:
                details['lcp'] = {'rating': 'Poor', 'value_ms': round(lcp), 'label': f'{lcp/1000:.1f}s'}

        # FID: Good <100ms, Needs Work <300ms, Poor >=300ms
        fid = perf.get('fid', 0)
        if fid > 0:
            if fid < 100:
                details['fid'] = {'rating': 'Good', 'value_ms': round(fid)}
            elif fid < 300:
                details['fid'] = {'rating': 'Needs work', 'value_ms': round(fid)}
            else:
                details['fid'] = {'rating': 'Poor', 'value_ms': round(fid)}

        # CLS: Good <0.1, Needs Work <0.25, Poor >=0.25
        cls = perf.get('cls', 0)
        if cls > 0:
            if cls < 0.1:
                details['cls'] = {'rating': 'Good', 'value': round(cls, 3)}
            elif cls < 0.25:
                details['cls'] = {'rating': 'Needs work', 'value': round(cls, 3)}
            else:
                details['cls'] = {'rating': 'Poor', 'value': round(cls, 3)}

        # INP: Good <200ms, Needs Work <500ms, Poor >=500ms
        inp = perf.get('inp', 0)
        if inp > 0:
            if inp < 200:
                details['inp'] = {'rating': 'Good', 'value_ms': round(inp)}
            elif inp < 500:
                details['inp'] = {'rating': 'Needs work', 'value_ms': round(inp)}
            else:
                details['inp'] = {'rating': 'Poor', 'value_ms': round(inp)}

        # TTFB: Good <800ms, Needs Work <1800ms, Poor >=1800ms
        ttfb = perf.get('ttfb', 0)
        if ttfb > 0:
            if ttfb < 800:
                details['ttfb'] = {'rating': 'Good', 'value_ms': round(ttfb)}
            elif ttfb < 1800:
                details['ttfb'] = {'rating': 'Needs work', 'value_ms': round(ttfb)}
            else:
                details['ttfb'] = {'rating': 'Poor', 'value_ms': round(ttfb)}

        # Composite grade: count Good/Needs Work/Poor
        ratings = [v['rating'] for v in details.values()]
        if not ratings:
            return 'N/A', details

        good = ratings.count('Good')
        poor = ratings.count('Poor')
        total = len(ratings)

        if poor == 0 and good >= total * 0.75:
            grade = 'A'
        elif poor == 0:
            grade = 'B'
        elif poor <= 1:
            grade = 'C'
        elif poor <= 2:
            grade = 'D'
        else:
            grade = 'F'

        return grade, details

    @staticmethod
    def _generate_perf_recommendations(perf, resources):
        recs = []
        load_ms = perf.get('load_complete', 0)
        if load_ms > 4000:
            recs.append(f"Page takes {load_ms/1000:.1f}s to load — users expect under 3s")
        elif load_ms > 2500:
            recs.append(f"Page loads in {load_ms/1000:.1f}s — good but could be faster")

        lcp = perf.get('lcp', 0)
        if lcp > 4000:
            recs.append("Main content appears slowly (LCP > 4s) — optimize hero images or server response")

        cls = perf.get('cls', 0)
        if cls > 0.25:
            recs.append("Page elements shift around as it loads (high CLS) — reserve space for images/ads")

        rb = perf.get('render_blocking', {})
        if rb.get('scripts', 0) > 3:
            recs.append(f"{rb['scripts']} render-blocking scripts in <head> — add async or defer")

        sizes = perf.get('transfer_sizes', {})
        if sizes.get('js', 0) > 500:
            recs.append(f"JavaScript is {sizes['js']}KB — consider code splitting")
        if sizes.get('image', 0) > 2000:
            recs.append(f"Images total {sizes['image']}KB — use WebP/AVIF and lazy loading")

        tp = perf.get('third_party', {})
        if tp.get('script_count', 0) > 10:
            recs.append(f"{tp['script_count']} third-party scripts — each adds latency")

        if resources.get('image', 0) > 50:
            recs.append(f"Consider lazy loading images ({resources['image']} images)")

        return recs
