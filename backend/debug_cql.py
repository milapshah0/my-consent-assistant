#!/usr/bin/env python3
"""Debug script to test CQL construction."""

import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.services.confluence_service import ConfluenceService


def test_cql_construction():
    """Test CQL construction without making API calls."""
    print("Testing CQL Construction...")
    
    settings = get_settings()
    print(f"Confluence space keys: {settings.confluence_space_keys}")
    print(f"Confluence base URL: {settings.confluence_base_url}")
    
    service = ConfluenceService()
    
    # Test space filters
    space_filters = [
        f'space = "{space}"' for space in settings.confluence_space_keys
    ]
    print(f"Space filters: {space_filters}")
    
    # Test basic CQL
    cql_parts = ["type = page"]
    if space_filters:
        cql_parts.append(f"({' OR '.join(space_filters)})")
    
    cql = " AND ".join(cql_parts)
    print(f"Basic CQL: {cql}")
    
    # Test CQL with time filters
    cql_parts = ["type = page"]
    if space_filters:
        cql_parts.append(f"({' OR '.join(space_filters)})")
    
    time_filters = ['lastmodified >= "2026-03-25 00:00"']
    if time_filters:
        cql_parts.append(f"({' OR '.join(time_filters)})")
    
    cql = " AND ".join(cql_parts)
    print(f"CQL with time filter: {cql}")
    
    # Test URL encoding
    import urllib.parse
    encoded_cql = urllib.parse.quote(cql)
    print(f"URL encoded CQL: {encoded_cql}")
    
    # Test full URL construction
    endpoint = f"{settings.confluence_base_url}/rest/api/content/search"
    params = {
        "cql": cql,
        "cqlcontext": {"spaceKey": settings.confluence_space_keys},
        "limit": 10,
        "start": 0,
        "expand": "version,history,space",
    }
    
    url = f"{endpoint}?" + "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
    print(f"Full URL: {url}")


if __name__ == "__main__":
    test_cql_construction()
