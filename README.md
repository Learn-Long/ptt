# PTT 使用者行為分析工具

這是一套以 Python 撰寫的 PTT `HatePolitics` 看板資料抓取與使用者行為分析工具。程式會先抓取近期文章索引，再取得文章內容與推文，接著分析推文中的使用者、IP 位址及重複內容，產生共用 IP、疑似多重帳號、水桶名單交叉比對與重複推文報告。

## 功能概覽

- 自動估算 PTT 看板近七天文章的起始索引，也可以手動指定 `--start-index`。
- 多執行緒抓取 `HatePolitics` 看板文章索引。
- 取得文章全文、推文、推文時間與 IP 位址。
- 彙整每個使用者使用過的 IP，並找出共用 IP 的帳號群組。
- 將公告文章中的帳號視為水桶名單，與共用 IP 結果交叉比對。
- 偵測八小時內單篇文章重複推文至少三次，或跨文章重複推文至少五次。
- 將重複推文報告輸出成 TXT、JSON，並提供 Flask 網頁介面瀏覽。

## 執行環境

- Python 3.9 或更新版本
- 可連線至 `https://www.ptt.cc`
- 建議在 Windows Terminal、PowerShell 或其他 UTF-8 終端機中執行

## 安裝

在專案根目錄執行：

```powershell
cd F:\AI\ptt
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`web_viewer.py` 使用 Flask，而目前的 `requirements.txt` 尚未列出 Flask。若要啟動網頁報告，請另外安裝：

```powershell
python -m pip install flask
```

## 快速開始

### 互動式流程

推薦使用互動式執行器，它會顯示每個步驟的依賴與執行結果：

```powershell
python interactive_runner.py
```

選擇 `8` 可依序執行全部模組，選擇 `0` 離開。若要單獨執行某一步，也可以在選單中選擇對應項目。

### 全自動流程

```powershell
python auto_runner.py
```

此流程會先清理 `processed_urls.txt` 與 `output/word/` 的舊資料，再依序執行所有模組，最後刪除 `output/` 下的索引 JSON。若需要保留既有資料或增量處理，請改用互動式流程或個別執行腳本。

### 個別執行

```powershell
python scraper.py --start-index 12345
python article_scraper.py
python data_extractor.py
python ip_aggregator.py
python ip_cross_checker.py
python "5水桶检测.py"
python hyperlink_spam_detector.py
```

不指定 `--start-index` 時，`scraper.py` 會嘗試從 PTT 最新頁面估算近七天的起始索引；互動終端會詢問是否採用建議值，非互動環境則自動採用建議值。

## 處理流程

```text
scraper.py
    -> output/*.json                  文章索引
article_scraper.py
    -> output/word/*.json             文章、推文與 IP
data_extractor.py
    -> stdout                         使用者/IP/文章 URL JSON
ip_aggregator.py
    -> ID/<使用者>.txt                 使用者 IP 彙整
ip_cross_checker.py
    -> 比對結果.txt、实锤.txt          共用 IP 分析
5水桶检测.py
    -> 水桶名单.txt、检举名单.txt      水桶交叉比對
hyperlink_spam_detector.py
    -> hyperlink_spam_report.txt
    -> hyperlink_spam_report.json      重複推文報告
web_viewer.py
    -> http://localhost:5000           瀏覽 JSON 報告
```

分析模組會使用 `date_filter.py` 過濾近七天的文章資料。`article_scraper.py` 會透過 `processed_urls.txt` 避免重複抓取 URL；但 `auto_runner.py` 每次啟動前會刪除這個檔案。

## 輸出檔案

| 路徑 | 說明 |
| --- | --- |
| `output/*.json` | 看板文章索引，包含標題、日期與文章連結 |
| `output/word/*.json` | 文章詳細內容、推文、推文時間與 IP |
| `ID/*.txt` | 各使用者的 IP 彙整結果 |
| `ip_aggregator_summary.txt` | IP 彙整統計摘要 |
| `比對結果.txt` | 共用 IP 的帳號分析結果 |
| `实锤.txt` | 共用多個 IP 的疑似帳號對 |
| `水桶名单.txt` | 從公告文章檔名整理出的水桶帳號 |
| `检举名单.txt` | 水桶帳號與共用 IP 群組的交集 |
| `hyperlink_spam_report.txt` | 可直接閱讀的重複推文報告 |
| `hyperlink_spam_report.json` | 網頁介面使用的結構化報告 |

`data_extractor.py` 預設把 JSON 結果輸出到標準輸出，不會自行建立 `user_ip_url_records.json`。如需保存結果，可使用 PowerShell 重導向：

```powershell
python data_extractor.py > user_ip_url_records.json
```

## 查看網頁報告

先完成 `hyperlink_spam_detector.py`，再啟動 Flask：

```powershell
python web_viewer.py
```

開啟 <http://localhost:5000>。網頁支援單篇／跨篇違規切換、使用者搜尋、排序與複製報告內容。

## 注意事項

- 本工具只針對 PTT `HatePolitics` 看板，網址與看板名稱目前寫死在 `scraper.py`。
- PTT 可能因網路錯誤、頁面格式變更或存取限制導致抓取失敗；請檢查終端輸出的失敗索引。
- IP 共用不等於帳號必然由同一人操作，分析結果應視為線索，不應單獨作為定案依據。
- `output/word/`、`ID/` 及報告檔可能含有使用者名稱、IP 與文章內容，請妥善保存並限制分享範圍。
- 請遵守 PTT 使用規範、所在地法律及適用的隱私要求，並控制抓取頻率。
- 目前 `main.py` 是較早的基本串接入口，未包含水桶及重複推文分析；完整流程請使用 `interactive_runner.py` 或 `auto_runner.py`。

## 專案結構

```text
ptt/
├── scraper.py                  # 抓取文章索引
├── article_scraper.py          # 抓取文章與推文
├── date_filter.py              # 近七天資料過濾
├── data_extractor.py           # 輸出使用者/IP/URL 關聯
├── ip_aggregator.py            # 使用者 IP 彙整
├── ip_cross_checker.py         # 共用 IP 分析
├── 5水桶检测.py                # 水桶名單交叉比對
├── hyperlink_spam_detector.py  # 重複推文偵測
├── interactive_runner.py       # 互動式流程控制
├── auto_runner.py              # 全自動流程控制
├── web_viewer.py               # Flask 報告伺服器
├── templates/report.html       # 報告網頁介面
├── requirements.txt            # Python 套件依賴
├── output/                     # 抓取與分析產物
└── ID/                         # 使用者 IP 彙整產物
```
