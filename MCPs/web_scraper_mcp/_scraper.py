#!/usr/bin/env python3
"""
web_scraper_mcp — Simple human-like web scraper MCP server.
Uses BeautifulSoup with html.parser (fault-tolerant, no encoding issues).
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json
import random
from typing import Optional, List, Dict, Any, Set
from urllib.parse import urljoin, urlparse
import re
import requests
import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, ConfigDict, field_validator

# ── Server ───────────────────────────────────────────────────────────────────────
mcp = FastMCP("web_scraper_mcp")

# ── Constants ────────────────────────────────────────────────────────────────────
USER_AGENTS = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",

    # Chrome (Mac)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",

    # Chrome (Linux)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",

    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",

    # Firefox (Mac)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:124.0) Gecko/20100101 Firefox/124.0",

    # Safari (Mac) — keep WebKit consistent
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",

    # Edge (Windows) — important, often overlooked
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
]

SKIP_EXTENSIONS = {
    "jpg","jpeg","png","gif","webp","svg","ico","pdf","doc","docx",
    "zip","tar","gz","mp4","mp3","avi","css","woff","woff2","exe",
}

CONTENT_WORDS = {"article","post","blog","guide","about","topic","detail","read","learn","product"}

CTX = {} # use redis later on

# Minimum path depth to be considered an article (not a nav/utility link)
# e.g. /news/world/asia/article-slug = depth 4 ✅
#      /about = depth 1 ❌
#      /search/ = depth 1 ❌
MIN_PATH_DEPTH = 3

# Path segments that indicate nav/utility pages — never articles
NAV_SEGMENTS = {
    "search", "about", "contact", "privacy", "terms",
    "advertise", "subscribe", "login", "register",
    "tag", "author", "category", "page", "feed",
    "sitemap", "rss", "amp"
}

BASE_DOMAINS = {
    "reuters":        "https://www.reuters.com",
    "aninews":        "https://aninews.in",
    "bbc":            "https://www.bbc.com",
    "guardian":       "https://www.theguardian.com",
    "scmp":           "https://www.scmp.com",
    "republic":       "https://www.republicworld.com",
    "hindustantimes": "https://www.hindustantimes.com",
    "economictimes":  "https://economictimes.indiatimes.com",
    "ndtv":           "https://www.ndtv.com",
    "wikipedia":      "https://en.wikipedia.org",
    "occrp":          "https://www.occrp.org",
    "bellingcat":     "https://www.bellingcat.com",
    "icij":           "https://www.icij.org",
    "thediplomat":    "https://thediplomat.com",
    "firstpost":      None,
}

# ── Helpers ──────────────────────────────────────────────────────────────────────

def _headers(referrer: Optional[str] = None) -> Dict[str, str]:
    h = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if referrer:
        h["Referer"] = referrer
    return h

def _decode(response: httpx.Response) -> str:
    """Safely decode response bytes — tries declared encoding, falls back gracefully."""
    raw = response.content
    # Check Content-Type header
    ct = response.headers.get("content-type", "")
    m = re.search(r"charset=([^\s;]+)", ct, re.I)
    declared = m.group(1).strip() if m else None
    # Check <meta charset> in first 2KB
    snippet = raw[:2048].decode("ascii", errors="ignore")
    meta_m = re.search(r'<meta[^>]+charset=["\']?([^"\';\s>]+)', snippet, re.I)
    meta_enc = meta_m.group(1).strip() if meta_m else None

    for enc in filter(None, [declared, meta_enc, "utf-8", "latin-1"]):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")

def _is_valid_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

async def _fetch(url: str, referrer: Optional[str] = None, timeout: float = 15.0) -> Optional[httpx.Response]:
    """Fetch a URL. Returns None on any error rather than raising."""
    try:
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            r = await client.get(url, headers=_headers(referrer), timeout=timeout)
            r.raise_for_status()
            return r
    except Exception:
        return None

# async def _human_delay(min_s: float, max_s: float) -> None:
#     d = random.uniform(min_s, max_s)
#     if random.random() < 0.08:   # occasional longer pause
#         d *= random.uniform(1.5, 2.5)
#     await asyncio.sleep(d)


def _prioritize(links: List[Dict], strategy: str) -> List[Dict]:
    if strategy == "random":
        random.shuffle(links)
    elif strategy == "content_biased":
        links.sort(
            key=lambda l: sum(1 for w in CONTENT_WORDS if w in l["url"].lower() + l["text"].lower()),
            reverse=True,
        )
    return links  # top_down = DOM order, no sort needed

def _parse(html: str, url: str) -> Dict[str, Any]:
    """Parse HTML into clean structured content. Uses html.parser — handles malformed pages."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "nav", "footer", "iframe", "header"]):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""

    headings = [
        {"level": t.name, "text": t.get_text(strip=True)}
        for t in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        if t.get_text(strip=True)
    ][:25]

    # Best guess at main content container
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.find("div", class_=re.compile(r"content|main|article|post|body", re.I))
        or soup.body
    )

    paragraphs = []
    if main:
        for p in main.find_all("p"):
            t = p.get_text(strip=True)
            if len(t) > 40:
                paragraphs.append(t)

    body_text = re.sub(r"\s{2,}", " ", (main or soup).get_text(separator=" ", strip=True))[:600]

    return {
        "url": url,
        "title": title,
        "headings": headings,
        "paragraphs": paragraphs[:15],
        "body_text": body_text,
        "word_count": len(body_text.split()),
    }

async def _accessibility_tree(url: str) -> Dict[str, Any]:
    """Generate a simplified accessibility tree from HTML. Captures tag, role, name, and hierarchy."""
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@playwright/mcp@latest"]
    )
    r = "result not loaded yet"
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call browser_navigate tool
            result = await session.call_tool(
                "browser_navigate",
                {
                    "url": url
                }
            )

            r = getattr(result.content[0], 'text', '')

    return r

RELATIVE_URL_SITES = {
    "aninews",
    "republic",
    "hindustantimes",
    "economictimes",
    "ndtv",
    # add others when confirmed
}


def is_article_path(path: str) -> bool:
    """
    Returns True if a relative path looks like an article, not a nav/utility link.
    Checks:
      - Minimum path depth (number of segments)
      - No nav/utility segment in the path
      - No query-string-only paths
      - No anchor-only paths
    """
    if not path or not path.startswith("/"):
        return False
    if path.startswith("/?") or path == "/":
        return False
    if path.startswith("#"):
        return False

    segments = [s for s in path.split("/") if s]  # drop empty strings from split

    if len(segments) < MIN_PATH_DEPTH:
        return False

    # If any segment is a known nav/utility word, skip
    if any(seg.lower() in NAV_SEGMENTS for seg in segments):
        return False

    # Skip pure pagination paths
    if "page=" in path:
        return False

    return True


def extract_links(snapshot_text: str, agency: str, q: Optional[str]) -> list[str]:
    base = BASE_DOMAINS.get(agency, "")
    results = []
    # sepatate for firstpost
    if agency == "firstpost":
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Origin": "https://www.firstpost.com",
            "Referer": "https://www.firstpost.com/",
            "Host": "api-mt.firstpost.com",
            "Accept": "application/json,",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        body = {
            "fields":"headline,weburl,updated_at",
            "query":[q],
            "offset":0,
            "count":5
        }
        res = requests.post("https://api-mt.firstpost.com/nodeapi/v1/mfp/semantic-search", 
                            headers=headers, json=body)
        results = [item["weburl"] for item in res.json().get("data", []) if "weburl" in item]
    # --- Absolute URL match (works for Reuters, Guardian via Google, Wikipedia etc.) ---
    if base:
        abs_pattern = rf"/url:\s*\"?({re.escape(base)}/[^\s\)\"]+)\"?"
        results += re.findall(abs_pattern, snapshot_text)

    # --- Relative URL match (for sites that strip the domain in accessibility tree) ---
    if agency in RELATIVE_URL_SITES and base:
        rel_pattern = r"/url:\s*\"?(/[^\s\)\"]+)\"?"
        candidates = re.findall(rel_pattern, snapshot_text)
        for path in candidates:
            if is_article_path(path):
                results.append(base + path)

    # --- Fallback for unknown agencies ---
    if not base and agency != "firstpost":
        fallback_pattern = r"/url:\s*\"?(https://www\.[^/]+/[^\s\)\"]+)\"?"
        results += re.findall(fallback_pattern, snapshot_text)

    # Deduplicate and strip any trailing punctuation artifacts
    cleaned = set()
    for url in results:
        url = url.rstrip(".,);\"'")
        cleaned.add(url)

    return list(cleaned)

# ── Input Models ─────────────────────────────────────────────────────────────────

class FetchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    url: str = Field(..., description="Full URL to fetch (http or https)")
    # delay_min: float = Field(default=1.0, ge=0, le=30, description="Min seconds to wait before fetching")
    # delay_max: float = Field(default=3.5, ge=0, le=60, description="Max seconds to wait before fetching")

    @field_validator("url")
    @classmethod
    def check_url(cls, v: str) -> str:
        if not _is_valid_url(v):
            raise ValueError("URL must start with http:// or https://")
        return v


class ExtractLinksInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    agency: str = Field(..., description="News agency name (e.g., reuters, bbc, guardian) to apply site-specific link extraction heuristics")
    strategy: str = Field(default="content_biased", description="Link order: content_biased | random")
    max_links: int = Field(default=5, ge=1, le=20)
    query: Optional[str] = Field(default="", description="Optional search query (used when agency is firstpost) - add agency name here too to help with link extraction heuristics")
    # delay_min: float = Field(default=1.0, ge=0, le=30)
    # delay_max: float = Field(default=3.5, ge=0, le=60)

    # @field_validator("url")
    # @classmethod
    # def check_url(cls, v: str) -> str:
    #     if not _is_valid_url(v):
    #         raise ValueError("URL must start with http:// or https://")
    #     return v

    @field_validator("strategy")
    @classmethod
    def check_strategy(cls, v: str) -> str:
        if v not in {"content_biased", "random"}:
            raise ValueError("strategy must be content_biased or random")
        return v


class ExtractContentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    url: str = Field(..., description="Page URL to extract structured content from")
    # delay_min: float = Field(default=1.0, ge=0, le=30)
    # delay_max: float = Field(default=3.5, ge=0, le=60)

    @field_validator("url")
    @classmethod
    def check_url(cls, v: str) -> str:
        if not _is_valid_url(v):
            raise ValueError("URL must start with http:// or https://")
        return v

# ── MCP Tools ────────────────────────────────────────────────────────────────────

@mcp.tool(name="scraper_fetch_accessibility_tree", annotations={"readOnlyHint": True, "openWorldHint": True})
async def scraper_fetch_accessibility_tree(params: FetchInput, ctx: Context) -> str:
    """Fetch a web page's accessibility tree using httpx and return page info with all tags, page count, etc.
    Useful to run before scraper_extract_links or scraper_extract_content to understand page structure and if it's accessible without JS.

    Args:
        params: url, delay_min, delay_max
    Returns:
        JSON: status_code, final_url, html_length, html_preview (first 4000 chars)
    """
    try:
        r = None
        # await _human_delay(params.delay_min, params.delay_max)
        r = await _accessibility_tree(params.url)
        # await ctx.set_state("accessibility_tree", r)
        CTX["accessibility_tree"] = r
        if r is None:
            return json.dumps({"error": f"Could not fetch {params.url} — may be down, blocked, or 404."})
        
        return json.dumps({
            "error": "No error",
            "message": "accessibility tree fetched successfully and saved in request context for future tools to use",
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(name="scraper_extract_links", annotations={"readOnlyHint": True, "openWorldHint": True})
async def scraper_extract_links(params: ExtractLinksInput, ctx: Context) -> str:
    """Fetch a page and extract all hyperlinks using BeautifulSoup.
    Binary files (images, PDFs, media) are automatically skipped.

    Args:
        params: url, same_domain_only, strategy, max_links, delay_min, delay_max
    Returns:
        JSON: total_found, strategy, links[] with url + anchor text
    """
    try:
        r = CTX.get("accessibility_tree")
        if params.agency == "firstpost":
            # Use the search query for firstpost agency
            if params.query:
                # Call the firstpost API with the search query
                links = extract_links(r, params.agency, params.query)
                return json.dumps({
                    "strategy": params.strategy,
                    "total_found": len(links),
                    "links": links,
                }, indent=2)
        if r is None:
            return json.dumps({"error": f"Could not fetch {params}"})
        links = extract_links(r, params.agency, None)
        # links = _prioritize(links, params.strategy)[:params.max_links]
        return json.dumps({
            "strategy": params.strategy,
            "total_found": len(links),
            "links": links,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(name="scraper_extract_content", annotations={"readOnlyHint": True, "openWorldHint": True})
async def scraper_extract_content(params: ExtractContentInput, ctx: Context) -> str:
    """Fetch a page and return clean structured content: title, description,
    headings, paragraphs, and body text.

    Args:
        params: url, delay_min, delay_max
    Returns:
        JSON: url, title, meta_description, headings[], paragraphs[], body_text, word_count
    """
    try:
        # await _human_delay(params.delay_min, params.delay_max)
        r = await _fetch(params.url)
        if r is None:
            return json.dumps({"error": f"Could not fetch {params.url}"})
        html = _decode(r)
        return json.dumps(_parse(html, str(r.url)), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()