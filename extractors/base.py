"""
Base Extractor — Interface and shared context for all extractors.

Every extractor inherits from BaseExtractor and implements extract().
ExtractionContext carries shared state between extractors so they
can access each other's results (e.g., accessibility needs colors).
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from patchright.async_api import Page

logger = logging.getLogger(__name__)


@dataclass
class ExtractionContext:
    """Shared state passed between extractors during a single-page analysis."""
    page: Page
    url: str
    html_content: str
    network_requests: List[Dict] = field(default_factory=list)
    network_responses: List[Dict] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def get_evidence(self, key: str, default=None):
        """Safely retrieve a previously-extracted evidence result."""
        return self.evidence.get(key, default)


class BaseExtractor:
    """
    Abstract base class for all metric extractors.

    Subclasses must set `name` (str) and implement `extract(ctx)`.
    The name becomes the key in the evidence dict.
    """
    name: str = "base"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        """
        Run extraction logic and return an evidence dict.

        Args:
            ctx: ExtractionContext with page, url, html, and cross-extractor data.

        Returns:
            Dict with at least 'pattern' (str) and 'confidence' (int).
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement extract()")

    @staticmethod
    def safe_get(data: Any, *keys, default=None):
        """
        Defensive nested dict access.

        Example:
            safe_get(evidence, 'colors', 'palette', 'primary', default=[])
        """
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, default)
            else:
                return default
        return data
