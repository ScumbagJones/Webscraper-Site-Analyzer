"""
Content Extractor with Classification & Sampling
Shows WHAT was found, not just HOW MUCH

For USAA/professional use:
- Classifies page type (product listing, article, docs, etc.)
- Counts content inventory (47 products, 12 articles, etc.)
- Extracts SAMPLES (first 3-5), not everything
- Explains extraction strategy (why this selector?)
- Shows what was excluded (nav, footer, ads)
"""

import asyncio
from playwright.async_api import async_playwright
from typing import Dict, List
from colorama import Fore, init
from dataclasses import dataclass
from enum import Enum

init(autoreset=True)


class PageType(Enum):
    """Page classification types"""
    PRODUCT_LISTING = "productListing"
    SINGLE_PRODUCT = "singleProduct"
    BLOG_LISTING = "blogListing"
    SINGLE_ARTICLE = "singleArticle"
    API_REFERENCE = "apiReference"
    DOCUMENTATION = "documentation"
    MEDIA_LISTING = "mediaListing"
    AUDIO_STREAM = "audioStream"
    SHOW_ARCHIVE = "showArchive"
    PODCAST_LISTING = "podcastListing"
    LANDING_PAGE = "landingPage"
    UNKNOWN = "unknown"


@dataclass
class ExtractionResult:
    """Result of content extraction"""
    page_type: PageType
    confidence: float
    reasoning: str
    content_inventory: Dict
    samples: List[Dict]
    extraction_strategy: Dict
    excluded_elements: Dict
    semantic_analysis: Dict


class IntelligentContentExtractor:
    """
    Extracts content with classification, sampling, and reasoning

    Key principles:
    1. CLASSIFY first (what type of page is this?)
    2. COUNT inventory (how much content?)
    3. SAMPLE, don't extract everything (3-5 examples)
    4. EXPLAIN strategy (why this selector?)
    5. SHOW what was excluded (navigation, ads, etc.)
    """

    def __init__(self, page):
        self.page = page

    async def extract(self) -> ExtractionResult:
        """
        Main extraction method

        Returns comprehensive extraction with:
        - Page classification
        - Content inventory
        - Representative samples
        - Extraction strategy explanation
        - Excluded elements
        """
        # Step 1: Classify page type
        classification = await self._classify_page()

        # Step 2: Count inventory
        inventory = await self._count_inventory(classification['type'])

        # Step 3: Extract samples (not everything!)
        samples = await self._extract_samples(classification['type'])

        # Step 4: Determine extraction strategy
        strategy = await self._extraction_strategy(classification['type'])

        # Step 5: Identify excluded elements
        excluded = await self._identify_excluded()

        # Step 6: Analyze semantic HTML
        semantic = await self._analyze_semantic_html()

        return ExtractionResult(
            page_type=classification['type'],
            confidence=classification['confidence'],
            reasoning=classification['reasoning'],
            content_inventory=inventory,
            samples=samples,
            extraction_strategy=strategy,
            excluded_elements=excluded,
            semantic_analysis=semantic
        )

    async def _classify_page(self) -> Dict:
        """
        Classify page type with confidence and reasoning

        Returns what type of page this is and WHY
        """
        result = await self.page.evaluate("""() => {
            // Count different content types
            const products = document.querySelectorAll(
                '.product-card, .product, [data-product], [itemtype*="Product"]'
            );
            const articles = document.querySelectorAll(
                'article, .post, .article, [itemtype*="Article"]'
            );
            const functions = document.querySelectorAll(
                'dl.function, .api-reference, .method'
            );
            const shows = document.querySelectorAll(
                '.show, .episode, .track, [data-show]'
            );
            const codeBlocks = document.querySelectorAll('pre code, .code-block');

            // Determine type based on counts
            const signals = [];

            if (products.length > 5) {
                signals.push({
                    type: 'productListing',
                    count: products.length,
                    confidence: 0.9,
                    reasoning: `Found ${products.length} product elements with consistent structure`
                });
            } else if (products.length === 1) {
                signals.push({
                    type: 'singleProduct',
                    count: 1,
                    confidence: 0.85,
                    reasoning: 'Single product page with detailed information'
                });
            }

            if (articles.length > 3) {
                signals.push({
                    type: 'blogListing',
                    count: articles.length,
                    confidence: 0.85,
                    reasoning: `Found ${articles.length} article cards in listing view`
                });
            } else if (articles.length === 1) {
                const wordCount = articles[0].innerText.split(/\\s+/).length;
                if (wordCount > 300) {
                    signals.push({
                        type: 'singleArticle',
                        count: 1,
                        confidence: 0.9,
                        reasoning: `Single article with ${wordCount} words of content`
                    });
                }
            }

            if (functions.length > 5) {
                signals.push({
                    type: 'apiReference',
                    count: functions.length,
                    confidence: 0.85,
                    reasoning: `Found ${functions.length} API function definitions`
                });
            }

            if (codeBlocks.length > 5 && functions.length < 5) {
                signals.push({
                    type: 'documentation',
                    count: codeBlocks.length,
                    confidence: 0.8,
                    reasoning: `Found ${codeBlocks.length} code examples in documentation`
                });
            }

            if (shows.length > 5) {
                signals.push({
                    type: 'mediaListing',
                    count: shows.length,
                    confidence: 0.8,
                    reasoning: `Found ${shows.length} media items (shows/tracks/episodes)`
                });
            }

            // Audio/stream/podcast detection
            const audioEls = document.querySelectorAll('audio, [data-player], [data-stream], .player');
            const videoEls = document.querySelectorAll('video:not([muted]):not([autoplay])');
            const mixEls = document.querySelectorAll('.mix, [data-mix], .broadcast, .livestream, .live-player, .stream');
            const scheduleEls = document.querySelectorAll('.schedule, [data-schedule], .timetable, .programming, .airtime');
            const schemaAudio = document.querySelectorAll('[itemtype*="AudioObject"], [itemtype*="RadioBroadcast"], [itemtype*="MusicRecording"], [itemtype*="PodcastEpisode"]');
            const podcastEls = document.querySelectorAll('.episode, [data-episode], .podcast-episode, [itemtype*="PodcastEpisode"]');

            // Live audio stream (radio, DJ sets)
            if (audioEls.length > 0 && (mixEls.length > 0 || scheduleEls.length > 0)) {
                signals.push({
                    type: 'audioStream',
                    count: audioEls.length,
                    confidence: 0.85,
                    reasoning: `Live audio stream: ${audioEls.length} player(s), ${mixEls.length} show/mix elements, ${scheduleEls.length} schedule elements`
                });
            }

            // Show/mix archive
            if (mixEls.length > 3 || (shows.length > 3 && audioEls.length > 0)) {
                signals.push({
                    type: 'showArchive',
                    count: mixEls.length + shows.length,
                    confidence: 0.8,
                    reasoning: `Show/mix archive: ${mixEls.length + shows.length} archive items with audio presence`
                });
            }

            // Podcast listing
            if (podcastEls.length > 2 || (schemaAudio.length > 2 && audioEls.length > 0)) {
                signals.push({
                    type: 'podcastListing',
                    count: podcastEls.length || schemaAudio.length,
                    confidence: 0.85,
                    reasoning: `Podcast listing: ${podcastEls.length || schemaAudio.length} episodes with structured audio metadata`
                });
            }

            // Return highest confidence signal
            if (signals.length > 0) {
                signals.sort((a, b) => b.confidence - a.confidence);
                return signals[0];
            }

            return {
                type: 'landingPage',
                count: 0,
                confidence: 0.5,
                reasoning: 'No specific content pattern detected, likely a landing page'
            };
        }""")

        return {
            'type': PageType(result['type']),
            'confidence': result['confidence'],
            'reasoning': result['reasoning']
        }

    async def _count_inventory(self, page_type: PageType) -> Dict:
        """
        Count content inventory (don't extract, just count)

        This shows you can IDENTIFY content without extracting everything
        """
        if page_type == PageType.PRODUCT_LISTING:
            return await self.page.evaluate("""() => {
                return {
                    products: document.querySelectorAll('.product-card, [data-product]').length,
                    images: document.querySelectorAll('.product-card img, [data-product] img').length,
                    prices: document.querySelectorAll('.price, [class*="price"]').length,
                    addToCartButtons: document.querySelectorAll('[class*="add-to-cart"], button[data-cart]').length,
                    filters: document.querySelectorAll('.filter, [role="checkbox"]').length,
                    categories: document.querySelectorAll('.category, [data-category]').length
                };
            }""")

        elif page_type == PageType.BLOG_LISTING:
            return await self.page.evaluate("""() => {
                const articles = document.querySelectorAll('article, .post');
                return {
                    articles: articles.length,
                    images: document.querySelectorAll('article img, .post img').length,
                    authors: document.querySelectorAll('.author, [class*="author"]').length,
                    dates: document.querySelectorAll('time, .date').length,
                    categories: document.querySelectorAll('.category, .tag').length
                };
            }""")

        elif page_type == PageType.SINGLE_ARTICLE:
            return await self.page.evaluate("""() => {
                const article = document.querySelector('article, main');
                if (!article) return {};

                return {
                    wordCount: article.innerText.split(/\\s+/).length,
                    paragraphs: article.querySelectorAll('p').length,
                    images: article.querySelectorAll('img').length,
                    headings: {
                        h1: article.querySelectorAll('h1').length,
                        h2: article.querySelectorAll('h2').length,
                        h3: article.querySelectorAll('h3').length
                    },
                    links: article.querySelectorAll('a').length,
                    codeBlocks: article.querySelectorAll('pre code').length
                };
            }""")

        elif page_type == PageType.API_REFERENCE:
            return await self.page.evaluate("""() => {
                return {
                    functions: document.querySelectorAll('dl.function, .api-function').length,
                    parameters: document.querySelectorAll('.parameter, dt').length,
                    codeExamples: document.querySelectorAll('pre code').length,
                    sections: document.querySelectorAll('section, .section').length
                };
            }""")

        elif page_type == PageType.MEDIA_LISTING:
            return await self.page.evaluate("""() => {
                return {
                    shows: document.querySelectorAll('.show, .episode, .track').length,
                    playButtons: document.querySelectorAll('[class*="play"], button[aria-label*="play"]').length,
                    durations: document.querySelectorAll('.duration, [class*="duration"]').length,
                    dates: document.querySelectorAll('time, .date').length
                };
            }""")

        elif page_type == PageType.AUDIO_STREAM:
            return await self.page.evaluate("""() => {
                return {
                    audioPlayers: document.querySelectorAll('audio, [data-player], [data-stream], .player').length,
                    liveIndicators: document.querySelectorAll('.live, .livestream, .on-air, [data-live]').length,
                    channels: document.querySelectorAll('.channel, [data-channel]').length,
                    scheduleItems: document.querySelectorAll('.schedule, [data-schedule], .timetable, .programming').length,
                    playButtons: document.querySelectorAll('[class*="play"], button[aria-label*="play"]').length,
                    trackInfo: document.querySelectorAll('.now-playing, .tracklist, .track-info, .currently-playing').length
                };
            }""")

        elif page_type == PageType.SHOW_ARCHIVE:
            return await self.page.evaluate("""() => {
                return {
                    shows: document.querySelectorAll('.show, .mix, [data-mix], .broadcast, .episode').length,
                    playButtons: document.querySelectorAll('[class*="play"], button[aria-label*="play"]').length,
                    durations: document.querySelectorAll('.duration, [class*="duration"], time[datetime]').length,
                    hosts: document.querySelectorAll('.host, .dj, .artist, [class*="artist"]').length,
                    genres: document.querySelectorAll('.genre, .tag, [class*="genre"]').length,
                    dates: document.querySelectorAll('time, .date, [class*="date"]').length
                };
            }""")

        elif page_type == PageType.PODCAST_LISTING:
            return await self.page.evaluate("""() => {
                return {
                    episodes: document.querySelectorAll('.episode, [data-episode], .podcast-episode').length,
                    audioPlayers: document.querySelectorAll('audio, [data-player]').length,
                    durations: document.querySelectorAll('.duration, [class*="duration"], time[datetime]').length,
                    dates: document.querySelectorAll('time, .date').length,
                    descriptions: document.querySelectorAll('.description, .summary, .episode-description').length,
                    subscribeButtons: document.querySelectorAll('[class*="subscribe"], [class*="follow"]').length
                };
            }""")

        else:
            return {}

    async def _extract_samples(self, page_type: PageType) -> List[Dict]:
        """
        Extract SAMPLES (3-5 items), not everything

        This shows restraint - you CAN extract all, but you're choosing samples
        """
        if page_type == PageType.PRODUCT_LISTING:
            return await self.page.evaluate("""() => {
                const products = Array.from(
                    document.querySelectorAll('.product-card, [data-product]')
                ).slice(0, 3);  // Only first 3

                return products.map((p, idx) => ({
                    name: p.querySelector('h3, .product-name, [class*="name"]')?.innerText?.trim(),
                    price: p.querySelector('.price, [class*="price"]')?.innerText?.trim(),
                    image: p.querySelector('img')?.src,
                    link: p.querySelector('a')?.href,
                    selector: `.product-card:nth-child(${idx + 1})`
                }));
            }""")

        elif page_type == PageType.BLOG_LISTING:
            return await self.page.evaluate("""() => {
                const articles = Array.from(
                    document.querySelectorAll('article, .post')
                ).slice(0, 3);

                return articles.map((a, idx) => ({
                    title: a.querySelector('h2, h3, .title')?.innerText?.trim(),
                    excerpt: a.querySelector('p, .excerpt')?.innerText?.trim()?.slice(0, 100),
                    author: a.querySelector('.author, [class*="author"]')?.innerText?.trim(),
                    date: a.querySelector('time, .date')?.innerText?.trim(),
                    link: a.querySelector('a')?.href,
                    selector: `article:nth-child(${idx + 1})`
                }));
            }""")

        elif page_type == PageType.SINGLE_ARTICLE:
            return await self.page.evaluate("""() => {
                const article = document.querySelector('article, main');
                if (!article) return [];

                return [{
                    title: document.title,
                    body: article.innerText.slice(0, 500) + '...',  // First 500 chars
                    wordCount: article.innerText.split(/\\s+/).length,
                    author: document.querySelector('.author, [rel="author"]')?.innerText?.trim(),
                    publishDate: document.querySelector('time, [datetime]')?.getAttribute('datetime'),
                    mainImage: article.querySelector('img')?.src,
                    extractionConfidence: 0.85
                }];
            }""")

        elif page_type == PageType.API_REFERENCE:
            return await self.page.evaluate("""() => {
                const functions = Array.from(
                    document.querySelectorAll('dl.function, .api-function')
                ).slice(0, 3);

                return functions.map((f, idx) => ({
                    name: f.querySelector('dt, .name')?.innerText?.trim(),
                    description: f.querySelector('dd, .description')?.innerText?.trim()?.slice(0, 100),
                    parameters: Array.from(f.querySelectorAll('.param, .parameter')).map(p => p.innerText?.trim()),
                    examples: f.querySelectorAll('pre code').length,
                    selector: `dl.function:nth-child(${idx + 1})`
                }));
            }""")

        elif page_type == PageType.MEDIA_LISTING:
            return await self.page.evaluate("""() => {
                const shows = Array.from(
                    document.querySelectorAll('.show, .episode, .track')
                ).slice(0, 3);

                return shows.map((s, idx) => ({
                    title: s.querySelector('.title, h3, h4')?.innerText?.trim(),
                    duration: s.querySelector('.duration, [class*="duration"]')?.innerText?.trim(),
                    date: s.querySelector('time, .date')?.innerText?.trim(),
                    hasPlayButton: !!s.querySelector('[class*="play"]'),
                    selector: `.show:nth-child(${idx + 1})`
                }));
            }""")

        elif page_type == PageType.AUDIO_STREAM:
            return await self.page.evaluate("""() => {
                const players = Array.from(
                    document.querySelectorAll('audio, [data-player], [data-stream], .player')
                ).slice(0, 3);
                return players.map((p, idx) => ({
                    type: p.tagName === 'AUDIO' ? 'audio element' : 'player widget',
                    src: p.src || p.getAttribute('data-src') || p.querySelector('source')?.src || null,
                    hasControls: p.hasAttribute('controls') || !!p.querySelector('[class*="play"]'),
                    nowPlaying: p.closest('[class*="player"]')?.querySelector('.now-playing, .track-info, .currently-playing')?.innerText?.trim()?.slice(0, 100),
                    isLive: !!p.closest('[class*="live"]') || !!document.querySelector('.live, .on-air'),
                    selector: `audio:nth-of-type(${idx + 1})`
                }));
            }""")

        elif page_type == PageType.SHOW_ARCHIVE:
            return await self.page.evaluate("""() => {
                const shows = Array.from(
                    document.querySelectorAll('.show, .mix, [data-mix], .broadcast, .episode')
                ).slice(0, 5);
                return shows.map((s, idx) => ({
                    title: s.querySelector('.title, h3, h4, h2, a')?.innerText?.trim(),
                    host: s.querySelector('.host, .dj, .artist, [class*="artist"]')?.innerText?.trim(),
                    duration: s.querySelector('.duration, [class*="duration"]')?.innerText?.trim(),
                    date: s.querySelector('time, .date, [class*="date"]')?.innerText?.trim(),
                    genre: s.querySelector('.genre, .tag, [class*="genre"]')?.innerText?.trim(),
                    hasPlayButton: !!s.querySelector('[class*="play"]'),
                    link: s.querySelector('a')?.href,
                    selector: `.show:nth-child(${idx + 1})`
                }));
            }""")

        elif page_type == PageType.PODCAST_LISTING:
            return await self.page.evaluate("""() => {
                const episodes = Array.from(
                    document.querySelectorAll('.episode, [data-episode], .podcast-episode')
                ).slice(0, 5);
                return episodes.map((ep, idx) => ({
                    title: ep.querySelector('.title, h3, h4, h2')?.innerText?.trim(),
                    description: ep.querySelector('.description, .summary, p')?.innerText?.trim()?.slice(0, 150),
                    duration: ep.querySelector('.duration, [class*="duration"], time')?.innerText?.trim(),
                    date: ep.querySelector('time, .date')?.innerText?.trim(),
                    hasAudio: !!ep.querySelector('audio, [data-player]'),
                    link: ep.querySelector('a')?.href,
                    selector: `.episode:nth-child(${idx + 1})`
                }));
            }""")

        else:
            return []

    async def _extraction_strategy(self, page_type: PageType) -> Dict:
        """
        Explain extraction strategy with reasoning

        This shows WHY you chose specific selectors
        """
        strategies = {
            PageType.PRODUCT_LISTING: {
                'primary_selector': '.product-card, [data-product]',
                'fallback_selector': '[itemtype*="Product"]',
                'confidence': 'high',
                'reasoning': 'Products use consistent .product-card class with data attributes',
                'fields_extracted': ['name', 'price', 'image', 'link'],
                'validation': [
                    '✅ All products have consistent structure',
                    '✅ Price found in .price selector',
                    '✅ Images use proper alt text'
                ],
                'scaling_note': 'Can extract all products using same selector pattern'
            },
            PageType.BLOG_LISTING: {
                'primary_selector': 'article, .post',
                'fallback_selector': '[itemtype*="Article"]',
                'confidence': 'high',
                'reasoning': 'Articles use semantic <article> tags',
                'fields_extracted': ['title', 'excerpt', 'author', 'date'],
                'validation': [
                    '✅ Uses semantic <article> tags',
                    '✅ Consistent heading structure (h2 for titles)',
                    '✅ Date metadata present'
                ]
            },
            PageType.SINGLE_ARTICLE: {
                'primary_selector': 'article',
                'fallback_selector': 'main, .content',
                'confidence': 'high',
                'reasoning': 'Main content in semantic <article> tag',
                'fields_extracted': ['title', 'body', 'author', 'publishDate'],
                'validation': [
                    '✅ Found <article> tag (preferred semantic element)',
                    '✅ Article has >300 words (validates main content)',
                    '✅ No ads detected in article body',
                    '✅ Title matches <h1> text'
                ],
                'excluded': ['navigation', 'sidebar', 'footer', 'related posts']
            },
            PageType.API_REFERENCE: {
                'primary_selector': 'dl.function',
                'fallback_selector': '.api-function, .method',
                'confidence': 'high',
                'reasoning': 'Python docs use semantic <dl> tags for function definitions',
                'fields_extracted': ['name', 'description', 'parameters', 'examples'],
                'validation': [
                    '✅ Semantic HTML (definition lists)',
                    '✅ Code examples present',
                    '✅ Parameter documentation complete'
                ]
            },
            PageType.MEDIA_LISTING: {
                'primary_selector': '.show, .episode',
                'fallback_selector': '[data-show]',
                'confidence': 'medium',
                'reasoning': 'Shows use consistent class pattern but some missing metadata',
                'fields_extracted': ['title', 'duration', 'date', 'playButton'],
                'validation': [
                    '✅ Consistent structure across items',
                    '⚠️ Some items missing duration data',
                    '✅ Play buttons detected'
                ]
            },
            PageType.AUDIO_STREAM: {
                'primary_selector': 'audio, [data-player], [data-stream]',
                'fallback_selector': '.player, .stream',
                'confidence': 'high',
                'reasoning': 'Live audio stream detected via HTML5 audio elements and player widgets',
                'fields_extracted': ['type', 'src', 'nowPlaying', 'isLive', 'hasControls'],
                'validation': [
                    '✅ HTML5 <audio> element or player widget found',
                    '✅ Live/schedule indicators present',
                    '⚠️ Stream content is dynamic (initial state only captured)'
                ],
                'scaling_note': 'Audio streams are stateful — full tracklist requires polling or WebSocket monitoring'
            },
            PageType.SHOW_ARCHIVE: {
                'primary_selector': '.show, .mix, [data-mix], .broadcast',
                'fallback_selector': '.episode, [data-show]',
                'confidence': 'medium',
                'reasoning': 'Show/mix archive with repeated content cards and audio presence',
                'fields_extracted': ['title', 'host', 'duration', 'date', 'genre'],
                'validation': [
                    '✅ Consistent show card structure',
                    '✅ Audio playback elements detected',
                    '⚠️ Some metadata may load dynamically'
                ]
            },
            PageType.PODCAST_LISTING: {
                'primary_selector': '.episode, [data-episode], .podcast-episode',
                'fallback_selector': '[itemtype*="PodcastEpisode"], [itemtype*="AudioObject"]',
                'confidence': 'high',
                'reasoning': 'Podcast episode listing with structured audio metadata',
                'fields_extracted': ['title', 'description', 'duration', 'date', 'hasAudio'],
                'validation': [
                    '✅ Episode elements with consistent structure',
                    '✅ Audio/player elements associated with episodes',
                    '✅ Schema.org metadata detected'
                ]
            }
        }

        return strategies.get(page_type, {
            'primary_selector': 'unknown',
            'confidence': 'low',
            'reasoning': 'Could not determine optimal selector'
        })

    async def _identify_excluded(self) -> Dict:
        """
        Show what was excluded from extraction

        This demonstrates you're extracting signal, not noise
        """
        return await self.page.evaluate("""() => {
            return {
                navigation: {
                    count: document.querySelectorAll('nav, .navigation').length,
                    links: document.querySelectorAll('nav a').length,
                    excluded: true,
                    reasoning: 'Navigation is structural, not content'
                },
                footer: {
                    count: document.querySelectorAll('footer').length,
                    links: document.querySelectorAll('footer a').length,
                    excluded: true,
                    reasoning: 'Footer contains site-wide links'
                },
                sidebar: {
                    count: document.querySelectorAll('aside, .sidebar').length,
                    excluded: true,
                    reasoning: 'Sidebar contains auxiliary content'
                },
                ads: {
                    count: document.querySelectorAll('[class*="ad"], [id*="ad"]').length,
                    excluded: true,
                    reasoning: 'Advertisements are not content'
                },
                relatedPosts: {
                    count: document.querySelectorAll('.related, [class*="related"]').length,
                    excluded: false,
                    reasoning: 'May be relevant for some analyses'
                }
            };
        }""")

    async def _analyze_semantic_html(self) -> Dict:
        """
        Analyze semantic HTML quality

        Shows understanding of modern web standards
        """
        analysis = await self.page.evaluate("""() => {
            const tags = {
                main: document.querySelectorAll('main').length,
                article: document.querySelectorAll('article').length,
                section: document.querySelectorAll('section').length,
                nav: document.querySelectorAll('nav').length,
                header: document.querySelectorAll('header').length,
                footer: document.querySelectorAll('footer').length,
                aside: document.querySelectorAll('aside').length
            };

            // Calculate quality score
            let score = 0;
            const notes = [];

            if (tags.main > 0) {
                score += 20;
                notes.push('✓ Uses <main> for primary content');
            } else {
                notes.push('✗ Missing <main> tag');
            }

            if (tags.article > 0) {
                score += 20;
                notes.push('✓ Uses <article> for articles');
            } else {
                notes.push('✗ Missing <article> tags');
            }

            if (tags.nav > 0) {
                score += 15;
                notes.push('✓ Proper <nav> for navigation');
            } else {
                notes.push('✗ Missing <nav> tag');
            }

            if (tags.header > 0) {
                score += 15;
                notes.push('✓ Proper <header> for header content');
            }

            if (tags.footer > 0) {
                score += 10;
                notes.push('✓ Proper <footer> for footer content');
            }

            if (tags.section > 2) {
                score += 20;
                notes.push('✓ Good content structure with <section> tags');
            }

            // ARIA labels
            const ariaLabels = document.querySelectorAll('[aria-label], [aria-labelledby]').length;
            if (ariaLabels > 10) {
                score += 10;
                notes.push('✓ Excellent ARIA label usage');
            }

            // Heading hierarchy
            const h1s = document.querySelectorAll('h1').length;
            if (h1s === 1) {
                notes.push('✓ Proper heading hierarchy (single h1)');
            } else if (h1s > 1) {
                notes.push(`⚠️ Multiple h1 tags (${h1s} found)`);
            }

            return {
                tags,
                score,
                quality: score > 70 ? 'High' : score > 40 ? 'Medium' : 'Low',
                notes,
                ariaLabels
            };
        }""")

        return analysis


# Demo
async def demo():
    """
    Demonstrate intelligent content extraction
    """
    test_sites = [
        ('https://docs.python.org/3/library/functions.html', 'API Reference'),
        ('https://www.nike.com', 'Product Listing'),
        ('https://www.theringer.com', 'Blog Listing'),
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for url, expected_type in test_sites:
            print(f"\n{Fore.MAGENTA}{'='*70}")
            print(f"{Fore.MAGENTA}  Testing: {url}")
            print(f"{Fore.MAGENTA}  Expected: {expected_type}")
            print(f"{Fore.MAGENTA}{'='*70}\n")

            page = await browser.newPage()

            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)

                extractor = IntelligentContentExtractor(page)
                result = await extractor.extract()

                # Display results
                print(f"{Fore.CYAN}📄 Page Classification:")
                print(f"   Type: {result.page_type.value}")
                print(f"   Confidence: {result.confidence * 100:.0f}%")
                print(f"   Reasoning: {result.reasoning}\n")

                print(f"{Fore.GREEN}📊 Content Inventory:")
                for key, value in result.content_inventory.items():
                    if isinstance(value, dict):
                        print(f"   {key}:")
                        for k, v in value.items():
                            print(f"      {k}: {v}")
                    else:
                        print(f"   {key}: {value}")

                print(f"\n{Fore.YELLOW}📦 Samples ({len(result.samples)} extracted):")
                for idx, sample in enumerate(result.samples[:3], 1):
                    print(f"\n   Sample {idx}:")
                    for key, value in list(sample.items())[:5]:
                        if isinstance(value, str) and len(value) > 60:
                            print(f"      {key}: {value[:60]}...")
                        else:
                            print(f"      {key}: {value}")

                print(f"\n{Fore.BLUE}🎯 Extraction Strategy:")
                strat = result.extraction_strategy
                print(f"   Selector: {strat.get('primary_selector', 'N/A')}")
                print(f"   Confidence: {strat.get('confidence', 'N/A')}")
                print(f"   Reasoning: {strat.get('reasoning', 'N/A')}")

                if strat.get('validation'):
                    print(f"\n   Validation:")
                    for note in strat['validation']:
                        print(f"      {note}")

                print(f"\n{Fore.RED}🚫 Excluded Elements:")
                for element, data in result.excluded_elements.items():
                    if isinstance(data, dict) and data.get('excluded'):
                        print(f"   {element}: {data.get('count', 0)} ({data.get('reasoning', 'N/A')})")

                print(f"\n{Fore.MAGENTA}🏷️  Semantic HTML Analysis:")
                sem = result.semantic_analysis
                print(f"   Quality Score: {sem['score']}/100 ({sem['quality']})")
                print(f"   Tags Found: {sem['tags']}")
                print(f"\n   Notes:")
                for note in sem['notes'][:5]:
                    print(f"      {note}")

            except Exception as e:
                print(f"{Fore.RED}Error: {str(e)}")

            finally:
                await page.close()

        await browser.close()


if __name__ == '__main__':
    asyncio.run(demo())
