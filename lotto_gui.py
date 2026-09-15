# -*- coding: utf-8 -*-
"""
台灣彩券 - 威力彩全功能一體化大數據與 AI 運籌系統 (All-in-One Desktop GUI)
========================================================================
整合在單一現代桌面視窗內，提供：
1. 頂部即時開獎 Showcase（擬真 3D 光影彩球、派彩金額與銷售總額）
2. 🤖 AI 智慧運籌預測專區（0-1 整數規劃、自訂膽碼/殺號、和值、多注包牌多樣性）
3. 📋 各期歷史獎號資料庫清單（282+ 期完整紀錄、即時搜尋過濾、落球與大小排序）
4. 📊 號碼頻率與數據分析（熱門號/冷門號排行榜、遺漏值回補潛力、第二區分佈）
5. 一鍵線上同步更新、匯出 CSV / JSON、下載台彩官方年度封存 ZIP
"""

import sys
import os
import json
import csv
import threading
import time
import webbrowser
from datetime import datetime

from collections import Counter, defaultdict
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Windows 高解析度螢幕 (High DPI) 支援
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# 引入核心模組
try:
    from taiwan_lottery import (
        fetch_super_lotto_by_year,
        fetch_super_lotto_by_period,
        fetch_super_lotto_by_month,
        download_official_yearly_zip,
        download_super_lotto_range,
        fetch_lotto649_by_year,
        fetch_lotto649_by_period,
        fetch_lotto649_by_month,
        download_lotto649_range,
        parse_lotto649_record,
        save_to_csv,
        save_to_json
    )
except ImportError:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    from taiwan_lottery import (
        fetch_super_lotto_by_year,
        fetch_super_lotto_by_period,
        fetch_super_lotto_by_month,
        download_official_yearly_zip,
        download_super_lotto_range,
        fetch_lotto649_by_year,
        fetch_lotto649_by_period,
        fetch_lotto649_by_month,
        download_lotto649_range,
        parse_lotto649_record,
        save_to_csv,
        save_to_json
    )

# 引入 AI 運籌求解引擎 (延遲載入)
try:
    from lotto_ai_optimizer import (
        LottoAnalyzer,
        LottoAIOptimizer,
        check_ortools_status,
        generate_predictions
    )
except ImportError:
    LottoAnalyzer = None
    LottoAIOptimizer = None
    check_ortools_status = lambda: {"available": False, "engine": "啟發式約束優化器", "install_cmd": "pip install ortools"}
    generate_predictions = None

GAME_NAMES = {
    "super_lotto": "威力彩",
    "lotto649": "大樂透",
    "daily539": "今彩539",
    "lotto39m": "39樂合彩",
    "lotto49m": "49樂合彩",
    "3star": "3星彩",
    "4star": "4星彩",
    "bingo": "BINGO BINGO"
}

SUPER_LOTTO_CSV = "super_lotto_history.csv"
SUPER_LOTTO_JSON = "super_lotto_history.json"
LOTTO649_CSV = "lotto649_history.csv"
LOTTO649_JSON = "lotto649_history.json"

CSV_FILE = SUPER_LOTTO_CSV
JSON_FILE = SUPER_LOTTO_JSON

# 配色主題 (Modern Dark & Gold)
COLOR_BG = "#0f121a"
COLOR_CARD = "#171c28"
COLOR_HEADER = "#212838"
COLOR_CARD_HOVER = "#232b3d"
COLOR_TEXT = "#f3f4f6"
COLOR_MUTED = "#94a3b8"
COLOR_GOLD = "#f59e0b"
COLOR_GOLD_LIGHT = "#fef08a"
COLOR_RED = "#ef4444"
COLOR_RED_LIGHT = "#fca5a5"
COLOR_TEAL = "#10b981"
COLOR_BLUE = "#3b82f6"
COLOR_BORDER = "#2b3448"


def get_next_draw_info(game="super_lotto"):
    """計算下一期預計開獎日期與星期 (精確支援 8 大台灣彩券開獎時間表)"""
    from datetime import timedelta
    now = datetime.now()
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    cur_w = now.weekday()  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    draw_time_passed = (now.hour > 20) or (now.hour == 20 and now.minute >= 30)
    g = (game or "super_lotto").lower()

    if g in ["lotto649", "lotto49m", "649", "49m"]:
        # 大樂透 / 49樂合彩：每週二、五 20:30
        if cur_w == 1:   # Tue
            days_ahead = 0 if not draw_time_passed else 3
        elif cur_w == 2: # Wed
            days_ahead = 2
        elif cur_w == 3: # Thu
            days_ahead = 1
        elif cur_w == 4: # Fri
            days_ahead = 0 if not draw_time_passed else 4
        elif cur_w == 5: # Sat
            days_ahead = 3
        elif cur_w == 6: # Sun
            days_ahead = 2
        else:            # Mon (0)
            days_ahead = 1
        draw_rule = "每週二、五 20:30"
        target = now + timedelta(days=days_ahead)
        w_str = weekday_names[target.weekday()]
        return f"{target.strftime('%Y-%m-%d')} ({w_str}) 20:30 [{draw_rule}]"

    elif g in ["daily539", "lotto39m", "3star", "4star", "539", "39m", "3s", "4s"]:
        # 今彩539 / 39樂合彩 / 3星彩 / 4星彩：每週一至週六 20:30 (週日休)
        if cur_w == 6:   # Sun
            days_ahead = 1
        elif draw_time_passed:
            days_ahead = 2 if cur_w == 5 else 1
        else:
            days_ahead = 0
        draw_rule = "每週一~六 20:30"
        target = now + timedelta(days=days_ahead)
        w_str = weekday_names[target.weekday()]
        return f"{target.strftime('%Y-%m-%d')} ({w_str}) 20:30 [{draw_rule}]"

    elif g in ["bingo", "賓果"]:
        # BINGO BINGO 天天每 5 分鐘一期 (07:05 ~ 23:55)
        draw_rule = "天天 07:05~23:55 每5分鐘"
        mins = now.minute
        next_min = ((mins // 5) + 1) * 5
        if next_min >= 60:
            target = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            target = now.replace(minute=next_min, second=0, microsecond=0)
        
        if target.hour < 7 or (target.hour == 7 and target.minute < 5):
            target = target.replace(hour=7, minute=5)
        elif target.hour > 23 or (target.hour == 23 and target.minute > 55):
            target = (now + timedelta(days=1)).replace(hour=7, minute=5, second=0, microsecond=0)
            
        w_str = weekday_names[target.weekday()]
        return f"{target.strftime('%Y-%m-%d %H:%M')} ({w_str}) [{draw_rule}]"

    else:
        # 威力彩：每週一、四 20:30
        if cur_w == 0:   # Mon
            days_ahead = 0 if not draw_time_passed else 3
        elif cur_w == 1: # Tue
            days_ahead = 2
        elif cur_w == 2: # Wed
            days_ahead = 1
        elif cur_w == 3: # Thu
            days_ahead = 0 if not draw_time_passed else 4
        elif cur_w == 4: # Fri
            days_ahead = 3
        elif cur_w == 5: # Sat
            days_ahead = 2
        else:            # Sun
            days_ahead = 1
        draw_rule = "每週一、四 20:30"
        target = now + timedelta(days=days_ahead)
        w_str = weekday_names[target.weekday()]
        return f"{target.strftime('%Y-%m-%d')} ({w_str}) 20:30 [{draw_rule}]"


class LottoBall(tk.Canvas):
    """繪製具有立體光影質感的樂透號碼球"""
    def __init__(self, parent, number, is_special=False, size=44, bg=COLOR_CARD, **kwargs):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0)
        self.size = size
        self.number = number
        self.is_special = is_special
        self.ball_bg = bg
        self.draw_ball()

    def update_number(self, number, is_special=False):
        self.number = number
        self.is_special = is_special
        self.delete("all")
        self.draw_ball()

    def draw_ball(self):
        s = self.size
        if self.is_special:
            fill_base = "#dc2626"
            fill_highlight = "#fca5a5"
            border_color = "#991b1b"
        else:
            fill_base = "#d97706"
            fill_highlight = "#fef08a"
            border_color = "#b45309"

        # 外陰影
        self.create_oval(3, 4, s - 1, s, fill="#000000", outline="", stipple="gray50")
        # 主球體
        self.create_oval(2, 2, s - 2, s - 2, fill=fill_base, outline=border_color, width=1.5)
        # 高光光暈 (左上方光澤)
        highlight_size = s * 0.45
        self.create_oval(6, 4, 6 + highlight_size, 4 + highlight_size * 0.7, fill=fill_highlight, outline="")
        # 數字
        if str(self.number).isdigit():
            text_val = f"{int(self.number):02d}"
        else:
            text_val = str(self.number)
        font_size = int(s * 0.38)
        self.create_text(s / 2, s / 2 + 1, text=text_val, fill="#ffffff", font=("Segoe UI", font_size, "bold"))


class TaiwanLottoApp(tk.Tk):
    """威力彩全功能整合型主程式視窗"""
    def __init__(self):
        super().__init__()
        self.title("台灣彩券 · 威力彩大數據歷史系統與 AI 運籌預測系統")
        self.geometry("1280x920")
        self.minsize(1080, 760)
        self.configure(bg=COLOR_BG)

        # 設定 Windows 工作列與視窗標題列專屬 Icon
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TaiwanLottery.SuperAI.GUI.1.0")
            except Exception:
                pass

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        artifact_icon = r"C:\Users\USER\.gemini\antigravity-ide\brain\69a2e7a7-0a3c-4978-ae54-2cca864a7b35\lotto_icon_1789355314888.png"
        if not os.path.exists(icon_path) and os.path.exists(artifact_icon):
            try:
                import shutil
                shutil.copy(artifact_icon, icon_path)
                web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
                shutil.copy(artifact_icon, os.path.join(web_dir, "icon.png"))
                shutil.copy(artifact_icon, os.path.join(web_dir, "favicon.ico"))
            except Exception:
                pass

        if os.path.exists(icon_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(icon_path)
                self.icon_img = ImageTk.PhotoImage(img)
                self.iconphoto(True, self.icon_img)
            except Exception:
                try:
                    self.icon_img = tk.PhotoImage(file=icon_path)
                    self.iconphoto(True, self.icon_img)
                except Exception as e:
                    print("載入 Icon 失敗:", e)




        # 狀態資料
        self.current_game = "super_lotto"
        self.records = []
        self.filtered_records = []
        self.analyzer = None
        self.ai_tickets = []
        self.is_downloading = False
        self.is_solving = False

        self.setup_styles()
        self.create_widgets()
        self.load_initial_data()

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # 通用設定
        style.configure(".", background=COLOR_BG, foreground=COLOR_TEXT, font=("Microsoft JhengHei UI", 10))
        style.configure("TFrame", background=COLOR_BG)
        style.configure("Card.TFrame", background=COLOR_CARD, relief="flat")

        # 頁籤 Notebook 風格
        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=COLOR_HEADER, foreground=COLOR_TEXT, padding=(18, 9), font=("Microsoft JhengHei UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_CARD), ("active", "#2d3748")],
                  foreground=[("selected", COLOR_GOLD), ("active", "#ffffff")])

        # 按鈕風格
        style.configure("Primary.TButton", background=COLOR_GOLD, foreground="#000000", font=("Microsoft JhengHei UI", 10, "bold"), padding=(12, 6))
        style.map("Primary.TButton", background=[("active", COLOR_GOLD_LIGHT), ("disabled", "#475569")])

        style.configure("Secondary.TButton", background=COLOR_HEADER, foreground=COLOR_TEXT, font=("Microsoft JhengHei UI", 10), padding=(10, 5))
        style.map("Secondary.TButton", background=[("active", "#334155")])

        style.configure("Success.TButton", background=COLOR_TEAL, foreground="#ffffff", font=("Microsoft JhengHei UI", 10, "bold"), padding=(10, 5))
        style.map("Success.TButton", background=[("active", "#34d399")])

        # 下拉選單與輸入框
        style.configure("TCombobox", fieldbackground=COLOR_HEADER, background=COLOR_HEADER, foreground=COLOR_TEXT, arrowcolor=COLOR_TEXT, padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", COLOR_HEADER)], selectbackground=[("readonly", COLOR_HEADER)], selectforeground=[("readonly", COLOR_TEXT)])
        style.configure("TEntry", fieldbackground=COLOR_HEADER, foreground=COLOR_TEXT, padding=5)

        # 表格 (Treeview)
        style.configure("Treeview", background=COLOR_CARD, foreground=COLOR_TEXT, fieldbackground=COLOR_CARD, rowheight=32, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=COLOR_HEADER, foreground=COLOR_GOLD, font=("Microsoft JhengHei UI", 10, "bold"), padding=6)
        style.map("Treeview", background=[("selected", "#2563eb")], foreground=[("selected", "#ffffff")])
        style.map("Treeview.Heading", background=[("active", "#374151")])

    def create_widgets(self):
        # 1. 頂部導覽列 (標題、操作按鈕、求解引擎狀態)
        self.create_top_bar()

        # 2. 開獎精選 Showcase (最新或點選期別之 3D 彩球看板)
        self.create_showcase()

        # 3. 核心功能頁籤 (整合在同一個視窗中，不彈出子視窗)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(side="top", fill="both", expand=True, padx=16, pady=(4, 12))

        # 頁籤 1: 🤖 AI 智慧運籌預測
        self.tab_ai = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.tab_ai, text="  🤖 AI 智慧運籌預測  ")
        self.build_ai_tab()

        # 頁籤 2: 📋 各期歷史獎號清單與查詢
        self.tab_table = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.tab_table, text="  📋 各期歷史獎號清單與篩選  ")
        self.build_table_tab()

        # 頁籤 3: 📊 號碼頻率與數據分析
        self.tab_stats = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.tab_stats, text="  📊 號碼開出頻率與特徵工程速報  ")
        self.build_stats_tab()

    def create_top_bar(self):
        top_bar = tk.Frame(self, bg=COLOR_HEADER, padx=16, pady=6)
        top_bar.pack(side="top", fill="x")

        # 標題
        title_box = tk.Frame(top_bar, bg=COLOR_HEADER)
        title_box.pack(side="left", padx=(0, 12))
        self.lbl_main_title = tk.Label(title_box, text="🎱 台灣彩券 · 威力彩大數據與 AI 運籌系統", font=("Microsoft JhengHei UI", 13, "bold"), bg=COLOR_HEADER, fg=COLOR_GOLD)
        self.lbl_main_title.pack(anchor="w")

        # 8 大彩種切換選單
        self.game_options = [
            ("super_lotto", "🎱 威力彩 (6/38)"),
            ("lotto649",    "💎 大樂透 (6/49)"),
            ("daily539",    "🎯 今彩539 (5/39)"),
            ("lotto39m",    "🔢 39樂合彩"),
            ("lotto49m",    "🔢 49樂合彩"),
            ("3star",       "⭐ 3星彩 (000~999)"),
            ("4star",       "🌟 4星彩 (0000~9999)"),
            ("bingo",       "🎰 BINGO BINGO"),
        ]
        self.combo_game = ttk.Combobox(top_bar, values=[title for _, title in self.game_options], width=20, state="readonly")
        self.combo_game.current(0)
        self.combo_game.pack(side="left", padx=(0, 14))
        self.combo_game.bind("<<ComboboxSelected>>", self.on_game_selected)

        # 年份選單與同步按鈕
        cur_year = datetime.now().year
        year_options = ["全期別 (2024~至今)"] + [str(y) for y in range(cur_year, 2023, -1)]
        self.year_combo = ttk.Combobox(top_bar, values=year_options, width=15, state="readonly")
        self.year_combo.current(0)
        self.year_combo.pack(side="left", padx=(0, 6))

        self.btn_fetch = ttk.Button(top_bar, text="🔄 同步最新獎號", style="Primary.TButton", command=self.on_start_download)
        self.btn_fetch.pack(side="left", padx=(0, 6))

        self.btn_web = ttk.Button(top_bar, text="🌐 開啟 Web 儀表板", style="Success.TButton", command=self.open_web_dashboard)
        self.btn_web.pack(side="left", padx=(0, 6))

        self.btn_csv = ttk.Button(top_bar, text="📊 匯出 CSV", style="Secondary.TButton", command=self.export_csv)
        self.btn_csv.pack(side="left", padx=(0, 6))

        self.btn_json = ttk.Button(top_bar, text="📄 匯出 JSON", style="Secondary.TButton", command=self.export_json)
        self.btn_json.pack(side="left", padx=(0, 6))

        self.btn_zip = ttk.Button(top_bar, text="📦 官方歷年 ZIP", style="Secondary.TButton", command=self.prompt_download_zip)
        self.btn_zip.pack(side="left")


        # 右側：求解引擎狀態指示徽章
        ortools_status = check_ortools_status() if check_ortools_status else {"available": False}
        if ortools_status.get("available"):
            engine_text = "🟢 AI 運籌 CP-SAT 啟用 (0-1 混合整數規劃)"
            badge_fg = COLOR_TEAL
        else:
            engine_text = "🟡 啟發式約束優化器 (建議: pip install ortools)"
            badge_fg = COLOR_GOLD

        self.lbl_engine_badge = tk.Label(top_bar, text=engine_text, font=("Segoe UI", 9, "bold"), bg=COLOR_CARD, fg=badge_fg, padx=10, pady=4, relief="groove")
        self.lbl_engine_badge.pack(side="right")

    def create_showcase(self):
        """頂部精選開獎 Showcase 看板"""
        self.showcase_frame = tk.Frame(self, bg=COLOR_CARD, padx=16, pady=6, highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.showcase_frame.pack(side="top", fill="x", padx=16, pady=(6, 2))


        # 左側：期別與日期
        self.info_left = tk.Frame(self.showcase_frame, bg=COLOR_CARD)
        self.info_left.pack(side="left", padx=(0, 25))

        self.lbl_selected_period = tk.Label(self.info_left, text="期別: 載入中...", font=("Segoe UI", 15, "bold"), bg=COLOR_CARD, fg=COLOR_GOLD)
        self.lbl_selected_period.pack(anchor="w")

        self.lbl_selected_date = tk.Label(self.info_left, text="開獎日期: --", font=("Microsoft JhengHei UI", 9), bg=COLOR_CARD, fg=COLOR_MUTED)
        self.lbl_selected_date.pack(anchor="w")

        self.lbl_next_draw = tk.Label(self.info_left, text=f"📅 下期預計開獎: {get_next_draw_info()}", font=("Microsoft JhengHei UI", 10, "bold"), bg=COLOR_CARD, fg=COLOR_TEAL)
        self.lbl_next_draw.pack(anchor="w", pady=(3, 0))

        # 中間：3D 彩球排
        self.balls_container = tk.Frame(self.showcase_frame, bg=COLOR_CARD)
        self.balls_container.pack(side="left", fill="y", padx=10)

        self.balls_row = tk.Frame(self.balls_container, bg=COLOR_CARD)
        self.balls_row.pack(anchor="w")

        self.ball_widgets = []
        for i in range(6):
            ball = LottoBall(self.balls_row, number="--", is_special=False, size=42, bg=COLOR_CARD)
            ball.pack(side="left", padx=3)
            self.ball_widgets.append(ball)

        self.sep_lbl = tk.Label(self.balls_row, text="+", font=("Segoe UI", 18, "bold"), bg=COLOR_CARD, fg=COLOR_MUTED)
        self.sep_lbl.pack(side="left", padx=5)

        self.special_ball = LottoBall(self.balls_row, number="--", is_special=True, size=42, bg=COLOR_CARD)
        self.special_ball.pack(side="left", padx=3)

        # 右側：頭獎派彩與銷售資訊
        self.info_right = tk.Frame(self.showcase_frame, bg=COLOR_CARD)
        self.info_right.pack(side="right")

        self.lbl_jackpot_val = tk.Label(self.info_right, text="頭獎: --", font=("Microsoft JhengHei UI", 11, "bold"), bg=COLOR_CARD, fg=COLOR_RED_LIGHT)
        self.lbl_jackpot_val.pack(anchor="e")

        self.lbl_sales_val = tk.Label(self.info_right, text="銷售總額: -- 元", font=("Microsoft JhengHei UI", 9), bg=COLOR_CARD, fg=COLOR_MUTED)
        self.lbl_sales_val.pack(anchor="e")

    # ==========================================
    # 頁籤 1: 🤖 AI 智慧運籌預測佈局
    # ==========================================
    def build_ai_tab(self):
        ai_main = tk.Frame(self.tab_ai, bg=COLOR_BG, padx=8, pady=8)
        ai_main.pack(fill="both", expand=True)

        # 左側面板：運籌約束控制 (寬度 340px)
        left_ctrl = tk.Frame(ai_main, bg=COLOR_CARD, width=340, padx=16, pady=16, highlightbackground=COLOR_BORDER, highlightthickness=1)
        left_ctrl.pack(side="left", fill="y", padx=(0, 12))
        left_ctrl.pack_propagate(False)

        tk.Label(left_ctrl, text="⚙️ 運籌約束條件 (Constraints)", font=("Microsoft JhengHei UI", 12, "bold"), bg=COLOR_CARD, fg=COLOR_GOLD).pack(anchor="w", pady=(0, 10))

        # 注數選擇
        tk.Label(left_ctrl, text="推薦注數 (Portfolio Size):", font=("Microsoft JhengHei UI", 9, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT).pack(anchor="w")
        self.combo_ai_count = ttk.Combobox(left_ctrl, values=["1 注 (單注精準)", "3 注 (小資組合)", "5 注 (包牌推薦)", "8 注 (廣域覆蓋)", "10 注 (全包最佳化)"], state="readonly")
        self.combo_ai_count.current(2)  # 預設 5 注
        self.combo_ai_count.pack(fill="x", pady=(3, 8))

        # 必出膽碼
        self.lbl_ai_locked = tk.Label(left_ctrl, text="📌 必選膽碼 (第一區，以逗號分隔，最多5個):", font=("Microsoft JhengHei UI", 9), bg=COLOR_CARD, fg=COLOR_TEXT)
        self.lbl_ai_locked.pack(anchor="w")
        self.entry_ai_locked = ttk.Entry(left_ctrl)
        self.entry_ai_locked.pack(fill="x", pady=(3, 8))

        # 排除殺號
        self.lbl_ai_excluded = tk.Label(left_ctrl, text="❌ 排除殺號 (第一區，以逗號分隔):", font=("Microsoft JhengHei UI", 9), bg=COLOR_CARD, fg=COLOR_TEXT)
        self.lbl_ai_excluded.pack(anchor="w")
        self.entry_ai_excluded = ttk.Entry(left_ctrl)
        self.entry_ai_excluded.pack(fill="x", pady=(3, 8))

        # 第二區指定特別號
        self.lbl_ai_z2 = tk.Label(left_ctrl, text="🔴 第二區特別號指定:", font=("Microsoft JhengHei UI", 9), bg=COLOR_CARD, fg=COLOR_TEXT)
        self.lbl_ai_z2.pack(anchor="w")
        z2_opts = ["隨機/AI最佳化推薦"] + [f"{i:02d}" for i in range(1, 9)]
        self.combo_ai_z2 = ttk.Combobox(left_ctrl, values=z2_opts, state="readonly")
        self.combo_ai_z2.current(0)
        self.combo_ai_z2.pack(fill="x", pady=(3, 8))

        # 和值範圍
        self.lbl_ai_sum = tk.Label(left_ctrl, text="和值區間限制 (建議 85 ~ 155):", font=("Microsoft JhengHei UI", 9), bg=COLOR_CARD, fg=COLOR_TEXT)
        self.lbl_ai_sum.pack(anchor="w")
        sum_row = tk.Frame(left_ctrl, bg=COLOR_CARD)
        sum_row.pack(fill="x", pady=(3, 8))
        self.entry_ai_sum_min = ttk.Entry(sum_row, width=8)
        self.entry_ai_sum_min.insert(0, "85")
        self.entry_ai_sum_min.pack(side="left")
        tk.Label(sum_row, text=" ~ ", bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="left")
        self.entry_ai_sum_max = ttk.Entry(sum_row, width=8)
        self.entry_ai_sum_max.insert(0, "155")
        self.entry_ai_sum_max.pack(side="left")

        # 多注包牌互斥覆蓋
        self.var_ai_diversity = tk.BooleanVar(value=True)
        chk_div = tk.Checkbutton(left_ctrl, text="啟用包牌多樣性互斥 (注間重疊 ≤ 3 球)", variable=self.var_ai_diversity, bg=COLOR_CARD, fg=COLOR_TEXT, selectcolor=COLOR_HEADER, activebackground=COLOR_CARD, activeforeground=COLOR_TEXT)
        chk_div.pack(anchor="w", pady=(2, 12))

        # 啟動求解按鈕
        self.btn_ai_solve = ttk.Button(left_ctrl, text="⚡ 啟動 AI 運籌最佳化求解", style="Primary.TButton", command=self.on_start_solve)
        self.btn_ai_solve.pack(fill="x", ipady=4, pady=(0, 10))

        # 特徵工程速報卡片
        self.stats_mini_card = tk.Frame(left_ctrl, bg=COLOR_HEADER, padx=10, pady=10, relief="groove")
        self.stats_mini_card.pack(fill="x", side="bottom")

        tk.Label(self.stats_mini_card, text="📊 歷史特徵工程速報", font=("Microsoft JhengHei UI", 9, "bold"), bg=COLOR_HEADER, fg=COLOR_GOLD).pack(anchor="w")
        self.lbl_stats_mini = tk.Label(self.stats_mini_card, text="載入歷史開獎數據中...", font=("Microsoft JhengHei UI", 8), bg=COLOR_HEADER, fg=COLOR_MUTED, justify="left")
        self.lbl_stats_mini.pack(anchor="w", pady=(4, 0))

        # 右側面板：AI 推薦注單結果列表 (可滾動)
        right_results = tk.Frame(ai_main, bg=COLOR_BG)
        right_results.pack(side="left", fill="both", expand=True)

        results_header = tk.Frame(right_results, bg=COLOR_BG)
        results_header.pack(side="top", fill="x", pady=(0, 6))

        self.lbl_ai_results_status = tk.Label(results_header, text="🎯 運籌推薦注單清單", font=("Microsoft JhengHei UI", 12, "bold"), bg=COLOR_BG, fg=COLOR_TEXT)
        self.lbl_ai_results_status.pack(side="left")

        self.btn_ai_copy_all = ttk.Button(results_header, text="📋 複製全部注單", style="Secondary.TButton", command=self.copy_all_ai_tickets)
        self.btn_ai_copy_all.pack(side="right")

        # 滾動 Canvas
        canvas_frame = tk.Frame(right_results, bg=COLOR_BG)
        canvas_frame.pack(side="top", fill="both", expand=True)

        self.ai_canvas = tk.Canvas(canvas_frame, bg=COLOR_BG, highlightthickness=0)
        self.ai_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.ai_canvas.yview)
        self.ai_scrollable_frame = tk.Frame(self.ai_canvas, bg=COLOR_BG)

        self.ai_scrollable_frame.bind("<Configure>", lambda e: self.ai_canvas.configure(scrollregion=self.ai_canvas.bbox("all")))
        self.ai_canvas_window = self.ai_canvas.create_window((0, 0), window=self.ai_scrollable_frame, anchor="nw")
        self.ai_canvas.configure(yscrollcommand=self.ai_scrollbar.set)
        self.ai_canvas.bind('<Configure>', lambda e: self.ai_canvas.itemconfig(self.ai_canvas_window, width=e.width))

        # 滑鼠滾輪支援 (當滑鼠指針移入 Canvas 時開啟滾輪)
        def _on_ai_mousewheel(event):
            self.ai_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.ai_canvas.bind("<Enter>", lambda e: self.ai_canvas.bind_all("<MouseWheel>", _on_ai_mousewheel))
        self.ai_canvas.bind("<Leave>", lambda e: self.ai_canvas.unbind_all("<MouseWheel>"))

        self.ai_canvas.pack(side="left", fill="both", expand=True)
        self.ai_scrollbar.pack(side="right", fill="y")


    # ==========================================
    # 頁籤 2: 📋 各期歷史獎號資料庫清單佈局
    # ==========================================
    def build_table_tab(self):
        # 搜尋篩選列
        filter_bar = tk.Frame(self.tab_table, bg=COLOR_BG, padx=4, pady=8)
        filter_bar.pack(side="top", fill="x")

        tk.Label(filter_bar, text="🔍 搜尋篩選 (期別/日期/球號):", bg=COLOR_BG, fg=COLOR_TEXT).pack(side="left", padx=(0, 6))
        self.search_entry = ttk.Entry(filter_bar, width=24)
        self.search_entry.pack(side="left", padx=(0, 15))
        self.search_entry.bind("<KeyRelease>", lambda e: self.apply_filter())

        self.lbl_stats_summary = tk.Label(filter_bar, text="統計：共 0 期", font=("Microsoft JhengHei UI", 10), bg=COLOR_BG, fg=COLOR_GOLD)
        self.lbl_stats_summary.pack(side="right")

        # 下載進度條 (預設隱藏)
        self.progress_frame = tk.Frame(self.tab_table, bg=COLOR_BG, padx=4)
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="indeterminate", length=240)
        self.progress_bar.pack(side="left", padx=(0, 10))
        self.lbl_status = tk.Label(self.progress_frame, text="", bg=COLOR_BG, fg=COLOR_GOLD)
        self.lbl_status.pack(side="left")

        # 資料表格 Treeview
        table_frame = tk.Frame(self.tab_table, bg=COLOR_BG, padx=4, pady=4)
        table_frame.pack(side="top", fill="both", expand=True)

        columns = ("period", "date", "draw_appear", "draw_size", "zone2", "jackpot_winners", "jackpot_prize", "sales")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("period", text="開獎期別", command=lambda: self.sort_treeview("period", False))
        self.tree.heading("date", text="開獎日期", command=lambda: self.sort_treeview("date", False))
        self.tree.heading("draw_appear", text="第一區 (落球順序)")
        self.tree.heading("draw_size", text="第一區 (大小順序)")
        self.tree.heading("zone2", text="第二區")
        self.tree.heading("jackpot_winners", text="頭獎注數")
        self.tree.heading("jackpot_prize", text="頭獎單注獎金 (元)")
        self.tree.heading("sales", text="銷售總金額 (元)")

        self.tree.column("period", width=105, anchor="center")
        self.tree.column("date", width=110, anchor="center")
        self.tree.column("draw_appear", width=190, anchor="center")
        self.tree.column("draw_size", width=190, anchor="center")
        self.tree.column("zone2", width=75, anchor="center")
        self.tree.column("jackpot_winners", width=85, anchor="center")
        self.tree.column("jackpot_prize", width=160, anchor="e")
        self.tree.column("sales", width=140, anchor="e")

        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll_y.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    # ==========================================
    # 頁籤 3: 📊 號碼開出頻率與特徵分析佈局
    # ==========================================
    def build_stats_tab(self):
        stats_main = tk.Frame(self.tab_stats, bg=COLOR_BG, padx=8, pady=8)
        stats_main.pack(fill="both", expand=True)

        # 頂部 4 大 KPI 卡片
        kpi_row = tk.Frame(stats_main, bg=COLOR_BG)
        kpi_row.pack(fill="x", pady=(0, 10))

        self.kpi_cards = {}
        kpi_defs = [
            ("total_draws", "資料庫總期數", "0 期", COLOR_TEXT),
            ("jackpot_wins", "累計頭獎開出注數", "0 注", COLOR_TEAL),
            ("max_jackpot", "最高單注頭獎金額", "$0 元", COLOR_RED_LIGHT),
            ("top_hot", "第一區最熱門球號 Top 1", "--", COLOR_GOLD)
        ]

        for key, title, default_val, fg_color in kpi_defs:
            card = tk.Frame(kpi_row, bg=COLOR_CARD, padx=14, pady=10, highlightbackground=COLOR_BORDER, highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=4)
            lbl_t = tk.Label(card, text=title, font=("Microsoft JhengHei UI", 9), bg=COLOR_CARD, fg=COLOR_MUTED)
            lbl_t.pack(anchor="w")
            lbl_val = tk.Label(card, text=default_val, font=("Outfit", 15, "bold"), bg=COLOR_CARD, fg=fg_color)
            lbl_val.pack(anchor="w", pady=(2, 0))
            self.kpi_cards[key] = lbl_val
            self.kpi_cards[key + "_title"] = lbl_t

        # 下方左右分割：左側第 1 區球號頻率，右側特別號頻率與常態指標
        tables_row = tk.Frame(stats_main, bg=COLOR_BG)
        tables_row.pack(fill="both", expand=True)

        # 左側：第一區號碼開出頻率排行榜
        left_frame = tk.Frame(tables_row, bg=COLOR_CARD, padx=12, pady=10, highlightbackground=COLOR_BORDER, highlightthickness=1)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.lbl_z1_stats_title = tk.Label(left_frame, text="🔥 第一區 38 顆球號歷史開出頻率與遺漏值排行", font=("Microsoft JhengHei UI", 10, "bold"), bg=COLOR_CARD, fg=COLOR_GOLD)
        self.lbl_z1_stats_title.pack(anchor="w", pady=(0, 6))

        cols_z1 = ("rank", "ball", "count", "omission", "rate", "status")
        self.tree_z1_stats = ttk.Treeview(left_frame, columns=cols_z1, show="headings", height=12)
        self.tree_z1_stats.heading("rank", text="排名")
        self.tree_z1_stats.heading("ball", text="號碼")
        self.tree_z1_stats.heading("count", text="開出次數")
        self.tree_z1_stats.heading("omission", text="當前遺漏期數")
        self.tree_z1_stats.heading("rate", text="出現頻率 (%)")
        self.tree_z1_stats.heading("status", text="冷熱指標")

        self.tree_z1_stats.column("rank", width=55, anchor="center")
        self.tree_z1_stats.column("ball", width=65, anchor="center")
        self.tree_z1_stats.column("count", width=80, anchor="center")
        self.tree_z1_stats.column("omission", width=95, anchor="center")
        self.tree_z1_stats.column("rate", width=90, anchor="center")
        self.tree_z1_stats.column("status", width=90, anchor="center")

        scroll_z1 = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree_z1_stats.yview)
        self.tree_z1_stats.configure(yscrollcommand=scroll_z1.set)
        self.tree_z1_stats.pack(side="left", fill="both", expand=True)
        scroll_z1.pack(side="right", fill="y")

        # 右側：特別號頻率 + 常態和值
        right_frame = tk.Frame(tables_row, bg=COLOR_CARD, padx=12, pady=10, highlightbackground=COLOR_BORDER, highlightthickness=1)
        right_frame.pack(side="left", fill="both", expand=True, padx=(6, 0))

        self.lbl_z2_stats_title = tk.Label(right_frame, text="🔴 第二區 1~8 號特別號頻率與常態分佈", font=("Microsoft JhengHei UI", 10, "bold"), bg=COLOR_CARD, fg=COLOR_RED_LIGHT)
        self.lbl_z2_stats_title.pack(anchor="w", pady=(0, 6))

        cols_z2 = ("ball", "count", "rate", "omission")
        self.tree_z2_stats = ttk.Treeview(right_frame, columns=cols_z2, show="headings", height=8)
        self.tree_z2_stats.heading("ball", text="特別號")
        self.tree_z2_stats.heading("count", text="開出次數")
        self.tree_z2_stats.heading("rate", text="出現頻率 (%)")
        self.tree_z2_stats.heading("omission", text="當前遺漏期數")

        self.tree_z2_stats.column("ball", width=80, anchor="center")
        self.tree_z2_stats.column("count", width=90, anchor="center")
        self.tree_z2_stats.column("rate", width=100, anchor="center")
        self.tree_z2_stats.column("omission", width=100, anchor="center")

        self.tree_z2_stats.pack(fill="x", pady=(0, 10))

        # 常態指標資訊文字
        self.lbl_norm_stats = tk.Label(right_frame, text="計算常態特徵中...", font=("Microsoft JhengHei UI", 9), bg=COLOR_HEADER, fg=COLOR_TEXT, justify="left", padx=10, pady=8, relief="groove")
        self.lbl_norm_stats.pack(fill="both", expand=True)

    # ==========================================
    # 資料讀取與刷新機制
    # ==========================================
    def get_game_paths(self):
        if self.current_game == "lotto649":
            return LOTTO649_JSON, LOTTO649_CSV
        return SUPER_LOTTO_JSON, SUPER_LOTTO_CSV

    def switch_game(self, game_type):
        if self.is_downloading or self.is_solving:
            return
        self.current_game = game_type
        is_649 = (game_type == "lotto649")

        # 更新切換按鈕樣式
        if is_649:
            self.btn_game_super.config(bg=COLOR_CARD, fg=COLOR_MUTED)
            self.btn_game_649.config(bg=COLOR_GOLD, fg="#000000")
            self.title("台灣彩券 · 大樂透大數據歷史系統與 AI 運籌預測系統")
            self.lbl_main_title.config(text="💎 台灣彩券 · 大樂透大數據與 AI 運籌系統")
            self.tree.heading("draw_appear", text="獎號 (落球順序)")
            self.tree.heading("draw_size", text="獎號 (大小順序)")
            self.tree.heading("zone2", text="特別號")
            self.lbl_ai_locked.config(text="📌 必選膽碼 (1~49，以逗號分隔，最多5個):")
            self.lbl_ai_excluded.config(text="❌ 排除殺號 (1~49，以逗號分隔):")
            self.lbl_ai_z2.config(text="🔴 特別號指定 (1~49):")
            self.lbl_ai_sum.config(text="和值區間限制 (建議 115 ~ 185):")
            z2_opts = ["隨機/AI最佳化推薦"] + [f"{i:02d}" for i in range(1, 50)]
            self.combo_ai_z2.config(values=z2_opts)
            self.combo_ai_z2.current(0)
            self.entry_ai_sum_min.delete(0, "end")
            self.entry_ai_sum_min.insert(0, "115")
            self.entry_ai_sum_max.delete(0, "end")
            self.entry_ai_sum_max.insert(0, "185")
            self.lbl_z1_stats_title.config(text="🔥 49 顆獎號歷史開出頻率與遺漏值排行")
            self.lbl_z2_stats_title.config(text="🔴 特別號 1~49 號頻率與常態分佈")
            self.kpi_cards["top_hot_title"].config(text="最熱門球號 Top 1")
        else:
            self.btn_game_super.config(bg=COLOR_GOLD, fg="#000000")
            self.btn_game_649.config(bg=COLOR_CARD, fg=COLOR_MUTED)
            self.title("台灣彩券 · 威力彩大數據歷史系統與 AI 運籌預測系統")
            self.lbl_main_title.config(text="🎱 台灣彩券 · 威力彩大數據與 AI 運籌系統")
            self.tree.heading("draw_appear", text="第一區 (落球順序)")
            self.tree.heading("draw_size", text="第一區 (大小順序)")
            self.tree.heading("zone2", text="第二區")
            self.lbl_ai_locked.config(text="📌 必選膽碼 (第一區 1~38，以逗號分隔，最多5個):")
            self.lbl_ai_excluded.config(text="❌ 排除殺號 (第一區 1~38，以逗號分隔):")
            self.lbl_ai_z2.config(text="🔴 第二區特別號指定 (1~8):")
            self.lbl_ai_sum.config(text="和值區間限制 (建議 85 ~ 155):")
            z2_opts = ["隨機/AI最佳化推薦"] + [f"{i:02d}" for i in range(1, 9)]
            self.combo_ai_z2.config(values=z2_opts)
            self.combo_ai_z2.current(0)
            self.entry_ai_sum_min.delete(0, "end")
            self.entry_ai_sum_min.insert(0, "85")
            self.entry_ai_sum_max.delete(0, "end")
            self.entry_ai_sum_max.insert(0, "155")
            self.lbl_z1_stats_title.config(text="🔥 第一區 38 顆球號歷史開出頻率與遺漏值排行")
            self.lbl_z2_stats_title.config(text="🔴 第二區 1~8 號特別號頻率與常態分佈")
            self.kpi_cards["top_hot_title"].config(text="第一區最熱門球號 Top 1")

        self.load_game_data()

    def load_initial_data(self):
        self.load_game_data()

    def load_game_data(self):
        """依當前選定彩種載入本地 JSON 快取或觸發下載"""
        json_file, _ = self.get_game_paths()
        if os.path.exists(json_file):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
                if self.records:
                    self.refresh_all_views()
                    # 初始自動為使用者運算推薦注單
                    self.after(300, self.on_start_solve)
                    return
            except Exception as e:
                print(f"載入 {self.current_game} 本地歷史資料失敗:", e)

        # 若無快取則自動背景下載
        self.on_start_download()

    def refresh_all_views(self):
        """一次刷新三大分頁與 Showcase 看板"""
        self.refresh_table()
        self.refresh_statistics_tab()

    def refresh_table(self):
        self.filtered_records = list(self.records)
        self.apply_filter()
        if self.records:
            latest = sorted(self.records, key=lambda x: x.get("period", 0), reverse=True)[0]
            self.display_showcase(latest)

    def display_showcase(self, item):
        period = item.get("period", "--")
        raw_date = item.get("lotteryDate", "")
        date_str = raw_date.split("T")[0] if "T" in raw_date else raw_date

        game_title = next((title for code, title in self.game_options if code == self.current_game), self.current_game)
        self.lbl_selected_period.config(text=f"第 {period} 期 ({game_title})")
        self.lbl_selected_date.config(text=f"開獎日: {date_str}")
        self.lbl_next_draw.config(text=f"📅 下期預計開獎: {get_next_draw_info(self.current_game)}")

        draw_appear = item.get("drawNumberAppear", [])
        has_zone2 = (self.current_game in ["super_lotto", "lotto649"])
        num_main_balls = 3 if self.current_game == "3star" else (4 if self.current_game == "4star" else (5 if self.current_game in ["daily539", "lotto39m"] else 6))

        for i in range(6):
            if i < num_main_balls and i < len(draw_appear):
                val_str = str(draw_appear[i])
                if val_str.isdigit() and self.current_game not in ["3star", "4star"]:
                    val_str = f"{int(val_str):02d}"
                self.ball_widgets[i].pack(side="left", padx=3)
                self.ball_widgets[i].update_number(val_str, is_special=False)
            else:
                self.ball_widgets[i].pack_forget()

        if has_zone2:
            self.sep_lbl.pack(side="left", padx=5)
            self.special_ball.pack(side="left", padx=3)
            special_num = draw_appear[6] if len(draw_appear) >= 7 else "--"
            if str(special_num).isdigit() and self.current_game not in ["3star", "4star"]:
                special_num = f"{int(special_num):02d}"
            self.special_ball.update_number(special_num, is_special=True)
        else:
            self.sep_lbl.pack_forget()
            self.special_ball.pack_forget()

        jackpot = item.get("super638JackpotAssign") or item.get("jackpotAssign") or item.get("daily539JackpotAssign") or {}
        winners = jackpot.get("winnerCount", 0)
        prize = jackpot.get("perPrize", 0)
        sales = item.get("sellAmount", 0)

        if winners > 0:
            jackpot_txt = f"頭獎 {winners} 注：各得 ${prize:,} 元"
        else:
            jackpot_txt = "頭獎槓龜 (無人中獎)"

        self.lbl_jackpot_val.config(text=jackpot_txt)
        self.lbl_sales_val.config(text=f"銷售金額: ${sales:,} 元")

    def on_game_selected(self, event=None):
        idx = self.combo_game.current()
        if 0 <= idx < len(self.game_options):
            game_code = self.game_options[idx][0]
            self.switch_game(game_code)

    def switch_game(self, game_code):
        self.current_game = game_code
        game_title = GAME_NAMES.get(game_code, game_code)
        self.lbl_main_title.config(text=f"🎱 台灣彩券 · {game_title}大數據與 AI 運籌系統")
        self.update_ai_controls_for_game()
        self.load_initial_data()

    def update_ai_controls_for_game(self):
        has_zone2 = (self.current_game in ["super_lotto", "lotto649"])
        if has_zone2:
            self.lbl_ai_z2.config(text="🔴 第二區特別號指定:" if self.current_game == "super_lotto" else "🔴 特別號指定:")
            self.combo_ai_z2.config(state="readonly")
        else:
            self.lbl_ai_z2.config(text="🔴 第二區特別號指定: (本彩種無特別號)")
            self.combo_ai_z2.config(state="disabled")

        if self.current_game == "lotto649":
            sum_min, sum_max = 115, 185
        elif self.current_game in ["3star", "4star"]:
            sum_min, sum_max = (0, 27) if self.current_game == "3star" else (0, 36)
        elif self.current_game in ["daily539", "lotto39m"]:
            sum_min, sum_max = 60, 140
        else:
            sum_min, sum_max = 85, 155

        self.lbl_ai_sum.config(text=f"和值區間限制 (建議 {sum_min} ~ {sum_max}):")
        self.entry_ai_sum_min.delete(0, tk.END)
        self.entry_ai_sum_min.insert(0, str(sum_min))
        self.entry_ai_sum_max.delete(0, tk.END)
        self.entry_ai_sum_max.insert(0, str(sum_max))

    def get_game_paths(self):
        g = self.current_game
        return f"{g}_history.json", f"{g}_history.csv"

    def apply_filter(self):
        keyword = self.search_entry.get().strip().lower()
        self.tree.delete(*self.tree.get_children())

        sorted_list = sorted(self.records, key=lambda x: x.get("period", 0), reverse=True)
        count = 0

        for r in sorted_list:
            period = str(r.get("period", ""))
            raw_date = r.get("lotteryDate", "")
            date_str = raw_date.split("T")[0] if "T" in raw_date else raw_date

            appear_nums = r.get("drawNumberAppear", [])
            size_nums = r.get("drawNumberSize", []) or appear_nums

            if self.current_game in ["3star", "4star"]:
                z1_appear = " ".join(str(n) for n in appear_nums)
                z1_size = z1_appear
                z2 = ""
            else:
                z1_appear = " ".join(f"{int(n):02d}" for n in appear_nums[:6]) if len(appear_nums) >= 1 else ""
                z1_size = " ".join(f"{int(n):02d}" for n in size_nums[:6]) if len(size_nums) >= 1 else ""
                z2 = f"{int(size_nums[6]):02d}" if len(size_nums) >= 7 and str(size_nums[6]).isdigit() else ""

            jackpot = r.get("super638JackpotAssign") or r.get("jackpotAssign") or r.get("daily539JackpotAssign") or {}
            winners = jackpot.get("winnerCount", 0)
            prize = jackpot.get("perPrize", 0)
            sales = r.get("sellAmount", 0)

            if keyword:
                combined_text = f"{period} {date_str} {z1_appear} {z1_size} {z2}".lower()
                if keyword not in combined_text:
                    continue

            prize_str = f"${prize:,}" if winners > 0 else "-"
            sales_str = f"${sales:,}" if sales > 0 else "-"

            self.tree.insert("", "end", values=(
                period,
                date_str,
                z1_appear,
                z1_size,
                z2,
                winners,
                prize_str,
                sales_str
            ))
            count += 1

        game_name = next((title for code, title in self.game_options if code == self.current_game), self.current_game)
        self.lbl_stats_summary.config(text=f"{game_name}：顯示 {count} / {len(self.records)} 期資料")

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        item_id = selected_items[0]
        values = self.tree.item(item_id, "values")
        if not values:
            return

        period = values[0]
        matched = next((r for r in self.records if str(r.get("period")) == str(period)), None)
        if matched:
            self.display_showcase(matched)

    def sort_treeview(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        if col in ("jackpot_winners", ):
            l.sort(key=lambda t: int(t[0]) if str(t[0]).isdigit() else 0, reverse=reverse)
        elif col in ("jackpot_prize", "sales"):
            l.sort(key=lambda t: int(t[0].replace("$", "").replace(",", "")) if t[0] not in ("-", "") else 0, reverse=reverse)
        else:
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, "", index)

        self.tree.heading(col, command=lambda: self.sort_treeview(col, not reverse))

    def refresh_statistics_tab(self):
        """更新統計分頁的 KPI、熱門號排行表與常態特徵"""
        if not self.records:
            return

        try:
            self.analyzer = LottoAnalyzer(self.records, game_type=self.current_game)
            summary = self.analyzer.get_summary()
        except Exception as ex:
            print("初始化分析器出錯:", ex)
            return

        total_draws = len(self.records)
        jackpot_wins = 0
        max_jackpot = 0

        for r in self.records:
            jp = r.get("super638JackpotAssign") or r.get("jackpotAssign") or r.get("daily539JackpotAssign") or {}
            w = jp.get("winnerCount", 0)
            p = jp.get("perPrize", 0)
            if w > 0:
                jackpot_wins += w
                if p > max_jackpot:
                    max_jackpot = p

        hot_list = summary.get("hot_numbers_zone1") or []
        top_hot = hot_list[0] if len(hot_list) > 0 else 0
        top_hot_str = f"{top_hot:02d}" if str(top_hot).isdigit() and self.current_game not in ["3star", "4star"] else str(top_hot)
        top_hot_cnt = self.analyzer.zone1_freq.get(top_hot, 0)

        # 更新 4 大 KPI
        self.kpi_cards["total_draws"].config(text=f"{total_draws:,} 期")
        self.kpi_cards["jackpot_wins"].config(text=f"{jackpot_wins} 注")
        self.kpi_cards["max_jackpot"].config(text=f"${max_jackpot:,} 元")
        self.kpi_cards["top_hot"].config(text=f"{top_hot_str} 號 ({top_hot_cnt}次)")

        # 更新左側第 1 區頻率樹狀表
        max_z1 = self.analyzer.max_ball_z1
        min_digit = 0 if self.current_game in ["3star", "4star"] else 1
        self.tree_z1_stats.delete(*self.tree_z1_stats.get_children())
        sorted_z1 = sorted(range(min_digit, max_z1 + 1), key=lambda n: self.analyzer.zone1_freq.get(n, 0), reverse=True)

        hot_th = max(3, int(len(sorted_z1) * 0.2))
        cold_th = max(5, int(len(sorted_z1) * 0.8))

        for rank, num in enumerate(sorted_z1, start=1):
            cnt = self.analyzer.zone1_freq.get(num, 0)
            rate = round((cnt / total_draws) * 100, 1) if total_draws > 0 else 0
            omiss = self.analyzer.zone1_omission.get(num, 0)
            if rank <= hot_th:
                status = "🔥 極熱門"
            elif rank >= cold_th:
                status = "❄️ 極冷門"
            elif omiss >= 10:
                status = "⏳ 遺漏待補"
            else:
                status = "⚖️ 溫號"

            num_str = f"{num:02d}" if self.current_game not in ["3star", "4star"] else str(num)
            self.tree_z1_stats.insert("", "end", values=(
                f"#{rank}",
                num_str,
                f"{cnt} 次",
                f"{omiss} 期未開",
                f"{rate} %",
                status
            ))

        # 更新右側第二區 / 特別號頻率樹狀表
        max_z2 = self.analyzer.max_ball_z2 if self.analyzer.has_zone2 else 0
        self.tree_z2_stats.delete(*self.tree_z2_stats.get_children())
        if max_z2 > 0:
            sorted_z2 = sorted(range(1, max_z2 + 1), key=lambda n: self.analyzer.zone2_freq.get(n, 0), reverse=True)
            for num in sorted_z2:
                cnt = self.analyzer.zone2_freq.get(num, 0)
                rate = round((cnt / total_draws) * 100, 1) if total_draws > 0 else 0
                omiss = self.analyzer.zone2_omission.get(num, 0)
                self.tree_z2_stats.insert("", "end", values=(
                    f"{num:02d} 號",
                    f"{cnt} 次",
                    f"{rate} %",
                    f"{omiss} 期未開"
                ))

        # 常態指標資訊
        game_desc = "大樂透 (6/49)" if self.current_game == "lotto649" else "威力彩 (6/38+1/8)"
        def_sum = "115 ~ 185" if self.current_game == "lotto649" else "85 ~ 155"
        norm_txt = (
            f"【{game_desc} 歷史常態特徵大數據】\n"
            f"• 歷史平均和值: {summary.get('avg_sum', 150.0 if self.current_game == 'lotto649' else 117.0)} (黃金常態區間: {def_sum})\n"
            f"• 最常見奇偶比: {', '.join(summary.get('common_odd_even', ['3:3', '2:4']))}\n"
            f"• 最常見大小比: {', '.join(summary.get('common_high_low', ['3:3', '4:2']))}\n"
            f"• 最熱門 Top 5: {', '.join(f'{n:02d}' for n in summary.get('hot_numbers_zone1', [])[:5])}\n"
            f"• 最熱門特別號: {', '.join(f'{n:02d}' for n in summary.get('hot_numbers_zone2', [])[:3])}"
        )
        self.lbl_norm_stats.config(text=norm_txt)

        # 同步更新 AI 標籤頁的特徵速報
        self.lbl_stats_mini.config(text=(
            f"• 歷史分析樣本: {total_draws} 期 ({game_desc})\n"
            f"• 歷史平均和值: {summary.get('avg_sum', 150.0 if self.current_game == 'lotto649' else 117.0)}\n"
            f"• 熱門號 Top 5: {', '.join(f'{n:02d}' for n in summary.get('hot_numbers_zone1', [])[:5])}\n"
            f"• 特別號 Top 3: {', '.join(f'{n:02d}' for n in summary.get('hot_numbers_zone2', [])[:3])}"
        ))

    # ==========================================
    # 🤖 AI 運籌最佳化求解與渲染邏輯
    # ==========================================
    def on_start_solve(self):
        if self.is_solving:
            return

        if not self.records:
            return

        # 解析注數
        count_str = self.combo_ai_count.get()
        count = int(count_str.split(" ")[0].replace("注", "")) if count_str else 5
        max_ball = 49 if self.current_game == "lotto649" else 38

        # 膽碼解析
        locked_z1 = []
        raw_locked = self.entry_ai_locked.get().replace("，", ",").split(",")
        for item in raw_locked:
            item = item.strip()
            if item.isdigit():
                val = int(item)
                if 1 <= val <= max_ball and val not in locked_z1:
                    locked_z1.append(val)
        if len(locked_z1) > 5:
            messagebox.showerror("約束錯誤", "必選膽碼最多只能設定 5 個號碼！")
            return

        # 殺號解析
        excluded_z1 = []
        raw_excluded = self.entry_ai_excluded.get().replace("，", ",").split(",")
        for item in raw_excluded:
            item = item.strip()
            if item.isdigit():
                val = int(item)
                if 1 <= val <= max_ball and val not in excluded_z1:
                    excluded_z1.append(val)

        conflict = set(locked_z1).intersection(set(excluded_z1))
        if conflict:
            messagebox.showerror("約束錯誤", f"號碼 {conflict} 同時出現在膽碼與殺號中，請修正！")
            return

        # 第二區 / 特別號
        z2_val = self.combo_ai_z2.get()
        locked_z2 = int(z2_val) if z2_val.isdigit() else None

        # 和值
        try:
            sum_min = int(self.entry_ai_sum_min.get().strip())
            sum_max = int(self.entry_ai_sum_max.get().strip())
        except ValueError:
            sum_min = 115 if self.current_game == "lotto649" else 85
            sum_max = 185 if self.current_game == "lotto649" else 155

        constraints = {
            "locked_z1": locked_z1,
            "excluded_z1": excluded_z1,
            "locked_z2": locked_z2,
            "sum_min": sum_min,
            "sum_max": sum_max,
            "diversity": self.var_ai_diversity.get(),
            "game_type": self.current_game
        }

        self.is_solving = True
        self.btn_ai_solve.config(text="⏳ 運籌求解計算中...", state="disabled")
        self.lbl_ai_results_status.config(text="求解器運算中，請稍候...")

        def _worker():
            try:
                self.analyzer = LottoAnalyzer(self.records, game_type=self.current_game)

                if self.analyzer and LottoAIOptimizer:
                    optimizer = LottoAIOptimizer(self.analyzer)
                    results = optimizer.solve_combinations(num_tickets=count, user_constraints=constraints)
                else:
                    results = []
                self.after(0, lambda res=results: self._on_solve_complete(res))
            except Exception as ex:
                import traceback
                traceback.print_exc()
                err_msg = str(ex)
                self.after(0, lambda msg=err_msg: self._on_solve_error(msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_solve_complete(self, results):
        self.is_solving = False
        self.btn_ai_solve.config(text="⚡ 啟動 AI 運籌最佳化求解", state="normal")
        self.ai_tickets = results
        game_name = GAME_NAMES.get(self.current_game, self.current_game)
        self.lbl_ai_results_status.config(text=f"🎯 成功求解 {len(results)} 組最佳 {game_name} 注單 (點擊可個別複製)")
        self.render_ai_tickets(results)

    def _on_solve_error(self, err_msg):
        self.is_solving = False
        self.btn_ai_solve.config(text="⚡ 啟動 AI 運籌最佳化求解", state="normal")
        self.lbl_ai_results_status.config(text="❌ 求解過程發生異常")
        messagebox.showerror("求解失敗", f"運籌求解器發生錯誤：\n{err_msg}")

    def render_ai_tickets(self, tickets):
        for widget in self.ai_scrollable_frame.winfo_children():
            widget.destroy()

        if not tickets:
            empty_lbl = tk.Label(self.ai_scrollable_frame, text="無求解結果，可能約束條件過於嚴格，請放寬後重試。", bg=COLOR_BG, fg=COLOR_MUTED, font=("Microsoft JhengHei UI", 11))
            empty_lbl.pack(pady=40)
            return

        has_zone2 = (self.current_game in ["super_lotto", "lotto649"])

        for idx, t in enumerate(tickets):
            card = tk.Frame(self.ai_scrollable_frame, bg=COLOR_CARD, padx=12, pady=6, highlightbackground=COLOR_BORDER, highlightthickness=1)
            card.pack(fill="x", pady=2, padx=4)

            # 第一列：注號、評分、3D彩球排、統計數據、複製按鈕
            row_main = tk.Frame(card, bg=COLOR_CARD)
            row_main.pack(fill="x")

            # 1. 右側複製按鈕優先排列
            btn_copy_single = ttk.Button(row_main, text="📋 複製此注", style="Secondary.TButton", command=lambda cur_t=t: self.copy_single_ticket(cur_t))
            btn_copy_single.pack(side="right", padx=(4, 0))

            # 2. 注號與評分
            t_no = t.get("ticket_no", idx + 1)
            score = t.get("score", 90)
            tk.Label(row_main, text=f"第 {t_no:02d} 注", font=("Segoe UI", 11, "bold"), bg=COLOR_CARD, fg=COLOR_GOLD).pack(side="left")

            score_badge = tk.Label(row_main, text=f"🌟 {score}分", font=("Microsoft JhengHei UI", 8, "bold"), bg="#1e3a2f", fg="#34d399", padx=5, pady=1)
            score_badge.pack(side="left", padx=6)

            # 3. 中間 3D 彩球排 (直徑 28px 精緻小球)
            balls_row = tk.Frame(row_main, bg=COLOR_CARD)
            balls_row.pack(side="left", padx=6)

            z1 = t.get("zone1", [])
            for num in z1:
                num_str = f"{int(num):02d}" if str(num).isdigit() and self.current_game not in ["3star", "4star"] else str(num)
                ball = LottoBall(balls_row, number=num_str, is_special=False, size=28, bg=COLOR_CARD)
                ball.pack(side="left", padx=1)

            if has_zone2:
                sep = tk.Label(balls_row, text="+", font=("Segoe UI", 12, "bold"), bg=COLOR_CARD, fg=COLOR_MUTED)
                sep.pack(side="left", padx=3)

                z2 = t.get("zone2", "--")
                z2_str = f"{int(z2):02d}" if str(z2).isdigit() else str(z2)
                ball_z2 = LottoBall(balls_row, number=z2_str, is_special=True, size=28, bg=COLOR_CARD)
                ball_z2.pack(side="left", padx=1)

            # 4. 指標
            metrics_text = f"和值:{t.get('sum', '--')} | 奇偶:{t.get('odd_even', '--')} | 大小:{t.get('high_low', '--')}"
            tk.Label(row_main, text=metrics_text, font=("Segoe UI", 8), bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="left", padx=4)

            # 第二列：AI 特徵標籤
            reasons = t.get("reasons", [])
            engine_name = t.get("engine", "AI 運籌最佳化")
            reasons_row = tk.Frame(card, bg=COLOR_CARD)
            reasons_row.pack(anchor="w", pady=(2, 0))

            tk.Label(reasons_row, text=f"⚙️ {engine_name}:", font=("Microsoft JhengHei UI", 8), bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="left", padx=(0, 4))
            for r in reasons:
                lbl_tag = tk.Label(reasons_row, text=f"[{r}]", font=("Microsoft JhengHei UI", 8), bg=COLOR_HEADER, fg=COLOR_GOLD_LIGHT, padx=4, pady=0)
                lbl_tag.pack(side="left", padx=2)

        # 底部留白區域，保障滾動到底部時第 5 注絕不被遮擋
        bottom_spacer = tk.Frame(self.ai_scrollable_frame, bg=COLOR_BG, height=40)
        bottom_spacer.pack(fill="x", pady=10)

        # 強制刷新 Canvas 滾動範圍與置頂
        self.ai_scrollable_frame.update_idletasks()
        self.ai_canvas.configure(scrollregion=self.ai_canvas.bbox("all"))
        self.ai_canvas.yview_moveto(0)

    def copy_single_ticket(self, t):
        game_name = GAME_NAMES.get(self.current_game, self.current_game)
        has_zone2 = (self.current_game in ["super_lotto", "lotto649"])
        special_name = "特別號" if self.current_game == "lotto649" else "第二區"

        z1_nums = t.get("zone1", [])
        z1_str = " ".join(f"{int(n):02d}" if str(n).isdigit() and self.current_game not in ["3star", "4star"] else str(n) for n in z1_nums)

        if has_zone2:
            z2_num = t.get("zone2", 0)
            z2_str = f"{int(z2_num):02d}" if str(z2_num).isdigit() else str(z2_num)
            text = f"{game_name}推薦 第 {t.get('ticket_no', 1)} 注: [{z1_str}] + {special_name} [{z2_str}] (和值:{t.get('sum', 0)}, 評分:{t.get('score', 0)}分)"
        else:
            text = f"{game_name}推薦 第 {t.get('ticket_no', 1)} 注: [{z1_str}] (和值:{t.get('sum', 0)}, 評分:{t.get('score', 0)}分)"

        self.clipboard_clear()
        self.clipboard_append(text)
        self.lbl_ai_results_status.config(text=f"✅ 已成功複製 第 {t.get('ticket_no', 1)} 注 到剪貼簿！")

    def copy_all_ai_tickets(self):
        if not self.ai_tickets:
            messagebox.showinfo("提示", "目前沒有可複製的注單。")
            return

        game_name = GAME_NAMES.get(self.current_game, self.current_game)
        has_zone2 = (self.current_game in ["super_lotto", "lotto649"])
        special_name = "特別號" if self.current_game == "lotto649" else "第二區"
        lines = [f"【台灣彩券 · {game_name} AI 智慧運籌推薦注單】"]
        for t in self.ai_tickets:
            z1_nums = t.get("zone1", [])
            z1_str = " ".join(f"{int(n):02d}" if str(n).isdigit() and self.current_game not in ["3star", "4star"] else str(n) for n in z1_nums)
            if has_zone2:
                z2_num = t.get("zone2", 0)
                z2_str = f"{int(z2_num):02d}" if str(z2_num).isdigit() else str(z2_num)
                lines.append(f"第 {t.get('ticket_no', 1):02d} 注: [{z1_str}] + {special_name} [{z2_str}]  | 和值:{t.get('sum', 0):3d} | 評分:{t.get('score', 0)}分 | {', '.join(t.get('reasons', []))}")
            else:
                lines.append(f"第 {t.get('ticket_no', 1):02d} 注: [{z1_str}]  | 和值:{t.get('sum', 0):3d} | 評分:{t.get('score', 0)}分 | {', '.join(t.get('reasons', []))}")

        full_text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(full_text)
        self.lbl_ai_results_status.config(text=f"✅ 已成功複製全部 {len(self.ai_tickets)} 組注單至剪貼簿！")
        messagebox.showinfo("複製成功", f"已複製全部 {len(self.ai_tickets)} 組推薦注單至剪貼簿，可直接貼上使用！")

    # ==========================================
    # 下載與匯出功能
    # ==========================================
    def on_start_download(self):
        if self.is_downloading:
            return

        year_val = self.year_combo.get()
        self.is_downloading = True
        self.btn_fetch.config(state="disabled")
        self.progress_frame.pack(side="top", fill="x", padx=4, pady=4)
        self.progress_bar.start(10)
        game_name = next((title for code, title in self.game_options if code == self.current_game), self.current_game)
        self.lbl_status.config(text=f"正在連線台灣彩券官方下載 {game_name} 獎號...")

        def _worker():
            cur_y = datetime.now().year
            json_file, csv_file = self.get_game_paths()
            from taiwan_lottery import download_game_range, fetch_game_by_year, save_to_csv, save_to_json
            if "全期別" in year_val:
                download_game_range(self.current_game, 2024, cur_y, csv_file)
            else:
                y = int(year_val)
                recs = fetch_game_by_year(self.current_game, y)
                if recs:
                    save_to_csv(recs, csv_file, game_type=self.current_game)
                    save_to_json(recs, json_file)

            if os.path.exists(json_file):
                with open(json_file, "r", encoding="utf-8") as f:
                    self.records = json.load(f)

            self.after(0, self._on_download_complete)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_download_complete(self):
        self.is_downloading = False
        self.btn_fetch.config(state="normal")
        self.progress_bar.stop()
        self.progress_frame.pack_forget()
        self.refresh_all_views()
        game_name = "大樂透" if self.current_game == "lotto649" else "威力彩"
        messagebox.showinfo("同步完成", f"已成功更新！目前資料庫共有 {len(self.records)} 期 {game_name} 開獎紀錄。")

    def export_csv(self):
        if not self.records:
            messagebox.showwarning("提示", "目前尚無資料可匯出！")
            return
        prefix = "lotto649" if self.current_game == "lotto649" else "super_lotto"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 試算表", "*.csv"), ("所有檔案", "*.*")],
            initialfile=f"{prefix}_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        if filepath:
            if self.current_game == "lotto649":
                formatted = [parse_lotto649_record(r) for r in self.records]
                with open(filepath, "w", newline="", encoding="utf-8-sig") as cf:
                    writer = csv.DictWriter(cf, fieldnames=list(formatted[0].keys()))
                    writer.writeheader()
                    writer.writerows(formatted)
            else:
                save_to_csv(self.records, filepath)
            messagebox.showinfo("匯出成功", f"資料已成功匯出至：\n{filepath}")

    def export_json(self):
        if not self.records:
            messagebox.showwarning("提示", "目前尚無資料可匯出！")
            return
        prefix = "lotto649" if self.current_game == "lotto649" else "super_lotto"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 資料檔", "*.json"), ("所有檔案", "*.*")],
            initialfile=f"{prefix}_{datetime.now().strftime('%Y%m%d')}.json"
        )
        if filepath:
            save_to_json(self.records, filepath)
            messagebox.showinfo("匯出成功", f"JSON 資料已成功匯出至：\n{filepath}")

    def prompt_download_zip(self):
        cur_year = datetime.now().year
        zip_win = tk.Toplevel(self)
        zip_win.title("下載台彩官方歷年開獎總檔 (ZIP)")
        zip_win.geometry("420x220")
        zip_win.configure(bg=COLOR_CARD)
        zip_win.transient(self)
        zip_win.grab_set()

        tk.Label(zip_win, text="請選擇要下載的年度 (2007 ~ 至今):", bg=COLOR_CARD, fg=COLOR_TEXT, font=("Microsoft JhengHei UI", 11, "bold")).pack(pady=(20, 10))

        years = [str(y) for y in range(cur_year, 2006, -1)]
        combo = ttk.Combobox(zip_win, values=years, state="readonly", width=15)
        combo.current(0)
        combo.pack(pady=5)

        lbl_note = tk.Label(zip_win, text="* 官方總檔包含該年度所有彩券歷史總表，下載後將自動解壓縮。", bg=COLOR_CARD, fg=COLOR_MUTED, font=("Microsoft JhengHei UI", 9))
        lbl_note.pack(pady=5)

        def do_download():
            target_y = int(combo.get())
            zip_win.destroy()
            self.lbl_status.config(text=f"正在下載 {target_y} 年官方 ZIP 總檔...")
            self.progress_frame.pack(side="top", fill="x", padx=16, pady=4)
            self.progress_bar.start(10)

            def _zip_worker():
                path = download_official_yearly_zip(target_y, save_dir="./downloads")
                self.after(0, lambda p=path, y=target_y: self._on_zip_complete(p, y))

            threading.Thread(target=_zip_worker, daemon=True).start()

        btn_dl = ttk.Button(zip_win, text="開始下載", style="Primary.TButton", command=do_download)
        btn_dl.pack(pady=15)

    def _on_zip_complete(self, path, year):
        self.progress_bar.stop()
        self.progress_frame.pack_forget()
        if path:
            messagebox.showinfo("下載成功", f"{year} 年度官方開獎總表已下載並解壓縮至：\n{os.path.abspath('./downloads/' + str(year))}")
        else:
            messagebox.showerror("下載失敗", f"無法下載 {year} 年度 ZIP 壓縮檔，請稍候重試。")

    def open_web_dashboard(self):
        """一鍵自動清理舊伺服器、重啟背景 Web 伺服器並使用本機真實區網 IP (LAN IP) 開啟瀏覽器"""
        import subprocess
        import urllib.request
        import socket

        # 取得電腦真實區域網路 IP (例如 192.168.1.X)
        def get_real_local_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0.1)
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                try:
                    return socket.gethostbyname(socket.gethostname())
                except Exception:
                    return "127.0.0.1"

        def kill_old_server_process():
            """清理背景佔用 5000 埠口的舊版伺服器進程"""
            try:
                if os.name == 'nt':
                    output = subprocess.check_output('netstat -ano | findstr :5000', shell=True).decode('utf-8', errors='ignore')
                    pids = set()
                    for line in output.strip().splitlines():
                        parts = line.split()
                        if len(parts) >= 5 and 'LISTENING' in line:
                            pids.add(parts[-1])
                    for pid in pids:
                        if pid != '0':
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        real_ip = get_real_local_ip()
        web_url = f"http://127.0.0.1:5000"

        # 1. 強制關閉背景運行的舊版 5000 埠口伺服器
        kill_old_server_process()
        time.sleep(0.5)

        # 2. 重新啟動最新的 app.py 伺服器
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            subprocess.Popen([sys.executable, script_path], creationflags=creation_flags)
        except Exception as ex:
            print("自動啟動 Web 伺服器失敗:", ex)

        # 輪詢等待 Web 伺服器埠口 5000 Ready (最多等待 6 秒)
        server_ready = False
        for _ in range(30):
            try:
                with socket.create_connection(("127.0.0.1", 5000), timeout=0.2):
                    server_ready = True
                    break
            except Exception:
                time.sleep(0.2)

        # 3. 在預設瀏覽器開啟 Web 網址
        webbrowser.open(web_url)






def launch_gui():
    app = TaiwanLottoApp()
    app.mainloop()

if __name__ == "__main__":
    launch_gui()
