# -*- coding: utf-8 -*-
from datetime import datetime
from taiwan_lottery import download_lotto649_range

if __name__ == "__main__":
    cur_year = datetime.now().year
    print(f"開始抓取 2024 ~ {cur_year} 年大樂透歷史獎號...")
    download_lotto649_range(2024, cur_year, "lotto649_history.csv")
    print("大樂透歷史獎號抓取完成！")
