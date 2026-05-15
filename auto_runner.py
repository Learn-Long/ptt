import subprocess
import sys
import os

SCRIPTS_CONFIG = [
    {
        "name": "scraper.py",
        "description": "從 PTT HatePolitics 板塊抓取指定範圍內的文章列表。",
        "dependencies": [],
    },
    {
        "name": "article_scraper.py",
        "description": "根據步驟 1 產生的索引，抓取每篇文章的詳細內容和所有推文。",
        "dependencies": ["output"],
    },
    {
        "name": "data_extractor.py",
        "description": "從文章的推文中提取使用者ID、IP位址和該推文所在的文章URL。",
        "dependencies": [os.path.join("output", "word")],
    },
    {
        "name": "ip_aggregator.py",
        "description": "整理每個使用者使用過的所有IP位址。",
        "dependencies": [os.path.join("output", "word")],
    },
    {
        "name": "ip_cross_checker.py",
        "description": "分析共用IP的情況，找出可能的多重帳戶或共用帳戶。",
        "dependencies": [os.path.join("output", "word")],
    },
    {
        "name": "5水桶检测.py",
        "description": "交叉比對水桶名單與共用IP群組，產生檢舉名單。",
        "dependencies": [os.path.join("output", "word"), "比對結果.txt", "实锤.txt"],
    },
    {
        "name": "hyperlink_spam_detector.py",
        "description": "偵測在近期文章的留言中濫發超連結的使用者。",
        "dependencies": [os.path.join("output", "word")],
    },
]


def check_dependencies(script_config):
    for dep_path in script_config["dependencies"]:
        if not os.path.exists(dep_path):
            print(f"錯誤：依賴項 '{dep_path}' 不存在。")
            print(f"請先執行產生 '{dep_path}' 的前置腳本。")
            return False
        if os.path.isdir(dep_path) and not os.listdir(dep_path):
            print(f"警告：依賴目錄 '{dep_path}' 為空。")
            print(f"前置腳本可能未成功產生所需檔案。")
    return True


def run_script(script_name):
    print(f"\n--- 正在執行 {script_name} ---")
    try:
        if script_name == "scraper.py":
            process = subprocess.run(
                [sys.executable, script_name],
                text=True,
                check=True,
            )
        else:
            process = subprocess.run(
                [sys.executable, script_name],
                check=True,
                text=True,
            )
        print(f"--- {script_name} 執行完畢 ---")
        return True
    except subprocess.CalledProcessError as e:
        print(f"執行 {script_name} 時發生錯誤: {e}")
        return False
    except FileNotFoundError:
        print(f"錯誤: 腳本 {script_name} 未找到。請確保它在當前目錄中。")
        return False


def cleanup_output_index_files():
    output_dir = "output"
    if not os.path.exists(output_dir):
        return
    deleted = 0
    for filename in os.listdir(output_dir):
        filepath = os.path.join(output_dir, filename)
        if filename.endswith(".json") and os.path.isfile(filepath):
            try:
                os.remove(filepath)
                deleted += 1
            except OSError as e:
                print(f"刪除 {filepath} 失敗: {e}")
    print(f"已清理 output/ 目錄中的 {deleted} 個索引 JSON 檔案。")


def main():
    print("=== PTT 全自動分析流程 ===")
    all_success = True
    for i, script_config in enumerate(SCRIPTS_CONFIG):
        print(f"\n準備執行模組 {i + 1}/{len(SCRIPTS_CONFIG)}: {script_config['name']}")
        if not check_dependencies(script_config):
            all_success = False
            print(f"由於依賴檢查失敗，無法繼續執行 {script_config['name']} 及後續模組。")
            break
        if not run_script(script_config["name"]):
            all_success = False
            print(f"{script_config['name']} 執行失敗。停止後續操作。")
            break

    if all_success:
        print("\n--- 所有模組已成功執行完畢 ---")
        print("\n開始清理 output/ 目錄中的索引 JSON 檔案...")
        cleanup_output_index_files()
        print("\n=== 全自動分析流程完成 ===")
    else:
        print("\n--- 自動執行過程中斷 ---")


if __name__ == "__main__":
    main()
