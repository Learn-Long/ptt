from datetime import datetime, timedelta
import json
import os


def parse_ptt_article_timestamp(timestamp_str):
    try:
        return datetime.strptime(timestamp_str, "%a %b %d %H:%M:%S %Y")
    except (ValueError, TypeError):
        try:
            return datetime.strptime(timestamp_str, "%a %b  %d %H:%M:%S %Y")
        except (ValueError, TypeError):
            return None


def is_within_days(timestamp_str, days=7):
    article_dt = parse_ptt_article_timestamp(timestamp_str)
    if article_dt is None:
        return False
    cutoff = (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return article_dt >= cutoff


def get_valid_json_files(directory, days=7):
    valid_files = []
    if not os.path.exists(directory):
        return valid_files
    for filename in os.listdir(directory):
        if filename.endswith('.json') and os.path.isfile(os.path.join(directory, filename)):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                timestamp_str = data.get('timestamp', '')
                if is_within_days(timestamp_str, days):
                    valid_files.append(filepath)
            except (json.JSONDecodeError, IOError):
                continue
    return valid_files


def _parse_ptt_date_str(date_str):
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        parts = date_str.strip().split('/')
        if len(parts) == 2:
            month, day = int(parts[0]), int(parts[1])
            now = datetime.now()
            year = now.year
            parsed = datetime(year, month, day)
            if parsed > now + timedelta(days=1):
                parsed = datetime(year - 1, month, day)
            return parsed
    except (ValueError, TypeError):
        pass
    return None


def get_valid_index_files(directory, days=7):
    valid_files = []
    if not os.path.exists(directory):
        return valid_files
    cutoff = (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    for filename in os.listdir(directory):
        if filename.endswith('.json') and os.path.isfile(os.path.join(directory, filename)):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for entry in data:
                        date_str = entry.get('date', '')
                        entry_dt = _parse_ptt_date_str(date_str)
                        if entry_dt and entry_dt >= cutoff:
                            valid_files.append(filepath)
                            break
            except (json.JSONDecodeError, IOError):
                continue
    return valid_files
