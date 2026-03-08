"""
Site Architecture Extractor — Framework, state management, routing, capabilities.

Detects window globals, script tag patterns, CSS framework signals, and DOM
signals to produce an ERD-style map of what the site IS and what it DOES or DOES NOT do.
"""

import logging
from typing import Dict
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class SiteArchitectureExtractor(BaseExtractor):
    name = "site_architecture"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Detecting site architecture...")

        arch_data = await ctx.page.evaluate('''() => {
            const result = {
                framework: null,
                css_framework: null,
                css_class_analysis: null,
                generator: null,
                cms: null,
                ssg: null,
                state_mgmt: null,
                router_type: null,
                data_layer: null,
                auth_detected: false,
                capabilities: {
                    client_side_routing: false,
                    server_side_rendering: false,
                    hydration: false,
                    graphql: false,
                    feature_flags: false,
                    prefetching: false,
                    websockets: false,
                    service_worker: false,
                    i18n: false
                },
                evidence: [],
                hydration_keys: [],
                routes: []
            };

            // ── Framework detection via window globals ──
            if (window.__NEXT_DATA__) {
                result.framework = 'Next.js';
                result.evidence.push('window.__NEXT_DATA__ present');
                const nd = window.__NEXT_DATA__;
                if (nd.page) result.routes.push(nd.page);
                if (nd.props && nd.props.pageProps) {
                    result.hydration_keys = Object.keys(nd.props.pageProps).slice(0, 12);
                }
                result.capabilities.server_side_rendering = true;
                result.capabilities.hydration = true;
                result.capabilities.prefetching = true;
                result.evidence.push('Next.js: SSR + hydration + prefetching by default');
                const pp = nd.props && nd.props.pageProps || {};
                if (pp.user || pp.session || pp.currentUser || pp.me || pp.account) {
                    result.auth_detected = true;
                    const key = pp.user ? 'user' : pp.session ? 'session' : pp.currentUser ? 'currentUser' : pp.me ? 'me' : 'account';
                    result.evidence.push('Auth: pageProps.' + key + ' present');
                }
            } else if (window.__NUXT__) {
                result.framework = 'Nuxt';
                result.evidence.push('window.__NUXT__ present');
                result.capabilities.server_side_rendering = true;
                result.capabilities.hydration = true;
                if (window.__NUXT__.state) {
                    result.hydration_keys = Object.keys(window.__NUXT__.state).slice(0, 12);
                }
            } else if (window.__APOLLO_STATE__ || window.__APOLLO_CLIENT__) {
                result.evidence.push('Apollo client detected');
                result.capabilities.graphql = true;
            }

            if (!result.framework) {
                const rootEl = document.getElementById('root') || document.getElementById('app') || document.getElementById('__next');
                if (rootEl && rootEl._reactRootContainer) {
                    result.framework = 'React';
                    result.evidence.push('_reactRootContainer on #root');
                } else if (rootEl && rootEl.__vue_app__) {
                    result.framework = 'Vue';
                    result.evidence.push('__vue_app__ on #app');
                } else if (window.ng) {
                    result.framework = 'Angular';
                    result.evidence.push('window.ng present');
                }
            }

            // ── Script attribute patterns for SSG/meta-frameworks ──
            const allScripts = Array.from(document.querySelectorAll('script'));
            const allEls = document.querySelectorAll('[data-nscript], [data-astro-cid], [data-sveltekit], [data-gatsby], [data-remix]');
            if (allEls.length > 0) {
                for (const el of allEls) {
                    if (el.hasAttribute('data-nscript') && !result.framework) {
                        result.framework = 'Next.js';
                        result.evidence.push('data-nscript attribute detected');
                    }
                    if (el.hasAttribute('data-astro-cid') || el.hasAttribute('data-astro-source-file')) {
                        result.ssg = 'Astro';
                        result.evidence.push('data-astro attribute detected');
                    }
                    if (el.hasAttribute('data-sveltekit')) {
                        result.framework = result.framework || 'SvelteKit';
                        result.ssg = 'SvelteKit';
                        result.evidence.push('data-sveltekit attribute detected');
                    }
                    if (el.hasAttribute('data-gatsby')) {
                        result.framework = result.framework || 'React';
                        result.ssg = 'Gatsby';
                        result.evidence.push('data-gatsby attribute detected');
                    }
                    if (el.hasAttribute('data-remix')) {
                        result.framework = result.framework || 'React';
                        result.ssg = 'Remix';
                        result.evidence.push('data-remix attribute detected');
                    }
                }
            }
            // Svelte detection via class pattern (svelte-xxxxxx)
            if (!result.framework) {
                const svelteEls = document.querySelectorAll('[class*="svelte-"]');
                if (svelteEls.length > 10) {
                    result.framework = 'Svelte';
                    result.evidence.push(svelteEls.length + ' elements with svelte-* classes');
                }
            }

            // ── Meta generator tag (CMS / SSG detection) ──
            const generatorMeta = document.querySelector('meta[name="generator"]');
            if (generatorMeta) {
                const gen = generatorMeta.content || '';
                result.generator = gen;
                result.evidence.push('meta[name=generator]: ' + gen.substring(0, 60));

                const genLower = gen.toLowerCase();
                if (genLower.includes('wordpress')) { result.cms = 'WordPress'; }
                else if (genLower.includes('drupal')) { result.cms = 'Drupal'; }
                else if (genLower.includes('joomla')) { result.cms = 'Joomla'; }
                else if (genLower.includes('shopify')) { result.cms = 'Shopify'; }
                else if (genLower.includes('squarespace')) { result.cms = 'Squarespace'; }
                else if (genLower.includes('wix')) { result.cms = 'Wix'; }
                else if (genLower.includes('webflow')) { result.cms = 'Webflow'; }
                else if (genLower.includes('ghost')) { result.cms = 'Ghost'; }

                if (genLower.includes('hugo')) { result.ssg = result.ssg || 'Hugo'; }
                else if (genLower.includes('gatsby')) { result.ssg = result.ssg || 'Gatsby'; }
                else if (genLower.includes('jekyll')) { result.ssg = result.ssg || 'Jekyll'; }
                else if (genLower.includes('eleventy') || genLower.includes('11ty')) { result.ssg = result.ssg || 'Eleventy'; }
                else if (genLower.includes('hexo')) { result.ssg = result.ssg || 'Hexo'; }
            }

            // ── CSS framework detection via class pattern matching ──
            const cssAnalysis = {
                tailwind: { count: 0, samples: [] },
                bootstrap: { count: 0, samples: [] },
                material_ui: { count: 0, samples: [] },
                bulma: { count: 0, samples: [] },
                chakra: { count: 0, samples: [] }
            };

            // Sample elements for class analysis (limit for performance)
            const sampleEls = document.querySelectorAll('body *');
            const maxSample = Math.min(sampleEls.length, 2000);

            // Tailwind patterns: utility classes like flex, px-4, text-sm, bg-*, w-*, etc.
            const twPatterns = /^(flex|grid|block|inline|hidden|relative|absolute|fixed|sticky|overflow-|z-|p[xytblr]?-|m[xytblr]?-|w-|h-|min-|max-|text-|font-|leading-|tracking-|bg-|border-|rounded|shadow|opacity-|transition|duration-|ease-|gap-|space-|justify-|items-|self-|order-|col-span|row-span|aspect-|cursor-|select-|resize-|snap-|scroll-|ring-|outline-|fill-|stroke-|sr-only|not-sr-only|container|prose|line-clamp|truncate|uppercase|lowercase|capitalize|italic|underline|no-underline|line-through|antialiased|tabular-nums|decoration-|indent-|align-|whitespace-|break-|hyphens-)/;

            // Bootstrap patterns
            const bsPatterns = /^(col-|row|container|btn-|nav-|navbar-|card-|modal-|form-|input-|badge-|alert-|dropdown-|table-|list-group|d-|mb-|mt-|ms-|me-|mx-|my-|p-|pb-|pt-|ps-|pe-|px-|py-|g-|gy-|gx-|fs-|fw-|text-center|text-start|text-end|float-|position-|top-|bottom-|start-|end-|translate-|ratio-|vw-|vh-|overflow-)/;

            // Material UI patterns (MUI)
            const muiPatterns = /^(Mui|css-[a-z0-9]{6}|MuiButton|MuiTypography|MuiContainer|MuiGrid|MuiPaper|MuiCard|MuiBox|MuiStack|MuiChip|MuiAvatar|makeStyles-)/;

            for (let i = 0; i < maxSample; i++) {
                const el = sampleEls[i];
                const classList = el.classList;
                if (!classList || classList.length === 0) continue;

                for (let j = 0; j < classList.length; j++) {
                    const cls = classList[j];
                    if (twPatterns.test(cls)) {
                        cssAnalysis.tailwind.count++;
                        if (cssAnalysis.tailwind.samples.length < 8) cssAnalysis.tailwind.samples.push(cls);
                    }
                    if (bsPatterns.test(cls)) {
                        cssAnalysis.bootstrap.count++;
                        if (cssAnalysis.bootstrap.samples.length < 8) cssAnalysis.bootstrap.samples.push(cls);
                    }
                    if (muiPatterns.test(cls)) {
                        cssAnalysis.material_ui.count++;
                        if (cssAnalysis.material_ui.samples.length < 8) cssAnalysis.material_ui.samples.push(cls);
                    }
                    // Bulma
                    if (/^(is-|has-|column|columns|hero|section|tile|level|media|notification|tag|tabs|breadcrumb|menu|panel)/.test(cls)) {
                        cssAnalysis.bulma.count++;
                    }
                    // Chakra UI
                    if (/^(chakra-|css-[a-z0-9]+$)/.test(cls) || (el.hasAttribute('data-theme') && el.closest('[class*="chakra"]'))) {
                        cssAnalysis.chakra.count++;
                    }
                }
            }

            result.css_class_analysis = cssAnalysis;

            // Determine winning CSS framework (threshold: 30+ matches)
            const cssThreshold = 30;
            const candidates = [];
            if (cssAnalysis.tailwind.count >= cssThreshold) {
                candidates.push({ name: 'Tailwind CSS', count: cssAnalysis.tailwind.count });
                result.evidence.push('Tailwind CSS: ' + cssAnalysis.tailwind.count + ' utility classes (' + cssAnalysis.tailwind.samples.slice(0, 4).join(', ') + ')');
            }
            if (cssAnalysis.bootstrap.count >= cssThreshold) {
                candidates.push({ name: 'Bootstrap', count: cssAnalysis.bootstrap.count });
                result.evidence.push('Bootstrap: ' + cssAnalysis.bootstrap.count + ' utility classes (' + cssAnalysis.bootstrap.samples.slice(0, 4).join(', ') + ')');
            }
            if (cssAnalysis.material_ui.count >= cssThreshold) {
                candidates.push({ name: 'Material UI', count: cssAnalysis.material_ui.count });
                result.evidence.push('Material UI: ' + cssAnalysis.material_ui.count + ' MUI classes (' + cssAnalysis.material_ui.samples.slice(0, 4).join(', ') + ')');
            }
            if (cssAnalysis.bulma.count >= cssThreshold) {
                candidates.push({ name: 'Bulma', count: cssAnalysis.bulma.count });
                result.evidence.push('Bulma: ' + cssAnalysis.bulma.count + ' Bulma classes');
            }
            if (cssAnalysis.chakra.count >= cssThreshold) {
                candidates.push({ name: 'Chakra UI', count: cssAnalysis.chakra.count });
                result.evidence.push('Chakra UI: ' + cssAnalysis.chakra.count + ' Chakra classes');
            }

            // Pick the highest-count winner
            if (candidates.length > 0) {
                candidates.sort(function(a, b) { return b.count - a.count; });
                result.css_framework = candidates[0].name;
            }

            // Also check for CSS framework stylesheets in <link> tags
            const linkHrefs = Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(function(l) { return l.href || ''; });
            linkHrefs.forEach(function(href) {
                const hrefLower = href.toLowerCase();
                if (hrefLower.includes('bootstrap') && !result.css_framework) {
                    result.css_framework = 'Bootstrap';
                    result.evidence.push('Bootstrap stylesheet: ' + href.substring(0, 80));
                }
                if (hrefLower.includes('bulma') && !result.css_framework) {
                    result.css_framework = 'Bulma';
                    result.evidence.push('Bulma stylesheet: ' + href.substring(0, 80));
                }
                if (hrefLower.includes('foundation') && !result.css_framework) {
                    result.css_framework = 'Foundation';
                    result.evidence.push('Foundation stylesheet: ' + href.substring(0, 80));
                }
            });

            // ── State management ──
            if (window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || window.__REDUX_DEVTOOLS_EXTENSION__) {
                result.state_mgmt = 'Redux';
                result.evidence.push('Redux DevTools extension hook detected');
            } else if (window.__APOLLO_STATE__) {
                result.state_mgmt = 'Apollo';
                result.evidence.push('Apollo state cache present');
            } else if (window.__NUXT__ && window.__NUXT__.state) {
                result.state_mgmt = 'Vuex/Pinia';
                result.evidence.push('Nuxt state present (Vuex or Pinia)');
            }

            // ── Router type ──
            if (window.location.hash && window.location.hash.length > 2) {
                result.router_type = 'hash-based';
                result.evidence.push('Hash fragment in URL: ' + window.location.hash.substring(0, 40));
            } else if (result.framework === 'Next.js' || result.framework === 'Nuxt') {
                result.router_type = 'client-side';
                result.capabilities.client_side_routing = true;
                result.evidence.push(result.framework + ' uses client-side routing');
            } else if (result.framework === 'React' || result.framework === 'Vue' || result.framework === 'Svelte' || result.framework === 'SvelteKit') {
                result.router_type = 'client-side (probable)';
                result.capabilities.client_side_routing = true;
                result.evidence.push(result.framework + ' detected - client-side routing probable');
            } else {
                result.router_type = 'server-rendered';
                result.evidence.push('No SPA framework globals - assuming server-rendered');
            }

            // ── GraphQL ──
            if (!result.capabilities.graphql) {
                if (window.__RELAY_STORE__ || window.relay) {
                    result.capabilities.graphql = true;
                    result.data_layer = 'Relay';
                    result.evidence.push('Relay store detected');
                }
            }
            if (result.capabilities.graphql && !result.data_layer) {
                result.data_layer = 'Apollo';
            }

            // ── Data layer ──
            if (!result.data_layer) {
                if (window.__SWR_CACHE__) {
                    result.data_layer = 'SWR';
                    result.evidence.push('SWR cache present');
                } else if (window.__REACT_QUERY_DEVTOOLS__) {
                    result.data_layer = 'React Query';
                    result.evidence.push('React Query devtools hook present');
                }
            }

            // ── Feature flags ──
            if (window.__FEATURE_FLAGS__ || window.__FLAGS__ || window.featureFlags) {
                result.capabilities.feature_flags = true;
                const flags = window.__FEATURE_FLAGS__ || window.__FLAGS__ || window.featureFlags;
                result.evidence.push('Feature flags object: ' + Object.keys(flags).slice(0, 5).join(', '));
            }
            if (window.LDClient || window.ldClient) {
                result.capabilities.feature_flags = true;
                result.evidence.push('LaunchDarkly client detected');
            }

            // ── Service worker ──
            if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                result.capabilities.service_worker = true;
                result.evidence.push('Active service worker registered');
            }

            // ── WebSocket ──
            try {
                const resources = performance.getEntriesByType('resource');
                const wsLike = resources.filter(r => r.name.startsWith('ws://') || r.name.startsWith('wss://'));
                if (wsLike.length > 0) {
                    result.capabilities.websockets = true;
                    result.evidence.push('WebSocket resource entries found');
                }
            } catch(e) {}

            // ── i18n ──
            if (window.i18n || window.__i18n__ || window.I18n || window.intl) {
                result.capabilities.i18n = true;
                result.evidence.push('i18n global detected');
            }
            if (window.__NEXT_DATA__ && window.__NEXT_DATA__.props && window.__NEXT_DATA__.props.pageProps && window.__NEXT_DATA__.props.pageProps.locale) {
                result.capabilities.i18n = true;
                result.evidence.push('Locale in Next.js pageProps');
            }

            // ── Bundler detection ──
            const scripts = Array.from(document.querySelectorAll('script[src]'));
            const scriptUrls = scripts.map(s => s.src);
            const bundlerSignals = { webpack: false, vite: false, parcel: false };
            scriptUrls.forEach(function(url) {
                if (url.includes('webpack') || url.includes('chunk')) bundlerSignals.webpack = true;
                if (url.includes('/@vite/') || url.includes('/src/') || url.includes('.module.')) bundlerSignals.vite = true;
                if (url.includes('parcel')) bundlerSignals.parcel = true;
            });
            result.bundler = bundlerSignals.vite ? 'Vite' : bundlerSignals.webpack ? 'Webpack' : bundlerSignals.parcel ? 'Parcel' : null;
            if (result.bundler) result.evidence.push('Bundler: ' + result.bundler);

            const prefetchLinks = document.querySelectorAll('link[rel="prefetch"], link[rel="preload"]');
            if (prefetchLinks.length > 0) {
                result.capabilities.prefetching = true;
                if (!result.evidence.some(function(e) { return e.includes('prefetch'); })) {
                    result.evidence.push(prefetchLinks.length + ' prefetch/preload link tags');
                }
            }

            return result;
        }''')

        evidence_count = len(arch_data.get('evidence', []))
        confidence = min(40 + evidence_count * 12, 95)

        if not arch_data.get('framework'):
            arch_data['framework'] = 'vanilla / unknown'

        # Build rich pattern string: "Next.js + Tailwind CSS" instead of just "Next.js"
        pattern_parts = [arch_data.get('framework', 'unknown')]
        if arch_data.get('css_framework'):
            pattern_parts.append(arch_data['css_framework'])
        if arch_data.get('ssg') and arch_data['ssg'] != arch_data.get('framework'):
            pattern_parts.insert(0, arch_data['ssg'])
        if arch_data.get('cms'):
            pattern_parts.insert(0, arch_data['cms'])

        pattern = ' + '.join(pattern_parts)

        return {
            'pattern': pattern,
            'confidence': confidence,
            'details': arch_data
        }
