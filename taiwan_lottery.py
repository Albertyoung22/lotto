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
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# 台灣彩券官方 API 端點設定
API_BASE_URL = "https://api.taiwanlottery.com/TLCAPIWeB"
API_SUPER_LOTTO = f"{API_BASE_URL}/Lottery/SuperLotto638Result"
API_DOWNLOAD_ANNUAL = f"{API_BASE_URL}/Lottery/ResultDownload"
CDN_DOWNLOAD_URL = "https://cdn.taiwanlottery.com.tw/app/FilesForDownload/Download/LottoResult/{year}.zip"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.taiwanlottery.com/",
    "Origin": "https://www.taiwanlottery.com",
    "Accept": "application/json, text/plain, */*"
}

def http_get(url: str, headers: dict = None, timeout: int = 15) -> dict:
    """發送 HTTP GET 請求並解析 JSON 回應"""
    req_headers = DEFAULT_HEADERS.copy()
    if headers:
        req_headers.update(headers)
    
    req = Request(url, headers=req_headers, method="GET")
    try:
        with urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                raw_data = response.read().decode("utf-8")
                return json.loads(raw_data)
            else:
                print(f"[錯誤] HTTP 狀態碼: {response.status}")
                return None
    except HTTPError as e:
        print(f"[HTTP 錯誤] {e.code} - {e.reason} (URL: {url})")
        return None
    except URLError as e:
        print(f"[網路錯誤] {e.reason} (URL: {url})")
        return None
    except Exception as e:
        print(f"[未知錯誤] {str(e)} (URL: {url})")
        return None

def fetch_super_lotto_by_period(period: str or int) -> dict:
    """依指定期別查詢威力彩開獎紀錄 (如 113000001)"""
    url = f"{API_SUPER_LOTTO}?period={period}"
    return http_get(url)

def fetch_super_lotto_by_month(month: str, end_month: str = None, page_num: int = 1, page_size: int = 200) -> dict:
    """
    依月份區間查詢威力彩開獎紀錄
    :param month: 起始月份 (格式 YYYY-MM，例如 '2024-01')
    :param end_month: 結束月份 (格式 YYYY-MM，例如 '2024-12')，若為 None 則與 month 相同
    :param page_num: 頁碼
    :param page_size: 單頁筆數（預設 200，單一年度威力彩約 104~105 期，可單頁全取）
    """
    if not end_month:
        end_month = month
    url = f"{API_SUPER_LOTTO}?month={month}&endMonth={end_month}&pageNum={page_num}&pageSize={page_size}"
    return http_get(url)

def fetch_super_lotto_by_year(year: int) -> list:
    """
    抓取指定西元年份的全年威力彩獎號（支援第5屆 2024 年至今）
    :param year: 西元年份 (如 2024, 2025)
    :return: 開獎紀錄串列
    """
    start_month = f"{year}-01"
    end_month = f"{year}-12"
    print(f"正在抓取 {year} 年 (民國 {year - 1911} 年) 威力彩開獎號碼...")
    res = fetch_super_lotto_by_month(start_month, end_month, page_num=1, page_size=200)
    
    if not res or res.get("rtCode") != 0:
        print(f"[警告] 抓取 {year} 年失敗或無資料: {res.get('rtMsg') if res else '無回應'}")
        return []
    
    records = res.get("content", {}).get("superLotto638Res", [])
    print(f"-> 成功抓取 {year} 年共 {len(records)} 期開獎紀錄")
    return records

def parse_record(item: dict) -> dict:
    """將官方單期 JSON 格式化為平整欄位結構"""
    draw_appear = item.get("drawNumberAppear", [])
    draw_size = item.get("drawNumberSize", [])
    
    # 前 6 碼為第一區，第 7 碼為第二區
    zone1_appear = draw_appear[:6] if len(draw_appear) >= 6 else []
    zone2_appear = draw_appear[6] if len(draw_appear) >= 7 else None
    
    zone1_sorted = draw_size[:6] if len(draw_size) >= 6 else []
    zone2_sorted = draw_size[6] if len(draw_size) >= 7 else None
    
    # 格式化日期時間
    raw_date = item.get("lotteryDate", "")
    date_str = raw_date.split("T")[0] if "T" in raw_date else raw_date
    
    raw_redeem = item.get("redeemableDate", "")
    redeem_str = raw_redeem.split("T")[0] if "T" in raw_redeem else raw_redeem
    
    # 獎金資訊
    jackpot = item.get("super638JackpotAssign", {})
    second_prize = item.get("super638SecondAssign", {})
    
    return {
        "期別": item.get("period"),
        "開獎日期": date_str,
        "兌獎截止日": redeem_str,
        "第一區_開出順序": " ".join(f"{n:02d}" for n in zone1_appear),
        "第一區_大小順序": " ".join(f"{n:02d}" for n in zone1_sorted),
        "第二區": f"{zone2_sorted:02d}" if zone2_sorted is not None else "",
        "第1球": zone1_sorted[0] if len(zone1_sorted) > 0 else None,
        "第2球": zone1_sorted[1] if len(zone1_sorted) > 1 else None,
        "第3球": zone1_sorted[2] if len(zone1_sorted) > 2 else None,
        "第4球": zone1_sorted[3] if len(zone1_sorted) > 3 else None,
        "第5球": zone1_sorted[4] if len(zone1_sorted) > 4 else None,
        "第6球": zone1_sorted[5] if len(zone1_sorted) > 5 else None,
        "銷售總金額": item.get("sellAmount", 0),
        "總獎金": item.get("totalAmount", 0),
        "頭獎中獎人數": jackpot.get("winnerCount", 0),
        "頭獎單注獎金": jackpot.get("perPrize", 0),
        "貳獎中獎人數": second_prize.get("winnerCount", 0),
        "貳獎單注獎金": second_prize.get("perPrize", 0),
    }

def save_to_csv(records: list, output_filepath: str):
    """將紀錄列表存為 CSV 格式（含 BOM，確保繁體中文在 Excel 中不亂碼）"""
    if not records:
        print("[提示] 無紀錄可匯出。")
        return
    
    # 按期別從小到大排序
    sorted_records = sorted(records, key=lambda x: x.get("period", 0))
    formatted_data = [parse_record(r) for r in sorted_records]
    
    fieldnames = list(formatted_data[0].keys())
    
    with open(output_filepath, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(formatted_data)
        
    print(f"[成功] 資料已儲存至: {os.path.abspath(output_filepath)} (共 {len(formatted_data)} 筆)")

def save_to_json(records: list, output_filepath: str):
    """將紀錄列表存為 JSON 格式"""
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

def download_super_lotto_range(start_year: int, end_year: int, output_csv: str = "super_lotto_history.csv"):
    """批量下載跨年份的威力彩開獎紀錄並合併儲存為 CSV"""
    all_records = []
    for y in range(start_year, end_year + 1):
        recs = fetch_super_lotto_by_year(y)
        all_records.extend(recs)
        time.sleep(0.5) # 友善請求間隔
    
    if all_records:
        save_to_csv(all_records, output_csv)
        json_path = output_csv.rsplit(".", 1)[0] + ".json"
        save_to_json(all_records, json_path)
    else:
        print("[警告] 未抓取到任何資料。")

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
                print(f"提示: 可執行 {status['install_cmd']} 啟用 Google OR-Tools CP-SAT 嚴謹數學求解器。")
            tickets_cnt = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 5
            res = generate_predictions("super_lotto_history.json", num_tickets=tickets_cnt)
            if res.get("status") == "success":
                summary = res["statistics_summary"]
                print(f"\n歷史特徵分析: {summary['total_draws']} 期 | 平均和值: {summary['avg_sum']}")
                print(f"第一區最熱門號碼: {summary['hot_numbers_zone1']}")
                print(f"第二區最熱門號碼: {summary['hot_numbers_zone2']}")
                print(f"\n【Google OR-Tools AI 智慧推薦注單 ({len(res['recommended_tickets'])} 注多樣性包牌)】")
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
