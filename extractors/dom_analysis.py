"""
DOM Analysis Extractor — DOM depth and CSS tricks/custom properties.

Produces two evidence keys: 'dom_depth' and 'css_tricks'.
"""

import logging
from typing import Dict
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class DOMAnalysisExtractor(BaseExtractor):
    name = "dom_depth"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Analyzing DOM depth...")

        dom_data = await ctx.page.evaluate('''() => {
            function getMaxDepth(element, currentDepth = 1) {
                if (!element.children || element.children.length === 0) {
                    return currentDepth;
                }
                let maxChildDepth = currentDepth;
                for (let child of element.children) {
                    const childDepth = getMaxDepth(child, currentDepth + 1);
                    maxChildDepth = Math.max(maxChildDepth, childDepth);
                }
                return maxChildDepth;
            }

            const maxDepth = getMaxDepth(document.body);
            const totalElements = document.querySelectorAll('*').length;

            const deepPaths = [];
            function findDeepPaths(element, depth, path = []) {
                if (depth > maxDepth - 3) {
                    const tagPath = path.map(el => {
                        const id = el.id ? `#${el.id}` : '';
                        const classes = el.className && typeof el.className === 'string' ?
                            `.${el.className.split(' ').filter(c => c).slice(0, 2).join('.')}` : '';
                        return el.tagName.toLowerCase() + id + classes;
                    }).join(' > ');
                    deepPaths.push(tagPath);
                }
                for (let child of (element.children || [])) {
                    findDeepPaths(child, depth + 1, [...path, child]);
                }
            }
            findDeepPaths(document.body, 1, [document.body]);

            return {
                max_depth: maxDepth,
                total_elements: totalElements,
                average_depth: Math.round(totalElements / maxDepth),
                deep_paths: deepPaths.slice(0, 3)
            };
        }''')

        max_depth = dom_data.get('max_depth', 0)

        if max_depth <= 10:
            complexity = 'Low (Optimal)'
            health = 'excellent'
        elif max_depth <= 15:
            complexity = 'Medium (Good)'
            health = 'good'
        elif max_depth <= 20:
            complexity = 'High (Acceptable)'
            health = 'acceptable'
        else:
            complexity = 'Very High (Performance Risk)'
            health = 'poor'

        return {
            'pattern': f"Max depth: {max_depth} levels",
            'confidence': 100,
            'max_depth': max_depth,
            'total_elements': dom_data.get('total_elements', 0),
            'average_depth': dom_data.get('average_depth', 0),
            'complexity': complexity,
            'health': health,
            'deep_paths': dom_data.get('deep_paths', []),
            'recommendation': (
                'Typical depth is 10-15 levels. Deeper nesting can impact rendering performance.'
                if max_depth > 15 else 'DOM depth is within optimal range.'
            )
        }

    async def extract_css_tricks(self, ctx: ExtractionContext) -> Dict:
        """Extract CSS custom properties and advanced CSS features."""
        logger.info("Detecting CSS tricks...")

        css_data = await ctx.page.evaluate('''() => {
            const root = window.getComputedStyle(document.documentElement);
            const tricks = {
                custom_properties: [],
                supports_queries: [],
                viewport_units: false,
                css_grid_advanced: false,
                blend_modes: false,
                clip_path: false
            };

            for (let i = 0; i < root.length; i++) {
                const prop = root[i];
                if (prop.startsWith('--')) {
                    tricks.custom_properties.push({
                        name: prop,
                        value: root.getPropertyValue(prop)
                    });
                }
            }

            const elements = document.querySelectorAll('*');
            for (const el of elements) {
                const styles = window.getComputedStyle(el);
                if (styles.width.includes('vw') || styles.height.includes('vh')) {
                    tricks.viewport_units = true;
                }
                if (styles.mixBlendMode !== 'normal') {
                    tricks.blend_modes = true;
                }
                if (styles.clipPath !== 'none') {
                    tricks.clip_path = true;
                }
            }

            return tricks;
        }''')

        return {
            'pattern': f"{len(css_data['custom_properties'])} CSS variables detected",
            'confidence': 85,
            'details': css_data,
        }
