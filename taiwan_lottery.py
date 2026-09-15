# -*- coding: utf-8 -*-
"""
台灣彩券 - 威力彩 (Super Lotto 6/38) 歷史各期獎號下載工具
======================================================
支援功能：
1. 透過台灣彩券官方 API 批量抓取威力彩開獎號碼（支援指定年份、月份範圍、最新期數）
2. 完整擷取：期別、開獎日期、兌獎截止日、第一區號碼（開出順序與大小順序）、第二區號碼、銷售總額、頭獎至普獎派彩資訊
3. 匯出為 CSV 檔案（使用 utf-8-sig 編碼，Excel 開啟不亂碼）與 JSON 檔案
4. 下載台彩官方歷年開獎總檔（2007 ~ 至今 ZIP 壓縮包）
5. 零第三方套件依賴：使用 Python 內建 standard library (urllib, json, csv)，隨裝隨用！
"""

import sys
import os
import json
import csv
import time
import zipfile
import ssl
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# 建立全域 SSL 不驗證 Context 避免 SSL 憑證問題
SSL_CTX = ssl._create_unverified_context()

# 台灣彩券官方 API 端點設定
API_BASE_URL = "https://api.taiwanlottery.com/TLCAPIWeB"
API_SUPER_LOTTO = f"{API_BASE_URL}/Lottery/SuperLotto638Result"
API_LOTTO649 = f"{API_BASE_URL}/Lottery/Lotto649Result"
API_DOWNLOAD_ANNUAL = f"{API_BASE_URL}/Lottery/ResultDownload"
CDN_DOWNLOAD_URL = "https://cdn.taiwanlottery.com.tw/app/FilesForDownload/Download/LottoResult/{year}.zip"

# 8 大彩種 API 配置
GAME_API_CONFIG = {
    "super_lotto": {"endpoint": f"{API_BASE_URL}/Lottery/SuperLotto638Result", "key": "superLotto638Res", "name": "威力彩", "file_prefix": "super_lotto"},
    "lotto649":    {"endpoint": f"{API_BASE_URL}/Lottery/Lotto649Result",       "key": "lotto649Res",       "name": "大樂透", "file_prefix": "lotto649"},
    "daily539":    {"endpoint": f"{API_BASE_URL}/Lottery/Daily539Result",       "key": "daily539Res",       "name": "今彩539", "file_prefix": "daily539"},
    "lotto39m":    {"endpoint": f"{API_BASE_URL}/Lottery/Lotto39MResult",      "fallback": f"{API_BASE_URL}/Lottery/Daily539Result", "key": "lotto39MRes", "fallback_key": "daily539Res", "name": "39樂合彩", "file_prefix": "lotto39m"},
    "lotto49m":    {"endpoint": f"{API_BASE_URL}/Lottery/Lotto49MResult",      "fallback": f"{API_BASE_URL}/Lottery/Lotto649Result",  "key": "lotto49MRes",  "fallback_key": "lotto649Res",  "name": "49樂合彩", "file_prefix": "lotto49m"},
    "3star":       {"endpoint": f"{API_BASE_URL}/Lottery/3DResult",            "key": "lotto3DRes",        "name": "3星彩", "file_prefix": "3star"},
    "4star":       {"endpoint": f"{API_BASE_URL}/Lottery/4DResult",            "key": "lotto4DRes",        "name": "4星彩", "file_prefix": "4star"},
    "bingo":       {"endpoint": f"{API_BASE_URL}/Lottery/BingoResult",         "key": "bingoQueryResult",  "name": "BINGO BINGO", "file_prefix": "bingo"}
}

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.taiwanlottery.com/",
    "Origin": "https://www.taiwanlottery.com",
    "Accept": "application/json, text/plain, */*"
}

def http_get(url: str, headers: dict = None, timeout: int = 15, silent_error: bool = False) -> dict:
    """發送 HTTP GET 請求並解析 JSON 回應"""
    req_headers = DEFAULT_HEADERS.copy()
    if headers:
        req_headers.update(headers)
    
    req = Request(url, headers=req_headers, method="GET")
    try:
        with urlopen(req, timeout=timeout, context=SSL_CTX) as response:
            if response.status == 200:
                raw_data = response.read().decode("utf-8")
                return json.loads(raw_data)
            else:
                if not silent_error:
                    print(f"[錯誤] HTTP 狀態碼: {response.status}")
                return None
    except HTTPError as e:
        if not silent_error:
            print(f"[HTTP 錯誤] {e.code} - {e.reason} (URL: {url})")
        return None
    except URLError as e:
        if not silent_error:
            print(f"[網路錯誤] {e.reason} (URL: {url})")
        return None
    except Exception as e:
        if not silent_error:
            print(f"[未知錯誤] {str(e)} (URL: {url})")
        return None

def fetch_game_by_month(game: str = "super_lotto", month: str = "2024-01", end_month: str = None, page_num: int = 1, page_size: int = 200) -> list:
    """通用：依月份區間查詢任一彩種開獎紀錄"""
    g = (game or "super_lotto").lower()
    config = GAME_API_CONFIG.get(g, GAME_API_CONFIG["super_lotto"])
    if not end_month:
        end_month = month
    
    has_fallback = "fallback" in config
    url = f"{config['endpoint']}?month={month}&endMonth={end_month}&pageNum={page_num}&pageSize={page_size}"
    res = http_get(url, silent_error=has_fallback)
    
    if (not res or res.get("rtCode") != 0) and has_fallback:
        fb_url = f"{config['fallback']}?month={month}&endMonth={end_month}&pageNum={page_num}&pageSize={page_size}"
        res = http_get(fb_url)

    if not res or res.get("rtCode") != 0:
        return []
        
    content = res.get("content", {})
    if isinstance(content, dict):
        if config["key"] in content and content[config["key"]]:
            return content[config["key"]]
        if config.get("fallback_key") in content and content[config.get("fallback_key")]:
            return content[config.get("fallback_key")]
        for k, v in content.items():
            if isinstance(v, list) and len(v) > 0:
                return v
    return []

def fetch_game_by_year(game: str, year: int) -> list:
    """通用：抓取指定西元年份全年的彩種開獎獎號"""
    g = (game or "super_lotto").lower()
    config = GAME_API_CONFIG.get(g, GAME_API_CONFIG["super_lotto"])
    start_month = f"{year}-01"
    end_month = f"{year}-12"
    print(f"正在抓取 {year} 年 (民國 {year - 1911} 年) {config['name']} 開獎號碼...")
    records = fetch_game_by_month(g, start_month, end_month, page_num=1, page_size=200)
    print(f"-> 成功抓取 {year} 年共 {len(records)} 期 {config['name']} 開獎紀錄")
    return records

# 相容舊版 API 介面名稱
def fetch_super_lotto_by_period(period: str or int) -> dict:
    url = f"{API_SUPER_LOTTO}?period={period}"
    return http_get(url)

def fetch_super_lotto_by_month(month: str, end_month: str = None, page_num: int = 1, page_size: int = 200) -> dict:
    return http_get(f"{API_SUPER_LOTTO}?month={month}&endMonth={end_month or month}&pageNum={page_num}&pageSize={page_size}")

def fetch_super_lotto_by_year(year: int) -> list:
    return fetch_game_by_year("super_lotto", year)

def fetch_lotto649_by_period(period: str or int) -> dict:
    return http_get(f"{API_LOTTO649}?period={period}")

def fetch_lotto649_by_month(month: str, end_month: str = None, page_num: int = 1, page_size: int = 200) -> dict:
    return http_get(f"{API_LOTTO649}?month={month}&endMonth={end_month or month}&pageNum={page_num}&pageSize={page_size}")

def fetch_lotto649_by_year(year: int) -> list:
    return fetch_game_by_year("lotto649", year)

def parse_record(item: dict, game_type: str = "super_lotto") -> dict:
    """將官方單期 JSON 格式化為平整欄位結構 (通用支援 8 大彩種)"""
    draw_appear = item.get("drawNumberAppear", [])
    draw_size = item.get("drawNumberSize", [])
    
    raw_date = item.get("lotteryDate", "")
    date_str = raw_date.split("T")[0] if "T" in raw_date else raw_date
    raw_redeem = item.get("redeemableDate", "")
    redeem_str = raw_redeem.split("T")[0] if "T" in raw_redeem else raw_redeem
    
    jackpot = item.get("jackpotAssign", {}) or item.get("super638JackpotAssign", {}) or item.get("daily539JackpotAssign", {})
    second_prize = item.get("secondAssign", {}) or item.get("super638SecondAssign", {})
    
    g = (game_type or "super_lotto").lower()
    
    if g in ["daily539", "539", "lotto39m", "39樂合彩"]:
        z1_sorted = draw_size[:5] if len(draw_size) >= 5 else draw_appear[:5]
        return {
            "期別": item.get("period"),
            "開獎日期": date_str,
            "兌獎截止日": redeem_str,
            "第一區_開出順序": " ".join(f"{int(n):02d}" for n in draw_appear[:5]),
            "第一區_大小順序": " ".join(f"{int(n):02d}" for n in z1_sorted),
            "第二區": "",
            "第1球": int(z1_sorted[0]) if len(z1_sorted) > 0 else None,
            "第2球": int(z1_sorted[1]) if len(z1_sorted) > 1 else None,
            "第3球": int(z1_sorted[2]) if len(z1_sorted) > 2 else None,
            "第4球": int(z1_sorted[3]) if len(z1_sorted) > 3 else None,
            "第5球": int(z1_sorted[4]) if len(z1_sorted) > 4 else None,
            "第6球": None,
            "銷售總金額": item.get("sellAmount", 0),
            "總獎金": item.get("totalAmount", 0),
            "頭獎中獎人數": jackpot.get("winnerCount", 0),
            "頭獎單注獎金": jackpot.get("perPrize", 0),
        }
    elif g in ["3star", "3星彩"]:
        digits = [str(n) for n in draw_appear[:3]]
        return {
            "期別": item.get("period"),
            "開獎日期": date_str,
            "兌獎截止日": redeem_str,
            "第一區_開出順序": " ".join(digits),
            "第一區_大小順序": " ".join(digits),
            "第二區": "",
            "第1球": digits[0] if len(digits) > 0 else None,
            "第2球": digits[1] if len(digits) > 1 else None,
            "第3球": digits[2] if len(digits) > 2 else None,
            "第4球": None, "第5球": None, "第6球": None,
            "銷售總金額": item.get("sellAmount", 0),
            "頭獎中獎人數": jackpot.get("winnerCount", 0),
            "頭獎單注獎金": jackpot.get("perPrize", 0),
        }
    elif g in ["4star", "4星彩"]:
        digits = [str(n) for n in draw_appear[:4]]
        return {
            "期別": item.get("period"),
            "開獎日期": date_str,
            "兌獎截止日": redeem_str,
            "第一區_開出順序": " ".join(digits),
            "第一區_大小順序": " ".join(digits),
            "第二區": "",
            "第1球": digits[0] if len(digits) > 0 else None,
            "第2球": digits[1] if len(digits) > 1 else None,
            "第3球": digits[2] if len(digits) > 2 else None,
            "第4球": digits[3] if len(digits) > 3 else None,
            "第5球": None, "第6球": None,
            "銷售總金額": item.get("sellAmount", 0),
            "頭獎中獎人數": jackpot.get("winnerCount", 0),
            "頭獎單注獎金": jackpot.get("perPrize", 0),
        }
    elif g in ["bingo", "賓果賓果"]:
        z1 = [int(n) for n in draw_appear[:20]]
        super_num = draw_appear[20] if len(draw_appear) > 20 else (item.get("superNumber") or "")
        return {
            "期別": item.get("period"),
            "開獎日期": date_str,
            "兌獎截止日": redeem_str,
            "第一區_開出順序": " ".join(f"{n:02d}" for n in z1),
            "第一區_大小順序": " ".join(f"{n:02d}" for n in sorted(z1)),
            "第二區": f"{int(super_num):02d}" if str(super_num).isdigit() else "",
            "第1球": z1[0] if len(z1) > 0 else None,
            "第2球": z1[1] if len(z1) > 1 else None,
            "第3球": z1[2] if len(z1) > 2 else None,
            "第4球": z1[3] if len(z1) > 3 else None,
            "第5球": z1[4] if len(z1) > 4 else None,
            "第6球": z1[5] if len(z1) > 5 else None,
            "銷售總金額": item.get("sellAmount", 0),
            "頭獎中獎人數": jackpot.get("winnerCount", 0),
            "頭獎單注獎金": jackpot.get("perPrize", 0),
        }
    else:
        # super_lotto, lotto649, lotto49m
        z1_appear = draw_appear[:6] if len(draw_appear) >= 6 else []
        z2_appear = draw_appear[6] if len(draw_appear) >= 7 else None
        z1_sorted = draw_size[:6] if len(draw_size) >= 6 else []
        z2_sorted = draw_size[6] if len(draw_size) >= 7 else None
        
        return {
            "期別": item.get("period"),
            "開獎日期": date_str,
            "兌獎截止日": redeem_str,
            "第一區_開出順序": " ".join(f"{int(n):02d}" for n in z1_appear),
            "第一區_大小順序": " ".join(f"{int(n):02d}" for n in z1_sorted),
            "第二區": f"{int(z2_sorted):02d}" if z2_sorted is not None else "",
            "第1球": int(z1_sorted[0]) if len(z1_sorted) > 0 else None,
            "第2球": int(z1_sorted[1]) if len(z1_sorted) > 1 else None,
            "第3球": int(z1_sorted[2]) if len(z1_sorted) > 2 else None,
            "第4球": int(z1_sorted[3]) if len(z1_sorted) > 3 else None,
            "第5球": int(z1_sorted[4]) if len(z1_sorted) > 4 else None,
            "第6球": int(z1_sorted[5]) if len(z1_sorted) > 5 else None,
            "銷售總金額": item.get("sellAmount", 0),
            "總獎金": item.get("totalAmount", 0),
            "頭獎中獎人數": jackpot.get("winnerCount", 0),
            "頭獎單注獎金": jackpot.get("perPrize", 0),
            "貳獎中獎人數": second_prize.get("winnerCount", 0),
            "貳獎單注獎金": second_prize.get("perPrize", 0),
        }

def parse_lotto649_record(item: dict) -> dict:
    return parse_record(item, "lotto649")

def save_to_csv(records: list, output_filepath: str, game_type: str = "super_lotto"):
    """將紀錄列表存為 CSV 格式（含 BOM，確保繁體中文在 Excel 中不亂碼）"""
    if not records:
        print("[提示] 無紀錄可匯出。")
        return
    sorted_records = sorted(records, key=lambda x: x.get("period", 0))
    formatted_data = [parse_record(r, game_type) for r in sorted_records]
    fieldnames = list(formatted_data[0].keys())
    with open(output_filepath, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(formatted_data)
    print(f"[成功] 資料已儲存至: {os.path.abspath(output_filepath)} (共 {len(formatted_data)} 筆)")

def save_to_json(records: list, output_filepath: str):
    if not records:
        print("[提示] 無紀錄可匯出。")
        return
    sorted_records = sorted(records, key=lambda x: x.get("period", 0))
    with open(output_filepath, "w", encoding="utf-8") as jsonfile:
        json.dump(sorted_records, jsonfile, ensure_ascii=False, indent=2)
    print(f"[成功] JSON 資料已儲存至: {os.path.abspath(output_filepath)} (共 {len(sorted_records)} 筆)")

def download_official_yearly_zip(year: int, save_dir: str = "./downloads") -> str:
    """
    從台彩官方 CDN 下載歷年開獎總表壓縮檔（支援民國96年~至今）
    :param year: 西元年份 (例如 2023, 2024)
    :param save_dir: 儲存目錄
    :return: 下載後的本地檔案路徑
    """
    os.makedirs(save_dir, exist_ok=True)
    zip_url = CDN_DOWNLOAD_URL.format(year=year)
    local_filename = os.path.join(save_dir, f"LottoResult_{year}.zip")
    
    print(f"正在從官方 CDN 下載 {year} 年度開獎總表: {zip_url} ...")
    req = Request(zip_url, headers=DEFAULT_HEADERS)
    try:
        with urlopen(req, timeout=30) as response, open(local_filename, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print(f"[成功] 已下載官方年度壓縮檔: {local_filename} ({len(data)} bytes)")
        
        # 自動解壓縮至以年份為名的子資料夾
        extract_folder = os.path.join(save_dir, str(year))
        with zipfile.ZipFile(local_filename, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        print(f"[成功] 已解壓縮至資料夾: {extract_folder}")
        return local_filename
    except HTTPError as e:
        print(f"[下載失敗] HTTP {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"[下載失敗] {str(e)}")
        return None

def download_game_range(game: str, start_year: int, end_year: int, output_csv: str = None):
    """通用：批量下載指定彩種與跨年份紀錄，同步寫入 CSV 與 JSON"""
    g = (game or "super_lotto").lower()
    config = GAME_API_CONFIG.get(g, GAME_API_CONFIG["super_lotto"])
    if not output_csv:
        output_csv = f"{config['file_prefix']}_history.csv"
    
    all_records = []
    for y in range(start_year, end_year + 1):
        recs = fetch_game_by_year(g, y)
        all_records.extend(recs)
        time.sleep(0.4)
    
    if all_records:
        save_to_csv(all_records, output_csv, game_type=g)
        json_path = output_csv.rsplit(".", 1)[0] + ".json"
        save_to_json(all_records, json_path)
    else:
        print(f"[警告] 未抓取到任何 {config['name']} 資料。")

def download_super_lotto_range(start_year: int, end_year: int, output_csv: str = "super_lotto_history.csv"):
    download_game_range("super_lotto", start_year, end_year, output_csv)

def download_lotto649_range(start_year: int, end_year: int, output_csv: str = "lotto649_history.csv"):
    download_game_range("lotto649", start_year, end_year, output_csv)


def main():
    print("=" * 60)
    print("       台灣樂透彩 - 威力彩歷史獎號自動下載工具")
    print("=" * 60)
    print("1. 抓取最新第 5 屆全期開獎資料 (2024 年至今) 並匯出 CSV")
    print("2. 抓取指定年份威力彩開獎號碼 (例: 2024)")
    print("3. 抓取指定月份區間 (例: 2024-01 到 2024-06)")
    print("4. 查詢指定期別開獎號碼 (例: 113000001)")
    print("5. 下載官方歷年年度總檔 ZIP (支援 2007 ~ 2024+ 解壓縮)")
    print("6. 一鍵下載所有可用開獎紀錄 (預設模式)")
    print("=" * 60)

    # 判斷是否帶有命令列參數
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd in ["--gui", "-g"]:
            from lotto_gui import launch_gui
            launch_gui()
            return
        elif cmd in ["--web", "-w"]:
            from web_app import run_server
            run_server()
            return
        elif cmd in ["--all", "-a"]:
            cur_year = datetime.now().year
            download_super_lotto_range(2024, cur_year, "super_lotto_all.csv")
            return
        elif cmd == "--year" and len(sys.argv) > 2:
            target_year = int(sys.argv[2])
            recs = fetch_super_lotto_by_year(target_year)
            save_to_csv(recs, f"super_lotto_{target_year}.csv")
            return
        elif cmd in ["--ai", "-ai", "--predict"]:
            from lotto_ai_optimizer import generate_predictions, check_ortools_status
            status = check_ortools_status()
            print(f"求解引擎狀態: {status['engine']}")
            if not status['available']:
                print(f"提示: 可執行 {status['install_cmd']} 啟用 AI 運籌 CP-SAT 嚴謹數學求解器。")
            tickets_cnt = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 5
            res = generate_predictions("super_lotto_history.json", num_tickets=tickets_cnt)
            if res.get("status") == "success":
                summary = res["statistics_summary"]
                print(f"\n歷史特徵分析: {summary['total_draws']} 期 | 平均和值: {summary['avg_sum']}")
                print(f"第一區最熱門號碼: {summary['hot_numbers_zone1']}")
                print(f"第二區最熱門號碼: {summary['hot_numbers_zone2']}")
                print(f"\n【AI 運籌最佳化智慧推薦注單 ({len(res['recommended_tickets'])} 注多樣性包牌)】")
                for t in res["recommended_tickets"]:
                    z1_str = " ".join(f"{n:02d}" for n in t["zone1"])
                    z2_str = f"{t['zone2']:02d}"
                    print(f"第 {t.get('ticket_no', 1):02d} 注: [{z1_str}] + 特別號 [{z2_str}] | 和值:{t['sum']:3d} | 評分:{t['score']}分")
                    print(f"       決策理由: {', '.join(t['reasons'])}")
            else:
                print("預測失敗:", res.get("message"))
            return
        elif cmd == "--zip" and len(sys.argv) > 2:
            target_year = int(sys.argv[2])
            download_official_yearly_zip(target_year)
            return

        elif cmd in ["--download", "--cli", "-d"]:
            cur_year = datetime.now().year
            print(f"\n[命令列模式] 開始抓取 2024 至 {cur_year} 年威力彩歷史獎號...")
            download_super_lotto_range(2024, cur_year, "super_lotto_history.csv")
            print("\n下載完成！您可以在當前目錄找到 'super_lotto_history.csv' 與 'super_lotto_history.json'。")
            return

    # 預設無參數時：直接啟動一體化整合桌面圖形 UI！
    print("正在啟動 台灣彩券 · 威力彩一體化整合桌面 UI 系統...")
    from lotto_gui import launch_gui
    launch_gui()

if __name__ == "__main__":
    main()
