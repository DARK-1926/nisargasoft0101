#!/usr/bin/env python
"""
Verification script for scheduler and data collection fixes.
Run this after starting the system with LAUNCH.bat to verify all fixes are working.
"""
import sys
import time
import socket
import httpx


def check_redis(host="127.0.0.1", port=6379):
    """Check if Redis is running."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((host, port))
        s.close()
        print("✓ Redis is running")
        return True
    except Exception as e:
        print(f"✗ Redis is NOT running: {e}")
        return False


def check_api(base_url="http://127.0.0.1:8000"):
    """Check if API is running."""
    try:
        response = httpx.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✓ API is running")
            return True
        else:
            print(f"✗ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ API is NOT running: {e}")
        return False


def check_locations_endpoint(base_url="http://127.0.0.1:8000"):
    """Check if /api/locations returns all 5 locations."""
    try:
        response = httpx.get(f"{base_url}/api/locations", timeout=5)
        if response.status_code == 200:
            locations = response.json()
            if len(locations) == 5:
                print(f"✓ /api/locations returns all 5 locations")
                for loc in locations:
                    print(f"  - {loc['city']}, {loc['state']} ({loc['pin_code']})")
                return True
            else:
                print(f"✗ /api/locations returns {len(locations)} locations (expected 5)")
                return False
        else:
            print(f"✗ /api/locations returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Failed to check /api/locations: {e}")
        return False


def check_celery_worker():
    """Check if Celery worker is running."""
    try:
        from celery import Celery
        app = Celery(broker="redis://127.0.0.1:6379/0")
        stats = app.control.inspect().stats()
        if stats:
            print(f"✓ Celery worker is running ({len(stats)} worker(s))")
            return True
        else:
            print("✗ Celery worker is NOT running")
            return False
    except Exception as e:
        print(f"✗ Failed to check Celery worker: {e}")
        return False


def main():
    print("=" * 60)
    print("Verifying Scheduler and Data Collection Fixes")
    print("=" * 60)
    print()

    results = []

    print("1. Checking Redis...")
    results.append(check_redis())
    print()

    print("2. Checking API...")
    results.append(check_api())
    print()

    print("3. Checking /api/locations endpoint...")
    results.append(check_locations_endpoint())
    print()

    print("4. Checking Celery worker...")
    results.append(check_celery_worker())
    print()

    print("=" * 60)
    if all(results):
        print("✓ All checks passed!")
        print()
        print("Next steps:")
        print("1. Open http://127.0.0.1:3000 in your browser")
        print("2. Verify the location dropdown shows all 5 cities")
        print("3. Add a product to the watchlist")
        print("4. Wait 10 minutes and verify automatic scraping occurs")
        print("5. Check logs in artifacts/ folder for celery_worker.log and celery_beat.log")
        return 0
    else:
        print("✗ Some checks failed. Please review the output above.")
        print()
        print("Common issues:")
        print("- Redis not installed: Install Redis or use Docker")
        print("- Celery not running: Check LAUNCH.bat started all processes")
        print("- API not responding: Check artifacts/launch_api.log for errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
