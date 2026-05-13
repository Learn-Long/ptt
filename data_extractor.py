import json
import os
import re
import sys
import unicodedata
from date_filter import get_valid_json_files

ARTICLE_JSON_DIR = os.path.join("output", "word")
OUTPUT_JSON_FILE = "user_ip_url_records.json"

def extract_ip(timestamp_str):
    """Extracts the IP address part from the timestamp string."""
    if not timestamp_str or not isinstance(timestamp_str, str):
        return None
    parts = timestamp_str.strip().split()
    if parts:
        ip_candidate = parts[0]
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_candidate):
            try:
                if all(0 <= int(p) <= 255 for p in ip_candidate.split('.')):
                    return ip_candidate
            except ValueError:
                pass
    return None

def main():
    """Extracts (user, ip, url) tuples from article JSONs and saves to a single JSON file."""
    if not os.path.exists(ARTICLE_JSON_DIR):
        print(f"Error: Article JSON directory not found: {ARTICLE_JSON_DIR}", file=sys.stderr)
        return

    json_files = get_valid_json_files(ARTICLE_JSON_DIR)

    if not json_files:
        print(f"No JSON files found in {ARTICLE_JSON_DIR}", file=sys.stderr)
        return

    print(f"Found {len(json_files)} JSON files to process in {ARTICLE_JSON_DIR}.")

    all_records = []
    processed_files = 0
    error_files = 0
    total_pushes_examined = 0
    records_extracted = 0

    for filepath in json_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {filename}. Skipping.", file=sys.stderr)
            error_files += 1
            continue
        except IOError as e:
            print(f"Error reading file {filename}: {e}. Skipping.", file=sys.stderr)
            error_files += 1
            continue
        except Exception as e:
             print(f"Unexpected error processing file {filename}: {e}. Skipping.", file=sys.stderr)
             error_files += 1
             continue

        pushes = data.get('pushes')
        article_url = data.get('url') # Get the URL of the article itself

        if not isinstance(pushes, list) or not article_url:
            processed_files += 1
            continue # Skip if no pushes or article URL is missing

        for push in pushes:
            total_pushes_examined += 1
            user = push.get('user')
            timestamp_str = push.get('timestamp')

            if not user or not timestamp_str:
                continue

            ip = extract_ip(timestamp_str)
            if not ip:
                continue

            # Add the record
            all_records.append({
                "user": user,
                "ip": ip,
                "url": article_url
            })
            records_extracted += 1

        processed_files += 1

    print(f"\nFinished processing {processed_files} files ({error_files} errors).")
    print(f"Total pushes examined: {total_pushes_examined}", file=sys.stderr)
    print(f"Extracted {records_extracted} (user, ip, url) records.", file=sys.stderr)

    # Print all records to stdout as a single JSON array
    try:
        json.dump(all_records, sys.stdout, ensure_ascii=False, indent=2)
        print()  # Add a newline at the end
    except Exception as e:
        print(f"Error: Could not print records to stdout: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
