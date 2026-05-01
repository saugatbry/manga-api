from flask import Flask, jsonify, request
import os
import sys
import requests
from bs4 import BeautifulSoup

# Add parent directory to path to import manga_scrape
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from manga_scrape import getChapters, scrape_img

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Manga Scraper API is running on Vercel",
        "endpoints": {
            "chapter_list": "/api/manga/chapters?name=<manga_slug>",
            "image_list": "/api/manga/images?url=<chapter_url>",
            "search": "/api/manga/search?q=<query>",
            "latest": "/api/manga/latest"
        }
    })

@app.route('/api/manga/chapters', methods=['GET'])
def fetch_chapters():
    manga_name = request.args.get('name')
    start = int(request.args.get('start', 1))
    end = int(request.args.get('end', 1000))
    if not manga_name: return jsonify({"error": "Manga name is required"}), 400
    try:
        links = getChapters(manga_name, start, end)
        chapters = []
        for link in links:
            num = link.split('chapter-')[-1].strip('/')
            chapters.append({"number": num, "url": link})
        return jsonify({"success": True, "manga": manga_name, "chapters": chapters})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/images', methods=['GET'])
def fetch_images():
    chapter_url = request.args.get('url')
    if not chapter_url: return jsonify({"error": "Chapter URL is required"}), 400
    try:
        img_urls = scrape_img(chapter_url)
        return jsonify({"success": True, "images": img_urls})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/search', methods=['GET'])
def search_manga():
    query = request.args.get('q')
    if not query: return jsonify({"success": False, "error": "Query is required"}), 400
    url = f"https://www.mangaread.org/?s={query}&post_type=wp-manga"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        items = soup.find_all('div', class_='c-tabs-item__content')
        for item in items:
            title_tag = item.find('h3', class_='h4').find('a')
            img_tag = item.find('img')
            results.append({
                "title": title_tag.text.strip(),
                "slug": title_tag['href'].strip('/').split('/')[-1],
                "poster": img_tag['src'] if img_tag else "",
                "latest_chapter": item.find('span', class_='font-meta').text.strip() if item.find('span', class_='font-meta') else ""
            })
        return jsonify({"success": True, "results": results})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

def fix_poster(url):
    if not url: return ""
    # Remove thumbnail suffixes like -175x238, -110x150, etc.
    return re.sub(r'-\d+x\d+(\.\w+)$', r'\1', url)

@app.route('/api/manga/latest', methods=['GET'])
def latest_manga():
    url = "https://www.mangaread.org/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        items = soup.find_all('div', class_='page-item-detail')
        for item in items:
            title_tag = item.find('h3', class_='h5').find('a')
            img_tag = item.find('img')
            chapter_tag = item.find('span', class_='chapter')
            time_tag = item.find('span', class_='post-on')
            
            poster_url = img_tag['data-src'] if img_tag and 'data-src' in img_tag.attrs else (img_tag['src'] if img_tag else "")
            
            results.append({
                "title": title_tag.text.strip(),
                "slug": title_tag['href'].strip('/').split('/')[-1],
                "poster": fix_poster(poster_url),
                "latest_chapter": chapter_tag.text.strip() if chapter_tag else "Ch. 1",
                "time": time_tag.text.strip() if time_tag else ""
            })
        return jsonify({"success": True, "results": results})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/trending', methods=['GET'])
def trending_manga():
    url = "https://www.mangaread.org/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        items = soup.find_all('div', class_='popular-item-wrap')
        for item in items:
            title_tag = item.find('h5').find('a')
            img_tag = item.find('img')
            poster_url = img_tag['data-src'] if img_tag and 'data-src' in img_tag.attrs else (img_tag['src'] if img_tag else "")
            
            results.append({
                "title": title_tag.text.strip(),
                "slug": title_tag['href'].strip('/').split('/')[-1],
                "poster": fix_poster(poster_url),
            })
        return jsonify({"success": True, "results": results})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/manga/genres', methods=['GET'])
def get_genres():
    # Fixed list of genres from mangaread.org
    genres = ["Action", "Adventure", "Comedy", "Drama", "Ecchi", "Fantasy", "Gender Bender", "Harem", "Historical", "Horror", "Isekai", "Josei", "Martial Arts", "Mature", "Mecha", "Mystery", "Psychological", "Romance", "School Life", "Sci-fi", "Seinen", "Shoujo", "Shoujo Ai", "Shounen", "Shounen Ai", "Slice of Life", "Smut", "Sports", "Supernatural", "Tragedy", "Webtoon"]
    return jsonify({"success": True, "genres": genres})

# Export for Vercel
app = app
