#!/usr/bin/env python
# run_optimization.py

import argparse
import sys
import os
import pandas as pd
import json
from datetime import datetime

from back_test.optimization import param_optimize_parallel  # 或 param_optimize
from strategy.boll_rsi import BollingerRSIStrategyV2

def load_data_from_cache_years(ticker: str, start_date: datetime, end_date: datetime,
                               interval: str = "5min", cache_dir: str = "cache") -> pd.DataFrame:
    """
    从本地 cache/ 文件夹里，逐年读取形如 aa_{ticker}_{year}_{interval}.pkl 的数据文件，
    并合并成一个完整 DataFrame，然后在内存中根据 [start_date, end_date] 做最终过滤。

    - 假设文件名格式: aa_{ticker}_{year}_{interval}.pkl (可按需修改)
    - 若某年份文件不存在，则此处会报错或跳过（可根据需求定制）
    """

    # 计算需要的年份列表
    start_year = start_date.year
    end_year = end_date.year

    all_dfs = []
    for year in range(start_year, end_year + 1):
        # 根据命名规则，构建缓存文件名
        cache_filename = f"aa_{ticker}_{year}_{interval}.pkl"
        cache_path = os.path.join(cache_dir, cache_filename)

        if not os.path.exists(cache_path):
            # 这里可以选择raise或跳过
            raise FileNotFoundError(f"找不到缓存文件: {cache_path}. 请确保你已提前下载并保存在此处。")

        print(f"加载 {year} 年缓存数据: {cache_filename}")
        df_year = pd.read_pickle(cache_path)

        if df_year.empty:
            print(f"[警告] {cache_filename} 数据为空, 跳过.")
            continue

        # 确保 index 是时间类型或有 'datetime' 列
        if isinstance(df_year.index, pd.DatetimeIndex):
            # 如果 index 就是 datetime，不需要 reset
            df_year = df_year.sort_index()
            df_year["datetime"] = df_year.index
        else:
            # 否则假设有 "datetime" 列
            if "datetime" not in df_year.columns:
                raise ValueError(f"DataFrame 缺少 datetime 列, 文件: {cache_filename}")
            df_year = df_year.sort_values(by="datetime")

        all_dfs.append(df_year)

    if not all_dfs:
        # 所有年份都没拼到数据
        print("[警告] 没有任何可用数据.")
        return pd.DataFrame()

    # 合并
    df_all = pd.concat(all_dfs, ignore_index=True)
    # 以 datetime 升序
    df_all = df_all.sort_values(by="datetime")
    df_all.reset_index(drop=True, inplace=True)

    # 最后在内存里过滤到 [start_date, end_date]
    # 确保 datetime 是 DatetimeIndex 或者可以loc筛选
    df_all = df_all[(df_all["datetime"] >= pd.to_datetime(start_date)) &
                    (df_all["datetime"] <= pd.to_datetime(end_date))]

    return df_all

def main():
    parser = argparse.ArgumentParser(description="Run optimization using local PKL cache data (yearly splitted).")

    parser.add_argument("--ticker", type=str, required=True, help="股票代码, e.g. TSLA")
    parser.add_argument("--start_date", type=str, required=True, help="开始日期, e.g. 2022-01-01")
    parser.add_argument("--end_date", type=str, required=True, help="结束日期, e.g. 2022-12-31")
    parser.add_argument("--interval", type=str, default="5min", help="数据频率, e.g. 5min, 15min, etc.")
    parser.add_argument("--cache_dir", type=str, default="cache", help="缓存文件夹, 默认'cache'")
    parser.add_argument("--output_csv", type=str, default="opt_results.csv", help="输出CSV文件")
    parser.add_argument("--output_json", type=str, default="opt_results.json", help="输出JSON文件")
    parser.add_argument("--max_workers", type=int, default=None, help="并行进程数")
    parser.add_argument("--initial_cash", type=float, default=100000, help="初始资金")

    args = parser.parse_args()

    start_dt = pd.to_datetime(args.start_date)
    end_dt = pd.to_datetime(args.end_date)

    # ========== 1) 从 cache 里按年份加载数据 ==========
    print(f"从 cache 读取 {args.ticker} {args.interval} 数据, 时间范围: {start_dt.date()} ~ {end_dt.date()}")
    df = load_data_from_cache_years(
        ticker=args.ticker,
        start_date=start_dt,
        end_date=end_dt,
        interval=args.interval,
        cache_dir=args.cache_dir
    )

    if df.empty:
        print("[警告] 读取到的 DataFrame 为空, 程序退出.")
        sys.exit(1)

    # 确保我们有 open/high/low/close/volume 列
    needed_cols = ["open", "high", "low", "close", "volume", "datetime"]
    missing = [c for c in needed_cols if c not in df.columns]
    if missing:
        print(f"[错误] DataFrame 缺少以下列: {missing}")
        sys.exit(1)

    # ========== 2) 构建 param_grid ==========
    param_grid = {
        "rsi_period": [10, 14],
        "rsi_overbought": [70, 75],
        "rsi_oversold": [25, 30],
        "bb_period": [20, 30],
        "bb_devfactor": [2.0, 2.5]
    }

    # ========== 3) 并行优化 ==========
    from back_test.optimization import param_optimize_parallel
    results_df, best_params = param_optimize_parallel(
        ticker=args.ticker,
        df=df,
        start_date=start_dt,
        end_date=end_dt,
        strategy_cls=BollingerRSIStrategyV2,
        param_grid=param_grid,
        initial_cash=args.initial_cash,
        sort_metric='sharpe_ratio',
        max_workers=args.max_workers
    )

    if results_df.empty:
        print("[警告] 结果 DataFrame 为空, 可能所有组合都没有交易或指标为 None.")
        sys.exit(0)

    # ========== 4) 保存结果 ==========
    results_df.to_csv(args.output_csv, index=False)
    print(f"[Info] 已保存优化结果到 CSV: {args.output_csv}")

    # 写 JSON
    records_json = results_df.to_dict(orient='records')
    out_json = {
        "results": records_json,
        "best_params": best_params
    }
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(out_json, f, ensure_ascii=False, indent=2)
    print(f"[Info] 已保存优化结果到 JSON: {args.output_json}")

    print("=== 最优参数 ===")
    print(best_params)

if __name__ == "__main__":
    main()
