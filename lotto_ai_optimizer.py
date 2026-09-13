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
    """威力彩歷史數據特徵分析器"""
    def __init__(self, records: list):
        self.records = sorted(records, key=lambda x: x.get("period", 0))
        self.total_draws = len(self.records)
        self.zone1_freq = Counter()
        self.zone2_freq = Counter()
        self.zone1_recent_freq = Counter() # 近 30 期加權
        self.zone1_omission = {n: 0 for n in range(1, 39)}
        self.zone2_omission = {n: 0 for n in range(1, 9)}
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
        last_seen_z1 = {n: -1 for n in range(1, 39)}
        last_seen_z2 = {n: -1 for n in range(1, 9)}

        for idx, r in enumerate(self.records):
            size_balls = r.get("drawNumberSize", [])
            if len(size_balls) < 7:
                continue

            z1 = size_balls[:6]
            z2 = size_balls[6]

            # 總頻率
            for b in z1:
                self.zone1_freq[b] += 1
                last_seen_z1[b] = idx
            self.zone2_freq[z2] += 1
            last_seen_z2[z2] = idx

            # 近期加權頻率 (衰減指數)
            if idx >= recent_cutoff:
                weight = 1.0 + (idx - recent_cutoff) / recent_window
                for b in z1:
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

            # 大小比 (大數 20~38, 小數 1~19)
            highs = sum(1 for b in z1 if b >= 20)
            self.high_low_stats[f"{highs}:{6 - highs}"] += 1

        # 計算遺漏值 (距離最後一期隔了幾期未開)
        last_idx = self.total_draws - 1
        for n in range(1, 39):
            if last_seen_z1[n] != -1:
                self.zone1_omission[n] = last_idx - last_seen_z1[n]
            else:
                self.zone1_omission[n] = self.total_draws

        for n in range(1, 9):
            if last_seen_z2[n] != -1:
                self.zone2_omission[n] = last_idx - last_seen_z2[n]
            else:
                self.zone2_omission[n] = self.total_draws

    def get_summary(self) -> dict:
        """取得統計特徵摘要"""
        avg_sum = round(sum(self.sum_stats) / len(self.sum_stats), 1) if self.sum_stats else 117.0
        top_odds = self.odd_even_stats.most_common(2)
        top_hl = self.high_low_stats.most_common(2)

        # 最熱門與最冷門號碼
        hot_z1 = [num for num, _ in self.zone1_freq.most_common(6)]
        cold_z1 = [num for num, _ in sorted(self.zone1_freq.items(), key=lambda x: x[1])[:6]]
        max_omission_z1 = sorted(self.zone1_omission.items(), key=lambda x: x[1], reverse=True)[:5]

        hot_z2 = [num for num, _ in self.zone2_freq.most_common(3)]

        return {
            "total_draws": self.total_draws,
            "avg_sum": avg_sum,
            "recommended_sum_range": [85, 155],
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
        max_omiss = max(self.zone1_omission.values()) if self.zone1_omission else 1

        for n in range(1, 39):
            freq_score = (self.zone1_freq[n] / max_freq) * 45
            recent_score = (self.zone1_recent_freq[n] / (max_freq * 1.5 + 1e-5)) * 25
            
            # 遺漏適中 (常態分佈，太短或極端長適度補償)
            omiss = self.zone1_omission[n]
            # 遺漏在 3~12 期具有較高回補期望
            if 3 <= omiss <= 12:
                omiss_score = 25
            elif omiss > 12:
                omiss_score = 18
            else:
                omiss_score = 12

            total_w = int(freq_score + recent_score + omiss_score + random.uniform(0, 5))
            weights_z1[n] = max(10, total_w)

        # 第二區權重
        weights_z2 = {}
        max_freq_z2 = max(self.zone2_freq.values()) if self.zone2_freq else 1
        for n in range(1, 9):
            f_score = (self.zone2_freq[n] / max_freq_z2) * 60
            omiss_z2 = self.zone2_omission[n]
            omiss_score_z2 = 30 if 2 <= omiss_z2 <= 10 else 15
            weights_z2[n] = int(f_score + omiss_score_z2 + random.uniform(0, 5))

        return weights_z1, weights_z2


class GoogleORLotteryOptimizer:
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
        locked_z1 = set(constraints.get("locked_z1", []))
        excluded_z1 = set(constraints.get("excluded_z1", []))
        locked_z2 = constraints.get("locked_z2", None)

        sum_min = constraints.get("sum_min", 85)
        sum_max = constraints.get("sum_max", 155)

        # 追蹤已選球號以維持多注之間的多樣性 (包牌覆蓋率)
        chosen_patterns = []

        for ticket_idx in range(num_tickets):
            model = cp_model.CpModel()

            # 1. 決策變數
            # x[i] == 1 表示第 i 號被選中 (i = 1 .. 38)
            x = {i: model.NewBoolVar(f"x_{ticket_idx}_{i}") for i in range(1, 39)}

            # 2. 基本約束：第一區必須剛好選出 6 個號碼
            model.Add(sum(x[i] for i in range(1, 39)) == 6)

            # 3. 膽碼約束 (必選)
            for num in locked_z1:
                if 1 <= num <= 38:
                    model.Add(x[num] == 1)

            # 4. 殺號約束 (排除)
            for num in excluded_z1:
                if 1 <= num <= 38:
                    model.Add(x[num] == 0)

            # 5. 和值約束 (Sum Constraint)
            model.Add(sum(i * x[i] for i in range(1, 39)) >= sum_min)
            model.Add(sum(i * x[i] for i in range(1, 39)) <= sum_max)

            # 6. 奇偶比約束 (Parity Balance: 奇數顆數限制在 2~4 顆之間)
            odd_count = sum(x[i] for i in range(1, 39) if i % 2 == 1)
            model.Add(odd_count >= 2)
            model.Add(odd_count <= 4)

            # 7. 大小比約束 (High/Low Balance: 大數 20~38 限制在 2~4 顆之間)
            high_count = sum(x[i] for i in range(20, 39))
            model.Add(high_count >= 2)
            model.Add(high_count <= 4)

            # 8. 連號約束 (連續三顆號碼開出機率極低: x[i] + x[i+1] + x[i+2] <= 2)
            for i in range(1, 37):
                model.Add(x[i] + x[i + 1] + x[i + 2] <= 2)

            # 9. 多樣性約束 (避免與前幾注重複超過 3 個號碼，最大化號碼覆蓋率)
            for prev_balls in chosen_patterns:
                overlap = sum(x[num] for num in prev_balls)
                model.Add(overlap <= 3)

            # 10. 目標函數 (最大化綜合潛力分數 + 動態隨機微擾)
            obj_terms = []
            for i in range(1, 39):
                w = self.weights_z1[i]
                # 對前幾注已選號碼略為降權，促進廣泛覆蓋
                prior_usage = sum(1 for p in chosen_patterns if i in p)
                adjusted_w = max(5, w - prior_usage * 15 + random.randint(-4, 4))
                obj_terms.append(adjusted_w * x[i])

            model.Maximize(sum(obj_terms))

            # 求解
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 2.0
            status = solver.Solve(model)

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                selected_z1 = [i for i in range(1, 39) if solver.Value(x[i]) == 1]
                selected_z1.sort()
                chosen_patterns.append(selected_z1)

                # 第二區選擇 (若未鎖定，則挑選最佳潛力號碼)
                if locked_z2 and 1 <= locked_z2 <= 8:
                    selected_z2 = locked_z2
                else:
                    # 依 weights_z2 輪轉分配
                    z2_candidates = sorted(range(1, 9), key=lambda n: self.weights_z2[n] + random.randint(-5, 5), reverse=True)
                    selected_z2 = z2_candidates[ticket_idx % len(z2_candidates)]

                evaluation = self._evaluate_ticket(selected_z1, selected_z2)
                results.append({
                    "ticket_no": ticket_idx + 1,
                    "engine": "AI 運籌最佳化 (CP-SAT)",
                    "zone1": selected_z1,
                    "zone2": selected_z2,
                    "sum": sum(selected_z1),
                    "odd_even": f"{sum(1 for n in selected_z1 if n % 2 == 1)}:{sum(1 for n in selected_z1 if n % 2 == 0)}",
                    "high_low": f"{sum(1 for n in selected_z1 if n >= 20)}:{sum(1 for n in selected_z1 if n < 20)}",
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
        locked_z1 = set(constraints.get("locked_z1", []))
        excluded_z1 = set(constraints.get("excluded_z1", []))
        sum_min = constraints.get("sum_min", 85)
        sum_max = constraints.get("sum_max", 155)

        candidates = [n for n in range(1, 39) if n not in excluded_z1]
        
        # 依照權重進行機率抽樣
        weights = [self.weights_z1[n] for n in candidates]

        best_combo = None
        best_score = -1

        # 蒙地卡羅約束採樣
        for _ in range(1500):
            sample = set(locked_z1)
            remaining_needed = 6 - len(sample)
            available = [c for c in candidates if c not in sample]
            sub_weights = [self.weights_z1[c] for c in available]
            
            picked = random.choices(available, weights=sub_weights, k=remaining_needed * 2)
            for p in picked:
                sample.add(p)
                if len(sample) == 6:
                    break

            if len(sample) != 6:
                continue

            balls = sorted(list(sample))
            s = sum(balls)
            if not (sum_min <= s <= sum_max):
                continue

            odds = sum(1 for b in balls if b % 2 == 1)
            if not (2 <= odds <= 4):
                continue

            highs = sum(1 for b in balls if b >= 20)
            if not (2 <= highs <= 4):
                continue

            # 多樣性檢查
            too_similar = False
            for prev in prev_patterns:
                if len(set(balls).intersection(prev)) > 3:
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
            # 極端情況保底
            best_combo = sorted(random.sample([n for n in range(1, 39) if n not in excluded_z1], 6))

        # 第二區
        locked_z2 = constraints.get("locked_z2")
        if locked_z2 and 1 <= locked_z2 <= 8:
            z2 = locked_z2
        else:
            z2 = random.choices(range(1, 9), weights=[self.weights_z2[n] for n in range(1, 9)])[0]

        eval_res = self._evaluate_ticket(best_combo, z2)
        return {
            "engine": "啟發式約束優化器 (Heuristic Solver)",
            "zone1": best_combo,
            "zone2": z2,
            "sum": sum(best_combo),
            "odd_even": f"{sum(1 for n in best_combo if n % 2 == 1)}:{sum(1 for n in best_combo if n % 2 == 0)}",
            "high_low": f"{sum(1 for n in best_combo if n >= 20)}:{sum(1 for n in best_combo if n < 20)}",
            "score": eval_res["score"],
            "reasons": eval_res["reasons"]
        }

    def _evaluate_ticket(self, z1, z2) -> dict:
        """評估注單指標並給予 AI 評語與分數"""
        reasons = []
        score = 80

        s = sum(z1)
        if 100 <= s <= 135:
            score += 8
            reasons.append("和值黃金分佈區間 (100~135)")
        else:
            reasons.append(f"和值 {s} (常態範圍)")

        odds = sum(1 for n in z1 if n % 2 == 1)
        if odds in (3, ):
            score += 5
            reasons.append("奇偶比 3:3 完美平衡")
        elif odds in (2, 4):
            score += 3
            reasons.append(f"奇偶比 {odds}:{6-odds} 標準常態")

        highs = sum(1 for n in z1 if n >= 20)
        if highs in (3, ):
            score += 5
            reasons.append("大小號碼 3:3 均勻分佈")

        # 檢查冷熱號
        hot_count = sum(1 for n in z1 if n in self.analyzer.zone1_freq.most_common(10))
        if hot_count >= 2:
            score += 4
            reasons.append(f"包含 {hot_count} 顆歷史高頻熱門球")

        score = min(98, score)
        return {"score": score, "reasons": reasons}


def generate_predictions(records_json_path="super_lotto_history.json", num_tickets=5, constraints=None) -> dict:
    """供外界調用的主介面函數"""
    if not os.path.exists(records_json_path):
        return {"status": "error", "message": f"找不到歷史開獎紀錄檔: {records_json_path}"}

    with open(records_json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    analyzer = LottoAnalyzer(records)
    summary = analyzer.get_summary()

    optimizer = GoogleORLotteryOptimizer(analyzer)
    tickets = optimizer.solve_combinations(num_tickets=num_tickets, user_constraints=constraints)

    ortools_info = check_ortools_status()

    return {
        "status": "success",
        "ortools_info": ortools_info,
        "statistics_summary": summary,
        "recommended_tickets": tickets,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


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
