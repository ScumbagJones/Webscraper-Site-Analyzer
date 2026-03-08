"""
Typography Extractor — Font families, sizes, weights, type scale detection.

Extracts heading hierarchy, body typography, and optionally runs
intelligent type scale analysis via typography_intelligence module.
"""

import logging
from typing import Dict
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class TypographyExtractor(BaseExtractor):
    name = "typography"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Analyzing typography...")

        typo_data = await ctx.page.evaluate('''() => {
            const headings = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].map(tag => {
                const el = document.querySelector(tag);
                if (!el) return null;
                const styles = window.getComputedStyle(el);
                return {
                    tag,
                    fontFamily: styles.fontFamily,
                    fontSize: styles.fontSize,
                    fontWeight: styles.fontWeight,
                    lineHeight: styles.lineHeight,
                    letterSpacing: styles.letterSpacing
                };
            }).filter(Boolean);

            const body = window.getComputedStyle(document.body);
            const paragraph = document.querySelector('p');
            const pStyles = paragraph ? window.getComputedStyle(paragraph) : body;

            // Collect ALL unique fonts, sizes, and weights across the page
            const allFonts = new Set();
            const allSizes = new Set();
            const allWeights = new Set();

            // Sample a reasonable number of elements (not all, for performance)
            const elements = document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, span, a, button, li');
            for (const el of elements) {
                const styles = window.getComputedStyle(el);
                if (styles.fontFamily) allFonts.add(styles.fontFamily);
                if (styles.fontSize) allSizes.add(styles.fontSize);
                if (styles.fontWeight) allWeights.add(styles.fontWeight);
            }

            return {
                headings,
                body: {
                    fontFamily: body.fontFamily,
                    fontSize: body.fontSize,
                    fontWeight: body.fontWeight,
                    lineHeight: body.lineHeight
                },
                paragraph: {
                    fontSize: pStyles.fontSize,
                    lineHeight: pStyles.lineHeight,
                    color: pStyles.color
                },
                all_fonts: Array.from(allFonts),
                all_sizes: Array.from(allSizes),
                all_weights: Array.from(allWeights)
            };
        }''')

        # Get stylesheet URLs for web font detection
        stylesheet_urls = await ctx.page.evaluate('''() => {
            const stylesheets = Array.from(document.styleSheets);
            return stylesheets.map(s => s.href).filter(Boolean);
        }''')

        # Intelligent typography analysis
        typography_intelligence = None
        try:
            from typography_intelligence import extract_typography_intelligence
            typography_intelligence = extract_typography_intelligence(typo_data, stylesheet_urls)
            logger.info(
                "Type scale: %s (%d%%)",
                typography_intelligence['type_scale']['pattern'],
                typography_intelligence['confidence']
            )
        except Exception as e:
            logger.warning("Typography intelligence failed: %s", str(e)[:100])

        # Backwards-compatible type scale
        type_scale = self._calculate_type_scale(typo_data)

        # Calculate typography confidence from actual evidence
        confidence = 40  # Base: extraction ran
        if typo_data.get('all_fonts'):
            confidence += 15
        if typo_data.get('headings'):
            confidence += 15
        if typo_data.get('body', {}).get('lineHeight') and typo_data['body']['lineHeight'] != 'normal':
            confidence += 10
        if typography_intelligence and typography_intelligence.get('type_scale', {}).get('ratio'):
            confidence += 15
        confidence = min(confidence, 95)

        result = {
            'pattern': self._determine_typo_pattern(typo_data),
            'confidence': confidence,
            'details': typo_data,
            'type_scale': type_scale,
            'code_snippets': self._generate_typo_snippets(typo_data)
        }

        if typography_intelligence:
            result['intelligent_typography'] = typography_intelligence

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_typo_pattern(data: Dict) -> str:
        primary_font = data['body']['fontFamily'].split(',')[0].strip().replace('"', '')
        return primary_font

    @staticmethod
    def _calculate_type_scale(data: Dict):
        """Calculate modular type scale from heading sizes.

        Returns a dict with both the ratio and the raw size array so
        consumers can use either.  For backward compatibility, the
        'ratio' value is the same float previously returned bare.
        """
        all_sizes_raw = sorted(
            list(set(data.get('all_sizes', []))),
            key=lambda s: float(s.replace('px', '').replace('rem', '').replace('em', '') or '0'),
            reverse=True
        )

        if not data.get('headings') or len(data['headings']) < 2:
            return {
                'ratio': None,
                'sizes_px': [s for s in all_sizes_raw if s.endswith('px')][:12],
            }

        sizes = [float(h['fontSize'].replace('px', '')) for h in data['headings']]
        if len(sizes) < 2:
            return {
                'ratio': None,
                'sizes_px': [s for s in all_sizes_raw if s.endswith('px')][:12],
            }

        ratio = sizes[0] / sizes[1] if sizes[1] > 0 else 1

        return {
            'ratio': round(ratio, 2),
            'sizes_px': [s for s in all_sizes_raw if s.endswith('px')][:12],
            'heading_sizes_px': [f"{s}px" for s in sizes],
        }

    @staticmethod
    def _generate_typo_snippets(data: Dict) -> str:
        return (
            f"body {{\n"
            f"  font-family: {data['body']['fontFamily']};\n"
            f"  font-size: {data['body']['fontSize']};\n"
            f"  line-height: {data['body']['lineHeight']};\n"
            f"}}"
        )
