"""
Article Content Extractor — Finds articles via <article> tags and common patterns.

Uses BeautifulSoup to parse HTML rather than page.evaluate.
"""

import logging
from typing import Dict, Optional
from bs4 import BeautifulSoup
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class ArticleContentExtractor(BaseExtractor):
    name = "article_content"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Extracting article content...")

        soup = BeautifulSoup(ctx.html_content, 'html.parser')
        articles = []

        # Strategy 1: <article> tags
        article_tags = soup.find_all('article')
        for article in article_tags[:5]:
            content = self._extract_article_from_element(article)
            if content:
                articles.append(content)

        # Strategy 2: Common article class patterns
        if len(articles) == 0:
            for selector in ['.article', '.post', '.entry-content', 'main']:
                elements = soup.select(selector)
                for el in elements[:3]:
                    content = self._extract_article_from_element(el)
                    if content:
                        articles.append(content)
                        break

        return {
            'pattern': f"{len(articles)} articles found",
            'confidence': self._calculate_article_confidence(articles),
            'articles': articles
        }

    @staticmethod
    def _extract_article_from_element(element) -> Optional[Dict]:
        title = element.find(['h1', 'h2', 'h3'])
        paragraphs = element.find_all('p')

        if not paragraphs or len(paragraphs) < 2:
            return None

        word_count = sum(len(p.get_text().split()) for p in paragraphs)
        has_title = title is not None
        has_date = element.find(['time', '.date', '.published']) is not None
        has_author = element.find(['.author', '.by-author']) is not None

        confidence = 50
        if has_title:
            confidence += 15
        if has_date:
            confidence += 10
        if has_author:
            confidence += 10
        if word_count > 100:
            confidence += 15

        return {
            'title': title.get_text().strip() if title else 'Untitled',
            'author': (
                element.find(['.author', '.by-author']).get_text().strip()
                if element.find(['.author', '.by-author']) else 'Unknown'
            ),
            'date': (
                element.find(['time', '.date']).get_text().strip()
                if element.find(['time', '.date']) else None
            ),
            'preview': ' '.join([p.get_text() for p in paragraphs[:2]])[:200] + '...',
            'word_count': word_count,
            'confidence': min(confidence, 100),
            'status': 'Success' if confidence >= 70 else 'Warning' if confidence >= 50 else 'Failed'
        }

    @staticmethod
    def _calculate_article_confidence(articles) -> int:
        if not articles:
            return 0
        avg_confidence = sum(a['confidence'] for a in articles) / len(articles)
        return int(avg_confidence)
