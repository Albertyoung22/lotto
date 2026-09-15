# -*- coding: utf-8 -*-
import sys
import subprocess
import json
import py_compile

def run(cmd):
    print(f"==> CMD: {cmd}")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
        print(res.stderr.strip())
    return res.returncode

def main():
    print("=== 1. 語法檢查 (Syntax Validation) ===")
    for f in ["lotto_ai_optimizer.py", "lotto_gui.py", "app.py"]:
        print(f"Compiling {f}...")
        py_compile.compile(f, doraise=True)
    print("語法檢查通過！")

    print("\n=== 2. 五大策略求解測試 (Strategy Verification) ===")
    from lotto_ai_optimizer import generate_predictions
    res = generate_predictions("super_lotto_history.json", num_tickets=5)
    assert res["status"] == "success", f"Prediction failed: {res}"
    tickets = res["recommended_tickets"]
    assert len(tickets) == 5, f"Expected 5 tickets, got {len(tickets)}"
    for idx, t in enumerate(tickets):
        print(f"注 {t.get('ticket_no')}: {t.get('strategy')} | 球號: {t.get('zone1')} + {t.get('zone2')} | 評分: {t.get('score')} | 理由: {t.get('reasons')[:2]}")
    print("五大策略運籌求解驗證成功！")

    print("\n=== 3. 自動提交並推送至 GitHub ===")
    run("git rm -r --cached .github 2>nul")
    run("git add -A")
    commit_msg = "feat: upgrade AI with 5-strategy portfolio engine, arithmetic pattern defense & web UI"
    run(f'git commit -m "{commit_msg}"')
    ret = run("git push origin main")
    if ret == 0:
        print("[SUCCESS] Push completed: https://github.com/Albertyoung22/lotto")
    else:
        print("[INFO] Retrying push with upstream...")
        run("git push -u origin main")

if __name__ == "__main__":
    main()
