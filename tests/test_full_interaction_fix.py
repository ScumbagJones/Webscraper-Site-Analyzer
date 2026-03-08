#!/usr/bin/env python3
"""Test the complete 4-strategy interaction states extraction"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from deep_evidence_engine import DeepEvidenceEngine

async def test_interaction_fix():
    """Test on Stripe.com with all 4 strategies"""
    print("Testing interaction states extraction with 4-strategy approach...\n")

    # Test on Stripe
    print("🧪 Testing on Stripe.com...")
    engine = DeepEvidenceEngine('https://stripe.com', analysis_mode='single')
    evidence = await engine.extract_all()

    if evidence and 'interaction_states' in evidence:
        interaction_data = evidence.get('interaction_states', {})

        print(f"\n✅ RESULTS:")
        print(f"   Pattern: {interaction_data.get('pattern', 'N/A')}")
        print(f"   Confidence: {interaction_data.get('confidence', 0)}%")

        breakdown = interaction_data.get('detection_breakdown', {})
        print(f"\n   Detection breakdown:")
        print(f"      Traditional CSS: {breakdown.get('traditional_css', 0)}")
        print(f"      Utility classes: {breakdown.get('utility_classes', 0)}")
        print(f"      Style tags: {breakdown.get('style_tags', 0)}")
        print(f"      Computed hover: {breakdown.get('computed_hover', 0)}")

        if interaction_data.get('computed_states'):
            print(f"\n   Computed hover changes detected on:")
            for tag, count in interaction_data['computed_states'].items():
                print(f"      {tag}: {count} elements")

        print(f"\n   Evidence trail:")
        for item in interaction_data.get('evidence_trail', {}).get('found', []):
            print(f"      - {item}")

    else:
        print(f"❌ FAILED: No interaction_states data in evidence")

if __name__ == '__main__':
    asyncio.run(test_interaction_fix())
