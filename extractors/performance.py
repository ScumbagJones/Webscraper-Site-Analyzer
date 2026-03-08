"""
Performance Extractor — Load timing, Core Web Vitals, resource summary.

Measures navigation timing, LCP, FID, CLS, INP, and generates
performance recommendations based on resource counts and load times.
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

            return {
                dom_content_loaded: perf?.domContentLoadedEventEnd - perf?.domContentLoadedEventStart,
                load_complete: perf?.loadEventEnd - perf?.loadEventStart,
                dom_interactive: perf?.domInteractive - perf?.fetchStart,
                total_resources: performance.getEntriesByType('resource').length,
                // Core Web Vitals
                lcp: lcp,
                fid: fid,
                inp: inp,
                cls: cls,
                // Supporting metrics
                ttfb: perf?.responseStart - perf?.requestStart,
                fcp: performance.getEntriesByType('paint').find(e => e.name === 'first-contentful-paint')?.startTime || 0
            };
        }''')

        # Analyze resource sizes
        resource_summary = self._analyze_resources(ctx)

        # Analyze Core Web Vitals
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
            logger.warning("Core Web Vitals failed: %s", str(e)[:100])

        result = {
            'pattern': f"Load time: {perf_data.get('load_complete', 0):.0f}ms",
            'confidence': 95,
            'timings': perf_data,
            'resources': resource_summary,
            'recommendations': self._generate_perf_recommendations(perf_data, resource_summary)
        }

        # Add Core Web Vitals if available
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
    def _generate_perf_recommendations(perf, resources):
        recs = []
        if perf.get('load_complete', 0) > 3000:
            recs.append("Optimize load time (currently > 3s)")
        if resources.get('image', 0) > 50:
            recs.append(f"Consider lazy loading images ({resources['image']} images)")
        return recs
