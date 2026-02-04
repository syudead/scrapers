import json
import sys
import re
import io
import subprocess

# Fix Windows console encoding
if sys.stdout:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def log(msg):
    print(f"[AvBase] {msg}", file=sys.stderr)

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])

try:
    import cloudscraper
except ImportError:
    log("Installing cloudscraper...")
    install_package("cloudscraper")
    import cloudscraper

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
)

def fetch_page(url):
    try:
        response = scraper.get(url, timeout=30)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
        log(f"HTTP {response.status_code} for {url}")
        return None
    except Exception as e:
        log(f"Fetch error: {e}")
        return None

def extract_next_data(html):
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            log(f"JSON parse error: {e}")
    return None

def parse_date(date_str):
    if not date_str:
        return None
    months = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
              'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
    match = re.search(r'(\w+)\s+(\w+)\s+(\d+)\s+(\d{4})', date_str)
    if match:
        return f"{match.group(4)}-{months.get(match.group(2),'01')}-{match.group(3).zfill(2)}"
    return None

def clean_dict(d):
    """Remove None values and empty lists from dict"""
    if not isinstance(d, dict):
        return d
    return {k: clean_dict(v) for k, v in d.items()
            if v is not None and v != [] and v != {}}

def scrape_scene(url):
    log(f"Scraping: {url}")
    html = fetch_page(url)
    if not html:
        return None

    next_data = extract_next_data(html)
    if not next_data:
        log("Failed to extract __NEXT_DATA__")
        return None

    work = next_data.get('props', {}).get('pageProps', {}).get('work')
    if not work:
        log("No work data found")
        return None

    products = work.get('products', [])
    primary = products[0] if products else {}

    scene = {
        'title': work.get('title'),
        'code': work.get('work_id'),
        'details': work.get('note') or None,
        'date': parse_date(work.get('min_date')),
        'url': url,
        'image': primary.get('image_url'),
        'studio': {'name': primary.get('maker', {}).get('name')} if primary.get('maker', {}).get('name') else None,
        'performers': [{'name': c['actor']['name']} for c in work.get('casts', []) if c.get('actor', {}).get('name')],
        'tags': [{'name': g['name']} for g in work.get('genres', [])]
    }

    return clean_dict(scene)

def scrape_by_fragment(fragment):
    # Extract code from various input formats
    code = re.sub(r'[^a-zA-Z0-9\-:]', '', fragment).upper()
    # Remove common prefixes if present
    code = re.sub(r'^(FC2-PPV-|FC2PPV)', '', code)
    url = f"https://www.avbase.net/works/{code}"
    return scrape_scene(url)

def extract_code_from_data(data):
    """Extract code from various input fields"""
    # Try direct code field
    if data.get('code'):
        return data['code']
    # Try title field (might contain code)
    if data.get('title'):
        # Extract code pattern from title (e.g., "SSIS-001" from filename)
        match = re.search(r'([A-Z]{2,}[-_]?\d{3,})', data['title'].upper())
        if match:
            return match.group(1)
        return data['title']
    # Try filename from files
    if data.get('files'):
        for f in data['files']:
            basename = f.get('basename', '')
            # Remove extension
            basename = re.sub(r'\.[^.]+$', '', basename)
            match = re.search(r'([A-Z]{2,}[-_]?\d{3,})', basename.upper())
            if match:
                return match.group(1)
            # If no pattern match, use basename without extension as-is
            if basename:
                return basename
    return None

if __name__ == '__main__':
    result = None

    try:
        # Read JSON from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data else {}

        # Get mode from command argument
        mode = sys.argv[1] if len(sys.argv) > 1 else None

        if mode == 'scene-by-url':
            if 'url' in data:
                result = scrape_scene(data['url'])
            else:
                log("No URL in input")

        elif mode == 'scene-by-fragment':
            code = extract_code_from_data(data)
            if code:
                result = scrape_by_fragment(code)
            else:
                log("No code found in fragment data")

        elif mode == 'scene-by-name':
            # User's search query - return array of results
            query = data.get('name', '')
            if query:
                scene = scrape_by_fragment(query)
                result = [scene] if scene else []
            else:
                log("No search query")
                result = []

        elif mode == 'scene-by-query-fragment':
            code = extract_code_from_data(data)
            if code:
                scene = scrape_by_fragment(code)
                result = [scene] if scene else []
            else:
                log("No code found in query fragment")
                result = []

        else:
            # CLI test mode
            if len(sys.argv) > 1:
                arg = sys.argv[1]
                result = scrape_scene(arg) if arg.startswith('http') else scrape_by_fragment(arg)
            else:
                log("Usage: avbase.py <mode>")
                log("Modes: scene-by-url, scene-by-fragment, scene-by-name, scene-by-query-fragment")

    except json.JSONDecodeError:
        # CLI test mode fallback
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            result = scrape_scene(arg) if arg.startswith('http') else scrape_by_fragment(arg)
    except Exception as e:
        log(f"Error: {e}")
        result = None

    # Output result
    if result is None:
        print("{}")
    elif isinstance(result, list):
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))
