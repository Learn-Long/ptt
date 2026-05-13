import os
import json
import re
from collections import defaultdict
from date_filter import get_valid_json_files

# --- Configuration ---
ARTICLE_JSON_DIR = os.path.join("output", "word")
BENT_BUCKET_FILE = "水桶名单.txt" # Changed filename
SUSPICIOUS_FILE = "实锤.txt"
COMPARISON_RESULT_FILE = "比對結果.txt"
REPORT_FILE = "检举名单.txt" # New file for report

def extract_id_from_filename(filename):
    """Extracts the ID from a filename like '[公告] ID 废话.json' or '[公告]ID.json'."""
    # Matches '[公告]', optional whitespace, then captures non-space characters until the first space or '.json'
    match = re.match(r"\[公告\]\s*([^ ]+).*?\.json", filename)
    if match:
        return match.group(1) # Return only the captured ID part
    return None

def create_bent_bucket_list():
    """Creates a list of IDs from JSON filenames starting with '[公告]'."""
    bent_bucket_ids = set()
    if not os.path.exists(ARTICLE_JSON_DIR):
        print(f"Warning: Directory not found - {ARTICLE_JSON_DIR}")
        return bent_bucket_ids
    try:
        valid_files = get_valid_json_files(ARTICLE_JSON_DIR)
        for filepath in valid_files:
            filename = os.path.basename(filepath)
            id_extracted = extract_id_from_filename(filename)
            if id_extracted:
                bent_bucket_ids.add(id_extracted)
    except FileNotFoundError:
        print(f"Warning: Directory not found - {ARTICLE_JSON_DIR}")
        return bent_bucket_ids


    try:
        with open(BENT_BUCKET_FILE, "w", encoding="utf-8") as f:
            for id_entry in sorted(bent_bucket_ids):
                f.write(f"{id_entry}\n")
    except IOError as e:
        print(f"Error writing to {BENT_BUCKET_FILE}: {e}")

    return bent_bucket_ids

def find_shared_groups(comparison_file, bent_bucket_ids):
    """Finds groups of users where at least one user is in the bent_bucket_ids,
       processing the comparison file line by line."""
    found_groups = set()
    if not os.path.exists(comparison_file):
        print(f"Warning: {comparison_file} not found. Skipping group finding.")
        return found_groups

    try:
        with open(comparison_file, "r", encoding="utf-8") as f:
            for line in f:
                if "Shared by Users:" in line:
                    parts = line.strip().split(": ")
                    if len(parts) > 1:
                        shared_users_str = parts[1].strip()
                        # Split the string by comma and/or space, removing empty strings
                        shared_users = [u.strip() for u in re.split(r'[,\s]+', shared_users_str) if u.strip()]

                        if not shared_users: # Skip if no users found after splitting
                            continue

                        # Check if any user in this group is in the bent bucket list
                        match_found = any(user in bent_bucket_ids for user in shared_users)

                        if match_found:
                            # Add the frozenset of the *entire group* from this line
                            # Using frozenset because sets cannot contain mutable sets, but can contain immutable frozensets
                            found_groups.add(frozenset(shared_users))
    except IOError as e:
        print(f"Error reading from {comparison_file}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while processing {comparison_file}: {e}")


    return found_groups

def main():
    """Main function to create the lists."""
    print(f"Creating {BENT_BUCKET_FILE}...")
    bent_bucket_ids = create_bent_bucket_list()
    if not bent_bucket_ids:
        print("No IDs found for bent bucket list. Exiting.")
        # Optionally create empty report file here if needed even when no bucket IDs exist
        try:
            with open(REPORT_FILE, "w", encoding="utf-8") as f_report:
                f_report.write("实锤名单:\n(无)\n\n嫌疑名单:\n(无)\n")
            print(f"Empty report file created: {REPORT_FILE}")
        except IOError as e:
            print(f"Error writing empty report file {REPORT_FILE}: {e}")
        return # Exit if no bucket IDs to compare against
    print(f"Created {BENT_BUCKET_FILE} with {len(bent_bucket_ids)} IDs.")

    print("Finding 实锤 groups...")
    suspicious_groups = find_shared_groups(SUSPICIOUS_FILE, bent_bucket_ids)
    print(f"Found {len(suspicious_groups)} 实锤 groups.")

    print("Finding 嫌疑 groups...")
    suspect_groups = find_shared_groups(COMPARISON_RESULT_FILE, bent_bucket_ids)
    print(f"Found {len(suspect_groups)} 嫌疑 groups.")

    # Write results to report file
    print(f"Writing results to {REPORT_FILE}...")
    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f_report:
            f_report.write("实锤名单:\n")
            if suspicious_groups:
                # Sort groups alphabetically based on the first user after converting back to list
                # Convert frozenset back to list for sorting and joining
                sorted_groups = sorted([list(group) for group in suspicious_groups], key=lambda x: x[0])
                for group_list in sorted_groups:
                    f_report.write(", ".join(group_list) + "\n") # Write comma-separated sorted list
            else:
                f_report.write("(无)\n") # Indicate if empty

            f_report.write("\n嫌疑名单:\n")
            if suspect_groups:
                sorted_groups = sorted([list(group) for group in suspect_groups], key=lambda x: x[0])
                for group_list in sorted_groups:
                    f_report.write(", ".join(group_list) + "\n") # Write comma-separated sorted list
            else:
                f_report.write("(无)\n") # Indicate if empty
        print("Finished writing report.")
    except IOError as e:
        print(f"Error writing report file {REPORT_FILE}: {e}")


if __name__ == "__main__":
    main()
