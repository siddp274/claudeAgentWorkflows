# brave-search-mcp

A Python MCP server that gives AI agents access to the **Brave Search API** — with web search, news search, and built-in pagination support. Results are structured for maximum context with minimum token cost.

---

## Features

- **`brave_web_search`** — General web search with optional freshness, country, and language filters
- **`brave_news_search`** — Recent news articles with publish dates
- **`brave_paginate`** — Convenience tool: pass the `next_offset` from any result to get the next page
- **Token-efficient output** — HTML stripped, verbose metadata removed, only useful fields returned
- **Extra snippets** — Optional `extra_snippets=true` adds up to 3 extra page excerpts per result for deeper context without fetching the URL
- **Pagination metadata** — Every response includes `has_more`, `next_offset`, and a plain-English note

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Get a Brave Search API key

Sign up at https://api-dashboard.search.brave.com/ and create an API key.

### 3. Set the environment variable

```bash
export BRAVE_API_KEY=your_key_here
```

Or add it to a `.env` file and load it with `python-dotenv`.

---

## Running

### stdio (local / Claude Desktop / Claude Code)

```bash
python src/server.py
```

### HTTP transport (remote / multi-client)

```python
# At the bottom of server.py, change:
mcp.run()
# to:
mcp.run(transport="streamable_http", port=8000)
```

---

## Connecting to Claude Desktop

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "brave-search": {
      "command": "python",
      "args": ["/absolute/path/to/brave-search-mcp/src/server.py"],
      "env": {
        "BRAVE_API_KEY": "your_key_here"
      }
    }
  }
}
```

## Connecting to Claude Code

```bash
claude mcp add brave-search python /absolute/path/to/brave-search-mcp/src/server.py
```

Then set the env var in your shell or pass it via `--env BRAVE_API_KEY=...`.

---

## Response Structure

All tools return JSON. Example `brave_web_search` response:

```json
{
  "query": "python async best practices",
  "results": [
    {
      "rank": 1,
      "title": "Async IO in Python: A Complete Walkthrough",
      "url": "https://realpython.com/async-io-python/",
      "source": "realpython.com",
      "description": "A hands-on guide to async IO in Python using asyncio, covering coroutines, tasks, and event loops.",
      "extra_context": [
        "asyncio.run() is the recommended entry point for running top-level async code.",
        "Use asyncio.gather() to run multiple coroutines concurrently."
      ],
      "published": "2024-03-10"
    }
  ],
  "pagination": {
    "page": 1,
    "count": 10,
    "has_more": true,
    "next_offset": 1,
    "note": "Pass offset=1 to get the next page."
  }
}
```

---

## Pagination

Every response includes a `pagination` block. To get the next page:

```
brave_paginate(query="...", next_offset=<pagination.next_offset>, count=10)
```

Or pass `offset` directly to `brave_web_search` / `brave_news_search`.

Brave supports offsets **0–9** (10 pages max per query).

---

## Extra Snippets

Set `extra_snippets=true` on any search to get up to 3 additional page excerpts per result. These come directly from Brave's index and give the agent more context about a page without needing to fetch and parse the URL. Requires an **AI or Data** Brave plan.

---

## Notes

- Web search: max 20 results/page, max 9 offsets
- News search: max 50 results/page, max 9 offsets
- `text_decorations=false` is always set — snippets are returned as clean plain text, no HTML bold tags
- HTML entities in descriptions are decoded automatically