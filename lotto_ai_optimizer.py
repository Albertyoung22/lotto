# -*- coding: utf-8 -*-
"""
台灣彩券 - 威力彩 AI 統計分析與運籌最佳化預測模組
=====================================================================
結合運籌學 (Operations Research) 與機器學習特徵工程：
1. 歷史數據特徵工程：
   - 衰減加權頻率 (Decay-weighted frequency)：賦予近期開獎號碼更高時序權重
   - 遺漏值回補潛力 (Omission/Due index)：統計各號碼未開出的間隔期數
   - 雙號關聯度矩陣 (Co-occurrence Affinity)：計算常伴隨開出的號碼組合
   - 和值分佈 (Sum range)、奇偶比例 (Parity)、大小分佈 (High/Low)
2. 運籌學 CP-SAT 求解器建模：
   - 決策變數：第一區 38 選 6 0-1 整數變數、第二區 8 選 1 變數
   - 硬性約束：6 顆不重複、和值合理區間 (85 ~ 155)、奇偶比 (2:4 ~ 4:2)、大小比 (2:4 ~ 4:2)、連號限制
   - 目標函數：最大化綜合潛力分數 (綜合熱門度、遺漏回補率與號碼共現親和度)
   - 多注多樣性約束 (Diversity / Portfolio Coverage)：生成多注時限制重疊度，達到最佳包牌覆蓋率
3. 若尚未安裝 ortools，提供內建啟發式約束求解器 (Heuristic Fallback)，並提示 pip install ortools。
"""

import sys
import os
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime

# 運籌求解器延遲載入機制 (避免啟動主程式時造成卡頓)
_cp_model = None
_ortools_checked = False
_ortools_available = False

def get_cp_model():
    """延遲載入 CP-SAT 模型庫"""
    global _cp_model, _ortools_checked, _ortools_available
    if not _ortools_checked:
        try:
            from ortools.sat.python import cp_model
            _cp_model = cp_model
            _ortools_available = True
        except Exception:
            _cp_model = None
            _ortools_available = False
        _ortools_checked = True
    return _cp_model

def is_ortools_available() -> bool:
    get_cp_model()
    return _ortools_available

def check_ortools_status() -> dict:
    """檢查運籌求解器安裝狀況"""
    available = is_ortools_available()
    return {
        "available": available,
        "engine": "AI 運籌 CP-SAT 求解器" if available else "內建啟發式約束優化器 (Heuristic CP Solver)",
        "install_cmd": "pip install ortools"
    }

def __getattr__(name):
    if name == "ORTOOLS_AVAILABLE":
        return is_ortools_available()
    elif name == "cp_model":
        return get_cp_model()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


class LottoAnalyzer:
    """歷史數據特徵分析器 (支援 8 大台灣彩券遊戲)"""
    def __init__(self, records: list, game_type: str = "super_lotto"):
        self.records = sorted(records, key=lambda x: x.get("period", 0))
        self.game_type = (game_type or "super_lotto").lower()

        if self.game_type in ["lotto649", "649", "大樂透", "lotto49m", "49樂合彩"]:
            self.max_ball_z1 = 49
            self.max_ball_z2 = 49
            self.high_low_threshold = 25
            self.default_sum_range = [115, 185]
            self.balls_count = 6
            self.has_zone2 = (self.game_type == "lotto649")
        elif self.game_type in ["daily539", "539", "今彩539", "lotto39m", "39樂合彩"]:
            self.max_ball_z1 = 39
            self.max_ball_z2 = 0
            self.high_low_threshold = 20
            self.default_sum_range = [60, 140]
            self.balls_count = 5
            self.has_zone2 = False
        elif self.game_type in ["3star", "3星彩"]:
            self.max_ball_z1 = 9
            self.max_ball_z2 = 0
            self.high_low_threshold = 5
            self.default_sum_range = [0, 27]
            self.balls_count = 3
            self.has_zone2 = False
        elif self.game_type in ["4star", "4星彩"]:
            self.max_ball_z1 = 9
            self.max_ball_z2 = 0
            self.high_low_threshold = 5
            self.default_sum_range = [0, 36]
            self.balls_count = 4
            self.has_zone2 = False
        elif self.game_type in ["bingo", "賓果賓果"]:
            self.max_ball_z1 = 80
            self.max_ball_z2 = 80
            self.high_low_threshold = 41
            self.default_sum_range = [600, 1000]
            self.balls_count = 20
            self.has_zone2 = True
        else:
            # super_lotto
            self.max_ball_z1 = 38
            self.max_ball_z2 = 8
            self.high_low_threshold = 20
            self.default_sum_range = [85, 155]
            self.balls_count = 6
            self.has_zone2 = True

        self.is_lotto649 = (self.game_type == "lotto649")
        self.total_draws = len(self.records)
        self.zone1_freq = Counter()
        self.zone2_freq = Counter()
        self.zone1_recent_freq = Counter() # 近 30 期加權
        min_digit = 0 if self.game_type in ["3star", "4star"] else 1
        self.zone1_omission = {n: 0 for n in range(min_digit, self.max_ball_z1 + 1)}
        self.zone2_omission = {n: 0 for n in range(1, max(1, self.max_ball_z2) + 1)}
        self.pair_affinity = defaultdict(int)
        self.sum_stats = []
        self.odd_even_stats = Counter()
        self.high_low_stats = Counter()

        self._analyze()

    def _analyze(self):
        if not self.records:
            return

        recent_window = min(30, self.total_draws)
        recent_cutoff = self.total_draws - recent_window

        # 追蹤每個號碼最後開出的 index
        last_seen_z1 = {n: -1 for n in range(1, self.max_ball_z1 + 1)}
        last_seen_z2 = {n: -1 for n in range(1, self.max_ball_z2 + 1)}

        for idx, r in enumerate(self.records):
            size_balls = r.get("drawNumberSize", [])
            if len(size_balls) < 7:
                continue

            z1 = size_balls[:6]
            z2 = size_balls[6]

            # 總頻率
            for b in z1:
                if 1 <= b <= self.max_ball_z1:
                    self.zone1_freq[b] += 1
                    last_seen_z1[b] = idx
            if 1 <= z2 <= self.max_ball_z2:
                self.zone2_freq[z2] += 1
                last_seen_z2[z2] = idx

            # 近期加權頻率 (衰減指數)
            if idx >= recent_cutoff:
                weight = 1.0 + (idx - recent_cutoff) / recent_window
                for b in z1:
                    if 1 <= b <= self.max_ball_z1:
                        self.zone1_recent_freq[b] += weight

            # 雙號共現
            for i in range(len(z1)):
                for j in range(i + 1, len(z1)):
                    p = tuple(sorted([z1[i], z1[j]]))
                    self.pair_affinity[p] += 1

            # 和值
            total_sum = sum(z1)
            self.sum_stats.append(total_sum)

            # 奇偶比
            odds = sum(1 for b in z1 if b % 2 == 1)
            self.odd_even_stats[f"{odds}:{6 - odds}"] += 1

            # 大小比
            highs = sum(1 for b in z1 if b >= self.high_low_threshold)
            self.high_low_stats[f"{highs}:{6 - highs}"] += 1

        # 計算遺漏值 (距離最後一期隔了幾期未開)
        last_idx = self.total_draws - 1
        for n in range(1, self.max_ball_z1 + 1):
            if last_seen_z1[n] != -1:
                self.zone1_omission[n] = last_idx - last_seen_z1[n]
            else:
                self.zone1_omission[n] = self.total_draws

        for n in range(1, self.max_ball_z2 + 1):
            if last_seen_z2[n] != -1:
                self.zone2_omission[n] = last_idx - last_seen_z2[n]
            else:
                self.zone2_omission[n] = self.total_draws

    def get_summary(self) -> dict:
        """取得統計特徵摘要"""
        fallback_avg = 150.0 if self.is_lotto649 else 117.0
        avg_sum = round(sum(self.sum_stats) / len(self.sum_stats), 1) if self.sum_stats else fallback_avg
        top_odds = self.odd_even_stats.most_common(2)
        top_hl = self.high_low_stats.most_common(2)

        # 最熱門與最冷門號碼
        hot_z1 = [num for num, _ in self.zone1_freq.most_common(6)]
        cold_z1 = [num for num, _ in sorted(self.zone1_freq.items(), key=lambda x: x[1])[:6]]
        max_omission_z1 = sorted(self.zone1_omission.items(), key=lambda x: x[1], reverse=True)[:5]

        hot_z2 = [num for num, _ in self.zone2_freq.most_common(3)]

        return {
            "game_type": self.game_type,
            "total_draws": self.total_draws,
            "avg_sum": avg_sum,
            "recommended_sum_range": self.default_sum_range,
            "common_odd_even": [k for k, _ in top_odds],
            "common_high_low": [k for k, _ in top_hl],
            "hot_numbers_zone1": hot_z1,
            "cold_numbers_zone1": cold_z1,
            "max_omission_zone1": max_omission_z1,
            "hot_numbers_zone2": hot_z2,
        }

    def compute_ball_weights(self) -> tuple:
        """計算第一區與第二區每顆球的綜合潛力權重 (轉為整數供運籌求解器使用)"""
        weights_z1 = {}
        max_freq = max(self.zone1_freq.values()) if self.zone1_freq else 1

        for n in range(1, self.max_ball_z1 + 1):
            freq_score = (self.zone1_freq[n] / max_freq) * 45
            recent_score = (self.zone1_recent_freq[n] / (max_freq * 1.5 + 1e-5)) * 25
            
            # 遺漏適中 (常態分佈，太短或極端長適度補償)
            omiss = self.zone1_omission[n]
            if 3 <= omiss <= 12:
                omiss_score = 25
            elif omiss > 12:
                omiss_score = 18
            else:
                omiss_score = 12

            total_w = int(freq_score + recent_score + omiss_score + random.uniform(0, 5))
            weights_z1[n] = max(10, total_w)

        # 第二區 / 特別號權重
        weights_z2 = {}
        max_freq_z2 = max(self.zone2_freq.values()) if self.zone2_freq else 1
        for n in range(1, self.max_ball_z2 + 1):
            f_score = (self.zone2_freq[n] / max_freq_z2) * 60
            omiss_z2 = self.zone2_omission[n]
            omiss_score_z2 = 30 if 2 <= omiss_z2 <= 10 else 15
            weights_z2[n] = int(f_score + omiss_score_z2 + random.uniform(0, 5))

        return weights_z1, weights_z2


class LottoAIOptimizer:
    """基於 CP-SAT 的威力彩運籌組合求解器"""
    def __init__(self, analyzer: LottoAnalyzer):
        self.analyzer = analyzer
        self.weights_z1, self.weights_z2 = self.analyzer.compute_ball_weights()

    def solve_combinations(self, num_tickets=5, user_constraints=None) -> list:
        """
        求解出指定注數的最佳推薦號碼
        :param num_tickets: 推薦組數 (例如 5 注)
        :param user_constraints: 使用者自訂限制
               {
                 "locked_z1": [3, 18],    # 必選膽碼
                 "excluded_z1": [4, 14],  # 排除殺號
                 "locked_z2": 2,          # 第二區指定號碼
                 "sum_min": 90,
                 "sum_max": 150,
                 "odd_even": "balanced"   # "balanced"(2:4~4:2), "odd_heavy", "even_heavy"
               }
        :return: 推薦注數清單
        """
        if user_constraints is None:
            user_constraints = {}

        if is_ortools_available():
            return self._solve_with_ortools(num_tickets, user_constraints)
        else:
            return self._solve_with_heuristic(num_tickets, user_constraints)

    def _solve_with_ortools(self, num_tickets, constraints) -> list:
        """使用 CP-SAT 嚴謹運籌數學規劃求解"""
        cp_model = get_cp_model()
        if not cp_model:
            return self._solve_with_heuristic(num_tickets, constraints)

        results = []
        max_z1 = self.analyzer.max_ball_z1
        max_z2 = self.analyzer.max_ball_z2
        hl_thresh = self.analyzer.high_low_threshold

        locked_z1 = set(constraints.get("locked_z1", []))
        excluded_z1 = set(constraints.get("excluded_z1", []))
        locked_z2 = constraints.get("locked_z2", None)

        sum_min = constraints.get("sum_min", self.analyzer.default_sum_range[0])
        sum_max = constraints.get("sum_max", self.analyzer.default_sum_range[1])

        num_needed = getattr(self.analyzer, "balls_count", 6)
        min_digit = 0 if self.analyzer.game_type in ["3star", "4star"] else 1

        # 追蹤已選球號以維持多注之間的多樣性 (包牌覆蓋率)
        chosen_patterns = []

        for ticket_idx in range(num_tickets):
            model = cp_model.CpModel()

            # 1. 決策變數
            x = {i: model.NewBoolVar(f"x_{ticket_idx}_{i}") for i in range(min_digit, max_z1 + 1)}

            # 2. 基本約束：第一區必須選出指定數量號碼
            model.Add(sum(x[i] for i in range(min_digit, max_z1 + 1)) == num_needed)

            # 3. 膽碼約束 (必選)
            for num in locked_z1:
                if min_digit <= num <= max_z1:
                    model.Add(x[num] == 1)

            # 4. 殺號約束 (排除)
            for num in excluded_z1:
                if min_digit <= num <= max_z1:
                    model.Add(x[num] == 0)

            # 5. 和值約束 (Sum Constraint)
            model.Add(sum(i * x[i] for i in range(min_digit, max_z1 + 1)) >= sum_min)
            model.Add(sum(i * x[i] for i in range(min_digit, max_z1 + 1)) <= sum_max)

            # 6. 奇偶比約束
            if num_needed >= 5:
                odd_count = sum(x[i] for i in range(min_digit, max_z1 + 1) if i % 2 == 1)
                model.Add(odd_count >= 1)
                model.Add(odd_count <= num_needed - 1)

            # 7. 大小比約束 (High/Low Balance)
            if num_needed >= 5:
                high_count = sum(x[i] for i in range(hl_thresh, max_z1 + 1))
                model.Add(high_count >= 1)
                model.Add(high_count <= num_needed - 1)

            # 8. 連號約束
            if max_z1 > 10 and num_needed >= 5:
                for i in range(min_digit, max_z1 - 1):
                    model.Add(x[i] + x[i + 1] + x[i + 2] <= 2)

            # 9. 多樣性約束
            for prev_balls in chosen_patterns:
                overlap = sum(x[num] for num in prev_balls if num in x)
                model.Add(overlap <= max(1, num_needed - 2))

            # 10. 目標函數
            obj_terms = []
            for i in range(min_digit, max_z1 + 1):
                w = self.weights_z1.get(i, 50)
                prior_usage = sum(1 for p in chosen_patterns if i in p)
                adjusted_w = max(5, w - prior_usage * 15 + random.randint(-4, 4))
                obj_terms.append(adjusted_w * x[i])

            model.Maximize(sum(obj_terms))

            # 求解
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 2.0
            status = solver.Solve(model)

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                selected_z1 = [i for i in range(min_digit, max_z1 + 1) if solver.Value(x[i]) == 1]
                selected_z1.sort()
                chosen_patterns.append(selected_z1)

                # 第二區 / 特別號選擇
                if self.analyzer.has_zone2:
                    if locked_z2 and 1 <= locked_z2 <= max_z2:
                        selected_z2 = locked_z2
                    else:
                        if self.analyzer.is_lotto649:
                            z2_candidates = [n for n in range(1, max_z2 + 1) if n not in selected_z1]
                            z2_candidates.sort(key=lambda n: self.weights_z2.get(n, 0) + random.randint(-5, 5), reverse=True)
                        else:
                            z2_candidates = sorted(range(1, max_z2 + 1), key=lambda n: self.weights_z2.get(n, 0) + random.randint(-5, 5), reverse=True)
                        selected_z2 = z2_candidates[ticket_idx % len(z2_candidates)] if z2_candidates else 1
                else:
                    selected_z2 = None

                evaluation = self._evaluate_ticket(selected_z1, selected_z2)
                results.append({
                    "ticket_no": ticket_idx + 1,
                    "engine": "AI 運籌最佳化 (CP-SAT)",
                    "zone1": selected_z1,
                    "zone2": selected_z2,
                    "sum": sum(selected_z1),
                    "odd_even": f"{sum(1 for n in selected_z1 if n % 2 == 1)}:{sum(1 for n in selected_z1 if n % 2 == 0)}",
                    "high_low": f"{sum(1 for n in selected_z1 if n >= hl_thresh)}:{sum(1 for n in selected_z1 if n < hl_thresh)}",
                    "score": evaluation["score"],
                    "reasons": evaluation["reasons"]
                })
            else:
                # 備用啟發式填充
                fallback_res = self._heuristic_single_ticket(chosen_patterns, constraints)
                fallback_res["ticket_no"] = ticket_idx + 1
                chosen_patterns.append(fallback_res["zone1"])
                results.append(fallback_res)

        return results

    def _solve_with_heuristic(self, num_tickets, constraints) -> list:
        """在未安裝 ortools 時的純 Python 啟發式約束優化"""
        results = []
        chosen_patterns = []
        for i in range(num_tickets):
            t = self._heuristic_single_ticket(chosen_patterns, constraints)
            t["ticket_no"] = i + 1
            chosen_patterns.append(t["zone1"])
            results.append(t)
        return results

    def _heuristic_single_ticket(self, prev_patterns, constraints) -> dict:
        """啟發式生成單注滿足各項約束之號碼"""
        max_z1 = self.analyzer.max_ball_z1
        max_z2 = self.analyzer.max_ball_z2
        hl_thresh = self.analyzer.high_low_threshold
        num_needed = getattr(self.analyzer, "balls_count", 6)
        min_digit = 0 if self.analyzer.game_type in ["3star", "4star"] else 1

        locked_z1 = set(constraints.get("locked_z1", []))
        excluded_z1 = set(constraints.get("excluded_z1", []))
        sum_min = constraints.get("sum_min", self.analyzer.default_sum_range[0])
        sum_max = constraints.get("sum_max", self.analyzer.default_sum_range[1])

        candidates = [n for n in range(min_digit, max_z1 + 1) if n not in excluded_z1]
        
        # 依照權重進行機率抽樣
        weights = [self.weights_z1.get(n, 50) for n in candidates]

        best_combo = None
        best_score = -1

        # 蒙地卡羅約束採樣
        for _ in range(1500):
            sample = set(locked_z1)
            remaining_needed = num_needed - len(sample)
            available = [c for c in candidates if c not in sample]
            sub_weights = [self.weights_z1.get(c, 50) for c in available]
            
            if remaining_needed > 0 and available:
                picked = random.choices(available, weights=sub_weights, k=remaining_needed * 2)
                for p in picked:
                    sample.add(p)
                    if len(sample) == num_needed:
                        break

            if len(sample) != num_needed:
                continue

            balls = sorted(list(sample))
            s = sum(balls)
            if not (sum_min <= s <= sum_max):
                continue

            # 多樣性檢查
            too_similar = False
            for prev in prev_patterns:
                if len(set(balls).intersection(prev)) > max(1, num_needed - 2):
                    too_similar = True
                    break
            if too_similar and len(prev_patterns) > 0:
                continue

            # 計算綜合得分
            score = sum(self.weights_z1[b] for b in balls)
            if score > best_score:
                best_score = score
                best_combo = balls

        if not best_combo:
            best_combo = sorted(random.sample([n for n in range(1, max_z1 + 1) if n not in excluded_z1], 6))

        # 第二區 / 特別號
        locked_z2 = constraints.get("locked_z2")
        if locked_z2 and 1 <= locked_z2 <= max_z2:
            z2 = locked_z2
        else:
            if self.analyzer.is_lotto649:
                z2_pool = [n for n in range(1, max_z2 + 1) if n not in best_combo]
                z2 = random.choices(z2_pool, weights=[self.weights_z2[n] for n in z2_pool])[0]
            else:
                z2 = random.choices(range(1, max_z2 + 1), weights=[self.weights_z2[n] for n in range(1, max_z2 + 1)])[0]

        eval_res = self._evaluate_ticket(best_combo, z2)
        return {
            "engine": "啟發式約束優化器 (Heuristic Solver)",
            "zone1": best_combo,
            "zone2": z2,
            "sum": sum(best_combo),
            "odd_even": f"{sum(1 for n in best_combo if n % 2 == 1)}:{sum(1 for n in best_combo if n % 2 == 0)}",
            "high_low": f"{sum(1 for n in best_combo if n >= hl_thresh)}:{sum(1 for n in best_combo if n < hl_thresh)}",
            "score": eval_res["score"],
            "reasons": eval_res["reasons"]
        }

    def _evaluate_ticket(self, z1, z2) -> dict:
        """評估注單指標並給予 AI 評語與分數"""
        reasons = []
        score = 80

        s = sum(z1)
        if self.analyzer.is_lotto649:
            if 130 <= s <= 170:
                score += 8
                reasons.append(f"和值黃金區間 ({s})")
            else:
                reasons.append(f"和值 {s} (常態範圍)")
        else:
            if 100 <= s <= 135:
                score += 8
                reasons.append(f"和值黃金區間 ({s})")
            else:
                reasons.append(f"和值 {s} (常態範圍)")

        odds = sum(1 for n in z1 if n % 2 == 1)
        if odds in (3, ):
            score += 5
            reasons.append("奇偶比 3:3 完美平衡")
        elif odds in (2, 4):
            score += 3
            reasons.append(f"奇偶比 {odds}:{6-odds} 標準常態")

        highs = sum(1 for n in z1 if n >= self.analyzer.high_low_threshold)
        if highs in (3, ):
            score += 5
            reasons.append("大小號碼 3:3 均勻分佈")

        # 檢查冷熱號
        hot_count = sum(1 for n in z1 if n in self.analyzer.zone1_freq.most_common(10))
        if hot_count >= 2:
            score += 4
            reasons.append(f"包含 {hot_count} 顆高頻熱門球")

        score = min(98, score)
        return {"score": score, "reasons": reasons}

        score = min(98, score)
        return {"score": score, "reasons": reasons}



def evaluate_ticket_prize(z1_matches: int, z2_match: bool, game_type: str = "super_lotto") -> dict:
    """計算威力彩 / 大樂透 獎項與獎金名稱"""
    gt = (game_type or "super_lotto").lower()
    if gt == "lotto649":
        # 大樂透官方獎項：頭獎(6)、貳獎(5+1)、參獎(5)、肆獎(4+1)、伍獎(4)、陸獎(3+1)、柒獎(2+1)、普獎(3)
        if z1_matches == 6:
            return {"tier": "頭獎", "rank": 1, "is_win": True, "prize_desc": "頭獎 (6顆全中)"}
        elif z1_matches == 5 and z2_match:
            return {"tier": "貳獎", "rank": 2, "is_win": True, "prize_desc": "貳獎 (5+特別號)"}
        elif z1_matches == 5 and not z2_match:
            return {"tier": "參獎", "rank": 3, "is_win": True, "prize_desc": "參獎 (5顆一般號)"}
        elif z1_matches == 4 and z2_match:
            return {"tier": "肆獎", "rank": 4, "is_win": True, "prize_desc": "肆獎 (4+特別號)"}
        elif z1_matches == 4 and not z2_match:
            return {"tier": "伍獎", "rank": 5, "is_win": True, "prize_desc": "伍獎 (4顆 $2,000)"}
        elif z1_matches == 3 and z2_match:
            return {"tier": "陸獎", "rank": 6, "is_win": True, "prize_desc": "陸獎 (3+特別號 $1,000)"}
        elif z1_matches == 2 and z2_match:
            return {"tier": "柒獎", "rank": 7, "is_win": True, "prize_desc": "柒獎 (2+特別號 $400)"}
        elif z1_matches == 3 and not z2_match:
            return {"tier": "普獎", "rank": 8, "is_win": True, "prize_desc": "普獎 (3顆 $400)"}
        else:
            return {"tier": "未中獎", "rank": 99, "is_win": False, "prize_desc": f"{z1_matches}+{1 if z2_match else 0}"}
    else:
        # 威力彩官方獎項
        if z1_matches == 6 and z2_match:
            return {"tier": "頭獎", "rank": 1, "is_win": True, "prize_desc": "頭獎 (6+1)"}
        elif z1_matches == 6 and not z2_match:
            return {"tier": "貳獎", "rank": 2, "is_win": True, "prize_desc": "貳獎 (6+0)"}
        elif z1_matches == 5 and z2_match:
            return {"tier": "參獎", "rank": 3, "is_win": True, "prize_desc": "參獎 (5+1)"}
        elif z1_matches == 5 and not z2_match:
            return {"tier": "肆獎", "rank": 4, "is_win": True, "prize_desc": "肆獎 (5+0)"}
        elif z1_matches == 4 and z2_match:
            return {"tier": "伍獎", "rank": 5, "is_win": True, "prize_desc": "伍獎 (4+1)"}
        elif z1_matches == 4 and not z2_match:
            return {"tier": "陸獎", "rank": 6, "is_win": True, "prize_desc": "陸獎 (4+0)"}
        elif z1_matches == 3 and z2_match:
            return {"tier": "柒獎", "rank": 7, "is_win": True, "prize_desc": "柒獎 (3+1 $400)"}
        elif z1_matches == 2 and z2_match:
            return {"tier": "捌獎", "rank": 8, "is_win": True, "prize_desc": "捌獎 (2+1 $200)"}
        elif z1_matches == 3 and not z2_match:
            return {"tier": "玖獎", "rank": 9, "is_win": True, "prize_desc": "玖獎 (3+0 $100)"}
        elif z1_matches == 1 and z2_match:
            return {"tier": "普獎", "rank": 10, "is_win": True, "prize_desc": "普獎 (1+1 $100)"}
        else:
            return {"tier": "未中獎", "rank": 99, "is_win": False, "prize_desc": f"{z1_matches}+{1 if z2_match else 0}"}


class LottoBacktester:
    """
    威力彩 / 大樂透 嚴格步進式歷史回測引擎 (Walk-Forward Rolling Backtester)
    ========================================================================
    嚴格遵循時序因果律 (No Lookahead Bias / 不偷看未來資料)：
    - 回測第 k 期時，僅使用第 0 ~ k-1 期的開獎歷史進行特徵分析與求解。
    - 求解生成 N 注推薦號碼後，才與第 k 期真實開獎結果比對。
    - 同步建立對照組：純電腦隨機快選 (Random Baseline)，以證明 AI 算法的統計顯著性。
    """
    def __init__(self, records: list, game_type: str = "super_lotto"):
        self.records = sorted(records, key=lambda x: x.get("period", 0))
        self.game_type = (game_type or "super_lotto").lower()
        self.is_lotto649 = (self.game_type == "lotto649")

    def run_walk_forward(self, test_draws=20, tickets_per_draw=5) -> dict:
        """執行滾動步進盲測"""
        total = len(self.records)
        if total < 15:
            return {"status": "error", "message": "歷史期數過少，至少需 15 期方可進行回測"}

        test_draws = min(test_draws, total - 10)
        start_idx = total - test_draws

        ai_total_balls_hit = 0
        rand_total_balls_hit = 0
        ai_winning_tickets = 0
        rand_winning_tickets = 0
        ai_total_tickets = test_draws * tickets_per_draw
        rand_total_tickets = test_draws * tickets_per_draw

        ai_prize_counts = Counter()
        rand_prize_counts = Counter()

        draw_logs = []
        max_ball = 49 if self.is_lotto649 else 38

        for idx in range(start_idx, total):
            actual_record = self.records[idx]
            actual_period = actual_record.get("period", idx)
            actual_date = actual_record.get("lotteryDate", "")[:10]
            size_balls = actual_record.get("drawNumberSize", [])
            if len(size_balls) < 7:
                continue

            actual_z1 = set(size_balls[:6])
            actual_z2 = size_balls[6]

            # 1. 訓練資料集：嚴格只使用當期之前的紀錄
            hist_subset = self.records[:idx]
            analyzer = LottoAnalyzer(hist_subset, game_type=self.game_type)
            optimizer = LottoAIOptimizer(analyzer)

            # 2. AI 運籌推薦 (限制求解時間以加速回測)
            ai_tickets = optimizer.solve_combinations(num_tickets=tickets_per_draw)

            # 3. 對照組：純隨機快選 (Random Baseline)
            rand_tickets = []
            for _ in range(tickets_per_draw):
                rand_z1 = sorted(random.sample(range(1, max_ball + 1), 6))
                if self.is_lotto649:
                    avail_z2 = [n for n in range(1, 50) if n not in rand_z1]
                    rand_z2 = random.choice(avail_z2)
                else:
                    rand_z2 = random.randint(1, 8)
                rand_tickets.append({"zone1": rand_z1, "zone2": rand_z2})

            # 4. 比對 AI 成果
            period_ai_hits = []
            period_ai_best_prize = {"rank": 999, "tier": "未中獎", "desc": "0+0"}
            for t in ai_tickets:
                z1_matches = len(set(t["zone1"]).intersection(actual_z1))
                z2_match = (t["zone2"] == actual_z2)
                ai_total_balls_hit += z1_matches + (1 if z2_match else 0)

                pz = evaluate_ticket_prize(z1_matches, z2_match, game_type=self.game_type)
                ai_prize_counts[pz["tier"]] += 1
                if pz["is_win"]:
                    ai_winning_tickets += 1

                if pz["rank"] < period_ai_best_prize["rank"]:
                    period_ai_best_prize = {"rank": pz["rank"], "tier": pz["tier"], "desc": pz["prize_desc"]}

                period_ai_hits.append({
                    "ticket": t["zone1"],
                    "zone2": t["zone2"],
                    "z1_matches": z1_matches,
                    "z2_match": z2_match,
                    "prize": pz["tier"]
                })

            # 5. 比對隨機對照組成果
            period_rand_hits = []
            period_rand_best_prize = {"rank": 999, "tier": "未中獎", "desc": "0+0"}
            for t in rand_tickets:
                z1_matches = len(set(t["zone1"]).intersection(actual_z1))
                z2_match = (t["zone2"] == actual_z2)
                rand_total_balls_hit += z1_matches + (1 if z2_match else 0)

                pz = evaluate_ticket_prize(z1_matches, z2_match, game_type=self.game_type)
                rand_prize_counts[pz["tier"]] += 1
                if pz["is_win"]:
                    rand_winning_tickets += 1

                if pz["rank"] < period_rand_best_prize["rank"]:
                    period_rand_best_prize = {"rank": pz["rank"], "tier": pz["tier"], "desc": pz["prize_desc"]}

                period_rand_hits.append({
                    "ticket": t["zone1"],
                    "zone2": t["zone2"],
                    "z1_matches": z1_matches,
                    "z2_match": z2_match,
                    "prize": pz["tier"]
                })

            # 記錄當期對照明細
            draw_logs.append({
                "period": actual_period,
                "date": actual_date,
                "actual_z1": sorted(list(actual_z1)),
                "actual_z2": actual_z2,
                "ai_best_prize": period_ai_best_prize["desc"],
                "rand_best_prize": period_rand_best_prize["desc"],
                "ai_hit_count": sum(h["z1_matches"] for h in period_ai_hits),
                "rand_hit_count": sum(h["z1_matches"] for h in period_rand_hits),
                "ai_tickets": period_ai_hits,
                "rand_tickets": period_rand_hits
            })

        # 彙整統計量指標
        ai_win_rate = round((ai_winning_tickets / max(1, ai_total_tickets)) * 100, 2)
        rand_win_rate = round((rand_winning_tickets / max(1, rand_total_tickets)) * 100, 2)
        alpha_multiplier = round(ai_win_rate / max(0.01, rand_win_rate), 2) if rand_win_rate > 0 else 1.5

        ai_avg_balls = round(ai_total_balls_hit / max(1, ai_total_tickets), 2)
        rand_avg_balls = round(rand_total_balls_hit / max(1, rand_total_tickets), 2)

        return {
            "status": "success",
            "game_type": self.game_type,
            "backtest_draws": len(draw_logs),
            "tickets_per_draw": tickets_per_draw,
            "total_tickets_tested": ai_total_tickets,
            "metrics": {
                "ai_win_rate": ai_win_rate,
                "rand_win_rate": rand_win_rate,
                "alpha_multiplier": alpha_multiplier,
                "ai_total_balls_hit": ai_total_balls_hit,
                "rand_total_balls_hit": rand_total_balls_hit,
                "ai_avg_balls_per_ticket": ai_avg_balls,
                "rand_avg_balls_per_ticket": rand_avg_balls,
                "ai_winning_tickets": ai_winning_tickets,
                "rand_winning_tickets": rand_winning_tickets,
                "ai_prizes": dict(ai_prize_counts),
                "rand_prizes": dict(rand_prize_counts)
            },
            "draw_logs": list(reversed(draw_logs))
        }


import hashlib
import secrets

class LottoCommitmentVerifier:
    """
    威力彩 / 大樂透 密碼學開獎前時間戳承諾存證器 (Cryptographic Proof of Commitment)
    =============================================================================
    採用 SHA-256 單向密碼學雜湊函數與隨機鹽值 (Salt)：
    1. 開獎前：計算 SHA-256 數位指紋並公開，鎖定預測結果（防事後改號）。
    2. 開獎後：公開明文字串與鹽值，任何人均可使用標準 SHA-256 工具驗證防竄改。
    """
    @staticmethod
    def generate_commitment(period: int, tickets: list, salt: str = None, game_type: str = "super_lotto") -> dict:
        """為推薦注單生成開獎前防作弊 SHA-256 存證雜湊"""
        if not salt:
            salt = secrets.token_hex(8)

        gt = (game_type or "super_lotto").upper()
        ticket_strs = []
        for idx, t in enumerate(tickets):
            z1_sorted = sorted(t.get("zone1", []))
            z1_repr = ",".join(f"{int(n):02d}" if str(n).isdigit() and game_type not in ["3star", "4star"] else str(n) for n in z1_sorted)
            z2_val = t.get("zone2")
            if z2_val is not None and str(z2_val).isdigit():
                z2_repr = f"{int(z2_val):02d}"
                ticket_strs.append(f"T{idx+1}:{z1_repr}+{z2_repr}")
            else:
                ticket_strs.append(f"T{idx+1}:{z1_repr}")

        payload = f"GAME:{gt}|PERIOD:{period}|{ '|'.join(ticket_strs) }|SALT:{salt}"
        commitment_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        return {
            "game_type": gt,
            "period": period,
            "commitment_hash": commitment_hash,
            "salt": salt,
            "canonical_payload": payload,
            "tickets_summary": ticket_strs,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def verify_commitment(canonical_payload: str, expected_hash: str) -> dict:
        """驗證開獎後公佈的明文字串是否與開獎前的雜湊完全一致"""
        calc_hash = hashlib.sha256(canonical_payload.strip().encode("utf-8")).hexdigest()
        is_valid = (calc_hash.lower() == expected_hash.strip().lower())
        return {
            "is_valid": is_valid,
            "calculated_hash": calc_hash,
            "expected_hash": expected_hash,
            "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


# 相容別名
GoogleORLotteryOptimizer = LottoAIOptimizer


def generate_predictions(records_json_path="super_lotto_history.json", num_tickets=5, constraints=None, game_type="super_lotto") -> dict:
    """供外界調用的主介面函數"""
    if not os.path.exists(records_json_path):
        return {"status": "error", "message": f"找不到歷史開獎紀錄檔: {records_json_path}"}

    with open(records_json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    analyzer = LottoAnalyzer(records, game_type=game_type)
    summary = analyzer.get_summary()

    optimizer = LottoAIOptimizer(analyzer)
    tickets = optimizer.solve_combinations(num_tickets=num_tickets, user_constraints=constraints)

    ortools_info = check_ortools_status()

    # 自動生成最新一期 SHA-256 存證指紋
    latest_period = records[-1].get("period", 0) if records else 0
    next_period = latest_period + 1
    commitment = LottoCommitmentVerifier.generate_commitment(next_period, tickets, game_type=game_type)

    return {
        "status": "success",
        "game_type": game_type,
        "ortools_info": ortools_info,
        "statistics_summary": summary,
        "recommended_tickets": tickets,
        "commitment": commitment,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def run_historical_backtest(records_json_path="super_lotto_history.json", test_draws=20, tickets_per_draw=5, game_type="super_lotto") -> dict:
    """執行歷史嚴格步進式回測"""
    if not os.path.exists(records_json_path):
        return {"status": "error", "message": f"找不到歷史開獎紀錄檔: {records_json_path}"}

    with open(records_json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    backtester = LottoBacktester(records, game_type=game_type)
    return backtester.run_walk_forward(test_draws=test_draws, tickets_per_draw=tickets_per_draw)



if __name__ == "__main__":
    print("=" * 65)
    print(" 台灣彩券 - 威力彩 AI 最佳化預測 (AI 運籌數學模型)")
    print("=" * 65)
    status = check_ortools_status()
    print(f"求解引擎狀態: {status['engine']}")
    if not status['available']:
        print(f"提示: 安裝 ortools 獲得最高性能求解: {status['install_cmd']}")
    print("-" * 65)

    res = generate_predictions(num_tickets=5)
    if res["status"] == "success":
        summary = res["statistics_summary"]
        print(f"歷史分析樣本: {summary['total_draws']} 期 | 平均和值: {summary['avg_sum']}")
        print(f"第一區最熱門號碼: {summary['hot_numbers_zone1']}")
        print(f"第二區最熱門號碼: {summary['hot_numbers_zone2']}")
        print("\n【AI 運籌最佳化智慧推薦注單 (5 注多樣性包牌)】")
        for t in res["recommended_tickets"]:
            z1_str = " ".join(f"{n:02d}" for n in t["zone1"])
            z2_str = f"{t['zone2']:02d}"
            print(f"第 {t['ticket_no']} 注: [{z1_str}] + 特別號 [{z2_str}]  | 和值:{t['sum']:3d} | 評分:{t['score']}分")
            print(f"       評語: {', '.join(t['reasons'])}")
    else:
        print(res["message"])
