"""
回测工具模块

这个模块包含了执行回测相关的函数。
"""

import backtrader as bt
import pandas as pd
import numpy as np

def run_backtest(df, strategy_class, strategy_params=None, 
               initial_cash=100000.0, commission=0.001):
    """
    运行回测，返回结果和策略实例
    
    参数:
    df (pandas.DataFrame): 包含OHLCV数据的DataFrame
    strategy_class (bt.Strategy): 回测使用的策略类
    strategy_params (dict): 策略参数字典
    initial_cash (float): 初始资金
    commission (float): 交易佣金比例
    
    返回:
    tuple: (回测结果字典, 策略实例)
    """
    # 创建cerebro引擎
    cerebro = bt.Cerebro()
    
    # 添加策略
    if strategy_params:
        cerebro.addstrategy(strategy_class, **strategy_params)
    else:
        cerebro.addstrategy(strategy_class)
    
    # 添加数据
    # 确保日期在索引或者有trade_time列
    if not isinstance(df.index, pd.DatetimeIndex) and 'trade_time' in df.columns:
        df = df.copy()
        df['trade_time'] = pd.to_datetime(df['trade_time'])
        df.set_index('trade_time', inplace=True)
    
    # 创建用于backtrader的PandasData类
    class PandasDataCustom(bt.feeds.PandasData):
        params = (
            ('datetime', None),  # 使用索引作为日期
            ('open', 'open'),
            ('high', 'high'),
            ('low', 'low'),
            ('close', 'close'),
            ('volume', 'vol' if 'vol' in df.columns else 'volume' if 'volume' in df.columns else None),
            ('openinterest', None)  # 不使用持仓量数据
        )
    
    # 添加数据源
    data = PandasDataCustom(dataname=df)
    cerebro.adddata(data)
    
    # 设置初始资金和佣金
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=commission)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade')
    
    # 运行回测
    print(f'初始资金: {initial_cash:.2f}')
    results = cerebro.run()
    strat = results[0]
    
    # 获取回测结果数据
    final_value = cerebro.broker.getvalue()
    total_return = (final_value - initial_cash) / initial_cash * 100
    
    sharpe_ratio = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0.0)
    if np.isnan(sharpe_ratio):
        sharpe_ratio = 0.0
    
    max_drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)
    
    # 获取交易分析
    trade_analysis = strat.analyzers.trade.get_analysis()
    
    total_trades = trade_analysis.get('total', {}).get('total', 0)
    
    winning_trades = trade_analysis.get('won', {}).get('total', 0)
    losing_trades = trade_analysis.get('lost', {}).get('total', 0)
    
    if total_trades > 0:
        win_rate = winning_trades / total_trades * 100
    else:
        win_rate = 0.0
    
    # 打印回测结果
    print(f'最终资金: {final_value:.2f}')
    print(f'总收益率: {total_return:.2f}%')
    print(f'夏普比率: {sharpe_ratio:.2f}')
    print(f'最大回撤: {max_drawdown:.2f}%')
    print(f'总交易次数: {total_trades}')
    print(f'胜率: {win_rate:.2f}%')
    
    # 获取交易信号
    signals = strat.get_signals()
    
    # 返回回测结果和策略实例
    return {
        'initial_cash': initial_cash,
        'final_value': final_value,
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'signals': signals  # 包含买卖信号
    }, strat