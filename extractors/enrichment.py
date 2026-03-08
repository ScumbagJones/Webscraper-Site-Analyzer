"""
Enrichment Extractor — Post-processing pass that adds statistics and plain language summaries.

Unlike other extractors, this one modifies existing evidence in ExtractionContext
rather than producing a single new evidence key. It runs last.
"""

import logging
from typing import Dict
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class EnrichmentExtractor(BaseExtractor):
    name = "enrichment"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        """
        Enrich existing evidence with statistical fields and plain language summaries.

        Returns a metadata dict rather than a metric result. The actual enrichment
        is applied directly to ctx.evidence.
        """
        logger.info("Enriching evidence with statistical fields...")

        # Add statistical fields to typography
        typography = ctx.evidence.get('typography', {})
        if typography and typography.get('details'):
            details = typography['details']
            if details.get('all_fonts'):
                typography['fonts'] = details['all_fonts']
                typography['total_fonts'] = len(details['all_fonts'])
            if details.get('all_sizes'):
                typography['sizes'] = details['all_sizes']
                typography['total_sizes'] = len(details['all_sizes'])

        # Add statistical fields to colors
        colors = ctx.evidence.get('colors', {})
        if colors and colors.get('palette'):
            palette = colors['palette']
            total = sum(len(v) if isinstance(v, list) else 0 for v in palette.values())
            colors['total_unique_colors'] = total

        # Add plain language summaries
        logger.info("Adding plain language summaries...")
        summary_keys = [
            'shadow_system', 'typography', 'colors', 'spacing_scale',
            'responsive_breakpoints', 'z_index_stack', 'visual_hierarchy',
            'layout_system', 'interaction_states'
        ]
        for key in summary_keys:
            if key in ctx.evidence and ctx.evidence[key]:
                summary = self._generate_summary(key, ctx.evidence[key])
                if summary:
                    ctx.evidence[key]['plain_language_summary'] = summary

        return {
            'pattern': 'Evidence enriched',
            'confidence': 100,
            'summaries_added': len([k for k in summary_keys if k in ctx.evidence])
        }

    def _generate_summary(self, metric_name: str, evidence: Dict) -> str:
        """Generate a plain-language summary for a metric."""
        generators = {
            'typography': self._summarize_typography,
            'colors': self._summarize_colors,
            'spacing_scale': self._summarize_spacing,
            'shadow_system': self._summarize_shadows,
        }

        generator = generators.get(metric_name)
        if generator:
            try:
                return generator(evidence)
            except Exception:
                return None
        return None

    @staticmethod
    def _summarize_typography(evidence: Dict) -> str:
        details = evidence.get('details', {})
        families = details.get('all_fonts', [])
        sizes = details.get('all_sizes', [])
        primary_family = details.get('body', {}).get('fontFamily', 'unknown').split(',')[0].strip().replace('"', '')

        if len(sizes) <= 5:
            size_desc = "a tight set of text sizes (disciplined system)"
        elif len(sizes) <= 10:
            size_desc = "a moderate range of text sizes"
        else:
            size_desc = "many text sizes (may feel inconsistent)"

        return (
            f"This site uses {len(families)} font family/families with {size_desc}. "
            f"Primary font: {primary_family}."
        )

    @staticmethod
    def _summarize_colors(evidence: Dict) -> str:
        primary_colors = len(evidence.get('primary_colors', []))
        total_colors = evidence.get('total_unique_colors', 0)

        if primary_colors <= 3:
            palette_desc = "minimal, focused palette"
        elif primary_colors <= 5:
            palette_desc = "balanced color system"
        else:
            palette_desc = "extensive color palette"

        return f"This site uses a {palette_desc} with {total_colors} unique colors total."

    @staticmethod
    def _summarize_spacing(evidence: Dict) -> str:
        scale = evidence.get('scale', [])
        base_unit = evidence.get('base_unit')

        if not scale:
            return "No consistent spacing system detected."

        if base_unit:
            return (
                f"This site uses a strict {base_unit} spacing system with {len(scale)} increments. "
                f"This creates consistent rhythm and visual alignment."
            )

        return (
            f"This site uses {len(scale)} distinct spacing values. "
            f"Range: {min(scale)}px to {max(scale)}px."
        )

    @staticmethod
    def _summarize_shadows(evidence: Dict) -> str:
        levels = evidence.get('levels', [])
        if not levels:
            return "This site uses a flat design with no box shadows."

        return (
            f"This site uses {len(levels)} shadow level(s), "
            f"creating depth through elevation."
        )
