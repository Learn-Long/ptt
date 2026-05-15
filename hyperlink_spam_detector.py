import os
import json
from datetime import datetime, timedelta
from collections import defaultdict
from date_filter import get_valid_json_files

ARTICLE_JSON_DIR = os.path.join("output", "word")
OUTPUT_REPORT_FILE = "hyperlink_spam_report.txt"
HOURS_TO_CHECK = 8  # 8小時時間窗口

def parse_ptt_article_timestamp(timestamp_str):
    """
    解析PTT文章時間戳，格式如 "Fri May  2 10:21:25 2025"
    返回 datetime 對象。
    """
    try:
        return datetime.strptime(timestamp_str, "%a %b %d %H:%M:%S %Y")
    except ValueError as e:
        try:
            return datetime.strptime(timestamp_str, "%a %b  %d %H:%M:%S %Y")
        except ValueError:
            print(f"解析文章時間戳出錯: '{timestamp_str}'. Error: {e}")
            return None

def parse_ptt_push_timestamp(timestamp_str, year=None):
    """
    解析PTT推文時間戳，格式如 "1.171.1.1 05/02 10:21"
    返回 (ip, datetime) 元組。
    
    參數:
        timestamp_str: 推文時間戳字串
        year: 年份（推文時間戳不包含年份，需要從文章或其他來源獲取）
    """
    if not timestamp_str or not isinstance(timestamp_str, str):
        return None, None
    
    parts = timestamp_str.strip().split()
    if len(parts) < 2:
        return None, None
    
    ip = parts[0]
    date_time_str = ' '.join(parts[1:])  # 如 "05/02 10:21"
    
    # 解析日期時間
    try:
        # 格式: "05/02 10:21"
        date_part, time_part = date_time_str.split()
        month, day = date_part.split('/')
        hour, minute = time_part.split(':')
        
        if year is None:
            year = datetime.now().year  # 預設使用當前年份
        
        return ip, datetime(year, int(month), int(day), int(hour), int(minute))
    except (ValueError, IndexError) as e:
        return ip, None

def main():
    if not os.path.exists(ARTICLE_JSON_DIR):
        print(f"錯誤：文章JSON目錄 '{ARTICLE_JSON_DIR}' 未找到。")
        return

    now = datetime.now()
    print(f"腳本運行時間: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"檢測規則:")
    print(f"  1. 單篇文章內8小時相同內容 >= 3次")
    print(f"  2. 跨文章8小時內相同內容 >= 5次")

    json_files = get_valid_json_files(ARTICLE_JSON_DIR)

    if not json_files:
        print(f"在 '{ARTICLE_JSON_DIR}' 中沒有找到JSON檔案。")
        return

    print(f"找到 {len(json_files)} 個JSON檔案進行處理...")
    
    # 資料結構：
    # user_article_comments: {user: {article_url: [(comment, datetime), ...]}}
    # 用於檢測單篇文章內的重複
    user_article_comments = defaultdict(lambda: defaultdict(list))
    
    # user_all_comments: {user: [(comment, datetime, article_url), ...]}
    # 用於檢測跨文章的重複
    user_all_comments = defaultdict(list)
    
    # 儲存文章資訊
    article_info = {}  # {url: {'timestamp': datetime, 'title': str}}

    processed_files = 0
    total_pushes = 0

    for filepath in json_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"解碼JSON檔案 '{filename}' 時出錯。跳過。")
            continue
        except IOError as e:
            print(f"讀取檔案 '{filename}' 時出錯: {e}。跳過。")
            continue
        
        processed_files += 1
        article_timestamp_str = data.get("timestamp")
        article_url = data.get("url")
        article_title = data.get("title", "N/A")

        if not article_url:
            continue

        # 解析文章時間戳獲取年份
        article_year = None
        if article_timestamp_str:
            article_datetime = parse_ptt_article_timestamp(article_timestamp_str)
            if article_datetime:
                article_year = article_datetime.year
                article_info[article_url] = {
                    'timestamp': article_datetime,
                    'title': article_title
                }
        
        if article_year is None:
            article_year = now.year  # 預設使用當前年份

        pushes = data.get("pushes", [])
        if not isinstance(pushes, list):
            continue

        for push in pushes:
            user = push.get("user")
            comment = push.get("comment", "")
            push_timestamp = push.get("timestamp", "")

            if not user or not isinstance(comment, str):
                continue

            total_pushes += 1
            
            # 解析推文時間
            ip, push_datetime = parse_ptt_push_timestamp(push_timestamp, article_year)
            
            # 標準化評論內容（去除首尾空白）
            normalized_comment = comment.strip()
            
            # 儲存資料
            user_article_comments[user][article_url].append({
                'comment': normalized_comment,
                'datetime': push_datetime,
                'ip': ip
            })
            
            user_all_comments[user].append({
                'comment': normalized_comment,
                'datetime': push_datetime,
                'article_url': article_url,
                'ip': ip
            })
        
        if processed_files % 100 == 0:
            print(f"已處理 {processed_files}/{len(json_files)} 個檔案...")

    print(f"檔案處理完成。共處理 {processed_files} 個檔案，{total_pushes} 條推文。")

    # 檢測違規行為
    single_article_violations = []  # 單篇文章內重複3次
    cross_article_violations = []   # 跨文章重複5次

    # 檢測1: 單篇文章內8小時相同內容 >= 3次
    print("\n正在檢測單篇文章內的重複推文...")
    for user, articles in user_article_comments.items():
        for article_url, comments in articles.items():
            # 按評論內容分組
            comment_groups = defaultdict(list)
            for c in comments:
                if c['comment']:  # 忽略空評論
                    comment_groups[c['comment']].append(c)
            
            # 檢查每個評論內容是否在8小時內重複3次以上
            for comment_text, instances in comment_groups.items():
                if len(instances) >= 3:
                    # 過濾出在8小時內的實例
                    valid_instances = []
                    for inst in instances:
                        if inst['datetime']:
                            valid_instances.append(inst)
                    
                    if len(valid_instances) >= 3:
                        # 檢查是否在8小時窗口內
                        datetimes = sorted([inst['datetime'] for inst in valid_instances])
                        time_span = datetimes[-1] - datetimes[0]
                        
                        if time_span <= timedelta(hours=HOURS_TO_CHECK):
                            single_article_violations.append({
                                'user': user,
                                'article_url': article_url,
                                'comment': comment_text,
                                'count': len(valid_instances),
                                'time_span': str(time_span),
                                'instances': valid_instances
                            })

    # 檢測2: 跨文章8小時內相同內容 >= 5次
    print("正在檢測跨文章的重複推文...")
    for user, all_comments in user_all_comments.items():
        # 按評論內容分組
        comment_groups = defaultdict(list)
        for c in all_comments:
            if c['comment']:  # 忽略空評論
                comment_groups[c['comment']].append(c)
        
        # 檢查每個評論內容是否在8小時內跨文章重複5次以上
        for comment_text, instances in comment_groups.items():
            if len(instances) >= 5:
                # 過濾出有時間資訊的實例
                valid_instances = [inst for inst in instances if inst['datetime']]
                
                if len(valid_instances) >= 5:
                    # 按時間排序
                    valid_instances.sort(key=lambda x: x['datetime'])
                    
                    # 使用滑動窗口檢查是否存在8小時內的5次重複
                    for i in range(len(valid_instances) - 4):
                        window = valid_instances[i:i+5]
                        time_span = window[-1]['datetime'] - window[0]['datetime']
                        
                        if time_span <= timedelta(hours=HOURS_TO_CHECK):
                            # 檢查是否跨文章
                            articles_in_window = set(inst['article_url'] for inst in window)
                            
                            if len(articles_in_window) > 1:  # 確實跨文章
                                cross_article_violations.append({
                                    'user': user,
                                    'comment': comment_text,
                                    'count': len(window),
                                    'time_span': str(time_span),
                                    'articles': list(articles_in_window),
                                    'instances': window
                                })
                                break  # 找到一個符合條件的窗口即可

    # 排序結果
    single_article_violations.sort(key=lambda x: max(inst['datetime'] for inst in x['instances'] if inst['datetime']), reverse=True)
    cross_article_violations.sort(key=lambda x: max(inst['datetime'] for inst in x['instances'] if inst['datetime']), reverse=True)

    # 生成報告
    print(f"\n生成報告...")
    try:
        with open(OUTPUT_REPORT_FILE, 'w', encoding='utf-8') as outfile:
            outfile.write(f"重複推文檢測報告\n")
            outfile.write(f"報告生成時間: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
            outfile.write(f"檢測規則:\n")
            outfile.write(f"  1. 單篇文章內{HOURS_TO_CHECK}小時相同內容 >= 3次\n")
            outfile.write(f"  2. 跨文章{HOURS_TO_CHECK}小時內相同內容 >= 5次\n")
            outfile.write("=" * 80 + "\n\n")

            # 報告第一部分：單篇文章內重複
            outfile.write("【第一部分】單篇文章內重複推文 (>= 3次)\n")
            outfile.write("-" * 80 + "\n\n")
            
            if not single_article_violations:
                outfile.write("未發現單篇文章內的重複推文違規。\n\n")
            else:
                outfile.write(f"共發現 {len(single_article_violations)} 起違規：\n\n")
                
                for v in single_article_violations:
                    outfile.write(f"使用者: {v['user']}\n")
                    outfile.write(f"文章URL: {v['article_url']}\n")
                    article_data = article_info.get(v['article_url'], {})
                    if article_data.get('title'):
                        outfile.write(f"文章標題: {article_data['title']}\n")
                    outfile.write(f"重複次數: {v['count']} 次\n")
                    outfile.write(f"時間跨度: {v['time_span']}\n")
                    outfile.write(f"詳細記錄:\n")
                    for inst in v['instances']:
                        dt_str = inst['datetime'].strftime('%Y/%m/%d %H:%M') if inst['datetime'] else 'N/A'
                        outfile.write(f"  {v['user']}: {inst['comment']} - {dt_str} ({inst['ip'] or 'N/A'})\n")
                    outfile.write("-" * 80 + "\n\n")

            # 報告第二部分：跨文章重複
            outfile.write("\n【第二部分】跨文章重複推文 (>= 5次)\n")
            outfile.write("-" * 80 + "\n\n")
            
            if not cross_article_violations:
                outfile.write("未發現跨文章的重複推文違規。\n\n")
            else:
                outfile.write(f"共發現 {len(cross_article_violations)} 起違規：\n\n")
                
                for v in cross_article_violations:
                    outfile.write(f"使用者: {v['user']}\n")
                    outfile.write(f"重複次數: {v['count']} 次\n")
                    outfile.write(f"時間跨度: {v['time_span']}\n")
                    outfile.write(f"涉及文章 ({len(v['articles'])} 篇):\n")
                    
                    for article_url in v['articles']:
                        article_data = article_info.get(article_url, {})
                        title = article_data.get('title', 'N/A')
                        outfile.write(f"  - {article_url}\n")
                        if title != 'N/A':
                            outfile.write(f"    標題: {title}\n")
                    
                    outfile.write(f"詳細記錄:\n")
                    for inst in v['instances']:
                        dt_str = inst['datetime'].strftime('%Y/%m/%d %H:%M') if inst['datetime'] else 'N/A'
                        outfile.write(f"  {v['user']}: {inst['comment']} - {dt_str} ({inst['ip'] or 'N/A'})\n")
                    outfile.write("-" * 80 + "\n\n")

            # 統計摘要
            outfile.write("\n【統計摘要】\n")
            outfile.write("=" * 80 + "\n")
            outfile.write(f"單篇文章內重複違規: {len(single_article_violations)} 起\n")
            outfile.write(f"跨文章重複違規: {len(cross_article_violations)} 起\n")
            
            # 統計違規使用者
            single_users = set(v['user'] for v in single_article_violations)
            cross_users = set(v['user'] for v in cross_article_violations)
            outfile.write(f"單篇違規使用者數: {len(single_users)}\n")
            outfile.write(f"跨篇違規使用者數: {len(cross_users)}\n")
            outfile.write(f"總違規使用者數: {len(single_users | cross_users)}\n")

        print(f"報告已儲存到 '{OUTPUT_REPORT_FILE}'")
        print(f"\n統計摘要:")
        print(f"  單篇文章內重複違規: {len(single_article_violations)} 起")
        print(f"  跨文章重複違規: {len(cross_article_violations)} 起")
        print(f"  總違規使用者數: {len(single_users | cross_users)}")

        json_single = []
        for v in single_article_violations:
            article_data = article_info.get(v['article_url'], {})
            json_single.append({
                'user': v['user'],
                'article_url': v['article_url'],
                'article_title': article_data.get('title', ''),
                'count': v['count'],
                'time_span': v['time_span'],
                'instances': [
                    {
                        'user': inst.get('user', v['user']),
                        'comment': inst['comment'],
                        'datetime': inst['datetime'].strftime('%Y/%m/%d %H:%M') if inst['datetime'] else '',
                        'ip': inst.get('ip', '') or ''
                    }
                    for inst in v['instances']
                ]
            })

        json_cross = []
        for v in cross_article_violations:
            json_cross.append({
                'user': v['user'],
                'count': v['count'],
                'time_span': v['time_span'],
                'articles': [
                    {
                        'url': url,
                        'title': article_info.get(url, {}).get('title', '')
                    }
                    for url in v['articles']
                ],
                'instances': [
                    {
                        'user': inst.get('user', v['user']),
                        'comment': inst['comment'],
                        'datetime': inst['datetime'].strftime('%Y/%m/%d %H:%M') if inst['datetime'] else '',
                        'ip': inst.get('ip', '') or '',
                        'article_url': inst.get('article_url', '')
                    }
                    for inst in v['instances']
                ]
            })

        json_report = {
            'report_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'rules': [
                f'單篇文章內{HOURS_TO_CHECK}小時相同內容 >= 3次',
                f'跨文章{HOURS_TO_CHECK}小時內相同內容 >= 5次'
            ],
            'summary': {
                'single_violations': len(single_article_violations),
                'cross_violations': len(cross_article_violations),
                'single_users': len(single_users),
                'cross_users': len(cross_users),
                'total_users': len(single_users | cross_users)
            },
            'single_article_violations': json_single,
            'cross_article_violations': json_cross
        }

        json_output_file = 'hyperlink_spam_report.json'
        tmp_output_file = json_output_file + '.tmp'
        try:
            with open(tmp_output_file, 'w', encoding='utf-8') as jf:
                json.dump(json_report, jf, ensure_ascii=False, indent=2)
            os.replace(tmp_output_file, json_output_file)
        except OSError:
            try:
                with open(json_output_file, 'w', encoding='utf-8') as jf:
                    json.dump(json_report, jf, ensure_ascii=False, indent=2)
                if os.path.exists(tmp_output_file):
                    os.remove(tmp_output_file)
                print("警告：原子寫入失敗，已改用直接寫入模式。")
            except IOError as e2:
                print(f"寫入 JSON 報告失敗: {e2}")
        print(f"JSON報告已儲存到 '{json_output_file}'")

    except IOError as e:
        print(f"寫入報告檔案 '{OUTPUT_REPORT_FILE}' 時出錯: {e}")

if __name__ == "__main__":
    main()
