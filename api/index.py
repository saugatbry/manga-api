from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
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
        
        # Combined selector for homepage and search results
        items = soup.select('div.page-item-detail, div.c-tabs-item__content')
        if not items: items = soup.select('div.manga-item')

        for item in items:
            title_link = item.select_one('.post-title a, h3 a, h4 a, h5 a')
            if not title_link: continue
            
            img_tag = item.find('img')
            chapter_link = item.select_one('.chapter a, .list-chapter a, .latest-chap a')
            time_tag = item.select_one('.post-on, .post-date, .chapter-release-date')
            
            # Robust type detection
            m_type = "Manga"
            item_html = str(item).lower()
            if 'manhwa' in item_html: m_type = "Manhwa"
            elif 'manhua' in item_html: m_type = "Manhua"
            else:
                type_badge = item.select_one('.mg-type, .manga-type')
                if type_badge: m_type = type_badge.text.strip()

            poster_url = ""
            if img_tag:
                poster_url = img_tag.get('data-src') or img_tag.get('src') or ""
                if ' ' in poster_url: poster_url = poster_url.split(' ')[0]

            results.append({
                "title": title_link.text.strip(),
                "slug": title_link['href'].strip('/').split('/')[-1],
                "poster": fix_poster(poster_url),
                "latest_chapter": chapter_link.text.strip() if chapter_link else "New",
                "time": time_tag.text.strip() if time_tag else "New",
                "type": m_type
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
    return latest_manga()

@app.route('/api/manga/suggestions', methods=['GET'])
def search_suggestions():
    query = request.args.get('q')
    if not query or len(query) < 2: return jsonify({"success": True, "results": []})
    url = f"https://www.mangaread.org/?s={query}&post_type=wp-manga"
    try:
        response = session.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        items = soup.select('div.c-tabs-item__content, div.page-item-detail')[:5]
        for item in items:
            title_tag = item.select_one('.post-title a, h3 a, h4 a, h5 a')
            if not title_tag: continue
            img_tag = item.find('img')
            results.append({
                "title": title_tag.text.strip(),
                "slug": title_tag['href'].strip('/').split('/')[-1],
                "poster": fix_poster(img_tag.get('src') or img_tag.get('data-src') if img_tag else ""),
            })
        return jsonify({"success": True, "results": results})
    except: return jsonify({"success": False, "results": []})

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
                
                # Extract time tag
                time_tag = item.select_one('.chapter-release-date, .post-on, i')
                time_text = time_tag.text.strip() if time_tag else "New"
                
                chapters.append({
                    "number": num, 
                    "url": a['href'],
                    "time": time_text
                })
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

@app.route('/api/manga/info', methods=['GET'])
def manga_info():
    name = request.args.get('name')
    if not name: return jsonify({"error": "Manga name is required"}), 400
    url = f"https://www.mangaread.org/manga/{name}/"
    try:
        response = session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        info = {
            "title": soup.select_one('.post-title h1').text.strip() if soup.select_one('.post-title h1') else name.replace('-', ' ').title(),
            "description": soup.select_one('.description-summary .summary__content').text.strip() if soup.select_one('.description-summary .summary__content') else "No description available.",
            "poster": fix_poster(soup.select_one('.summary_image img').get('data-src') or soup.select_one('.summary_image img').get('src') if soup.select_one('.summary_image img') else ""),
            "rating": soup.select_one('#averagerate').text.strip() if soup.select_one('#averagerate') else "4.5",
            "status": "Ongoing",
            "alternative": "N/A",
            "author": "N/A",
            "artist": "N/A",
            "genres": [],
            "type": "Manga",
            "release": "N/A"
        }

        # Detailed metadata extraction
        meta_items = soup.select('.post-content_item')
        for item in meta_items:
            heading = item.select_one('.summary-heading').text.strip().lower()
            content = item.select_one('.summary-content')
            if not content: continue
            
            if 'alt' in heading: info['alternative'] = content.text.strip()
            elif 'author' in heading: info['author'] = content.text.strip()
            elif 'artist' in heading: info['artist'] = content.text.strip()
            elif 'genre' in heading: info['genres'] = [a.text.strip() for a in content.find_all('a')]
            elif 'type' in heading: info['type'] = content.text.strip()
            elif 'status' in heading: info['status'] = content.text.strip()
            elif 'release' in heading: info['release'] = content.text.strip()

        return jsonify({"success": True, "info": info})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

app = app
