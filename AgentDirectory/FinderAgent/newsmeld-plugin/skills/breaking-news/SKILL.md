---
name: breaking-news
description: >
  Scan current events across multiple topic buckets and compile a breaking news briefing. Use when
  the user asks for "breaking news", "what's happening today", "news briefing", "current events",
  or wants a broad scan of today's headlines across war, politics, markets, sports, and science.
---

# Breaking News — Multi-Bucket Scan Pipeline

Before starting, read `../get-report/references/source-rules.md` for source-specific handling.

Breaking news is NOT a single query. It requires scanning multiple topic areas, extracting real named topics, then running a focused pipeline per topic.

## Step 1 — Run up to 5 Brave searches

Run all Brave searches BEFORE touching any scraper tool. Use `freshness="pd"` and `extra_snippets=true` for all.

| Bucket | Example query |
|--------|--------------|
| War / Conflict | "war conflict military strikes latest developments" |
| Politics / Diplomacy | "global politics elections government diplomacy" |
| Stocks / Economy | "stock markets oil prices economy today" |
| Sports | "sports results tournament championship" |
| Space / Earth / Science | "space science earthquake natural disaster" |

If the user specifies a country (e.g., "breaking news India"), bias the queries accordingly and use the `country` parameter.

## Step 2 — Extract real topics

From each bucket's results, extract actual named topics. Examples: "Iran peace talks dispute", "March Madness Sweet 16", "S&P 500 oil swing." If a bucket returns nothing meaningful, skip it.

## Step 3 — Run the downstream pipeline per topic

For each active topic bucket, run the standard get-report pipeline (Steps 2-8 from the get-report skill). Key differences for breaking news:

- Each topic bucket gets its own **3-slot content extraction budget**
- Strip all "breaking news" framing from scraper queries — use clean topic only
- Select sources that best match the specific topic, not generic news sources
- Firstpost remains highest priority for each topic

## Step 4 — Compile the briefing

Organize the final report by topic bucket, not by source. Each section should have:

- A headline summarizing the development
- Key details from extracted sources
- Source attribution for each claim

End with a **Transparency Note** covering all buckets: sources attempted, methods used, successes, and failures.

## Step 5 — Save to Notion Archive

After compiling the briefing and presenting it to the user, automatically save it to the **News Archive** database in Notion. Use the `notion-create-pages` tool with:

```
parent: { "data_source_id": "434a65a8-7915-4745-b4d6-a815ef859943" }
```

**Properties to set:**

| Property | How to fill it |
|----------|---------------|
| `Title` | `"Breaking News Briefing — <today's date in Month DD, YYYY format>"` |
| `Type` | `"Breaking News"` |
| `Topic` | JSON array — include all topic buckets that had coverage (e.g., `["Geopolitics", "Markets", "Conflict"]`) |
| `Tags` | JSON array of the most prominent entities across all buckets — countries, organizations, key subjects. Create new tag values as needed beyond presets. |
| `date:Date:start` | Today's date in `YYYY-MM-DD` format |
| `date:Date:is_datetime` | `0` |
| `Sources` | Total number of sources successfully extracted across all buckets (integer) |
| `Summary` | 1-2 sentence overview of the day's biggest stories |

**Content:** The full compiled briefing from Step 4 (all bucket sections + Transparency Note), formatted in Markdown.

**Icon:** `📰`

After saving, include the Notion page URL in your response so the user can access it directly.

## Failure Handling

Same rules as get-report. If all extractions fail for a bucket, use Brave snippets. Never fabricate content. If the pipeline is critically broken across all buckets, inform the user.
