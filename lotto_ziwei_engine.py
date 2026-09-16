# -*- coding: utf-8 -*-
"""
台灣彩券 · 紫微斗數與八字五行玄學預測引擎 (Ziwei & BaZi Metaphysics Engine)
=====================================================================
提供生辰八字與流日天干地支推算、五行喜用神屬性映射、紫微財星加權與吉號生成。
可與 CP-SAT 運籌求解器 (lotto_ai_optimizer) 無縫結合。
"""

import math
import random
from datetime import datetime

STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 五行與天干地支對應
STEM_ELEMENTS = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水"
}

BRANCH_ELEMENTS = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水"
}

# 紫微四化星曜
SI_HUA_TABLE = {
    "甲": {"lu": "廉貞", "quan": "破軍", "ke": "武曲", "ji": "太陽"},
    "乙": {"lu": "天機", "quan": "天梁", "ke": "紫微", "ji": "太陰"},
    "丙": {"lu": "天同", "quan": "天機", "ke": "文昌", "ji": "廉貞"},
    "丁": {"lu": "太陰", "quan": "天同", "ke": "天機", "ji": "巨門"},
    "戊": {"lu": "貪狼", "quan": "太陰", "ke": "右弼", "ji": "天機"},
    "己": {"lu": "武曲", "quan": "貪狼", "ke": "天梁", "ji": "文曲"},
    "庚": {"lu": "太陽", "quan": "武曲", "ke": "太陰", "ji": "天同"},
    "辛": {"lu": "巨門", "quan": "太陽", "ke": "文曲", "ji": "文昌"},
    "壬": {"lu": "天梁", "quan": "紫微", "ke": "左輔", "ji": "武曲"},
    "癸": {"lu": "破軍", "quan": "巨門", "ke": "太陰", "ji": "貪狼"}
}

# 財星對應五行與幸運尾數/數值映射 (河圖洛書五行數 + 彩券對應)
ELEMENT_NUMBERS = {
    "木": [1, 2, 3, 8, 11, 12, 13, 18, 21, 22, 23, 28, 31, 32, 33, 38, 41, 42, 43, 48],
    "火": [2, 7, 3, 4, 12, 17, 13, 14, 22, 27, 23, 24, 32, 37, 33, 34, 42, 47, 43, 44],
    "土": [5, 10, 8, 15, 18, 20, 25, 28, 30, 35, 38, 40, 45, 48],
    "金": [4, 9, 7, 8, 14, 19, 17, 18, 24, 29, 27, 28, 34, 39, 37, 38, 44, 49, 47, 48],
    "水": [1, 6, 9, 10, 11, 16, 19, 20, 21, 26, 29, 30, 31, 36, 39, 40, 41, 46, 49]
}

def get_ganzhi_year(year: int):
    """計算西元年份天干地支 (甲子年=1984)"""
    offset = (year - 1984) % 60
    stem = STEMS[offset % 10]
    branch = BRANCHES[offset % 12]
    return stem, branch

def get_ganzhi_day(year: int, month: int, day: int):
    """計算指定日期的日柱天干地支 (簡易儒略日演算法)"""
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    jd = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5
    # 儒略日與天干地支對應
    offset = int(jd + 49) % 60
    stem = STEMS[offset % 10]
    branch = BRANCHES[offset % 12]
    return stem, branch

def get_hour_branch(hour: int):
    """根據 24 小時制計算地支時辰"""
    h = (hour + 1) % 24
    idx = h // 2
    return BRANCHES[idx]

def calculate_ziwei_lotto_fortune(
    birth_year: int = None,
    birth_month: int = None,
    birth_day: int = None,
    birth_hour: int = 12,
    game_type: str = "super_lotto",
    target_date: datetime = None
) -> dict:
    """
    計算個人生辰 + 當日氣場之紫微斗數與八字偏財氣場指數。
    
    返回 dict:
        - wealth_index: 偏財氣場指數 (60 ~ 99)
        - year_ganzhi: 年柱
        - day_ganzhi: 日柱
        - favorable_element: 喜用五行 (木/火/土/金/水)
        - ziwei_star: 主耀財星 (武曲/太陰/貪狼/廉貞/天府等)
        - lucky_numbers_z1: 推薦第一區紫微吉數列表
        - lucky_numbers_z2: 推薦第二區紫微吉數列表
        - boost_weights_z1: 1 ~ max_ball 的加權權重字典
        - summary_text: 命理運勢速報
    """
    if target_date is None:
        target_date = datetime.now()

    now_y, now_m, now_d = target_date.year, target_date.month, target_date.day
    day_stem, day_branch = get_ganzhi_day(now_y, now_m, now_d)
    
    if birth_year and birth_month and birth_day:
        b_stem, b_branch = get_ganzhi_year(birth_year)
        b_day_stem, _ = get_ganzhi_day(birth_year, birth_month, birth_day)
    else:
        # 未提供出生生辰時，使用當日天干地支為氣場基準
        b_stem, b_branch = get_ganzhi_year(now_y)
        b_day_stem = day_stem

    # 確定五行喜用
    element_counts = {
        STEM_ELEMENTS[b_stem]: 2,
        STEM_ELEMENTS[day_stem]: 2,
        BRANCH_ELEMENTS[day_branch]: 1,
        BRANCH_ELEMENTS[get_hour_branch(birth_hour or 12)]: 1
    }
    # 挑選相對需要的喜用神
    favorable_element = min(element_counts, key=element_counts.get)
    
    # 四化與偏財星曜
    si_hua = SI_HUA_TABLE.get(day_stem, SI_HUA_TABLE["甲"])
    lu_star = si_hua["lu"]   # 化祿星
    quan_star = si_hua["quan"] # 化權星
    ke_star = si_hua["ke"]   # 化科星

    # 計算偏財指數 (根據天干地支合沖與四化)
    base_score = 75
    # 陰陽五行加成
    hash_val = (ord(b_stem) * 7 + ord(day_stem) * 13 + now_d * 3 + (birth_hour or 12)) % 25
    wealth_index = base_score + hash_val

    # 決定彩券號碼上限與最小位數
    g = (game_type or "super_lotto").lower()
    min_digit = 0 if g in ["3star", "3星彩", "4star", "4星彩"] else 1

    if g in ["lotto649", "649", "大樂透"]:
        max_ball_z1 = 49
        max_ball_z2 = 49
    elif g in ["lotto49m", "49樂合彩", "49m"]:
        max_ball_z1 = 49
        max_ball_z2 = 0
    elif g in ["daily539", "539", "今彩539", "lotto39m", "39樂合彩", "39m"]:
        max_ball_z1 = 39
        max_ball_z2 = 0
    elif g in ["3star", "3星彩"]:
        max_ball_z1 = 9
        max_ball_z2 = 0
    elif g in ["4star", "4星彩"]:
        max_ball_z1 = 9
        max_ball_z2 = 0
    elif g in ["bingo", "賓果", "賓果賓果"]:
        max_ball_z1 = 80
        max_ball_z2 = 80
    else:
        # 威力彩 (super_lotto)
        max_ball_z1 = 38
        max_ball_z2 = 8

    # 依五行與四化挑選 Zone 1 吉數
    candidate_elements = ELEMENT_NUMBERS.get(favorable_element, ELEMENT_NUMBERS["木"])
    # 根據 hash_val 定向挑選專屬吉數
    valid_z1 = [n for n in candidate_elements if min_digit <= n <= max_ball_z1]
    
    # 若不足則從號碼庫補充
    if len(valid_z1) < (6 if max_ball_z1 > 10 else 4):
        for i in range(min_digit, max_ball_z1 + 1):
            if i not in valid_z1:
                valid_z1.append(i)

    # 種子打散，保證每次生辰/流日結果一致
    seed_key = (birth_year or 2000) * 10000 + (birth_month or 1) * 100 + (birth_day or 1) + now_d
    rnd = random.Random(seed_key)
    shuffled_z1 = sorted(valid_z1, key=lambda x: rnd.random())
    
    num_pick = 3 if g in ["3star", "3星彩"] else (4 if g in ["4star", "4星彩"] else 12)
    lucky_z1 = sorted(shuffled_z1[:num_pick])
    
    if max_ball_z2 > 0:
        valid_z2 = list(range(1, max_ball_z2 + 1))
        rnd.shuffle(valid_z2)
        lucky_z2 = sorted(valid_z2[:(1 if g in ["super_lotto", "lotto649", "bingo"] else 3)])
    else:
        lucky_z2 = []

    # 建立 min_digit ~ max_ball_z1 的加權權重 (供 CP-SAT 求解器加算 Objective Score)
    boost_weights = {}
    for num in range(min_digit, max_ball_z1 + 1):
        if num in lucky_z1[:6]:
            boost_weights[num] = 0.8  # 高度偏好
        elif num in lucky_z1[6:]:
            boost_weights[num] = 0.4  # 中度偏好
        else:
            boost_weights[num] = 0.0

    GAME_NAME_MAP = {
        "super_lotto": "威力彩",
        "lotto649": "大樂透",
        "daily539": "今彩539",
        "lotto39m": "39樂合彩",
        "lotto49m": "49樂合彩",
        "3star": "3星彩",
        "4star": "4星彩",
        "bingo": "BINGO BINGO"
    }
    game_name = GAME_NAME_MAP.get(g, "威力彩")

    summary_text = (
        f"今日日柱【{day_stem}{day_branch}】，八字五行喜用為【{favorable_element}】。"
        f"紫微流日逢【{lu_star}化祿】與【{quan_star}化權】吉照，偏財氣場指數為 {wealth_index} 分。"
        f"對應【{game_name}】推薦偏財吉數：{', '.join(f'{x:02d}' for x in lucky_z1[:6])}。"
    )

    return {
        "game_type": g,
        "game_name": game_name,
        "wealth_index": wealth_index,
        "day_ganzhi": f"{day_stem}{day_branch}",
        "year_ganzhi": f"{b_stem}{b_branch}",
        "favorable_element": favorable_element,
        "lu_star": lu_star,
        "quan_star": quan_star,
        "ke_star": ke_star,
        "lucky_numbers_z1": lucky_z1,
        "lucky_numbers_z2": lucky_z2,
        "boost_weights_z1": boost_weights,
        "summary_text": summary_text
    }
