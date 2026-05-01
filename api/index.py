import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from flask_cors import CORS
import re
import os

app = Flask(__name__)
CORS(app)

# Use Session for faster requests
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Referer': 'https://www.mangaread.org/',
})

def fix_poster(url):
    if not url: return ""
    return re.sub(r'-\d+x\d+(\.\w+)$', r'\1', url)

@app.route('/')
def home():
    return jsonify({"status": "online", "message": "KageRead API Ready"})

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
            url = f"https://www.mangaread.org/manga/?m_orderby={orderby}"
        
    try:
        response = session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        items = soup.find_all('div', class_='page-item-detail')
        if not items: items = soup.select('div.manga-item')

        for item in items:
            title_link = item.select_one('.post-title a, h3 a, h5 a')
            if not title_link: continue
            
            img_tag = item.find('img')
            chapter_link = item.select_one('.chapter a, .list-chapter a')
            
            poster_url = ""
            if img_tag:
                poster_url = img_tag.get('data-src') or img_tag.get('src') or ""
                if ' ' in poster_url: poster_url = poster_url.split(' ')[0]

            results.append({
                "title": title_link.text.strip(),
                "slug": title_link['href'].strip('/').split('/')[-1],
                "poster": fix_poster(poster_url),
                "latest_chapter": chapter_link.text.strip() if chapter_link else "New",
                "time": ""
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
            results.append({
                "title": title_tag.text.strip(),
                "slug": title_tag['href'].strip('/').split('/')[-1],
                "poster": fix_poster(img_tag.get('src') or img_tag.get('data-src') if img_tag else ""),
                "latest_chapter": ""
            })
        return jsonify({"success": True, "results": results})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/trending', methods=['GET'])
def trending_manga():
    try:
        response = session.get("https://www.mangaread.org/", timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        items = soup.select('div.popular-item-wrap')
        for item in items:
            title_tag = item.find('h5').find('a')
            img_tag = item.find('img')
            results.append({
                "title": title_tag.text.strip(),
                "slug": title_tag['href'].strip('/').split('/')[-1],
                "poster": fix_poster(img_tag.get('data-src') or img_tag.get('src') or ""),
            })
        return jsonify({"success": True, "results": results})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/chapters', methods=['GET'])
def fetch_chapters():
    name = request.args.get('name')
    url = f"https://www.mangaread.org/manga/{name}/"
    try:
        response = session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('li', class_='wp-manga-chapter')
        chapters = []
        for item in items:
            a = item.find('a')
            if a:
                slug = a['href'].strip('/').split('/')[-1]
                num_match = re.search(r'chapter-(\d+(\.\d+)?)', slug)
                num = num_match.group(1) if num_match else slug.replace('chapter-', '')
                chapters.append({"number": num, "url": a['href']})
        chapters.reverse() # Story-wise order
        return jsonify({"success": True, "chapters": chapters})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/images', methods=['GET'])
def fetch_images():
    url = request.args.get('url')
    try:
        response = session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        images = soup.find_all('img', class_='wp-manga-chapter-img')
        img_urls = [img.get('src', '').strip() or img.get('data-src', '').strip() for img in images]
        img_urls = [u for u in img_urls if u]
        return jsonify({"success": True, "images": img_urls})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/genres', methods=['GET'])
def get_genres():
    return jsonify({"success": True, "genres": ["Action", "Adventure", "Comedy", "Drama", "Ecchi", "Fantasy", "Harem", "Historical", "Horror", "Isekai", "Josei", "Martial Arts", "Mature", "Mecha", "Mystery", "Psychological", "Romance", "School Life", "Sci-fi", "Seinen", "Shoujo", "Shounen", "Slice of Life", "Sports", "Supernatural", "Tragedy", "Webtoon"]})

app = app
