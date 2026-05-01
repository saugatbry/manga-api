# Manga Scraper API

This is a Flask-based API wrapper around the Manga Scrape script.

## Installation
1. Ensure you have Python installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Microsoft Edge must be installed on the system (for the scraper).

## Running the API
```bash
python api.py
```
The API will start at `http://localhost:5000`.

## API Endpoints

### 1. Get Chapter List
**Endpoint:** `/api/manga/chapters`  
**Method:** `GET`  
**Parameters:**
- `name`: The slug of the manga (e.g., `one-piece`)
- `start`: (Optional) Start chapter number (default: 1)
- `end`: (Optional) End chapter number (default: 1000)

**Example:**
`http://localhost:5000/api/manga/chapters?name=one-piece`

### 2. Get Chapter Images (Read Online)
**Endpoint:** `/api/manga/images`  
**Method:** `GET`  
**Parameters:**
- `url`: The full URL of the chapter from the previous endpoint.

**Example:**
`http://localhost:5000/api/manga/images?url=https://www.mangaread.org/manga/one-piece/chapter-1/`

## Note
This scraper currently targets `mangaread.org`. Ensure the `name` parameter matches the slug used on that website.
