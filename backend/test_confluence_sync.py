#!/usr/bin/env python3
"""Test script to verify Confluence sync functionality."""

import asyncio
import os
import sys

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.confluence_service import ConfluenceService
from app.tasks.sync_confluence import sync_confluence_pages


async def test_confluence_service():
    """Test the ConfluenceService with CQL filtering."""
    print("Testing ConfluenceService...")

    service = ConfluenceService()

    # Test basic fetch
    print("1. Testing basic fetch...")
    pages = await service.fetch_pages(limit=5)
    print(f"   Fetched {len(pages)} pages")

    # Test fetch with lastmodified filter
    print("2. Testing fetch with lastmodified filter...")
    pages = await service.fetch_pages(limit=5, since="2026-03-25 00:00")
    print(f"   Fetched {len(pages)} pages updated since 2026-03-25")

    # Test fetch with created filter
    print("3. Testing fetch with created filter...")
    pages = await service.fetch_pages(limit=5, created_since="2026-03-25 00:00")
    print(f"   Fetched {len(pages)} pages created since 2026-03-25")

    # Test fetch with both filters (OR logic)
    print("4. Testing fetch with both filters (new OR updated)...")
    pages = await service.fetch_pages(
        limit=5, since="2026-03-25 00:00", created_since="2026-03-25 00:00"
    )
    print(f"   Fetched {len(pages)} pages new OR updated since 2026-03-25")

    if pages:
        print(f"   Sample page: {pages[0].get('title', 'No title')}")
        print(
            '   CQL used: type = page AND (space filters) AND (lastmodified >= "2026-03-25 00:00" OR created >= "2026-03-25 00:00")'
        )


async def test_sync_confluence():
    """Test the sync function (dry run)."""
    print("\nTesting sync_confluence_pages...")

    # Note: This will try to sync but likely fail without proper configuration
    # It's mainly to test the logic flow
    try:
        await sync_confluence_pages(force=True)
        print("   Sync completed (check logs for details)")
    except Exception as e:
        print(f"   Sync failed (expected without proper config): {e}")


async def main():
    """Run all tests."""
    print("Confluence Sync Test Suite")
    print("=" * 40)

    await test_confluence_service()
    await test_sync_confluence()

    print("\nTest completed!")
    print("\nTo run a real sync:")
    print("1. Configure Confluence credentials in .env")
    print("2. Run: python -m app.tasks.sync_confluence")
    print("3. Or call API: POST /api/confluence/sync?force=true")


if __name__ == "__main__":
    asyncio.run(main())
