#!/usr/bin/env python3
"""
Quick test of Smart Nav mode
"""
import requests
import json
import time

def test_smart_nav(url, mode='smart-nav'):
    print(f"\n{'='*70}")
    print(f" Testing {mode} mode on: {url}")
    print('='*70)

    start_time = time.time()

    response = requests.post(
        'http://localhost:8080/api/deep-scan',
        json={
            'site_url': url,
            'analysis_mode': mode
        },
        timeout=300  # 5 minute timeout
    )

    elapsed = time.time() - start_time

    print(f"\n⏱️  Time: {elapsed:.1f} seconds")

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            evidence = data['evidence']

            print(f"\n✅ Analysis complete!")
            print(f"   Mode: {evidence.get('analysis_mode', 'single')}")

            if evidence.get('analysis_mode') == 'smart-nav':
                print(f"   Pages analyzed: {evidence.get('pages_analyzed', 0)}")
                print(f"\n   Page results:")
                for page_type, page_url in evidence.get('urls_discovered', {}).items():
                    print(f"      {page_type}: {page_url}")

                if evidence.get('site_patterns'):
                    print(f"\n   Site patterns:")
                    for key, value in evidence['site_patterns'].items():
                        print(f"      {key}: {value}")

            return True
        else:
            print(f"\n❌ Error: {data.get('error')}")
            return False
    else:
        print(f"\n❌ HTTP {response.status_code}")
        print(response.text[:200])
        return False

if __name__ == '__main__':
    # Test single mode first (should be fast)
    print("\n" + "="*70)
    print(" TEST 1: Single Page Mode (baseline)")
    print("="*70)
    test_smart_nav('https://stripe.com', mode='single')

    # Test smart-nav mode
    print("\n" + "="*70)
    print(" TEST 2: Smart Nav Mode")
    print("="*70)
    test_smart_nav('https://stripe.com', mode='smart-nav')
