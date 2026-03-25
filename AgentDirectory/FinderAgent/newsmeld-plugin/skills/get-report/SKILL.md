---
name: get-report
description: >
  Research a specific news topic and compile a multi-source report. Use when the user asks to
  "get a report on", "research", "what's happening with", "compile news about", or names a
  specific topic they want investigated across live news sources.
---

# Get Report — Topic Research Pipeline

Before starting, read `references/source-rules.md` for source-specific handling.

## Pipeline Steps

### Step 1 — Brave Search (context building)

Run ONE brave_web_search on the user's topic.

```
brave_web_search(
  query = "<topic keywords> <current year>",
  freshness = "pw",       # or "pd" for very recent topics
  count = 8,
  extra_snippets = true
)
```

Use results to understand angles, key entities, and which sources are likely to have coverage. Do NOT skip this step.

### Step 2 — Select up to 4 sources

After reviewing Brave results, pick up to 4 sources from the approved list in `references/source-rules.md`. Each source must cover a **different angle**. Do not select sources likely to say the same thing.

If the topic has India relevance, include at least one Indian outlet (ANI, NDTV, Republic World).

### Step 3 — Always try Firstpost first

Firstpost uses a custom backend search — no URL construction or accessibility tree needed.

```
scraper_extract_links(
  agency = "firstpost",
  query  = "semantic sentence describing what you're looking for",
  max_links = 8
)
```

The query MUST be a natural language sentence, not keywords. Example: "How Iran is using cryptocurrency to bypass western sanctions during the war" — NOT "iran crypto sanctions."

### Step 4 — Process each non-Firstpost, non-Wikipedia source

For each remaining source, follow this exact order:

1. `scraper_fetch_accessibility_tree` on the search URL
2. `scraper_extract_links` on the same search URL (pass `query=None` for all non-Firstpost agencies)
3. If 0 links returned and the source supports it, fall back to Google `as_sitesearch`

See `references/source-rules.md` for which sources are JS-gated (skip straight to Google fallback) vs native-search-works.

### Step 5 — Wikipedia (only when needed)

Use Wikipedia only for named entity grounding (e.g., "Binance", "IRGC", "Strait_of_Hormuz"). Skip tree and link extraction — go straight to `scraper_extract_content` on the direct URL: `https://en.wikipedia.org/wiki/{Entity_Name}`. This uses one of your 3 extraction slots.

Do NOT search compound abstract topics like `cryptocurrency_and_sanctions_evasion` — these will 404.

### Step 6 — Pre-allocate 3 content extraction slots

Read all link lists from all sources. Make a written plan assigning each slot to the highest-value article. Rules:

- Never use more than 2 slots on the same source
- Wikipedia counts as one slot
- If a source yielded no links, do not waste a slot on it

### Step 7 — Extract content

Execute the plan. If an article fails (403/blocked), reassign that slot to the next best URL from the same source's link list.

### Step 8 — Compile report

Synthesize all extracted content plus Brave snippets. Structure the report by topic section, not by source. For each claim, name the source it came from.

End every report with a **Transparency Note** listing:

- Sources attempted and methods used
- What succeeded and what failed
- Any fallbacks used

### Step 9 — Save to Notion Archive

After compiling the report and presenting it to the user, automatically save it to the **News Archive** database in Notion. Use the `notion-create-pages` tool with:

```
parent: { "data_source_id": "434a65a8-7915-4745-b4d6-a815ef859943" }
```

**Properties to set:**

| Property | How to fill it |
|----------|---------------|
| `Title` | A concise headline summarizing the report (not the user's raw query) |
| `Type` | `"Topic Report"` |
| `Topic` | JSON array — pick all that apply from: `Geopolitics`, `Trade`, `Defense`, `Technology`, `Economy`, `Energy`, `Climate`, `Health`, `Markets`, `Conflict` |
| `Tags` | JSON array of specific entities — countries, organizations, key subjects (e.g., `"China"`, `"US"`, `"Rare Earth Metals"`, `"Export Controls"`). Create new tag values as needed beyond presets. |
| `date:Date:start` | Today's date in `YYYY-MM-DD` format |
| `date:Date:is_datetime` | `0` |
| `Sources` | Number of sources successfully extracted (integer) |
| `Summary` | 1-2 sentence summary of the report's key finding |

**Content:** The full compiled report from Step 8 (all sections including the Transparency Note), formatted in Markdown.

**Icon:** Use a relevant emoji for the topic (e.g., `🌐` for geopolitics, `💰` for economy, `⚔️` for conflict, `🔬` for science, `💻` for technology).

After saving, include the Notion page URL in your response so the user can access it directly.

## Failure Handling

If all extractions fail, use Brave search snippets as primary content — label them clearly. Do NOT run additional Brave searches without user permission. Never hallucinate content.
