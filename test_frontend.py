#!/usr/bin/env python3
"""
Frontend Test - Check if all API endpoints work correctly
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, url, data=None):
    """Test a single endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"Method: {method}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS")
            try:
                json_data = response.json()
                print(f"Response: {json.dumps(json_data, indent=2)[:200]}...")
            except:
                print(f"Response: {response.text[:200]}...")
        else:
            print(f"❌ FAILED")
            print(f"Error: {response.text[:200]}")
            
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        print("❌ FAILED - Cannot connect to server")
        print("   Make sure server is running: ./run.sh")
        return False
    except Exception as e:
        print(f"❌ FAILED - {e}")
        return False

def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║            Frontend API Endpoint Tests                      ║")
    print("╔══════════════════════════════════════════════════════════════╗")
    
    tests = []
    
    # Test 1: Home page
    tests.append(test_endpoint(
        "Home Page",
        "GET",
        f"{BASE_URL}/"
    ))
    
    # Test 2: Health check
    tests.append(test_endpoint(
        "Health Check",
        "GET",
        f"{BASE_URL}/api/health"
    ))
    
    # Test 3: Detailed health
    tests.append(test_endpoint(
        "Detailed Health",
        "GET",
        f"{BASE_URL}/api/health/detailed"
    ))
    
    # Test 4: Stats
    tests.append(test_endpoint(
        "Stats Endpoint",
        "GET",
        f"{BASE_URL}/api/stats"
    ))
    
    # Test 5: Ask question (only if database is ready)
    tests.append(test_endpoint(
        "Ask Question",
        "POST",
        f"{BASE_URL}/api/ask",
        {
            "question": "What is this about?",
            "include_sources": True,
            "file_filter": "all"
        }
    ))
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    passed = sum(tests)
    total = len(tests)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Frontend is working correctly!")
    elif passed >= 3:
        print("\n⚠️  Core endpoints working. Some features may not work yet.")
        print("   This is normal if you haven't added documents yet.")
    else:
        print("\n❌ Many tests failed. Check if:")
        print("   1. Server is running: ./run.sh")
        print("   2. LM Studio is running")
        print("   3. Documents are processed")

if __name__ == "__main__":
    main()
