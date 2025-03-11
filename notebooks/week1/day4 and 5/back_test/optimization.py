import itertools
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from .backtesting import run_backtest  # 确保 run_backtest 可被子进程导入

def _worker_run_backtest(ticker, df, start_date, end_date,
                         strategy_cls, initial_cash, combo_dict):
    """
    辅助函数：给每个进程使用的工作函数。
    传入 combo_dict 等参数，内部调用 run_backtest 并返回 {参数 + 结果} 的字典。
    """
    # 这里可以做任何你想要的预处理，比如把 float 转成 int...
    # combo_dict['rsi_period'] = int(combo_dict['rsi_period'])

    result_dict, _ = run_backtest(
        ticker=ticker,
        df=df,
        start_date=start_date,
        end_date=end_date,
        strategy=strategy_cls,
        initial_cash=initial_cash,
        strategy_params=combo_dict,
        print_log=False  # 避免在并行时打印大量日志
    )

    # 合并参数和结果
    row_data = {**combo_dict, **result_dict}
    return row_data


def param_optimize_parallel(ticker, df, start_date, end_date, strategy_cls, param_grid, 
                           initial_cash=100000, sort_metric='sharpe_ratio',
                           max_workers=None):
    """
    使用 run_backtest 函数对 param_grid 中的所有参数组合进行回测(并行模式)，
    并按 sort_metric 排序返回结果。

    参数：
    - ticker, df, start_date, end_date, strategy_cls, initial_cash: 
      与 run_backtest 相同，不再多解释。
    - param_grid: dict, 形如:
        {
          'rsi_period': [10, 14],
          'bb_period': [20, 30],
          ...
        }
    - sort_metric:   按哪个指标来排序，例如 'sharpe_ratio', 'final_value', 'rnorm', ...
    - max_workers:   并行进程数, 默认为 None(等于CPU核心数)

    返回:
    - results_df: 记录所有组合及其回测指标的 DataFrame
    - best_params: 表现最优的参数组合（基于 sort_metric）
    """
    param_names = list(param_grid.keys())
    all_combos = list(itertools.product(*param_grid.values()))

    # 存放每个参数组合回测后的结果
    results_list = []

    # 使用 ProcessPoolExecutor 并行执行
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_combo = {}
        for combo in all_combos:
            combo_dict = dict(zip(param_names, combo))
            future = executor.submit(
                _worker_run_backtest,
                ticker, df, start_date, end_date, strategy_cls, initial_cash, combo_dict
            )
            future_to_combo[future] = combo_dict

        # 收集执行结果
        for future in as_completed(future_to_combo):
            combo_dict = future_to_combo[future]
            try:
                row_data = future.result()
                results_list.append(row_data)
            except Exception as e:
                # 如果某个组合运行报错，可以在这里打印或记录
                print(f"[警告] 参数 {combo_dict} 回测时出错: {e}")
                # 也可选择 continue 或其他处理

    # 整理结果为 DataFrame
    results_df = pd.DataFrame(results_list)

    # 如果 sort_metric 不在列里，先给个警告
    if not results_df.empty and sort_metric not in results_df.columns:
        print(f"[警告] sort_metric='{sort_metric}' 不存在于结果列中，将使用 'final_value' 排序。")
        sort_metric = 'final_value'

    # 如果结果为空或sort_metric全是NaN
    if results_df.empty or results_df[sort_metric].dropna().empty:
        print(f"[警告] 排序指标 '{sort_metric}' 全为 None 或 NaN, 或 results_df 为空，无法排序！")
        return results_df, {}

    # 排序(默认从大到小)
    results_df.sort_values(by=sort_metric, ascending=False, inplace=True)

    best_row = results_df.iloc[0].to_dict()
    best_params = {k: best_row[k] for k in param_names if k in best_row}

    return results_df, best_params

def param_optimize(ticker, df, start_date, end_date, strategy_cls, param_grid, 
                   initial_cash=100000, sort_metric='sharpe_ratio'):
    """
    使用 run_backtest 函数对 param_grid 中的所有参数组合进行回测，
    并按 sort_metric 排序返回结果。

    参数：
    - ticker, df, start_date, end_date, strategy_cls, initial_cash: 
      与 run_backtest 相同，不再多解释。
    - param_grid: dict，形如:
        {
          'rsi_period': [10, 14],
          'bb_period': [20, 30],
          ...
        }
    - sort_metric: 按哪个指标来排序，例如 'sharpe_ratio', 'final_value', 'rnorm', ...

    返回:
    - results_df: 记录所有组合及其回测指标的 DataFrame
    - best_params: 表现最优的参数组合（基于 sort_metric）
    """
    results_list = []
    param_names = list(param_grid.keys())
    all_combos = list(itertools.product(*param_grid.values()))

    for combo in all_combos:
        combo_dict = dict(zip(param_names, combo))
        # 调用 run_backtest，这里可设置 print_log=False，避免大量日志输出
        result_dict, _ = run_backtest(
            ticker=ticker,
            df=df,
            start_date=start_date,
            end_date=end_date,
            strategy=strategy_cls,
            initial_cash=initial_cash,
            strategy_params=combo_dict,
            print_log=False
        )

        # 合并参数组合和回测结果
        row_data = {**combo_dict, **result_dict}
        results_list.append(row_data)

    # 整理成 DataFrame
    results_df = pd.DataFrame(results_list)

    # 如果 sort_metric 不在列里，先给个警告
    if sort_metric not in results_df.columns:
        print(f"[警告] sort_metric='{sort_metric}' 不存在于结果列中，将使用 'final_value' 排序。")
        sort_metric = 'final_value'

    # 排序前，先看里面是否都是 NaN
    if results_df[sort_metric].dropna().empty:
        print(f"[警告] 排序指标 '{sort_metric}' 全为 None 或 NaN, 无法排序！")
        # 直接返回即可
        return results_df, {}

    # 排序(默认从大到小)
    results_df.sort_values(by=sort_metric, ascending=False, inplace=True)
    best_row = results_df.iloc[0].to_dict()

    # 抽取最优参数
    best_params = {k: best_row[k] for k in param_names if k in best_row}

    return results_df, best_params
