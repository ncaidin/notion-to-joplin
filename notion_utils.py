# notion_utils.py
"""
Utility functions for interacting with the Notion API.

Phase 1: generic query_notion_database()
"""

import os
import requests


NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _notion_headers() -> dict:
    """Build standard headers for Notion API calls."""
    token = os.environ.get("NOTION_SECRET")
    if not token:
        raise EnvironmentError("NOTION_SECRET environment variable not set.")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def query_notion_database(database_id: str, payload: dict) -> dict:
    """
    Generic wrapper for querying any Notion database.

    Args:
        database_id: The Notion database ID.
        payload: The JSON body for the query (filters, sorts, etc.).

    Returns:
        Parsed JSON response from Notion as a dict.
    """
    url = f"{NOTION_API_BASE}/databases/{database_id}/query"
    headers = _notion_headers()

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()
