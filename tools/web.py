"""
tools/web.py — Web search tools.
"""

import os
from logger import setup_logging

logger = setup_logging()


def search_google(query):
    """Open a Google search in the default browser."""
    try:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        os.system(f'start "" "{url}"')
        return f"Searching for {query}."
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return "Couldn't open the browser for search."


def open_url(url):
    """Open a URL in the default browser."""
    try:
        os.system(f'start "" "{url}"')
        return True
    except Exception as e:
        logger.error(f"Failed to open URL: {e}")
        return False
