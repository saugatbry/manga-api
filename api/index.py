import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from flask_cors import CORS
import re
import os
import sys

# Add parent directory to path to import manga_scrape
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from manga_scrape import getChapters, scrape_img

app = Flask(__name__)
CORS(app)

# Use Session for faster requests
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Referer': 'https://www.mangaread.org/',
})

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Manga Scraper API Reliable Mode",
        "endpoints": {
            "latest": "/api/manga/latest",
            "search": "/api/manga/search?q=query",
            "trending": "/api/manga/trending"
        }
    })

def fix_poster(url):
    if not url: return ""
    return re.sub(r'-\d+x\d+(\.\w+)$', r'\1', url)

@app.route('/api/manga/latest', methods=['GET'])
def latest_manga():
    orderby = request.args.get('orderby', '')
    genre = request.args.get('genre', '')
    query = request.args.get('q', '')
    
    if query:
        url = f"https://www.mangaread.org/?s={query}&post_type=wp-manga"
    elif genre:
        url = f"https://www.mangaread.org/genres/{genre}/"
        if orderby: url += f"?m_orderby={orderby}"
    else:
        url = "https://www.mangaread.org/"
        if orderby: 
            url = "https://www.mangaread.org/manga/"
            url += f"?m_orderby={orderby}"
        
    try:
        response = session.get(url, timeout=15)
        if response.status_code != 200:
            return jsonify({"success": False, "error": f"Status {response.status_code}"}), response.status_code
            
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Use simple find_all for reliability
        items = soup.find_all('div', class_='page-item-detail')
        if not items:
            items = soup.select('div.manga-item, div.page-listing-item')

        for item in items:
            title_link = item.find('a', title=True) or item.select_one('.post-title a, h3 a, h5 a')
            if not title_link: continue
            
            img_tag = item.find('img')
            chapter_link = item.select_one('.chapter a, .list-chapter a')
            time_tag = item.select_one('.post-on, .post-date')
            
            poster_url = ""
            if img_tag:
                poster_url = img_tag.get('data-src') or img_tag.get('src') or ""
                if ' ' in poster_url: poster_url = poster_url.split(' ')[0]
                if poster_url.startswith('//'): poster_url = 'https:' + poster_url

            results.append({
                "title": title_link.get('title') or title_link.text.strip(),
                "slug": title_link['href'].strip('/').split('/')[-1],
                "poster": fix_poster(poster_url),
                "latest_chapter": chapter_link.text.strip() if chapter_link else "New",
                "time": time_tag.text.strip() if time_tag else ""
            })
        
        seen = set()
        final_results = []
        for r in results:
            if r['slug'] not in seen:
                seen.add(r['slug'])
                final_results.append(r)
                
        return jsonify({"success": True, "results": final_results[:40]})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/search', methods=['GET'])
def search_manga():
    query = request.args.get('q')
    if not query: return jsonify({"success": False, "error": "Query is required"}), 400
    
    url = f"https://www.mangaread.org/?s={query}&post_type=wp-manga"
    try:
        response = session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        items = soup.select('div.c-tabs-item__content, div.page-item-detail')
        for item in items:
            title_tag = item.select_one('h3 a, h4 a, h5 a')
            if not title_tag: continue
            
            img_tag = item.find('img')
            chapter_tag = item.select_one('span.chapter a, .latest-chap a')
            
            poster_url = ""
            if img_tag:
                poster_url = img_tag.get('data-src') or img_tag.get('src') or ""
            
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
    url = "https://www.mangaread.org/"
    try:
        response = session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        items = soup.find_all('div', class_='popular-item-wrap')
        for item in items:
            title_tag = item.find('h5').find('a')
            img_tag = item.find('img')
            poster_url = img_tag.get('data-src') or img_tag.get('src') or ""
            
            results.append({
                "title": title_tag.text.strip(),
                "slug": title_tag['href'].strip('/').split('/')[-1],
                "poster": fix_poster(poster_url),
            })
        return jsonify({"success": True, "results": results})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/genres', methods=['GET'])
def get_genres():
    genres = ["Action", "Adventure", "Comedy", "Drama", "Ecchi", "Fantasy", "Gender Bender", "Harem", "Historical", "Horror", "Isekai", "Josei", "Martial Arts", "Mature", "Mecha", "Mystery", "Psychological", "Romance", "School Life", "Sci-fi", "Seinen", "Shoujo", "Shoujo Ai", "Shounen", "Shounen Ai", "Slice of Life", "Smut", "Sports", "Supernatural", "Tragedy", "Webtoon"]
    return jsonify({"success": True, "genres": genres})

app = app
