# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Stash scraper repository** that provides metadata scrapers for adult video databases. Stash is a media organizer application that uses these scrapers to fetch scene metadata. The scrapers are distributed via GitHub Pages.

## Architecture

### Scraper Types

1. **XPath Scrapers** (YAML-only): Define XPath selectors to extract data from HTML pages
   - Example: `scrapers/ppvdatabank.yml` - uses `scrapeXPath` action with selector definitions

2. **Script Scrapers** (Python + YAML): Use Python scripts for complex scraping logic
   - Example: `scrapers/AvBase/` - uses `cloudscraper` to bypass Cloudflare protection
   - YAML file defines entry points, Python script handles scraping

### Stash Scraper Interface

Python scrapers receive JSON on stdin and output JSON to stdout. The mode is passed as command argument:
- `scene-by-url`: Given `{"url": "..."}`, return full scene metadata
- `scene-by-fragment`: Given scene data, extract code and fetch metadata
- `scene-by-name`: Given `{"name": "..."}` search query, return array of minimal results
- `scene-by-query-fragment`: Same as scene-by-fragment

### Output Format

Scene metadata JSON should include: `title`, `code`, `details`, `date` (YYYY-MM-DD), `url`, `urls`, `image`, `studio`, `performers`, `tags`

## Build & Deployment

The project uses GitHub Actions (`.github/workflows/deploy.yml`) to:
1. Zip each scraper (single .yml or directory)
2. Calculate SHA256 checksums
3. Update `index.yml` with checksums
4. Deploy to GitHub Pages

No local build commands needed - just push to `main` branch.

## Testing Scrapers Locally

```bash
# Test AvBase scraper with URL
echo '{"url":"https://www.avbase.net/works/CODE"}' | python scrapers/AvBase/avbase.py scene-by-url

# Test with code/fragment
echo '{"code":"CODE"}' | python scrapers/AvBase/avbase.py scene-by-fragment

# CLI shortcut (auto-detects URL vs code)
python scrapers/AvBase/avbase.py https://www.avbase.net/works/CODE
python scrapers/AvBase/avbase.py CODE
```

## Key Files

- `index.yml`: Package index with scraper metadata and SHA256 checksums (updated by CI)
- `scrapers/*.yml`: XPath-based scrapers
- `scrapers/*/`: Script-based scrapers (Python + YAML + requirements.txt)
