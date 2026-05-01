import requests
import os
import time
import re
import img2pdf
import shutil
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# Returns a list of links to the chapters
def getChapters(manga_name, Ch_Start, Ch_End):
    # Open the manga page
    url = f'https://www.mangaread.org/manga/{manga_name}/'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching manga page: {e}")
        return []

    # Get the page source and parse it with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all chapters in the loaded page
    chapters = soup.find_all('li', class_='wp-manga-chapter')
    chapter_links = []

    # Loop through the chapters and print the title and link
    for chapter in chapters:
        a_tag = chapter.find('a')
        if not a_tag: continue
        
        ch_link = a_tag['href']
        match = re.findall(r'\d+', ch_link)
        nums = int(match[0]) if match else 0

        if nums >= Ch_Start and nums <= Ch_End:
            chapter_links.append(ch_link)

    chapter_links.reverse()
    return chapter_links

# Returns Urls for Images of a chapter
def scrape_img(ch_link):
    # Get Entire HTML of the Chapter
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(ch_link, headers=headers, timeout=15)
        html = response.text
        soup = BeautifulSoup(html, 'lxml')

        images = soup.find_all('img', class_='wp-manga-chapter-img')
        img_urls = [img['src'].strip() for img in images if 'src' in img.attrs]
        
        match = re.findall(r'\d+', ch_link)
        ch_num = match[0] if match else "Unknown"
        print(f'Starting Chapter {ch_num}')
        return img_urls
    except Exception as e:
        print(f"Error scraping images: {e}")
        return []

# Function to download and save images
def download_images(image_urls, manga_name, ch_link, base_dir):
    # Determine directory
    try:
        ch_slug = ch_link.split('chapter-')[1].split('/')[0]
        chFolder = f'Chapter-{ch_slug}'
    except:
        chFolder = 'Chapter-Unknown'
        
    manga_directory = os.path.join(base_dir, manga_name)
    directory_path = os.path.join(manga_directory, chFolder)

    # Create Determined Directory if not exist
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True) 

    # Save all the Url's in the list to the manga_name
    for i, url in enumerate(image_urls):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Save path & file name
                image_path = os.path.join(directory_path, f'{manga_name}_{chFolder}_pg{i+1}.png')
                if not os.path.exists(image_path):
                    # Save image to the path
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                else: 
                    print(f'Already Exists {url}')
        except Exception as e:
            print(f"Error downloading image {url}: {e}")
            
    print(f"Downloaded {chFolder}")

def convertPDF(mangaDirectory):
    if not os.path.exists(mangaDirectory):
        print(f"Directory {mangaDirectory} does not exist.")
        return

    chaptersList = os.listdir(mangaDirectory)
    
    for chapter in chaptersList:
        chapter_path = os.path.join(mangaDirectory, chapter)

        # Skip if chapter is not a directory
        if not os.path.isdir(chapter_path):
            continue

        if chapter + '.pdf' in chaptersList:
            continue
        
        # Gets List of all the images in the Chapter
        imgsDir = os.path.join(mangaDirectory, chapter)
        imgsList = os.listdir(imgsDir)

        # Ensure imgsList contains only files
        imgsList = [os.path.join(imgsDir, img) for img in imgsList if os.path.isfile(os.path.join(imgsDir, img))]

        if not imgsList:
            continue

        # Sort images by page number
        try:
            imgsList.sort(key=lambda x: int(re.findall(r'\d+', x.split('_pg')[-1])[0]))
        except:
            imgsList.sort()

        # Convert images to PDF
        try:
            with open(os.path.join(mangaDirectory, f'{chapter}.pdf'), 'wb') as f:
                f.write(img2pdf.convert(imgsList))      #type: ignore
            
            # Delete the images and chapter directory
            shutil.rmtree(chapter_path)
            print(f'Converted {chapter} to PDF')
        except Exception as e:
            print(f"Error converting to PDF: {e}")

    print("Executed convertPDF Function")

if __name__ == '__main__':
    start_ch = 1
    end_ch = 5
    manga_name = 'a-returners-magic-should-be-special-manga'
    base_dir = os.path.join(os.getcwd(), 'downloads')

    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)

    # Get Links of all chapters
    links = getChapters(manga_name, start_ch, end_ch)
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        for ch_link in links:
            img_url_list = scrape_img(ch_link)
            if img_url_list:
                executor.submit(download_images, img_url_list, manga_name, ch_link, base_dir)

    print('Scrape Completed')

    manga_path = os.path.join(base_dir, manga_name)
    if os.path.exists(manga_path):
        convertPDF(manga_path)
    print('Conversions Completed')
