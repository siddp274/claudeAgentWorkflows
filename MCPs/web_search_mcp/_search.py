import json
import os
import re
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

from dotenv import load_dotenv  

load_dotenv() 


API_KEY = os.environ.get("BRAVE_API_KEY", "")
BASE_URL = "https://api.search.brave.com/res/v1"
HEADERS = {"Accept": "application/json", "X-Subscription-Token": API_KEY}
MAX_OFFSET = 9

mcp = FastMCP("brave_search_mcp")


def _clean(text: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.split())


def _format_results(raw: list[dict], offset: int, count: int) -> dict:
    results = [
        {"rank": i + 1 + offset * count, "title": r.get("title", ""), "description": _clean(r.get("description", ""))}
        for i, r in enumerate(raw)
    ]
    has_more = len(raw) == count and offset < MAX_OFFSET
    return {
        "results": results,
        "pagination": {"page": offset + 1, "has_more": has_more, "next_offset": offset + 1 if has_more else None},
    }


async def _get(endpoint: str, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params)
        r.raise_for_status()
        return r.json()

# Brave web searches are keyword searches
@mcp.tool()
async def brave_web_search(
    query: str,
    count: int = 10,
    offset: int = 0,
    freshness: Optional[str] = None,
    country: Optional[str] = None,
    extra_snippets: bool = False,
) -> str:
    """Search the web via Brave. Returns {results: [{rank, title, description}], pagination: {page, has_more, next_offset}}.
    freshness: pd=day, pw=week, pm=month, py=year. Use offset (0-9) to paginate.
    country should be a 2-letter ISO code (e.g., US, GB, IN) to prioritize news from that country."""
    params = {"q": query, "count": min(count, 20), "offset": offset, "text_decorations": False}
    if freshness:
        params["freshness"] = freshness
    if country:
        params["country"] = country.upper()
    if extra_snippets:
        params["extra_snippets"] = True

    try:
        data = await _get("web/search", params)
        raw = data.get("web", {}).get("results", [])
        return json.dumps(_format_results(raw, offset, count))
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"Status Code: HTTP {e.response.status_code}, error: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()