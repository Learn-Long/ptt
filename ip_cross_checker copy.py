import json
import os
import sys
import re
from collections import defaultdict

ARTICLE_JSON_DIR = os.path.join("output", "word")

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
    """Cross-references IP addresses across user files to find duplicates and show details."""

    print("Loading article data from JSON files...")
    ip_usage = defaultdict(lambda: defaultdict(list))

    # Load article data from JSON files
    for filename in os.listdir(ARTICLE_JSON_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(ARTICLE_JSON_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    url = data.get('url')
                    pushes = data.get('pushes')

                    if url and pushes:
                        for push in pushes:
                            ip = extract_ip(push.get('timestamp'))
                            user = push.get('user')
                            if ip and user:
                                ip_usage[ip][user].append(url)

            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {filename}: {e}", file=sys.stderr)
            except IOError as e:
                print(f"Error reading file {filename}: {e}", file=sys.stderr)

    # Find IPs shared by multiple users
    shared_ip_details = []
    for ip, user_url_map in ip_usage.items():
        if len(user_url_map) > 1:
            user_details = []
            for user, urls in sorted(user_url_map.items()):
                user_details.append({"user": user, "urls": sorted(urls)})
            shared_ip_details.append({"ip": ip, "details": user_details})

    # Sort results by IP address for consistent output
    shared_ip_details.sort(key=lambda x: x['ip'])

    # --- 实锤逻辑 ---
    # Dictionary to store user pairs and their shared IP counts
    user_pair_ip_counts = defaultdict(lambda: defaultdict(int))
    for ip, user_url_map in ip_usage.items():
        users = list(user_url_map.keys())
        for i in range(len(users)):
            for j in range(i + 1, len(users)):
                user1, user2 = sorted((users[i], users[j]))  # Ensure consistent order
                user_pair_ip_counts[user1][user2] += 1

    # Find user pairs with at least two shared IPs
    suspicious_pairs = []
    for user1, user2_counts in user_pair_ip_counts.items():
        for user2, count in user2_counts.items():
            if count >= 2:
                suspicious_pairs.append((user1, user2))

    # --- 保存 "实锤.txt" ---
    实锤_filename = "实锤.txt"
    print(f"\nSaving suspicious pairs to {实锤_filename}...")
    try:
        with open(实锤_filename, 'w', encoding='utf-8') as outfile:
            if suspicious_pairs:
                outfile.write("--- Suspicious User Pairs (2+ Shared IPs) ---\n")
                for user1, user2 in sorted(suspicious_pairs):  # Sort for consistent output
                    outfile.write(f"{user1} and {user2}\n")
            else:
                outfile.write("--- No Suspicious User Pairs Found ---\n")
        print(f"Suspicious pairs successfully saved to {实锤_filename}")
    except IOError as e:
        print(f"\nError: Could not write results to {实锤_filename}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nUnexpected error writing results to {实锤_filename}: {e}", file=sys.stderr)
    # --- 结束 "实锤" 逻辑 ---
import json
import os
import sys
import re
from collections import defaultdict

ARTICLE_JSON_DIR = os.path.join("output", "word")

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
    """Cross-references IP addresses across user files to find duplicates and show details."""

    print("Loading article data from JSON files...")
    ip_usage = defaultdict(lambda: defaultdict(list))

    # Load article data from JSON files
    for filename in os.listdir(ARTICLE_JSON_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(ARTICLE_JSON_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    url = data.get('url')
                    pushes = data.get('pushes')

                    if url and pushes:
                        for push in pushes:
                            ip = extract_ip(push.get('timestamp'))
                            user = push.get('user')
                            if ip and user:
                                ip_usage[ip][user].append(url)

            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {filename}: {e}", file=sys.stderr)
            except IOError as e:
                print(f"Error reading file {filename}: {e}", file=sys.stderr)

    # Find IPs shared by multiple users
    shared_ip_details = []
    for ip, user_url_map in ip_usage.items():
        if len(user_url_map) > 1:
            user_details = []
            for user, urls in sorted(user_url_map.items()):
                user_details.append({"user": user, "urls": sorted(urls)})
            shared_ip_details.append({"ip": ip, "details": user_details})

    # Sort results by IP address for consistent output
    shared_ip_details.sort(key=lambda x: x['ip'])

    # --- 实锤逻辑 ---
    # Dictionary to store user pairs and their shared IP counts
    user_pair_ip_counts = defaultdict(lambda: defaultdict(int))
    for ip, user_url_map in ip_usage.items():
        users = list(user_url_map.keys())
        for i in range(len(users)):
            for j in range(i + 1, len(users)):
                user1, user2 = sorted((users[i], users[j]))  # Ensure consistent order
                user_pair_ip_counts[user1][user2] += 1

    # Find user pairs with at least two shared IPs
    suspicious_pairs = []
    for user1, user2_counts in user_pair_ip_counts.items():
        for user2, count in user2_counts.items():
            if count >= 2:
                suspicious_pairs.append((user1, user2))

    # --- 保存 "实锤.txt" ---
    实锤_filename = "实锤.txt"
    print(f"\nSaving suspicious pairs to {实锤_filename}...")
    try:
        with open(实锤_filename, 'w', encoding='utf-8') as outfile:
            if suspicious_pairs:
                outfile.write("--- Suspicious User Pairs (2+ Shared IPs) ---\n")
                for user1, user2 in sorted(suspicious_pairs):  # Sort for consistent output
                    # Find shared IPs and URLs for the pair
                    shared_ips_and_urls = defaultdict(lambda: defaultdict(list))
                    for ip, user_url_map in ip_usage.items():
                        if user1 in user_url_map and user2 in user_url_map:
                            shared_ips_and_urls[ip][user1].extend(user_url_map[user1])
                            shared_ips_and_urls[ip][user2].extend(user_url_map[user2])

                    if shared_ips_and_urls:
                        for ip, user_urls in shared_ips_and_urls.items():
                            outfile.write(f"IP: {ip}\n")
                            users = list(user_urls.keys())
                            for user in users:
                                urls = user_urls[user]
                                outfile.write(f"  Shared by Users: {user}\n")
                                for url in urls:
                                    outfile.write(f"    - {url}\n")
                            outfile.write("-" * 30 + "\n")
            else:
                outfile.write("--- No Suspicious User Pairs Found ---\n")
        print(f"Suspicious pairs successfully saved to {实锤_filename}")
    except IOError as e:
        print(f"\nError: Could not write results to {实锤_filename}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nUnexpected error writing results to {实锤_filename}: {e}", file=sys.stderr)
    # --- 结束 "实锤" 逻辑 ---

    # Print results and save to file
    output_filename = "比對結果.txt"
    print(f"\nAnalysis complete. Saving results to {output_filename}...")

    try:
        with open(output_filename, 'w', encoding='utf-8') as outfile:
            if shared_ip_details:
                header = "--- Shared IP Addresses Found ---"
                print(header)
                outfile.write(header + '\n')

                for item in shared_ip_details:
                    ip = item['ip']
                    details = item['details']
                    user_list = [d['user'] for d in details]

                    ip_line = f"IP: {ip}"
                    users_line = f"  Shared by Users: {', '.join(user_list)}"
                    print(ip_line)
                    outfile.write(ip_line + '\n')
                    outfile.write(users_line + '\n')

                    for user_detail in details:
                        user_line = f"    User: {user_detail['user']}"
                        print(user_line)
                        outfile.write(user_line + '\n')
                        for url in user_detail['urls']:
                            url_line = f"      - {url}"
                            print(url_line)
                            outfile.write(url_line + '\n')

                    separator = "-" * 30
                    print(separator)
                    outfile.write(separator + '\n')

                summary_line = f"\nFound {len(shared_ip_details)} shared IP addresses."
                print(summary_line)
                outfile.write(summary_line + '\n')
                print(f"\nResults successfully saved to {output_filename}")

            else:
                no_result_header = "\n--- No Shared IP Addresses Found ---"
                no_result_line_cn = "暂无重复 IP"
                print(no_result_header)
                outfile.write(no_result_header + '\n')
                outfile.write(no_result_line_cn + '\n')
                print(f"\nResults indicating no shared IPs saved to {output_filename}")

    except IOError as e:
        print(f"\nError: Could not write results to {output_filename}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nUnexpected error writing results to {output_filename}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
