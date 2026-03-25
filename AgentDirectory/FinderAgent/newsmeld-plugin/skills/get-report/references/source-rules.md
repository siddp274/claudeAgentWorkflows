# Source-Specific Rules

## Source Priority Order

1. **Firstpost** — always first, richest source, custom tool integration
2. **Reuters** — JS-gated, use Google as_sitesearch
3. **ANI News** — native search works, special link handling
4. **The Guardian** — JS-gated, use Google as_sitesearch
5. **NDTV** — JS-gated, use Google as_sitesearch
6. **BBC News** — native search works
7. **SCMP** — native search works
8. **The Diplomat** — native search works
9. **Republic World** — JS-gated, use Google as_sitesearch
10. **Bellingcat** — native search works
11. **OCCRP** — native search works
12. **ICIJ** — native search works

## Firstpost — Custom Integration

Call `scraper_extract_links` directly. No accessibility tree needed.

```
scraper_extract_links(
  agency = "firstpost",
  query  = "semantic sentence describing what you're looking for",
  max_links = 8
)
```

**Query must be a natural language sentence**, not keywords:

| Topic | Correct query |
|-------|--------------|
| Iran crypto sanctions | "How Iran is using cryptocurrency to bypass western sanctions during the war" |
| Oil crisis Hormuz | "Impact of Strait of Hormuz closure on global oil supply and prices" |
| Peace talks | "Iran US war Tehran strikes Trump peace talks Iran denying negotiations" |

Article extraction via `scraper_extract_content` works on Firstpost article URLs.

## JS-Gated Sites — Google as_sitesearch Fallback

These sites render search results with JavaScript. Skip native search entirely — go straight to Google fallback.

| Site | Google fallback URL |
|------|-------------------|
| Reuters | `https://www.google.com/search?q={query}&as_sitesearch=www.reuters.com` |
| The Guardian | `https://www.google.com/search?q={query}&as_sitesearch=www.theguardian.com` |
| NDTV | `https://www.google.com/search?q={query}&as_sitesearch=www.ndtv.com` |
| Republic World | `https://www.google.com/search?q={query}&as_sitesearch=www.republicworld.com` |

Run `scraper_fetch_accessibility_tree` on the Google URL, then `scraper_extract_links` on same URL.

**Timing risk**: Google may soft-block after multiple `as_sitesearch` queries in succession. Run Google-fallback sources early in the pipeline.

## Native Search Works — Try Direct

| Site | Native search URL pattern |
|------|--------------------------|
| BBC News | `https://www.bbc.com/search?q={query}` |
| SCMP | `https://www.scmp.com/search/{query}?q={query}` |
| OCCRP | `https://www.occrp.org/en/search?articles%5Bquery%5D={query}` |
| Bellingcat | `https://www.bellingcat.com/?s={query}` |
| ICIJ | `https://www.icij.org/search/?q={query}` |
| The Diplomat | `https://thediplomat.com/search?gcse={query}` |

If native search returns 0 links, fall back to Google `as_sitesearch`.

## ANI News — Special Handling

Native search URL: `https://aninews.in/search/?query={query}` (use `+` for spaces).

ANI's accessibility tree works. `scraper_extract_links` has been patched with agency-aware regex to reconstruct full URLs from ANI's relative paths.

```
scraper_fetch_accessibility_tree(url="https://aninews.in/search/?query=iran+war")
scraper_extract_links(agency="aninews", query=None)
```

If links still return 0, fall back to `scraper_extract_content` on the search URL itself — headings give article titles, paragraphs give lead sentences.

## Wikipedia — Named Entity Grounding Only

Use only for specific named entities from news content (e.g., "Binance", "IRGC", "Strait_of_Hormuz").

- Build URL directly: `https://en.wikipedia.org/wiki/{Entity_Name}` (underscores for spaces)
- Skip accessibility tree and link extraction entirely
- Go straight to `scraper_extract_content`
- Counts as one of your 3 extraction slots
- Do NOT search abstract compound topics — they will 404

## The `query` Parameter Rule

The `query` parameter in `scraper_extract_links` behaves differently per agency:

- **Firstpost** → required, must be a semantic sentence, drives backend search
- **All other agencies** → pass `query=None` (required by schema but ignored by extraction logic)

Never pass keyword strings for non-Firstpost agencies.

## Indian News Outlets

Include at least one Indian outlet when the topic has India relevance. Priority: ANI News > NDTV > Republic World.

If no Indian outlet has relevant content, note this transparently rather than forcing irrelevant coverage.

## Link Extraction Internals

The `scraper_extract_links` tool uses agency-aware regex:

- Sites like ANI return relative paths (e.g., `/news/world/asia/article`) — the tool reconstructs full URLs
- `MIN_PATH_DEPTH=3` filters out nav/utility links
- Nav segments like "search", "about", "tag", "author" are blocked
- Any section prefix works (`/news/`, `/world/`, `/sports/`, `/business/`)
