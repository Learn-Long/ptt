import subprocess
import os
import sys

SCRIPTS_CONFIG = [
    {
        "name": "scraper.py",
        "description": "從 PTT HatePolitics 板塊抓取指定範圍內的文章列表。",
        "details": "流程：輸入起始索引號，程式將抓取文章標題、連結等資訊，並儲存到 output/ 目錄下的 JSON 檔案中。",
        "dependencies": [],
        "output_check": "output"
    },
    {
        "name": "article_scraper.py",
        "description": "根據步驟 1 產生的索引，抓取每篇文章的詳細內容和所有推文。",
        "details": "流程：讀取 output/ 目錄中的 JSON 檔案，存取文章連結，抓取全文和推文，儲存到 output/word/ 目錄下的新 JSON 檔案中。",
        "dependencies": ["output"],
        "output_check": os.path.join("output", "word")
    },
    {
        "name": "data_extractor.py",
        "description": "從文章的推文中提取使用者ID、IP位址和該推文所在的文章URL。",
        "details": "流程：讀取 output/word/ 目錄中的 JSON 檔案，分析推文資訊，並將提取到的 (使用者, IP, URL) 記錄輸出 (預計儲存到 user_ip_url_records.json)。",
        "dependencies": [os.path.join("output", "word")],
        "output_check": "user_ip_url_records.json"
    },
    {
        "name": "ip_aggregator.py",
        "description": "整理每個使用者使用過的所有IP位址。",
        "details": "流程：讀取 output/word/ 目錄中的 JSON 檔案，為每個使用者在 ID/ 目錄下建立一個 .txt 檔案，記錄其所有用過的IP。結果摘要儲存到 ip_aggregator_summary.txt。",
        "dependencies": [os.path.join("output", "word")],
        "output_check": "ID"
    },
    {
        "name": "ip_cross_checker.py",
        "description": "分析共用IP的情況，找出可能的多重帳戶或共用帳戶。",
        "details": "流程：讀取 output/word/ 目錄中的 JSON 檔案，找出使用相同IP的多個使用者，以及共用多個IP的使用者對，結果儲存到 比對結果.txt 和 实锤.txt。",
        "dependencies": [os.path.join("output", "word")],
        "output_check": ["比對結果.txt", "实锤.txt"]
    },
    {
        "name": "5水桶检测.py",
        "description": "交叉比對水桶名單與共用IP群組，產生檢舉名單。",
        "details": "流程：讀取 output/word/ 目錄中以 '[公告]' 開頭的 JSON 檔案名稱建立水桶名單，再與比對結果.txt 和 实锤.txt 交叉分析，找出水桶名單中共用IP的使用者群組，結果儲存到 水桶名单.txt 和 检举名单.txt。",
        "dependencies": [os.path.join("output", "word"), "比對結果.txt", "实锤.txt"],
        "output_check": ["水桶名单.txt", "检举名单.txt"]
    },
    {
        "name": "hyperlink_spam_detector.py",
        "description": "偵測在近期文章的留言中濫發超連結的使用者。",
        "details": "流程：掃描 output/word/ 目錄下近168小時內的文章，找出在單篇文章留言中發布3條或以上含 'http://' 或 'https://' 評論的使用者。結果儲存到 hyperlink_spam_report.txt。",
        "dependencies": [os.path.join("output", "word")],
        "output_check": "hyperlink_spam_report.txt"
    }
]

def check_dependencies(script_config):
    for dep_path in script_config["dependencies"]:
        if not os.path.exists(dep_path):
            print(f"\n錯誤：依賴項 '{dep_path}' 不存在。")
            print(f"請先執行產生 '{dep_path}' 的前置腳本。")
            return False
        if os.path.isdir(dep_path) and not os.listdir(dep_path):
            print(f"\n警告：依賴目錄 '{dep_path}' 為空。")
            print(f"前置腳本可能未成功產生所需檔案。")
    return True

def run_script(script_name, script_index=None):
    print(f"\n--- 正在執行 {script_name} ---")
    try:
        if script_name == "data_extractor.py":
            print("注意: data_extractor.py 的輸出將直接列印到控制台。")
            print("在原始 main.py 流程中，其輸出可能被重導向到 user_ip_url_records.json。")
            process = subprocess.run([sys.executable, script_name], check=True, universal_newlines=True, capture_output=False)
        else:
            process = subprocess.run([sys.executable, script_name], check=True, universal_newlines=True, capture_output=False)
        print(f"--- {script_name} 執行完畢 ---")
        return True
    except subprocess.CalledProcessError as e:
        print(f"執行 {script_name} 時發生錯誤: {e}")
        return False
    except FileNotFoundError:
        print(f"錯誤: 腳本 {script_name} 未找到。請確保它在當前目錄中。")
        return False

def display_menu():
    print("\n===================================")
    print(" PTT 使用者行為分析工具")
    print("===================================")
    print("請選擇要執行的操作：")
    for i, script_info in enumerate(SCRIPTS_CONFIG):
        print(f"\n{i+1}. {script_info['name']}")
        print(f"   功能：{script_info['description']}")
        print(f"   流程：{script_info['details']}")
        if script_info["dependencies"]:
            deps_str = ", ".join([os.path.basename(dep) if dep else "N/A" for dep in script_info["dependencies"]])
            print(f"   依賴：必須先成功執行產出 '{deps_str}' 的模組。")
        else:
            print("   依賴：無。這是第一步。")

    print(f"\n{len(SCRIPTS_CONFIG) + 1}. 自動依序執行所有模組 (1 -> {len(SCRIPTS_CONFIG)})")
    print("   功能：按照預設順序，自動執行以上所有分析步驟。")
    print("\n0. 退出程式")
    print("-----------------------------------")

def main():
    while True:
        display_menu()
        try:
            choice = input("請輸入選項 (0-{}): ".format(len(SCRIPTS_CONFIG) + 1))
            if not choice.isdigit():
                print("無效輸入，請輸入數字。")
                continue
            choice = int(choice)

            if choice == 0:
                print("正在退出程式...")
                break
            elif 1 <= choice <= len(SCRIPTS_CONFIG):
                script_to_run_config = SCRIPTS_CONFIG[choice - 1]
                if not check_dependencies(script_to_run_config):
                    input("按 Enter 鍵返回主選單...")
                    continue
                run_script(script_to_run_config["name"], choice - 1)
                input("\n按 Enter 鍵返回主選單...")
            elif choice == len(SCRIPTS_CONFIG) + 1:
                print("\n--- 開始自動依序執行所有模組 ---")
                all_success = True
                for i, script_config in enumerate(SCRIPTS_CONFIG):
                    print(f"\n準備執行模組 {i+1}: {script_config['name']}")
                    if not check_dependencies(script_config):
                        all_success = False
                        print(f"由於依賴檢查失敗，無法繼續執行 {script_config['name']} 及後續模組。")
                        break
                    if not run_script(script_config["name"], i):
                        all_success = False
                        print(f"{script_config['name']} 執行失敗。停止後續操作。")
                        break
                if all_success:
                    print("\n--- 所有模組已成功執行完畢 ---")
                else:
                    print("\n--- 自動執行過程中斷 ---")
                input("按 Enter 鍵返回主選單...")
            else:
                print("無效選項，請重新輸入。")

        except ValueError:
            print("無效輸入，請輸入一個數字。")
        except KeyboardInterrupt:
            print("\n操作被使用者中斷。正在退出...")
            break
        except Exception as e:
            print(f"發生未知錯誤: {e}")
            break

if __name__ == "__main__":
    main()
