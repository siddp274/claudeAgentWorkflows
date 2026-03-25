# web_scraper_mcp

A **human-behavior-mimicking web scraper MCP server** built on [Scrapy](https://docs.scrapy.org/) and [BeautifulSoup](https://beautiful-soup-4.readthedocs.io/).

It simulates the browsing patterns of a real user — including random delays, rotating browser fingerprints, referrer chains, cookie management, selective link following, and simulated reading time — while performing recursive deep crawls.

---

## Features

| Feature | Description |
|---|---|
| 🧠 Human delays | Random inter-page pauses (configurable min/max), with occasional long "reading" pauses |
| 🔄 Rotating User-Agents | 7 real browser UA strings (Chrome, Firefox, Safari, Edge on Win/Mac/Linux) |
| 🔗 Referrer chaining | Each visited page becomes the `Referer` header for the next, creating a realistic navigation chain |
| 🍪 Cookie continuity | Cookies received from servers are stored in the session and sent on subsequent requests |
| 🕷️ Scrapy LinkExtractor | Configurable URL filtering with allow/deny regex patterns and extension blocking |
| 🥣 BeautifulSoup parsing | Structured content extraction: headings, paragraphs, tables, images, JSON-LD |
| 📖 Reading time simulation | Page dwell time calculated from word count at a realistic 180–280 wpm reading rate |
| 🎯 Link selection strategies | `top_down`, `content_biased`, `random`, `depth_first` |
| 🔁 Deep recursive crawl | BFS/DFS crawl up to 5 levels deep, visiting up to 50 pages |
| 🔒 Session persistence | In-memory session holds UA, cookies, referrer, and full visit history |

---

## Installation

```bash
pip install mcp[cli] httpx beautifulsoup4 lxml scrapy pydantic
```

Or with the requirements file:

```bash
pip install -r requirements.txt
```

---

## Running the Server

```bash
# stdio transport (for use with Claude Desktop / MCP clients)
python server.py

# Or install and run via MCP CLI
mcp run server.py
```

---

## Claude Desktop Config

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "web_scraper": {
      "command": "python",
      "args": ["/absolute/path/to/web_scraper_mcp/server.py"]
    }
  }
}
```

---

## Tools Reference

### `scraper_create_session`
Create a persistent browsing session with a fixed User-Agent, viewport, cookie jar, and language preferences.

```json
{
  "label": "Research session",
  "fixed_user_agent": null
}
```

Returns `session_id` to pass to other tools.

---

### `scraper_get_session`
Inspect a session's current state, visit history, and configuration.

```json
{ "session_id": "abc123def456" }
```

---

### `scraper_fetch_page`
Fetch raw HTML from a URL with all human-like behaviors applied.

```json
{
  "url": "https://example.com",
  "session_id": "abc123def456",
  "delay_min": 1.5,
  "delay_max": 4.0,
  "timeout": 20.0
}
```

---

### `scraper_extract_links`
Fetch a page and extract all hyperlinks using **Scrapy's LinkExtractor**, with configurable filters and prioritization.

```json
{
  "url": "https://example.com/blog",
  "session_id": "abc123def456",
  "same_domain_only": true,
  "allow_patterns": ["/blog/", "/article/"],
  "deny_patterns": ["/login", "/signup", "/cart"],
  "link_selection_strategy": "content_biased",
  "max_links": 30
}
```

**Strategies:**
- `top_down` — DOM order (how a human reads a page top-to-bottom)
- `content_biased` — Links with content-rich anchor text float to the top
- `random` — Shuffled (simulates casual browsing)
- `depth_first` — DOM order, same as top_down

---

### `scraper_extract_content`
Fetch and parse a page into **structured content blocks** using **BeautifulSoup**:
- Title, meta description, OG tags
- H1–H6 headings hierarchy
- Body paragraphs (noise-stripped)
- Tables (headers + rows)
- Images (with alt text)
- Schema.org / JSON-LD structured data

```json
{
  "url": "https://example.com/article/123",
  "session_id": "abc123def456",
  "simulate_reading": true
}
```

---

### `scraper_deep_crawl`
**The flagship tool.** Recursively crawl a website like a human exploring a topic:

1. Visit `start_url`, extract content and links
2. Apply link prioritization strategy
3. Selectively follow only `links_per_page` links (not all of them)
4. Repeat recursively up to `max_depth` levels
5. Pause between pages with human-like delays
6. Maintain referrer chain and cookie jar throughout

```json
{
  "start_url": "https://example.com/docs",
  "max_depth": 3,
  "max_pages": 15,
  "same_domain_only": true,
  "allow_patterns": ["/docs/", "/guide/"],
  "deny_patterns": ["/api-reference"],
  "link_selection_strategy": "content_biased",
  "links_per_page": 4,
  "delay_min": 2.0,
  "delay_max": 6.0,
  "simulate_reading": true
}
```

**Returns for each page:**
- `url`, `depth`, `status_code`
- `title`, `meta_description`
- `headings[]`, `paragraphs[]` (extracted via BeautifulSoup)
- `word_count`, `fetch_time_ms`, `reading_time_s`
- `links_discovered`, `links_selected_to_follow`, `followed_links[]`

---

## Human Behavior Model

```
Visit URL
   │
   ├── Wait [delay_min, delay_max] seconds  ← random, occasional 3× spike
   │
   ├── Send request with:
   │     • Random User-Agent (Chrome/FF/Safari/Edge)
   │     • Real Accept / Accept-Language / Sec-Fetch-* headers
   │     • Referrer = previous page URL
   │     • Cookies accumulated from all previous responses
   │
   ├── Receive HTML → absorb Set-Cookie headers
   │
   ├── Parse content (BeautifulSoup)
   │     • Strip scripts, ads, nav, footer
   │     • Extract main content element
   │     • Collect headings, paragraphs, tables, images
   │
   ├── Simulate reading time (word_count / reading_speed)
   │
   ├── Extract links (Scrapy LinkExtractor)
   │     • Apply allow/deny patterns
   │     • Block binary extensions
   │     • Filter same-domain if requested
   │
   ├── Prioritize links (strategy)
   │     • Pick only links_per_page (humans don't click everything)
   │
   └── Enqueue selected links → repeat
```

---

## Architecture

```
web_scraper_mcp/
├── server.py          ← FastMCP server (single-file)
├── requirements.txt
└── README.md
```

**Key dependencies:**

| Library | Role |
|---|---|
| `mcp[cli]` | FastMCP server framework |
| `scrapy` | `LinkExtractor` for robust link discovery |
| `beautifulsoup4` + `lxml` | HTML parsing and content extraction |
| `httpx` | Async HTTP client with cookie + redirect support |
| `pydantic` | Input validation for all tools |

---

## Notes

- **No JavaScript rendering** — This server uses plain HTTP. For JS-heavy SPAs, consider adding a Playwright integration layer.
- **In-memory sessions** — Sessions reset when the server restarts. For persistence, swap `_sessions` dict with a SQLite backend.
- **Rate limiting** — The human delays are the only rate limiting. For aggressive crawls, increase `delay_min` / `delay_max`.
- **Robots.txt** — This server does not check `robots.txt` by default. Respect website policies.