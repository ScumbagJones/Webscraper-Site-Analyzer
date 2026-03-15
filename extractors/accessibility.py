"""
Accessibility Extractor — ARIA attributes, semantic HTML, contrast ratios.

Checks for proper ARIA labelling, semantic HTML5 elements, alt text coverage,
and optionally runs contrast analysis against the extracted color palette.
"""

import logging
from typing import Dict, Optional
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class AccessibilityExtractor(BaseExtractor):
    name = "accessibility"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Checking accessibility...")

        a11y_data = await ctx.page.evaluate('''() => {
            return {
                aria_labels: document.querySelectorAll('[aria-label]').length,
                aria_roles: document.querySelectorAll('[role]').length,
                alt_tags: document.querySelectorAll('img[alt]').length,
                total_images: document.querySelectorAll('img').length,
                semantic_html: {
                    header: document.querySelectorAll('header').length,
                    nav: document.querySelectorAll('nav').length,
                    main: document.querySelectorAll('main').length,
                    footer: document.querySelectorAll('footer').length,
                    article: document.querySelectorAll('article').length
                },
                lang_attribute: document.documentElement.lang || 'missing'
            };
        }''')

        # Add contrast checking if color analysis is available
        contrast_analysis = None
        colors_evidence = ctx.get_evidence('colors')
        if colors_evidence:
            try:
                from contrast_checker import analyze_color_palette_contrast
                color_palette = colors_evidence.get('intelligent_palette', {})
                if color_palette:
                    contrast_analysis = analyze_color_palette_contrast(color_palette)
            except Exception as e:
                logger.warning("Contrast analysis failed: %s", str(e)[:100])

        score = self._calculate_a11y_score(a11y_data, contrast_analysis)

        result = {
            'pattern': f"Accessibility Score: {score}/100",
            'confidence': score,
            'score': score,
            'details': a11y_data,
            'recommendations': self._generate_a11y_recommendations(a11y_data, contrast_analysis)
        }

        # Add contrast analysis if available
        if contrast_analysis:
            result['contrast_analysis'] = contrast_analysis

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_a11y_score(data, contrast_analysis=None):
        score = 50
        if data['lang_attribute'] != 'missing':
            score += 10
        if data['aria_labels'] > 5:
            score += 15
        if data['semantic_html']['main'] > 0:
            score += 10
        if data['total_images'] > 0 and data['alt_tags'] / data['total_images'] > 0.8:
            score += 15

        # Contrast penalty: deduct for failing pairs (up to -20 points)
        if contrast_analysis:
            summary = contrast_analysis.get('summary', {})
            aa_pass_rate = summary.get('aa_pass_rate', 1.0)
            total_pairs = summary.get('total_pairs', 0)
            if total_pairs > 0 and aa_pass_rate < 1.0:
                penalty = int((1.0 - aa_pass_rate) * 20)
                score -= penalty

        return max(0, min(score, 100))

    @staticmethod
    def _generate_a11y_recommendations(data, contrast_analysis=None):
        recs = []
        if data['lang_attribute'] == 'missing':
            recs.append("Add lang attribute to <html> tag")
        if data['total_images'] > 0 and data['alt_tags'] < data['total_images']:
            recs.append(f"Add alt text to {data['total_images'] - data['alt_tags']} images")

        # Add contrast recommendations
        if contrast_analysis:
            summary = contrast_analysis.get('summary', {})
            aa_fails = summary.get('total_pairs', 0) - summary.get('aa_pass', 0)
            if aa_fails > 0:
                worst = summary.get('worst_contrast', {})
                recs.append(
                    f"Fix {aa_fails} color pairs failing WCAG AA "
                    f"(worst: {worst.get('foreground')} on {worst.get('background')}, "
                    f"{worst.get('contrast_ratio')}:1)"
                )

        return recs
