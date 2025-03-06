import backtrader as bt
import pandas as pd
from typing import Dict, List, Any, Tuple

def optimize_strategy(
    ticker: str,
    df: pd.DataFrame,
    strategy,  
    start_date,
    end_date,
    freq: int,
    param_grid: Dict[str, List[Any]],
    initial_cash: float = 100000.0,
    max_cpus: int = 1
) -> Tuple[Dict[str, Any], float, List[Tuple[Dict[str, Any], float]]]:
    """
    使用 Backtrader 对给定策略及参数网格进行优化。
    返回：
        - best_params: 最优参数组合（根据最终资金最大化）
        - best_value: 最优参数组合对应的回测结束资金
        - all_results: (params, final_value) 的列表，用于查看所有组合结果。
        
    参数：
        df          : 已经经过预处理（flatten, standardize等）的行情数据（必须包含 'datetime' 列）。
        strategy    : Backtrader 策略类。
        start_date  : 回测起始日期 (datetime)。
        end_date    : 回测结束日期 (datetime)。
        param_grid  : 策略参数网格，例如：{"period": [10,14], "overbought": [70,80], "oversold": [30,20]}。
        initial_cash: 初始资金。
        max_cpus    : 并行 CPU 数量（1 表示单核；-1 表示尽量使用多核）。
    """
    cerebro = bt.Cerebro(optreturn=False)  # optreturn=False: 方便获取最终资金
    
    # 添加待优化策略 (注意这里用 optstrategy)
    # 假设 param_grid 是一个字典，如 {"period": [12,14], "overbought": [70,80], "oversold": [20,30]}
    cerebro.optstrategy(
        strategy,
        **param_grid  # 解包 dict 来指定所有的可选参数
    )

    # 构建数据源
    data_feed = bt.feeds.PandasData(
        dataname=df,
        datetime='datetime',
        timeframe=bt.TimeFrame.Minutes,
        compression=freq,
        fromdate=start_date,
        todate=end_date
    )
    data_feed._name = ticker
    data_feed.plotinfo.plotname = ticker
    cerebro.adddata(data_feed)

    cerebro.broker.setcash(initial_cash)

    # 执行优化；返回结果会是一个双层列表，每个组合对应一个 list
    # maxcpus = 1 表示只用一个CPU并行，也可以根据机器性能设置不同的CPU数
    results = cerebro.run(maxcpus=max_cpus)

    # 解析所有组合的结果
    all_results = []
    for run in results:  
        # run 是一个列表，里面通常只有1个 strategy 实例（若有多策略则另行处理）
        for strategy_instance in run:
            # 获取该实例最终资金
            final_value = strategy_instance.broker.getvalue()
            # 获取该实例对应的策略参数，注意 params 是一个 AttributeDict
            # 可通过 strategy_instance.params._getkwargs() 来获取
            params_dict = dict(strategy_instance.params._getkwargs())
            # 也可对 params_dict 做进一步处理
            all_results.append((params_dict, final_value))

    # 根据最终资金进行降序排序，选取第一名
    all_results.sort(key=lambda x: x[1], reverse=True)
    best_params, best_value = all_results[0]

    return best_params, best_value, all_results
