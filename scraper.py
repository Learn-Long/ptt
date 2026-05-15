import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import time
import concurrent.futures
from datetime import datetime, timedelta
import re
import argparse

BASE_URL = "https://www.ptt.cc/bbs/HatePolitics/index{}.html"
BOARD_URL = "https://www.ptt.cc/bbs/HatePolitics/index.html"
OUTPUT_DIR = "output"
MAX_THREADS = 10
HEADERS = {'Cookie': 'over18=1'}

def get_latest_index():
    board_url = BOARD_URL
    try:
        response = requests.get(board_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        btn_group = soup.find('div', class_='btn-group-paging')
        if btn_group:
            prev_link = btn_group.find('a', string=re.compile(r'上頁|‹'))
            if prev_link and prev_link.get('href'):
                match = re.search(r'index(\d+)\.html', prev_link['href'])
                if match:
                    return int(match.group(1)) + 1
        return None
    except requests.exceptions.RequestException:
        return None

def get_page_last_date(index):
    url = BASE_URL.format(index)
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        if "404 - Not Found" in response.text:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        entries = soup.find_all('div', class_='r-ent')
        if not entries:
            return None
        now = datetime.now()
        for entry in reversed(entries):
            meta_tag = entry.find('div', class_='meta')
            if meta_tag:
                date_tag = meta_tag.find('div', class_='date')
                if date_tag:
                    date_str = date_tag.text.strip()
                    try:
                        month, day = date_str.split('/')
                        month, day = int(month), int(day)
                        year = now.year
                        parsed = datetime(year, month, day)
                        if parsed > now + timedelta(days=1):
                            parsed = datetime(year - 1, month, day)
                        return parsed
                    except ValueError:
                        continue
        return None
    except requests.exceptions.RequestException:
        return None

def estimate_seven_day_index():
    print("正在估算近七天文章的建議起始索引...")
    max_index = get_latest_index()
    if max_index is None:
        print("無法取得最新索引，跳過估算。")
        return None

    seven_days_ago = (datetime.now() - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    low, high = 1, max_index
    attempts = 0
    max_attempts = 20

    while low <= high and attempts < max_attempts:
        mid = (low + high) // 2
        page_date = get_page_last_date(mid)
        attempts += 1
        time.sleep(0.3)

        if page_date is None:
            high = mid - 1
            continue

        if page_date < seven_days_ago:
            low = mid + 1
        else:
            high = mid - 1

    suggested = low if low <= max_index else max_index
    print(f"估算完成（共 {attempts} 次查詢）")
    return suggested

LAST_INDEX_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_index.txt")

def save_last_index(index):
    try:
        with open(LAST_INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write(str(index))
    except IOError as e:
        print(f"無法寫入 last_index.txt: {e}")

def read_last_index():
    try:
        with open(LAST_INDEX_FILE, 'r', encoding='utf-8') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None

def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--start-index', type=int, default=None)
    return parser.parse_known_args()[0]

def get_start_index(args=None):
    if args and args.start_index is not None:
        print(f"使用命令列指定起始索引: {args.start_index}")
        save_last_index(args.start_index)
        return args.start_index

    suggested = estimate_seven_day_index()
    interactive = sys.stdin.isatty()

    if interactive:
        while True:
            if suggested is not None:
                prompt = f"近七天文章建議起始索引: {suggested}\n請輸入起始索引（直接按 Enter 採用建議值）: "
            else:
                prompt = "請輸入起始索引: "
            user_input = input(prompt).strip()
            if user_input == "":
                if suggested is not None:
                    print(f"採用建議值: {suggested}")
                    save_last_index(suggested)
                    return suggested
                else:
                    print("無建議值可用，請輸入一個數字。")
                    continue
            try:
                start_index = int(user_input)
                if start_index > 0:
                    save_last_index(start_index)
                    return start_index
                else:
                    print("起始索引必須是正整數。")
            except ValueError:
                print("無效的輸入。請輸入一個整數。")

    # Non-interactive (cronjob) mode
    if suggested is not None:
        print(f"自動採用建議值: {suggested}")
        save_last_index(suggested)
        return suggested

    persisted = read_last_index()
    if persisted is not None:
        print(f"建議值不可用，使用上次記錄的索引: {persisted}")
        return persisted

    print("無歷史記錄，嘗試重新取得最新索引...")
    time.sleep(2)
    latest = get_latest_index()
    if latest is not None:
        fallback = max(1, latest - 200)
        print(f"使用回退值: {fallback} (最新索引 {latest} - 200)")
        save_last_index(fallback)
        return fallback

    print("錯誤：無法自動決定起始索引，且無歷史記錄可用。請手動執行。")
    sys.exit(1)

START_INDEX = get_start_index(parse_args())

def fetch_page(url):
    """Fetches the HTML content of a given URL."""
    headers = {'Cookie': 'over18=1'} # PTT requires an 'over18' cookie
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        # Check for "404 - Not Found" specifically in the content as PTT might return 200 OK with a 404 page
        if "404 - Not Found" in response.text:
             print(f"Page not found (404 content): {url}")
             return None, 404
        return response.text, response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None, None # Indicate error without a specific status code

def parse_page(html_content):
    """Parses the HTML and extracts relevant article data."""
    soup = BeautifulSoup(html_content, 'html.parser')
    articles = []
    # Find all article entries (typically within 'div' elements with class 'r-ent')
    for entry in soup.find_all('div', class_='r-ent'):
        title_tag = entry.find('div', class_='title')
        meta_tag = entry.find('div', class_='meta')

        if title_tag and title_tag.a: # Ensure there's a link (not deleted posts)
            title = title_tag.a.text.strip()
            link = "https://www.ptt.cc" + title_tag.a['href']
            author = meta_tag.find('div', class_='author').text.strip() if meta_tag else 'N/A'
            date = meta_tag.find('div', class_='date').text.strip() if meta_tag else 'N/A'
            # Add more fields if needed, e.g., push count
            push_count_tag = entry.find('div', class_='nrec')
            push_count = push_count_tag.text.strip() if push_count_tag else '0'

            articles.append({
                'title': title,
                'author': author,
                'date': date,
                'push_count': push_count,
                'link': link
            })
    return articles

def save_to_json(data, index):
    """Saves the extracted data to a JSON file."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    filepath = os.path.join(OUTPUT_DIR, f"{index}.json")
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved data to {filepath}")
    except IOError as e:
        print(f"Error saving file {filepath}: {e}")

def process_index(current_index):
    """Processes a single index page."""
    json_filepath = os.path.join(OUTPUT_DIR, f"{current_index}.json")
    if os.path.exists(json_filepath):
        print(f"File {json_filepath} already exists. Skipping index {current_index}.")
        return None # Indicate skip

    url = BASE_URL.format(current_index)
    print(f"Fetching page: {url}")
    html_content, status_code = fetch_page(url)

    if status_code == 404 or html_content is None and status_code is None: # Stop if 404 or fetch error
        if status_code == 404:
            print("Reached 404 page. Stopping.")
        else: # Fetch error
            print("Stopping due to fetch error.")
        return False # Indicate stop

    if html_content:
        articles_data = parse_page(html_content)
        if articles_data:
            save_to_json(articles_data, current_index)
        else:
            print(f"No articles found on page {current_index}. It might be empty or structured differently.")
    else:
        # Handle cases where fetch_page returned None but not 404 (e.g., other errors)
        print(f"Skipping index {current_index} due to fetch issue (not 404).")

    return True # Indicate success

def main():
    """Main function to control the scraping process with multithreading."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        current_index = START_INDEX
        futures = []
        stop_requested = False

        while not stop_requested:
            # Submit tasks to the thread pool
            for i in range(MAX_THREADS * 2): # Submit a batch of tasks
                if stop_requested:
                    break
                future = executor.submit(process_index, current_index)
                futures.append(future)
                current_index += 1

            # Wait for the tasks to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result is False: # Explicit stop signal
                        stop_requested = True
                        break
                except Exception as e:
                    print(f"Exception in worker thread: {e}")
                    stop_requested = True
                    break
            futures = [] # Reset futures for the next batch

            # Add a small delay to avoid overwhelming the server
            time.sleep(0.2)

if __name__ == "__main__":
    main()
