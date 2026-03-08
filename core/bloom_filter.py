"""
Bloom Filter for URL deduplication

A probabilistic data structure that can answer:
- "Has this URL been crawled?" with 100% certainty for YES
- "Has this URL been crawled?" with high probability for NO

Space-efficient: 10,000 URLs in ~1.5KB of memory
"""

import hashlib
from typing import List


class BloomFilter:
    """
    Bloom filter for efficient URL deduplication

    Example:
        bf = BloomFilter(size=10000, hash_count=3)
        bf.add("https://nts.live")
        bf.contains("https://nts.live")  # True
        bf.contains("https://pi.fyi")     # False
    """

    def __init__(self, size: int = 10000, hash_count: int = 3):
        """
        Args:
            size: Number of bits in the filter
            hash_count: Number of hash functions to use
        """
        self.size = size
        self.hash_count = hash_count
        self.bit_array = [False] * size
        self.items_added = 0

    def _hash(self, item: str, seed: int) -> int:
        """Generate hash for item with seed"""
        hash_input = f"{item}{seed}".encode('utf-8')
        hash_output = hashlib.sha256(hash_input).hexdigest()
        return int(hash_output, 16) % self.size

    def add(self, item: str) -> None:
        """Add item to bloom filter"""
        for i in range(self.hash_count):
            index = self._hash(item, i)
            self.bit_array[index] = True
        self.items_added += 1

    def contains(self, item: str) -> bool:
        """
        Check if item is in bloom filter

        Returns:
            True: Item MIGHT be in the set (or false positive)
            False: Item is DEFINITELY NOT in the set
        """
        for i in range(self.hash_count):
            index = self._hash(item, i)
            if not self.bit_array[index]:
                return False
        return True

    def __contains__(self, item: str) -> bool:
        """Allow `url in bloom_filter` syntax"""
        return self.contains(item)

    def false_positive_rate(self) -> float:
        """
        Calculate approximate false positive rate

        Formula: (1 - e^(-k*n/m))^k
        where k=hash_count, n=items_added, m=size
        """
        import math
        k = self.hash_count
        n = self.items_added
        m = self.size

        if n == 0:
            return 0.0

        return (1 - math.exp(-k * n / m)) ** k

    def stats(self) -> dict:
        """Get bloom filter statistics"""
        bits_set = sum(self.bit_array)
        return {
            'size': self.size,
            'hash_count': self.hash_count,
            'items_added': self.items_added,
            'bits_set': bits_set,
            'fill_rate': bits_set / self.size,
            'false_positive_rate': self.false_positive_rate()
        }

    def __repr__(self) -> str:
        stats = self.stats()
        return f"BloomFilter(items={stats['items_added']}, fill={stats['fill_rate']:.1%}, fpr={stats['false_positive_rate']:.2%})"
