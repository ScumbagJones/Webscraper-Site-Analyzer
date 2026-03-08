#!/usr/bin/env python3
"""
Test Smart Nav on NTS Live
"""
import requests
import json
import time

def test_nts(mode='smart-nav'):
    url = 'https://www.nts.live'

    print(f"\n{'='*70}")
    print(f" Testing {mode} mode on NTS Live")
    print('='*70)

    start_time = time.time()

    response = requests.post(
        'http://localhost:8080/api/deep-scan',
        json={
            'site_url': url,
            'analysis_mode': mode
        },
        timeout=300
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

                if evidence.get('urls_discovered'):
                    print(f"\n📄 URLs Discovered:")
                    for page_type, page_url in evidence['urls_discovered'].items():
                        print(f"      {page_type}: {page_url}")

                if evidence.get('site_patterns'):
                    print(f"\n🔍 Site Patterns:")
                    for key, value in evidence['site_patterns'].items():
                        if isinstance(value, dict):
                            print(f"      {key}:")
                            for k, v in value.items():
                                print(f"         {k}: {v}")
                        else:
                            print(f"      {key}: {value}")

                # Check API patterns on each page
                print(f"\n📡 API Patterns by Page:")
                for page_type, page_data in evidence.get('page_results', {}).items():
                    api_patterns = page_data.get('api_patterns', {})
                    rest_apis = api_patterns.get('details', {}).get('rest_apis', [])
                    print(f"\n   {page_type} ({page_data.get('meta_info', {}).get('url', 'unknown')}):")
                    print(f"      REST APIs: {len(rest_apis)}")
                    if rest_apis:
                        for api in rest_apis[:3]:  # Show first 3
                            print(f"         - {api.get('method')} {api.get('path')}")

            return True
        else:
            print(f"\n❌ Error: {data.get('error')}")
            return False
    else:
        print(f"\n❌ HTTP {response.status_code}")
        print(response.text[:200])
        return False

if __name__ == '__main__':
    test_nts('smart-nav')
