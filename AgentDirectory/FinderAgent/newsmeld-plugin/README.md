# NewsMeld

Autonomous news research plugin that compiles multi-source reports from live news outlets using a structured scraping pipeline.

## Components

| Component | Name | Purpose |
|-----------|------|---------|
| Agent | news-reporter | Autonomous research agent that runs the full pipeline |
| Skill | get-report | Research a specific topic across up to 4 sources |
| Skill | breaking-news | Scan 5 topic buckets for current events briefing |

## How It Works

The plugin uses a disciplined pipeline: Brave web search for context, source selection from 12+ approved outlets, link extraction with agency-aware handling, content extraction (3 slots per topic), and report synthesis with full transparency notes.

Sources include Firstpost, Reuters, BBC, The Guardian, NDTV, ANI News, SCMP, The Diplomat, Bellingcat, OCCRP, ICIJ, Republic World, and Wikipedia for entity grounding.

## Usage

- **Topic report**: "Get me a report on the Iran sanctions developments"
- **Breaking news**: "What's the breaking news today?"

## Requirements

This plugin requires the following MCP tools to be available in the environment:

- `brave_web_search` — Brave search API
- `scraper_fetch_accessibility_tree` — Page accessibility tree fetcher
- `scraper_extract_links` — Agency-aware link extractor
- `scraper_extract_content` — Article content extractor
