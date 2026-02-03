#!/bin/bash

# Build script for Stash scraper repository
# Generates index.yml and zip files for each scraper

set -e

OUTPUT_DIR="${1:-_site}"
SCRAPERS_DIR="scrapers"

mkdir -p "$OUTPUT_DIR/main"

echo "# Auto-generated scraper index" > "$OUTPUT_DIR/main/index.yml"

for scraper in "$SCRAPERS_DIR"/*.yml; do
    [ -f "$scraper" ] || continue

    filename=$(basename "$scraper" .yml)
    name=$(grep -m1 "^name:" "$scraper" | sed 's/name: *//')

    # Get version from git or use date
    if git rev-parse --git-dir > /dev/null 2>&1; then
        version=$(git log -1 --format="%h" -- "$scraper" 2>/dev/null || echo "1.0.0")
        date=$(git log -1 --format="%Y-%m-%d" -- "$scraper" 2>/dev/null || date +%Y-%m-%d)
    else
        version="1.0.0"
        date=$(date +%Y-%m-%d)
    fi

    # Create zip
    zip_path="main/$filename.zip"
    (cd "$SCRAPERS_DIR" && zip -q "../$OUTPUT_DIR/$zip_path" "$filename.yml")

    # Calculate sha256
    sha256=$(sha256sum "$OUTPUT_DIR/$zip_path" | cut -d' ' -f1)

    # Append to index
    cat >> "$OUTPUT_DIR/main/index.yml" << EOF
- id: $filename
  name: "$name"
  version: $version
  date: $date
  path: $filename.zip
  sha256: $sha256
EOF

    echo "Processed: $filename"
done

echo "Build complete: $OUTPUT_DIR/main/index.yml"
