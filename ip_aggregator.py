import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from date_filter import get_valid_json_files

ARTICLE_JSON_DIR = os.path.join("output", "word")
ID_DIR = "ID"

def sanitize_filename_for_user(username):
    """Removes invalid characters for Windows filenames specifically for usernames."""
    # Basic check for empty username
    if not username:
        return "invalid_user"
    # Normalize unicode characters - important for consistency
    username = unicodedata.normalize('NFKD', username)
    # Remove characters invalid in Windows filenames: \ / * ? : " < > |
    username = re.sub(r'[\\/*?:"<>|]', "", username)
    # Remove control characters (ASCII 0-31)
    username = re.sub(r'[\x00-\x1f]', '', username)
    # Replace spaces with underscores (optional, but safer for filenames)
    username = username.replace(" ", "_")
    # Limit length
    max_len = 100
    if len(username) > max_len:
        username = username[:max_len]
    # Remove trailing dots or spaces
    username = username.rstrip('. ')
    # Ensure filename is not empty after sanitization
    if not username:
        return "invalid_user"
    return username

def extract_ip(timestamp_str):
    """Extracts the IP address part from the timestamp string."""
    if not timestamp_str or not isinstance(timestamp_str, str):
        return None
    parts = timestamp_str.strip().split()
    if parts:
        # Basic validation: check if it looks like an IPv4 address
        ip_candidate = parts[0]
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_candidate):
            # Further check if each part is <= 255 (optional but good)
            try:
                if all(0 <= int(p) <= 255 for p in ip_candidate.split('.')):
                    return ip_candidate
            except ValueError:
                pass # Not valid integers
    return None # Return None if no valid IP found

def load_existing_ips(filepath):
    """Loads existing IPs from a user's file into a set."""
    ips = set()
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    ip = line.strip()
                    if ip: # Avoid adding empty lines
                        ips.add(ip)
        except IOError as e:
            print(f"Warning: Could not read IP file {filepath}: {e}", file=sys.stderr)
    return ips

def append_ip_to_file(filepath, ip):
    """Appends a new IP to the user's file."""
    try:
        # Ensure the directory exists before writing
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(ip + '\n')
        return True
    except IOError as e:
        print(f"Error: Could not write IP to file {filepath}: {e}", file=sys.stderr)
        return False

def main():
    """Main function to process article JSONs and aggregate IPs by user."""
    if not os.path.exists(ARTICLE_JSON_DIR):
        print(f"Error: Article JSON directory not found: {ARTICLE_JSON_DIR}", file=sys.stderr)
        return

    # Ensure the output ID directory exists
    if not os.path.exists(ID_DIR):
        try:
            os.makedirs(ID_DIR)
            print(f"Created directory: {ID_DIR}")
        except OSError as e:
            print(f"Error: Could not create directory {ID_DIR}: {e}", file=sys.stderr)
            return

    json_files = get_valid_json_files(ARTICLE_JSON_DIR)

    if not json_files:
        print(f"No JSON files found in {ARTICLE_JSON_DIR}", file=sys.stderr)
        return

    print(f"Found {len(json_files)} JSON files to process in {ARTICLE_JSON_DIR}.")

    # Use a dictionary to keep track of IPs already seen *for the current run* per user,
    # to avoid reading the file repeatedly for the same user within the loop.
    # Key: user_filepath, Value: set of IPs in that file (loaded once per user)
    user_ip_cache = {}
    processed_files = 0
    total_pushes_processed = 0
    new_ips_added_count = 0
    error_files = 0

    for filepath in json_files:
        filename = os.path.basename(filepath)
        # print(f"Processing file: {filename}") # Can be verbose
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
        if not isinstance(pushes, list):
            # print(f"No 'pushes' list found or invalid format in {filename}. Skipping pushes.")
            processed_files += 1
            continue # Move to the next file if no pushes

        file_new_ips = 0
        for push in pushes:
            total_pushes_processed += 1
            user = push.get('user')
            timestamp_str = push.get('timestamp')

            if not user or not timestamp_str:
                # print(f"Skipping push due to missing user or timestamp in {filename}: {push}")
                continue

            ip = extract_ip(timestamp_str)
            if not ip:
                # print(f"Could not extract valid IP from timestamp '{timestamp_str}' for user '{user}' in {filename}")
                continue

            sanitized_user = sanitize_filename_for_user(user)
            user_filepath = os.path.join(ID_DIR, f"{sanitized_user}.txt")

            # Check cache first, load if not present
            if user_filepath not in user_ip_cache:
                user_ip_cache[user_filepath] = load_existing_ips(user_filepath)
                # print(f"Loaded {len(user_ip_cache[user_filepath])} existing IPs for user '{user}'")

            # Check if IP is already known for this user (from file or current run)
            if ip not in user_ip_cache[user_filepath]:
                if append_ip_to_file(user_filepath, ip):
                    user_ip_cache[user_filepath].add(ip) # Update cache
                    new_ips_added_count += 1
                    file_new_ips += 1
                # else: Error already printed by append_ip_to_file

        # if file_new_ips > 0:
        #     print(f"Added {file_new_ips} new IPs from file {filename}.")
        processed_files += 1


    print(f"\n--- IP Aggregation Complete ---")
    print(f"Processed JSON files: {processed_files}")
    print(f"Files skipped due to read/decode errors: {error_files}")
    print(f"Total pushes examined: {total_pushes_processed}")
    print(f"Total new unique User-IP entries added: {new_ips_added_count}")
    print(f"IP data saved in directory: {ID_DIR}")
    # Save summary to file
    summary_filename = "ip_aggregator_summary.txt"
    try:
        with open(summary_filename, 'w', encoding='utf-8') as summary_file:
            summary_file.write(f"Processed JSON files: {processed_files}\n")
            summary_file.write(f"Files skipped due to read/decode errors: {error_files}\n")
            summary_file.write(f"Total pushes examined: {total_pushes_processed}\n")
            summary_file.write(f"Total new unique User-IP entries added: {new_ips_added_count}\n")
        print(f"Summary saved to {summary_filename}")
    except IOError as e:
        print(f"Error: Could not write summary to {summary_filename}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Unexpected error writing summary to {summary_filename}: {e}", file=sys.stderr)
    processed_files = 0
    error_files = 0
    total_pushes_processed = 0
    new_ips_added_count = 0

if __name__ == "__main__":
    main()
