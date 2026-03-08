"""
SEO Extractor — Meta tags, Open Graph, canonical links, heading structure, brand assets.

Evaluates search-engine-relevant metadata, extracts logo/favicon/OG image,
and produces a score based on presence of key signals.
"""

import logging
from typing import Dict
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class SEOExtractor(BaseExtractor):
    name = "seo"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Analyzing SEO...")

        seo_data = await ctx.page.evaluate('''() => {
            const getMeta = (name) => {
                const meta = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
                return meta ? meta.content : null;
            };

            return {
                title: document.title,
                description: getMeta('description'),
                og_title: getMeta('og:title'),
                og_description: getMeta('og:description'),
                og_image: getMeta('og:image'),
                twitter_card: getMeta('twitter:card'),
                canonical: document.querySelector('link[rel="canonical"]')?.href,
                h1_count: document.querySelectorAll('h1').length,
                h1_text: document.querySelector('h1')?.innerText
            };
        }''')

        # Extract brand assets (logo, favicon, OG image)
        brand_assets = await ctx.page.evaluate('''() => {
            const result = {
                logo: null,
                favicon: null,
                og_image: null
            };

            // ── Logo detection heuristics ──
            const logoCandidates = [];

            // 1. Images/SVGs inside <header> or <nav> that link to "/"
            const headerNavEls = document.querySelectorAll('header, nav');
            headerNavEls.forEach(container => {
                // Look for <a href="/"> containing <img> or <svg>
                const homeLinks = container.querySelectorAll('a[href="/"], a[href="' + window.location.origin + '/"], a[href="' + window.location.origin + '"]');
                homeLinks.forEach(link => {
                    const img = link.querySelector('img');
                    if (img && img.src) {
                        const rect = img.getBoundingClientRect();
                        logoCandidates.push({
                            url: img.src,
                            alt: img.alt || '',
                            selector: img.id ? '#' + img.id : 'header img',
                            type: 'img',
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            score: 10  // Highest: img inside home link in header
                        });
                    }
                    const svg = link.querySelector('svg');
                    if (svg) {
                        const rect = svg.getBoundingClientRect();
                        logoCandidates.push({
                            url: null,
                            alt: svg.getAttribute('aria-label') || link.getAttribute('aria-label') || '',
                            selector: 'header a[href="/"] svg',
                            type: 'svg',
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            score: 9
                        });
                    }
                });

                // Also check for standalone images in header (not in a home link)
                const headerImgs = container.querySelectorAll('img');
                headerImgs.forEach(img => {
                    if (!img.src) return;
                    const rect = img.getBoundingClientRect();
                    if (rect.width < 20 || rect.height < 20) return;
                    if (rect.width > 400 || rect.height > 200) return; // Too large to be a logo
                    logoCandidates.push({
                        url: img.src,
                        alt: img.alt || '',
                        selector: img.id ? '#' + img.id : 'header img',
                        type: 'img',
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        score: 5
                    });
                });
            });

            // 2. Elements with class/id containing "logo"
            const logoEls = document.querySelectorAll('[class*="logo"], [id*="logo"], [class*="Logo"], [id*="Logo"]');
            logoEls.forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return;

                // Check if it's an img
                if (el.tagName === 'IMG' && el.src) {
                    logoCandidates.push({
                        url: el.src,
                        alt: el.alt || '',
                        selector: el.id ? '#' + el.id : '.' + (el.className || '').toString().split(/\\s+/)[0],
                        type: 'img',
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        score: 8
                    });
                } else if (el.tagName === 'svg' || el.querySelector('svg')) {
                    logoCandidates.push({
                        url: null,
                        alt: el.getAttribute('aria-label') || el.textContent?.trim().substring(0, 40) || '',
                        selector: el.id ? '#' + el.id : '[class*="logo"]',
                        type: 'svg',
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        score: 7
                    });
                } else {
                    // It might contain an img
                    const innerImg = el.querySelector('img');
                    if (innerImg && innerImg.src) {
                        logoCandidates.push({
                            url: innerImg.src,
                            alt: innerImg.alt || '',
                            selector: el.id ? '#' + el.id + ' img' : '[class*="logo"] img',
                            type: 'img',
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            score: 7
                        });
                    }
                }
            });

            // Pick highest-scoring logo candidate
            if (logoCandidates.length > 0) {
                logoCandidates.sort(function(a, b) { return b.score - a.score; });
                result.logo = logoCandidates[0];
            }

            // ── Favicon detection ──
            const faviconLink = document.querySelector('link[rel="icon"], link[rel="shortcut icon"]');
            const appleTouchIcon = document.querySelector('link[rel="apple-touch-icon"], link[rel="apple-touch-icon-precomposed"]');

            if (faviconLink) {
                result.favicon = {
                    url: faviconLink.href,
                    rel: faviconLink.rel,
                    sizes: faviconLink.getAttribute('sizes') || null,
                    type: faviconLink.getAttribute('type') || null
                };
            } else if (appleTouchIcon) {
                result.favicon = {
                    url: appleTouchIcon.href,
                    rel: appleTouchIcon.rel,
                    sizes: appleTouchIcon.getAttribute('sizes') || null,
                    type: appleTouchIcon.getAttribute('type') || null
                };
            }

            // ── OG Image ──
            const ogImg = document.querySelector('meta[property="og:image"]');
            if (ogImg && ogImg.content) {
                result.og_image = { url: ogImg.content };
            }

            return result;
        }''')

        score = self._calculate_seo_score(seo_data)

        return {
            'pattern': f"SEO Score: {score}/100",
            'confidence': 90,
            'score': score,
            'details': seo_data,
            'brand_assets': brand_assets,
            'recommendations': self._generate_seo_recommendations(seo_data)
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_seo_score(data):
        score = 0
        if data['title']:
            score += 20
        if data['description']:
            score += 20
        if data['og_title']:
            score += 15
        if data['canonical']:
            score += 15
        if data['h1_count'] == 1:
            score += 15
        if data['og_image']:
            score += 15
        return score

    @staticmethod
    def _generate_seo_recommendations(data):
        recs = []
        if not data['description']:
            recs.append("Add meta description")
        if data['h1_count'] != 1:
            recs.append(f"Use exactly one H1 tag (currently: {data['h1_count']})")
        return recs
