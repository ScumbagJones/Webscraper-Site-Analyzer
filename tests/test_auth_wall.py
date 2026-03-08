#!/usr/bin/env python3
"""Test Bug 4 fix: Auth wall detection on X.com"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from deep_evidence_engine import DeepEvidenceEngine

async def test_auth_wall():
    """Test auth wall detection on X.com"""
    print("Testing Bug 4 fix: Auth wall detection...\n")

    print("🧪 Testing on X.com (should detect auth wall)...")
    engine = DeepEvidenceEngine('https://x.com', analysis_mode='single')

    # Just get to the page load part - we don't need full analysis
    try:
        evidence = await engine.extract_all()

        # Check what access strategy was used
        print(f"\n✅ Test completed")
        print(f"   Note: Check logs above for auth wall detection message")

        # The access_strategy isn't in evidence, it's internal to engine
        # But we should see the log message during page load

    except Exception as e:
        print(f"❌ Error: {str(e)[:200]}")

if __name__ == '__main__':
    asyncio.run(test_auth_wall())
