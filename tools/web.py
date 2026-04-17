"""
tools/web.py — Web search and URL tools with LLM tool-call registry.
"""

import os
from logger import setup_logging
from tools.registry import registry

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


# ══════════════════════════════════════════════════════════════
#  Registered Tool Wrappers
# ══════════════════════════════════════════════════════════════

@registry.register(
    name="search_web",
    description="Searches Google for a query and opens the result in the browser.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."}
        },
        "required": ["query"]
    }
)
def search_web_tool(query: str):
    return search_google(query)


@registry.register(
    name="open_url",
    description="Opens a specific URL in the browser.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The full URL to open."}
        },
        "required": ["url"]
    }
)
def open_url_tool(url: str):
    ok = open_url(url)
    return f"Opened {url}." if ok else f"Failed to open {url}."
