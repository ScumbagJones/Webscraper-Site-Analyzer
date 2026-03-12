"""
Cloudflare /crawl Wrapper — Async bulk website crawler via Cloudflare Browser Rendering.

Wraps the Cloudflare REST API /accounts/{id}/browser-rendering/crawl endpoint.
Used as a complementary URL discovery + content fetching backend alongside
the local patchright-based deep analysis engine.

Requires:
  - CLOUDFLARE_ACCOUNT_ID env var
  - CLOUDFLARE_API_TOKEN env var  (with Browser Rendering permissions)

Usage:
  crawler = CloudflareCrawler()
  result = await crawler.crawl("https://stripe.com", limit=20, depth=3)
  # result = { pages: [...], crawl_id: "...", status: "completed" }

If credentials are missing, all methods raise CloudflareNotConfigured.
"""

import os
import asyncio
import logging
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Env var names
_ENV_ACCOUNT = 'CLOUDFLARE_ACCOUNT_ID'
_ENV_TOKEN = 'CLOUDFLARE_API_TOKEN'


class CloudflareNotConfigured(Exception):
    """Raised when Cloudflare credentials are missing."""
    pass


def is_cloudflare_available() -> bool:
    """Check if Cloudflare credentials are configured."""
    return bool(os.environ.get(_ENV_ACCOUNT) and os.environ.get(_ENV_TOKEN))


class CloudflareCrawler:
    """Thin wrapper around Cloudflare Browser Rendering /crawl REST API."""

    BASE_URL = "https://api.cloudflare.com/client/v4/accounts"

    def __init__(self, account_id: str = None, api_token: str = None):
        self.account_id = account_id or os.environ.get(_ENV_ACCOUNT)
        self.api_token = api_token or os.environ.get(_ENV_TOKEN)

        if not self.account_id or not self.api_token:
            raise CloudflareNotConfigured(
                f"Set {_ENV_ACCOUNT} and {_ENV_TOKEN} environment variables "
                f"to use Cloudflare /crawl integration."
            )

        self._headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

    @property
    def _crawl_url(self) -> str:
        return f"{self.BASE_URL}/{self.account_id}/browser-rendering/crawl"

    # ------------------------------------------------------------------
    # Core API methods
    # ------------------------------------------------------------------

    def start_crawl(
        self,
        url: str,
        limit: int = 10,
        depth: int = 2,
        formats: List[str] = None,
        render: bool = True,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
    ) -> str:
        """
        Start a crawl job.

        Args:
            url: Starting URL to crawl
            limit: Max pages to crawl (1-100000, default 10)
            depth: Max link depth from starting URL
            formats: Output formats — ['html'], ['markdown'], ['json'], or combo
            render: Whether to use headless browser (True) or static fetch (False)
            include_patterns: URL wildcard patterns to include
            exclude_patterns: URL wildcard patterns to exclude

        Returns:
            crawl_id (str) for status polling
        """
        payload = {
            'url': url,
            'limit': min(limit, 100000),
            'maxDiscoveryDepth': depth,
            'render': render,
            'formats': formats or ['markdown'],
        }

        if include_patterns:
            payload['includePatterns'] = include_patterns
        if exclude_patterns:
            payload['excludePatterns'] = exclude_patterns

        resp = requests.post(self._crawl_url, json=payload, headers=self._headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        crawl_id = data.get('result', {}).get('crawlId') or data.get('crawlId')
        if not crawl_id:
            # Try alternate response shape
            crawl_id = data.get('id') or data.get('result', {}).get('id')

        if not crawl_id:
            raise ValueError(f"Cloudflare did not return a crawl ID. Response: {data}")

        logger.info("Cloudflare crawl started: %s (limit=%d, depth=%d)", crawl_id, limit, depth)
        return crawl_id

    def check_status(self, crawl_id: str) -> Dict:
        """
        Check crawl job status and retrieve results.

        Returns:
            { status: 'completed'|'running'|'queued'|..., pages: [...], total: N }
        """
        url = f"{self._crawl_url}/{crawl_id}"
        resp = requests.get(url, headers=self._headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        result = data.get('result', data)
        return {
            'status': result.get('status', 'unknown'),
            'pages': result.get('data', result.get('pages', [])),
            'total': result.get('total', 0),
            'crawl_id': crawl_id,
        }

    async def poll_until_done(self, crawl_id: str, timeout: int = 300, interval: int = 5) -> Dict:
        """
        Poll a crawl job until completed or timeout.

        Args:
            crawl_id: Job ID from start_crawl()
            timeout: Max seconds to wait
            interval: Seconds between polls

        Returns:
            Final status dict with pages
        """
        elapsed = 0
        while elapsed < timeout:
            result = self.check_status(crawl_id)
            status = result.get('status', '').lower()

            if status in ('completed', 'complete'):
                logger.info("Cloudflare crawl completed: %d pages", len(result.get('pages', [])))
                return result
            elif status in ('failed', 'error', 'cancelled'):
                logger.warning("Cloudflare crawl failed: %s", result)
                return result

            await asyncio.sleep(interval)
            elapsed += interval

        logger.warning("Cloudflare crawl timed out after %ds", timeout)
        return {'status': 'timeout', 'crawl_id': crawl_id, 'pages': []}

    async def crawl(
        self,
        url: str,
        limit: int = 10,
        depth: int = 2,
        formats: List[str] = None,
        render: bool = True,
        timeout: int = 300,
    ) -> Dict:
        """
        High-level: start crawl → poll → return results.

        Returns:
            {
                status: str,
                crawl_id: str,
                pages: [{ url, content, ... }],
                total: int,
                urls: [str]  # extracted URLs for deep analysis
            }
        """
        crawl_id = self.start_crawl(url, limit=limit, depth=depth, formats=formats, render=render)
        result = await self.poll_until_done(crawl_id, timeout=timeout)

        # Extract unique URLs from pages
        pages = result.get('pages', [])
        urls = list(set(
            p.get('url') or p.get('sourceURL', '')
            for p in pages
            if p.get('url') or p.get('sourceURL')
        ))

        result['urls'] = sorted(urls)
        return result

    def cancel_crawl(self, crawl_id: str) -> bool:
        """Cancel a running crawl job."""
        try:
            url = f"{self._crawl_url}/{crawl_id}"
            resp = requests.delete(url, headers=self._headers, timeout=15)
            return resp.status_code < 300
        except Exception as e:
            logger.warning("Failed to cancel crawl %s: %s", crawl_id, e)
            return False

    # ------------------------------------------------------------------
    # Convenience: discover URLs for deep analysis
    # ------------------------------------------------------------------

    async def discover_urls(self, url: str, limit: int = 20, depth: int = 2) -> List[str]:
        """
        Crawl a site and return discovered URLs (no content, just URLs).
        Useful as a drop-in alternative to /api/discover-urls.
        """
        result = await self.crawl(url, limit=limit, depth=depth, formats=['markdown'], render=False)
        return result.get('urls', [])
