"""
Test API Relationship Map Integration

Quick test to verify the API map feature is properly integrated
"""

import asyncio
from deep_evidence_engine import DeepEvidenceEngine


async def test_api_map():
    print("\n" + "="*70)
    print(" 📡 API RELATIONSHIP MAP INTEGRATION TEST")
    print("="*70)

    # Test with a site that makes API calls
    test_url = 'https://stripe.com/docs'
    print(f"\n Testing URL: {test_url}")
    print("="*70)

    engine = DeepEvidenceEngine(test_url)
    evidence = await engine.extract_all()

    print("\n✅ Evidence extraction complete!")
    print(f"   Total categories: {len(evidence)}")

    # Check for API patterns
    if 'api_patterns' in evidence:
        api_data = evidence['api_patterns']
        print("\n📡 API Patterns Data:")
        print(f"   Pattern: {api_data.get('pattern', 'N/A')}")
        print(f"   Confidence: {api_data.get('confidence', 0)}%")

        details = api_data.get('details', {})
        print(f"   Total API Calls: {details.get('total_api_calls', 0)}")
        print(f"   REST APIs: {len(details.get('rest_apis', []))}")
        print(f"   GraphQL: {len(details.get('graphql', []))}")
        print(f"   WebSockets: {len(details.get('websockets', []))}")

        # Check for relationship map
        if 'relationship_map' in api_data and api_data['relationship_map']:
            rel_map = api_data['relationship_map']
            print("\n✅ RELATIONSHIP MAP FOUND!")

            stats = rel_map.get('stats', {})
            print(f"\n📊 Statistics:")
            print(f"   Total Requests: {stats.get('total_requests', 0)}")
            print(f"   Unique Endpoints: {stats.get('unique_endpoints', 0)}")
            print(f"   Relationships: {stats.get('relationships_detected', 0)}")
            print(f"   Data Dependencies: {stats.get('data_dependencies', 0)}")
            print(f"   Redundant Calls: {stats.get('redundant_calls', 0)}")
            print(f"   Efficiency Score: {stats.get('efficiency_score', 0)}%")

            # Show endpoints
            endpoints = rel_map.get('endpoints', [])
            if endpoints:
                print(f"\n🔗 Top Endpoints:")
                for i, endpoint in enumerate(endpoints[:5]):
                    print(f"   {i+1}. {endpoint['method']} {endpoint['path']}")
                    print(f"      Calls: {endpoint['call_count']}, Success: {endpoint['success_rate']:.1f}%")

            # Show relationships
            relationships = rel_map.get('relationships', [])
            if relationships:
                print(f"\n🔀 Top Relationships:")
                for i, rel in enumerate(relationships[:3]):
                    print(f"   {i+1}. {rel['type']}: {rel.get('time_diff', 0)}ms gap")

            # Show data dependencies
            dependencies = rel_map.get('data_dependencies', [])
            if dependencies:
                print(f"\n📦 Data Dependencies:")
                for i, dep in enumerate(dependencies[:3]):
                    print(f"   {i+1}. {dep['data_type']}: {dep['value']}")
                    print(f"      Confidence: {dep['confidence']}%")

            # Show redundant
            redundant = rel_map.get('redundant_requests', [])
            if redundant:
                print(f"\n♻️  Redundant Requests:")
                for i, red in enumerate(redundant[:3]):
                    print(f"   {i+1}. {red['count']} calls ({red['wasted_calls']} redundant)")
                    print(f"      💡 {red['recommendation']}")

            # Check Mermaid diagram
            if rel_map.get('mermaid_diagram'):
                diagram_lines = rel_map['mermaid_diagram'].split('\n')
                print(f"\n🎨 Mermaid Diagram: {len(diagram_lines)} lines generated")

            print("\n✅ INTEGRATION TEST PASSED!")
            print("   API relationship map is being generated successfully")
        else:
            print("\n⚠️  No relationship map found")
            print("   Relationship mapping may have failed or no API requests detected")
    else:
        print("\n❌ No API patterns data found in evidence")

    print("\n" + "="*70)
    print(" 🌐 WEB DASHBOARD TEST")
    print("="*70)
    print("\n Server running at: http://localhost:8080")
    print("\n To test the UI:")
    print("   1. Open http://localhost:8080 in your browser")
    print("   2. Enter URL: https://stripe.com/docs")
    print("   3. Click 'Analyze URL'")
    print("   4. Click the 'API Map' tab")
    print("   5. You should see:")
    print("      - Statistics cards (total requests, endpoints, etc.)")
    print("      - Mermaid diagram code")
    print("      - List of API endpoints with call counts")
    print("      - Data dependencies between APIs")
    print("      - Redundant request warnings")
    print("   6. Click 'Copy Mermaid Code' button")
    print("   7. Paste at https://mermaid.live to see visual diagram")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    asyncio.run(test_api_map())
