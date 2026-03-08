"""
Global configuration for Crawler, Scraper, and MRI
"""

class Config:
    """Global configuration"""

    # Crawler settings
    MAX_DEPTH = 2
    POLITENESS_DELAY_MS = 500  # milliseconds
    BLOOM_FILTER_SIZE = 10000
    BLOOM_FILTER_HASH_COUNT = 3

    # Scraper settings
    STEALTH_MODE = True
    PAGE_TIMEOUT = 30000  # milliseconds
    WAIT_AFTER_LOAD = 2  # seconds

    # MRI settings
    MIN_SIGNALS_FOR_ANALYSIS = 3
    CONFIDENCE_THRESHOLD = 0.7

    # Output settings
    SIGNALS_DIR = 'data/signals'
    REPORTS_DIR = 'data/reports'
    RECIPES_DIR = 'data/recipes'

    @classmethod
    def to_dict(cls):
        """Export config as dict"""
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith('_') and key.isupper()
        }
