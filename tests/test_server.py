#!/usr/bin/env python3
"""
Quick diagnostic script to test what's working
Run this AFTER starting the server (python3 app.py)
"""

import requests
import json

BASE_URL = "http://localhost:8080"

def test_health():
    """Test if server is running"""
    print("\n" + "="*70)
    print("🏥 Testing Server Health")
    print("="*70)

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Server returned {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server")
        print("   Make sure you ran: python3 app.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_deep_scan():
    """Test deep scan on simple site"""
    print("\n" + "="*70)
    print("🔍 Testing Deep Scan")
    print("="*70)

    try:
        print("Testing with: http://example.com")
        response = requests.post(
            f"{BASE_URL}/api/deep-scan",
            json={"site_url": "http://example.com"},
            timeout=120
        )

        if response.status_code == 200:
            data = response.json()
            evidence = data.get('evidence', {})

            print("✅ Deep scan works!")
            print(f"\n📊 Metrics found:")
            for key in evidence.keys():
                print(f"   - {key}")

            # Check specific features
            if 'content_extraction' in evidence:
                print("\n✅ Content Extraction: WORKING")
                ce = evidence['content_extraction']
                print(f"   Page Type: {ce.get('page_type', 'unknown')}")
                print(f"   Confidence: {ce.get('confidence', 0)}%")
            else:
                print("\n❌ Content Extraction: NOT FOUND")

            if 'visual_hierarchy' in evidence:
                print("✅ Visual Hierarchy: WORKING")
            else:
                print("❌ Visual Hierarchy: NOT FOUND")

            if 'api_patterns' in evidence:
                print("✅ API Patterns: WORKING")
                if evidence['api_patterns'].get('relationship_map'):
                    print("   Relationship map: Found")
                else:
                    print("   Relationship map: Empty")
            else:
                print("❌ API Patterns: NOT FOUND")

            return True
        else:
            print(f"❌ Deep scan failed with status {response.status_code}")
            print(f"   Error: {response.json().get('error', 'Unknown error')}")
            return False

    except requests.exceptions.Timeout:
        print("❌ Request timed out (>120s)")
        print("   This might be normal for first run (downloads browser)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_component_ripper():
    """Test component ripper"""
    print("\n" + "="*70)
    print("🔬 Testing Component Ripper")
    print("="*70)

    try:
        print("Testing with: http://example.com")
        print("Selector: h1")

        response = requests.post(
            f"{BASE_URL}/api/rip-component",
            json={
                "site_url": "http://example.com",
                "selector": "h1"
            },
            timeout=120
        )

        if response.status_code == 200:
            data = response.json()
            blueprint = data.get('blueprint', {})

            print("✅ Component Ripper works!")
            print(f"\n📦 Blueprint keys:")
            for key in blueprint.keys():
                print(f"   - {key}")

            return True
        else:
            print(f"❌ Component ripper failed with status {response.status_code}")
            print(f"   Error: {response.json().get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_style_extractor():
    """Test computed style extractor"""
    print("\n" + "="*70)
    print("🎨 Testing Style Extractor")
    print("="*70)

    try:
        print("Testing with: http://example.com")
        print("Selector: h1")

        response = requests.post(
            f"{BASE_URL}/api/extract-styles",
            json={
                "site_url": "http://example.com",
                "selector": "h1",
                "mode": "critical"
            },
            timeout=120
        )

        if response.status_code == 200:
            data = response.json()
            styles = data.get('styles', {})

            print("✅ Style Extractor works!")

            if styles.get('found'):
                print(f"\n🎨 Found styles:")
                if 'generated_css' in styles:
                    print(styles['generated_css'][:200] + "...")
            else:
                print("⚠️  Element not found on page")

            return True
        else:
            print(f"❌ Style extractor failed with status {response.status_code}")
            print(f"   Error: {response.json().get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 WEBSCRAPER DIAGNOSTIC TEST")
    print("="*70)
    print("\nMake sure the server is running in another terminal:")
    print("  cd /Users/jarradjones/Desktop/Webscraper")
    print("  python3 app.py")
    print("\nPress Enter when ready...")
    input()

    results = {
        'health': test_health(),
        'deep_scan': False,
        'component_ripper': False,
        'style_extractor': False
    }

    if results['health']:
        results['deep_scan'] = test_deep_scan()
        results['component_ripper'] = test_component_ripper()
        results['style_extractor'] = test_style_extractor()

    # Summary
    print("\n" + "="*70)
    print("📋 TEST SUMMARY")
    print("="*70)

    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test}")

    total = sum(results.values())
    print(f"\nScore: {total}/{len(results)} tests passed")

    if total == len(results):
        print("\n🎉 All tests passed! Server is working correctly.")
    elif total > 0:
        print("\n⚠️  Some features aren't working. Check errors above.")
    else:
        print("\n❌ Server is not working. Fix errors above.")

if __name__ == "__main__":
    main()
