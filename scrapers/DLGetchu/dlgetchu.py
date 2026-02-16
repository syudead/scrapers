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
    print(f"[DLGetchu] {msg}", file=sys.stderr)

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])

try:
    import requests
except ImportError:
    log("Installing requests...")
    install_package("requests")
    import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    log("Installing beautifulsoup4...")
    install_package("beautifulsoup4")
    from bs4 import BeautifulSoup

def fetch_page(url):
    """Fetch page with EUC-JP encoding support"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'euc-jp'
        if response.status_code == 200:
            return response.text
        log(f"HTTP {response.status_code} for {url}")
        return None
    except Exception as e:
        log(f"Fetch error: {e}")
        return None


def extract_item_id(url):
    """Extract item ID from URL"""
    match = re.search(r'item(\d+)', url)
    if match:
        return match.group(1)
    return None


def clean_dict(d):
    """Remove None values and empty lists from dict"""
    if not isinstance(d, dict):
        return d
    return {k: clean_dict(v) for k, v in d.items()
            if v is not None and v != [] and v != {}}


def scrape_scene(url):
    """Scrape scene metadata from dl.getchu.com"""
    log(f"Scraping: {url}")
    html = fetch_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Extract item ID from URL
    item_id = extract_item_id(url)

    # Extract title from og:title or page title
    title = None
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        title = og_title['content'].strip()
    if not title:
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            # Remove site suffix
            title = re.sub(r'\s*[|\-].*$', '', title)

    # Extract image from og:image
    image = None
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        image = og_image['content'].strip()

    # Extract description from meta description
    details = None
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        details = meta_desc['content'].strip()

    # Extract studio (circle name) from link with dojin_circle_detail.php
    studio = None
    circle_link = soup.find('a', href=re.compile(r'dojin_circle_detail\.php'))
    if circle_link:
        studio = circle_link.get_text().strip()

    # Extract date from table cell containing date info
    date = None
    # Look for text containing date format YYYY/MM/DD
    date_pattern = re.compile(r'(\d{4})/(\d{2})/(\d{2})')

    # Try to find in table cells
    for td in soup.find_all('td'):
        text = td.get_text()
        match = date_pattern.search(text)
        if match:
            date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            break

    # Extract tags/genres from genre links
    tags = []
    genre_links = soup.find_all('a', href=re.compile(r'genre_id='))
    for link in genre_links:
        tag_name = link.get_text().strip()
        if tag_name and tag_name not in [t['name'] for t in tags]:
            tags.append({'name': tag_name})

    scene = {
        'title': title,
        'code': item_id,
        'details': details,
        'date': date,
        'url': url,
        'image': image,
        'studio': {'name': studio} if studio else None,
        'tags': tags
    }

    return clean_dict(scene)


def scrape_by_code(code):
    """Scrape by item code/ID"""
    # Clean code - extract numbers only
    code = re.sub(r'[^\d]', '', code)
    if not code:
        return None
    url = f"https://dl.getchu.com/i/item{code}"
    return scrape_scene(url)


def extract_code_from_data(data):
    """Extract item code from various input fields"""
    # Try direct code field
    if data.get('code'):
        return data['code']

    # Try URL field - extract code from dl.getchu.com URL
    url = data.get('url') or (data.get('urls', [None])[0] if data.get('urls') else None)
    if url and 'dl.getchu.com' in url:
        item_id = extract_item_id(url)
        if item_id:
            return item_id

    # Try filename from files
    if data.get('files'):
        for f in data['files']:
            basename = f.get('basename', '')
            # Remove extension
            basename = re.sub(r'\.[^.]+$', '', basename)
            # Look for item ID pattern (sequence of digits)
            match = re.search(r'(\d{6,})', basename)
            if match:
                return match.group(1)

    # Try title field
    if data.get('title'):
        # Look for item ID in title
        match = re.search(r'(\d{6,})', data['title'])
        if match:
            return match.group(1)

    return None


if __name__ == '__main__':
    result = None

    try:
        # Read JSON from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data else {}

        # Get mode from command argument
        mode = sys.argv[1] if len(sys.argv) > 1 else None
        log(f"Mode: {mode}")
        log(f"Input: {json.dumps(data, ensure_ascii=False)[:500]}")

        if mode == 'scene-by-url':
            if 'url' in data:
                result = scrape_scene(data['url'])
            else:
                log("No URL in input")

        elif mode == 'scene-by-fragment':
            code = extract_code_from_data(data)
            log(f"Extracted code: {code}")
            if code:
                result = scrape_by_code(code)
            else:
                log("No code found in fragment data")

        elif mode == 'scene-by-name':
            # User's search query - treat as item ID
            query = data.get('name', '')
            if query:
                scene = scrape_by_code(query)
                if scene:
                    # Return minimal search result format
                    result = [{
                        'title': scene.get('title'),
                        'url': scene.get('url'),
                        'date': scene.get('date'),
                        'image': scene.get('image')
                    }]
                else:
                    result = []
            else:
                log("No search query")
                result = []

        elif mode == 'scene-by-query-fragment':
            # Return single scene object (same as scene-by-fragment)
            code = extract_code_from_data(data)
            log(f"Extracted code: {code}")
            if code:
                result = scrape_by_code(code)
            else:
                log("No code found in query fragment")

        else:
            # CLI test mode
            if len(sys.argv) > 1:
                arg = sys.argv[1]
                result = scrape_scene(arg) if arg.startswith('http') else scrape_by_code(arg)
            else:
                log("Usage: dlgetchu.py <mode>")
                log("Modes: scene-by-url, scene-by-fragment, scene-by-name, scene-by-query-fragment")

    except json.JSONDecodeError:
        # CLI test mode fallback
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            result = scrape_scene(arg) if arg.startswith('http') else scrape_by_code(arg)
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
