import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re
import unicodedata
import sys
from date_filter import get_valid_index_files

INDEX_JSON_DIR = "output"
ARTICLE_JSON_DIR = os.path.join(INDEX_JSON_DIR, "word")
PROCESSED_URLS_FILE = "processed_urls.txt"
HEADERS = {'Cookie': 'over18=1'} # PTT requires an 'over18' cookie

# --- URL Tracking Functions ---
def load_processed_urls():
    """Loads processed URLs from the tracking file into a set."""
    processed = set()
    if os.path.exists(PROCESSED_URLS_FILE):
        try:
            with open(PROCESSED_URLS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    processed.add(line.strip())
        except IOError as e:
            print(f"Warning: Could not read {PROCESSED_URLS_FILE}: {e}", file=sys.stderr)
    return processed

def add_processed_url(url):
    """Appends a successfully processed URL to the tracking file."""
    try:
        with open(PROCESSED_URLS_FILE, 'a', encoding='utf-8') as f:
            f.write(url + '\n')
    except IOError as e:
        print(f"Warning: Could not write to {PROCESSED_URLS_FILE}: {e}", file=sys.stderr)

# --- Filename Sanitization ---
def sanitize_filename(filename):
    """Removes invalid characters for Windows filenames while preserving CJK characters and limits length."""
    # Remove characters that are invalid in Windows filenames: \ / * ? : " < > |
    # We keep spaces for now, but they can sometimes cause issues in CLI.
    # Consider replacing them with underscores if needed: filename = filename.replace(" ", "_")
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Remove control characters (ASCII 0-31) except for tab (\t) if needed, but usually covered by the above.
    filename = re.sub(r'[\x00-\x1f]', '', filename)
    # Limit length to avoid filesystem issues (e.g., 150 chars allows for more CJK)
    # Windows max path length is ~260, but individual component length matters too.
    max_len = 150
    if len(filename) > max_len:
        # Simple truncation, might cut mid-character for some encodings if not careful,
        # but should be generally okay for UTF-8 handled by Python strings.
        filename = filename[:max_len]
    # Remove trailing dots or spaces which are problematic in Windows
    filename = filename.rstrip('. ')
    # Ensure filename is not empty after sanitization
    if not filename:
        filename = "invalid_title"
    return filename

def fetch_article_page(url):
    """Fetches the HTML content of a given article URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        # Check for "404 - Not Found" specifically in the content
        if "404 Not Found" in response.text or "找不到網頁" in response.text:
             print(f"Article page not found (404 content): {url}")
             return None
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching article {url}: {e}")
        return None

def parse_article_page(html_content, url):
    """Parses the article HTML and extracts relevant data."""
    if not html_content:
        return None
    soup = BeautifulSoup(html_content, 'html.parser')
    main_content = soup.find(id="main-content")
    if not main_content:
        print(f"Could not find main content for {url}")
        return None

    article_data = {}

    # Extract metadata (Author, Title, Time)
    meta_lines = main_content.find_all('div', class_='article-metaline')
    meta_map = {}
    for line in meta_lines:
        tag = line.find('span', class_='article-meta-tag')
        value = line.find('span', class_='article-meta-value')
        if tag and value:
            meta_map[tag.text.strip()] = value.text.strip()

    article_data['author'] = meta_map.get('作者', 'N/A')
    article_data['title'] = meta_map.get('標題', 'N/A')
    article_data['timestamp'] = meta_map.get('時間', 'N/A')
    article_data['url'] = url

    # Remove metadata lines and pushes from main content to get the body
    for meta in meta_lines:
        meta.extract()
    pushes = main_content.find_all('div', class_='push')
    for push in pushes:
        push.extract()

    # Remove potential IP source line if present
    ip_source_span = main_content.find('span', class_='f2', string=re.compile(r'※ 發信站:'))
    if ip_source_span:
        ip_source_span.extract()
    edit_span = main_content.find('span', class_='f2', string=re.compile(r'※ 文章網址:'))
    if edit_span:
        edit_span.extract()
    edit_span = main_content.find('span', class_='f2', string=re.compile(r'※ 編輯:'))
    if edit_span:
        # Remove the edit line and potentially the timestamp after it
        next_sibling = edit_span.next_sibling
        edit_span.extract()
        if next_sibling and isinstance(next_sibling, str) and next_sibling.strip():
             # Simple check if the next text node looks like a timestamp part
             if re.match(r'\s*\(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\)\s+\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}\s*$', next_sibling):
                 # This is heuristic, might need refinement
                 pass # Keep it simple for now, just remove the ※ 編輯: part

    article_data['content'] = main_content.text.strip()


    # Extract pushes (comments)
    article_data['pushes'] = []
    for push in pushes:
        push_tag = push.find('span', class_=re.compile(r'push-tag'))
        push_userid = push.find('span', class_='push-userid')
        push_content = push.find('span', class_='push-content')
        push_ipdatetime = push.find('span', class_='push-ipdatetime')

        if push_tag and push_userid and push_content and push_ipdatetime:
            article_data['pushes'].append({
                'type': push_tag.text.strip(),
                'user': push_userid.text.strip(),
                'comment': push_content.text.strip().lstrip(': '),
                'timestamp': push_ipdatetime.text.strip()
            })

    return article_data


def save_article_to_json(data, filename_base, article_url):
    """Saves the extracted article data to a JSON file, handling duplicates and tracking URL."""
    if not data or not filename_base:
        print(f"Skipping save for URL {article_url} due to missing data or filename base.")
        return

    if not os.path.exists(ARTICLE_JSON_DIR):
        try:
            os.makedirs(ARTICLE_JSON_DIR)
        except OSError as e:
            print(f"Error creating directory {ARTICLE_JSON_DIR}: {e}")
        return False # Indicate save failure

    safe_filename_base = sanitize_filename(filename_base)
    filename_suffix = ".json"
    filepath_base = os.path.join(ARTICLE_JSON_DIR, safe_filename_base)
    filepath = filepath_base + filename_suffix

    # Handle duplicate filenames by adding sequence numbers
    counter = 1
    while os.path.exists(filepath):
        print(f"Filename collision: {filepath} exists. Trying next sequence.")
        filepath = f"{filepath_base}_{counter}{filename_suffix}"
        counter += 1
        if counter > 100: # Safety break to prevent infinite loops
             print(f"Error: Could not find a unique filename for base '{safe_filename_base}' after 100 attempts. Skipping save for {article_url}.", file=sys.stderr)
             return False # Indicate save failure


    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved article data to {filepath}")
        # Add URL to processed list only after successful save
        add_processed_url(article_url)
        return True # Indicate save success
    except IOError as e:
        print(f"Error saving article file {filepath}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred while saving {filepath}: {e}", file=sys.stderr)
    return False # Indicate save failure


def main():
    """Main function to process index JSONs and scrape articles."""
    # Load already processed URLs
    processed_urls = load_processed_urls()
    print(f"Loaded {len(processed_urls)} previously processed URLs.")

    if not os.path.exists(INDEX_JSON_DIR):
        print(f"Index JSON directory not found: {INDEX_JSON_DIR}", file=sys.stderr)
        return

    # Ensure output directory exists
    if not os.path.exists(ARTICLE_JSON_DIR):
        try:
            os.makedirs(ARTICLE_JSON_DIR)
            print(f"Created directory: {ARTICLE_JSON_DIR}")
        except OSError as e:
            print(f"Error creating directory {ARTICLE_JSON_DIR}: {e}", file=sys.stderr)
            return

    index_files = sorted(get_valid_index_files(INDEX_JSON_DIR))

    if not index_files:
        print(f"No JSON files found in {INDEX_JSON_DIR}", file=sys.stderr)
        return

    total_processed_count = 0
    total_skipped_url_count = 0
    total_error_count = 0
    newly_saved_count = 0

    for index_file in index_files:
        filepath = index_file
        index_basename = os.path.basename(filepath)
        print(f"\nProcessing index file: {filepath}")
        articles = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                articles = json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {filepath}. Skipping file.", file=sys.stderr)
            total_error_count += 1 # Count file error
            continue
        except IOError as e:
            print(f"Error reading file {filepath}: {e}. Skipping file.", file=sys.stderr)
            total_error_count += 1 # Count file error
            continue

        print(f"Found {len(articles)} articles in {index_basename}.")
        file_processed_count = 0
        file_skipped_url_count = 0
        file_error_count = 0
        file_newly_saved_count = 0

        for i, article_summary in enumerate(articles):
            link = article_summary.get('link')
            title = article_summary.get('title')

            if not link or not title:
                print(f"Skipping entry #{i+1} in {index_basename} due to missing link or title: {article_summary}")
                file_error_count += 1
                continue

            # --- Check if URL has already been processed ---
            if link in processed_urls:
                # print(f"URL already processed: {link}. Skipping.")
                file_skipped_url_count += 1
                continue
            # --- End check ---

            print(f"Fetching article #{i+1}: {title} ({link})")
            html_content = fetch_article_page(link)

            if html_content:
                article_data = parse_article_page(html_content, link)
                if article_data:
                    # Use the title from the article page itself if available, otherwise fallback
                    filename_base_to_save = article_data.get('title', title)
                    if not filename_base_to_save: # Handle cases where title might be empty after parsing
                         print(f"Warning: Article title is empty for {link}. Using default filename base.")
                         filename_base_to_save = "untitled_article"

                    if save_article_to_json(article_data, filename_base_to_save, link):
                        file_newly_saved_count += 1
                        processed_urls.add(link) # Update in-memory set immediately
                    else:
                        # Save failed (error message printed in save_article_to_json)
                        file_error_count += 1
                else:
                    print(f"Failed to parse article content for: {link}")
                    file_error_count += 1
            else:
                # Fetch failed or returned None (e.g., 404)
                print(f"Failed to fetch article content for: {link}")
                file_error_count += 1

            file_processed_count += 1
            # Add a small delay between article fetches
            time.sleep(0.2) # Slightly reduced delay

        print(f"Finished processing {index_basename}:")
        print(f"  - Newly Saved: {file_newly_saved_count}")
        print(f"  - Skipped (URL already processed): {file_skipped_url_count}")
        print(f"  - Errors (fetch/parse/save/format): {file_error_count}")

        total_processed_count += file_processed_count
        total_skipped_url_count += file_skipped_url_count
        total_error_count += file_error_count
        newly_saved_count += file_newly_saved_count

    print(f"\n--- Overall Processing Complete ---")
    print(f"Total articles considered across all files: {total_processed_count + total_skipped_url_count}")
    print(f"Successfully saved (new): {newly_saved_count} articles")
    print(f"Skipped (URL already processed): {total_skipped_url_count} articles")
    print(f"Total Errors (fetch/parse/save/format/file): {total_error_count}")
    print(f"Total processed URLs in tracking file: {len(processed_urls)}")

    deleted_count = 0
    if os.path.exists(ARTICLE_JSON_DIR):
        for fname in os.listdir(ARTICLE_JSON_DIR):
            if '[公告]' in fname and os.path.isfile(os.path.join(ARTICLE_JSON_DIR, fname)):
                try:
                    os.remove(os.path.join(ARTICLE_JSON_DIR, fname))
                    deleted_count += 1
                except OSError as e:
                    print(f"刪除 {fname} 失敗: {e}")
    print(f"已刪除 {deleted_count} 個含有 '[公告]' 的檔案。")


if __name__ == "__main__":
    main()
