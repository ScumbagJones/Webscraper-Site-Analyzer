"""
Signal Schema: The "Contract" between Scraper and MRI

The Scraper outputs Signal objects.
The MRI consumes Signal objects.

This keeps the MRI "pure"—it doesn't care HOW the data was scraped,
only WHAT the data says.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class DOMSignals:
    """DOM-related signals"""
    active_selectors: List[str] = field(default_factory=list)
    persisted_elements: List[str] = field(default_factory=list)
    element_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class LayoutSignals:
    """Layout-related signals"""
    type: str = "unknown"  # 'grid', 'flex', 'block'
    direction: Optional[str] = None  # 'row', 'column'
    grid_template_columns: Optional[str] = None
    rigidity_score: int = 0  # 0-10 scale

    def to_dict(self):
        return asdict(self)


@dataclass
class NetworkSignals:
    """Network-related signals"""
    api_calls: List[str] = field(default_factory=list)
    graphql_calls: List[str] = field(default_factory=list)
    total_requests: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass
class PerformanceSignals:
    """Performance-related signals"""
    load_time: int = 0  # milliseconds
    first_contentful_paint: Optional[int] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class Signal:
    """
    A Signal represents architectural signals from ONE page

    This is the "contract" between Scraper and MRI:
    - Scraper PRODUCES Signal objects
    - MRI CONSUMES Signal objects
    """
    url: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Metadata
    framework: Optional[str] = None  # 'Next.js', 'React', etc.
    is_static: bool = False
    has_hydration: bool = False

    # Signals
    dom: DOMSignals = field(default_factory=DOMSignals)
    layout: LayoutSignals = field(default_factory=LayoutSignals)
    network: NetworkSignals = field(default_factory=NetworkSignals)
    performance: PerformanceSignals = field(default_factory=PerformanceSignals)

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'url': self.url,
            'timestamp': self.timestamp,
            'metadata': {
                'framework': self.framework,
                'isStatic': self.is_static,
                'hasHydration': self.has_hydration
            },
            'signals': {
                'dom': self.dom.to_dict(),
                'layout': self.layout.to_dict(),
                'network': self.network.to_dict(),
                'performance': self.performance.to_dict()
            }
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create Signal from dictionary"""
        return cls(
            url=data['url'],
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            framework=data['metadata'].get('framework'),
            is_static=data['metadata'].get('isStatic', False),
            has_hydration=data['metadata'].get('hasHydration', False),
            dom=DOMSignals(**data['signals']['dom']),
            layout=LayoutSignals(**data['signals']['layout']),
            network=NetworkSignals(**data['signals']['network']),
            performance=PerformanceSignals(**data['signals']['performance'])
        )


class SignalSchema:
    """Validator and helper for Signal objects"""

    @staticmethod
    def validate(signal: Signal) -> bool:
        """Validate a Signal object"""
        if not signal.url:
            return False
        if not signal.timestamp:
            return False
        return True

    @staticmethod
    def example() -> Signal:
        """Generate example Signal for documentation"""
        return Signal(
            url="https://nts.live/explore",
            framework="Next.js",
            is_static=False,
            has_hydration=True,
            dom=DOMSignals(
                active_selectors=["audio#nts-player-audio", "[class*='grid']"],
                persisted_elements=["audio#nts-player-audio"],
                element_counts={"audio": 1, "video": 0, "iframe": 0}
            ),
            layout=LayoutSignals(
                type="flex",
                direction="row",
                grid_template_columns=None,
                rigidity_score=4
            ),
            network=NetworkSignals(
                api_calls=["/api/shows", "/api/tags"],
                graphql_calls=[],
                total_requests=23
            ),
            performance=PerformanceSignals(
                load_time=1234,
                first_contentful_paint=567
            )
        )
