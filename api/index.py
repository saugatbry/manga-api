import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from flask_cors import CORS
import re
import time

app = Flask(__name__)
CORS(app)

# Use Session for faster requests
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
})

# Simple Cache (In-memory)
CACHE = {}
CACHE_EXPIRY = 300 # 5 minutes

def get_cache(key):
    if key in CACHE:
        data, expiry = CACHE[key]
        if time.time() < expiry:
            return data
    return None

def set_cache(key, data):
    CACHE[key] = (data, time.time() + CACHE_EXPIRY)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Manga Scraper API Optimized",
        "endpoints": {
            "latest": "/api/manga/latest",
            "search": "/api/manga/search?q=query",
            "trending": "/api/manga/trending",
            "genres": "/api/manga/genres"
        }
    })

def fix_poster(url):
    if not url: return ""
    # Remove thumbnail suffixes like -175x238, -110x150, etc.
    return re.sub(r'-\d+x\d+(\.\w+)$', r'\1', url)

@app.route('/api/manga/latest', methods=['GET'])
def latest_manga():
    orderby = request.args.get('orderby', '')
    genre = request.args.get('genre', '')
    query = request.args.get('q', '')
    
    # Cache Key
    cache_key = f"latest_{genre}_{orderby}_{query}"
    cached = get_cache(cache_key)
    if cached: return jsonify(cached)
    
    # Construct target URL
    if query:
        url = f"https://www.mangaread.org/?s={query}&post_type=wp-manga"
    elif genre:
        # Provider uses /genres/ instead of /manga-genre/
        url = f"https://www.mangaread.org/genres/{genre}/"
        if orderby: url += f"?m_orderby={orderby}"
    else:
        url = "https://www.mangaread.org/"
        if orderby: 
            url = "https://www.mangaread.org/manga/"
            url += f"?m_orderby={orderby}"
        
    try:
        response = session.get(url, timeout=10)
        if response.status_code != 200:
            return jsonify({"success": False, "error": f"Provider error {response.status_code}"}), 500
            
        # Use 'lxml' for much faster parsing
        soup = BeautifulSoup(response.text, 'lxml')
        results = []
        
        # Select items efficiently
        items = soup.select('div.page-item-detail, div.manga-item, div.page-listing-item')
        if not items:
            container = soup.find('div', id='loop-content') or soup.find('div', class_='page-content-listing')
            if container: items = container.select('div.page-item-detail')

        for item in items:
            title_tag = item.select_one('h3 a, h4 a, h5 a')
            if not title_tag: continue
            
            img_tag = item.find('img')
            chapter_tag = item.select_one('span.chapter a, .chapter-item a')
            time_tag = item.select_one('span.post-on, .post-date')
            
            # Poster extraction logic
            poster_url = ""
            if img_tag:
                poster_url = img_tag.get('data-src') or img_tag.get('src') or img_tag.get('data-srcset') or ""
                if ' ' in poster_url: poster_url = poster_url.split(' ')[0]
                if poster_url.startswith('//'): poster_url = 'https:' + poster_url

            results.append({
                "title": title_tag.text.strip(),
                "slug": title_tag['href'].strip('/').split('/')[-1],
                "poster": fix_poster(poster_url),
                "latest_chapter": chapter_tag.text.strip() if chapter_tag else "New",
                "time": time_tag.text.strip() if time_tag else ""
            })
        
        # Deduplicate
        seen = set()
        final_results = []
        for r in results:
            if r['slug'] not in seen:
                seen.add(r['slug'])
                final_results.append(r)
                
        output = {"success": True, "results": final_results[:40]}
        set_cache(cache_key, output)
        return jsonify(output)
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/search', methods=['GET'])
def search_manga():
    query = request.args.get('q')
    if not query: return jsonify({"success": False, "error": "Query is required"}), 400
    
    url = f"https://www.mangaread.org/?s={query}&post_type=wp-manga"
    try:
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        results = []
        
        items = soup.select('div.c-tabs-item__content, div.page-item-detail')
        for item in items:
            title_tag = item.select_one('h3 a, h4 a')
            if not title_tag: continue
            
            img_tag = item.find('img')
            chapter_tag = item.select_one('span.chapter a, .latest-chap a')
            
            poster_url = ""
            if img_tag:
                poster_url = img_tag.get('data-src') or img_tag.get('src') or ""
                if ' ' in poster_url: poster_url = poster_url.split(' ')[0]
            
            results.append({
                "title": title_tag.text.strip(),
                "slug": title_tag['href'].strip('/').split('/')[-1],
                "poster": fix_poster(poster_url),
                "latest_chapter": chapter_tag.text.strip() if chapter_tag else ""
            })
        return jsonify({"success": True, "results": results})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/trending', methods=['GET'])
def trending_manga():
    cached = get_cache('trending')
    if cached: return jsonify(cached)
    
    url = "https://www.mangaread.org/"
    try:
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        results = []
        
        items = soup.select('div.popular-item-wrap')
        for item in items:
            title_tag = item.find('h5').find('a')
            img_tag = item.find('img')
            poster_url = img_tag.get('data-src') or img_tag.get('src') or ""
            
            results.append({
                "title": title_tag.text.strip(),
                "slug": title_tag['href'].strip('/').split('/')[-1],
                "poster": fix_poster(poster_url),
            })
        output = {"success": True, "results": results}
        set_cache('trending', output)
        return jsonify(output)
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/genres', methods=['GET'])
def get_genres():
    genres = ["Action", "Adventure", "Comedy", "Drama", "Ecchi", "Fantasy", "Gender Bender", "Harem", "Historical", "Horror", "Isekai", "Josei", "Martial Arts", "Mature", "Mecha", "Mystery", "Psychological", "Romance", "School Life", "Sci-fi", "Seinen", "Shoujo", "Shoujo Ai", "Shounen", "Shounen Ai", "Slice of Life", "Smut", "Sports", "Supernatural", "Tragedy", "Webtoon"]
    return jsonify({"success": True, "genres": genres})

# Vercel Export
app = app
