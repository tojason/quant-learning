"""
回测工具模块 - 使用backtrader库实现基础回测功能
"""
import backtrader as bt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

class PerformanceAnalyzer(object):
    """
    性能分析工具
    """
    @staticmethod
    def analyze_returns(returns, benchmark_returns=None):
        """
        分析策略收益表现
        
        参数:
        returns (pandas Series): 策略日收益率
        benchmark_returns (pandas Series, optional): 基准日收益率
        
        返回:
        dict: 性能指标字典
        """
        # 确保returns是pandas Series
        if not isinstance(returns, pd.Series):
            returns = pd.Series(returns)
            
        # 如果有基准，确保它也是pandas Series
        if benchmark_returns is not None and not isinstance(benchmark_returns, pd.Series):
            benchmark_returns = pd.Series(benchmark_returns)
        
        # 计算累计收益
        cum_returns = (1 + returns).cumprod() - 1
        
        # 计算年化收益率 (假设252个交易日)
        n_days = len(returns)
        n_years = n_days / 252
        annual_return = ((1 + cum_returns.iloc[-1]) ** (1 / n_years)) - 1
        
        # 计算波动率 (年化)
        daily_vol = returns.std()
        annual_vol = daily_vol * np.sqrt(252)
        
        # 计算夏普比率 (假设无风险利率为0)
        sharpe_ratio = annual_return / annual_vol if annual_vol > 0 else 0
        
        # 计算最大回撤
        rolling_max = cum_returns.cummax()
        drawdown = (cum_returns - rolling_max) / (1 + rolling_max)
        max_drawdown = drawdown.min()
        
        # 如果有基准收益率，计算相对指标
        alpha, beta = 0, 0
        if benchmark_returns is not None:
            # 确保基准收益率与策略收益率有相同的日期
            common_idx = returns.index.intersection(benchmark_returns.index)
            if len(common_idx) > 0:
                returns = returns.loc[common_idx]
                benchmark_returns = benchmark_returns.loc[common_idx]
                
                # 计算Beta (市场敏感度)
                covar = returns.cov(benchmark_returns)
                benchmark_var = benchmark_returns.var()
                beta = covar / benchmark_var if benchmark_var > 0 else 0
                
                # 计算Alpha (超额收益)
                benchmark_annual_return = ((1 + (1 + benchmark_returns).cumprod().iloc[-1]) ** (1 / n_years)) - 1
                alpha = annual_return - (beta * benchmark_annual_return)
        
        # 汇总结果
        results = {
            'Total Return': cum_returns.iloc[-1],
            'Annual Return': annual_return,
            'Annual Volatility': annual_vol,
            'Sharpe Ratio': sharpe_ratio,
            'Max Drawdown': max_drawdown,
            'Alpha': alpha,
            'Beta': beta
        }
        
        return results
    
    @staticmethod
    def plot_returns(returns, benchmark_returns=None, title="Strategy Performance"):
        """
        绘制策略收益曲线
        
        参数:
        returns (pandas Series): 策略日收益率
        benchmark_returns (pandas Series, optional): 基准日收益率
        title (str): 图表标题
        """
        plt.figure(figsize=(12, 8))
        
        # 计算累计收益
        cum_returns = (1 + returns).cumprod() - 1
        
        # 绘制策略收益曲线
        plt.plot(cum_returns.index, cum_returns.values, label='Strategy', linewidth=2)
        
        # 如果有基准，绘制基准收益曲线
        if benchmark_returns is not None:
            # 确保基准收益率与策略收益率有相同的日期
            common_idx = returns.index.intersection(benchmark_returns.index)
            if len(common_idx) > 0:
                benchmark_returns = benchmark_returns.loc[common_idx]
                cum_benchmark = (1 + benchmark_returns).cumprod() - 1
                plt.plot(cum_benchmark.index, cum_benchmark.values, label='Benchmark', linewidth=2, alpha=0.7)
        
        # 绘制零线
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 设置图表
        plt.title(title, fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Cumulative Returns', fontsize=12)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        
        return plt.gcf()

# 基本Backtrader策略模板 
class BasicStrategy(bt.Strategy):
    """
    Backtrader的基本策略模板
    """
    params = (
        ('sma_period', 20),
    )
    
    def __init__(self):
        # 初始化指标
        self.dataclose = self.data.close
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.sma_period)
        
        # 跟踪订单和交易状态
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # 策略信号
        self.signal = bt.indicators.CrossOver(self.data.close, self.sma)
    
    def log(self, txt, dt=None):
        """记录策略日志"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')
    
    def notify_order(self, order):
        """处理订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行, 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f'卖出执行, 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')
            
        self.order = None
    
    def notify_trade(self, trade):
        """处理交易结果通知"""
        if not trade.isclosed:
            return
            
        self.log(f'操作利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')
    
    def next(self):
        """
        策略核心逻辑，每个bar都会调用一次
        这里实现了一个简单的均线交叉策略
        """
        # 检查是否有未完成的订单
        if self.order:
            return
            
        # 检查是否持仓
        if not self.position:
            # 没有持仓，检查是否有买入信号
            if self.signal > 0:  # 收盘价上穿均线
                self.log(f'买入信号, 收盘价: {self.dataclose[0]:.2f}')
                self.order = self.buy()
        else:
            # 已有持仓，检查是否有卖出信号
            if self.signal < 0:  # 收盘价下穿均线
                self.log(f'卖出信号, 收盘价: {self.dataclose[0]:.2f}')
                self.order = self.sell()

# 回测执行器类
class BacktestRunner:
    """
    回测执行器
    """
    def __init__(self, strategy_class, data_feed, cash=100000.0, commission=0.001, **strategy_params):
        self.strategy_class = strategy_class
        self.data_feed = data_feed
        self.cash = cash
        self.commission = commission
        self.strategy_params = strategy_params
        
        # 初始化cerebro引擎
        self.cerebro = bt.Cerebro()
        self.cerebro.addstrategy(self.strategy_class, **self.strategy_params)
        
        # 添加数据
        self.cerebro.adddata(self.data_feed)
        
        # 设置初始资金和手续费
        self.cerebro.broker.setcash(self.cash)
        self.cerebro.broker.setcommission(commission=self.commission)
        
        # 添加分析器
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
    def run(self, plot=True, figsize=(15, 10)):
        """
        运行回测
        
        参数:
        plot (bool): 是否绘制结果图表
        figsize (tuple): 图表大小
        
        返回:
        dict: 回测结果
        """
        # 运行回测
        results = self.cerebro.run()
        strat = results[0]
        
        # 获取回测结果
        initial_value = self.cash
        final_value = self.cerebro.broker.getvalue()
        
        # 计算回报
        total_return = (final_value - initial_value) / initial_value
        
        # 获取分析器结果
        sharpe_ratio = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        if isinstance(sharpe_ratio, dict):
            sharpe_ratio = sharpe_ratio.get('sharperatio', 0)
            
        max_drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
        
        # 打印结果
        print(f"初始资金: {initial_value:.2f}")
        print(f"最终资金: {final_value:.2f}")
        print(f"总收益率: {total_return:.2%}")
        print(f"夏普比率: {sharpe_ratio:.4f}")
        print(f"最大回撤: {max_drawdown:.2%}")
        
        # 获取交易分析
        trade_analysis = strat.analyzers.trades.get_analysis()
        
        # 获取胜率
        total_trades = trade_analysis.get('total', {}).get('total', 0)
        won_trades = trade_analysis.get('won', {}).get('total', 0)
        win_rate = won_trades / total_trades if total_trades > 0 else 0
        
        # 获取平均收益
        won_pnl = trade_analysis.get('won', {}).get('pnl', 0)
        lost_pnl = trade_analysis.get('lost', {}).get('pnl', 0)
        avg_won = won_pnl / won_trades if won_trades > 0 else 0
        avg_lost = lost_pnl / (total_trades - won_trades) if (total_trades - won_trades) > 0 else 0
        
        print(f"交易次数: {total_trades}")
        print(f"胜率: {win_rate:.2%}")
        print(f"平均盈利: {avg_won:.2f}")
        print(f"平均亏损: {avg_lost:.2f}")
        
        # 绘制结果
        if plot:
            self.cerebro.plot(style='candle', figsize=figsize)
        
        # 返回结果汇总
        return {
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_won': avg_won,
            'avg_lost': avg_lost,
            'strategy': strat
        }

def create_bt_data_feed(df, timeframe=bt.TimeFrame.Days, start_date=None, end_date=None):
    """
    将pandas DataFrame转换为backtrader的DataFeed
    
    参数:
    df (pandas DataFrame): 股票数据，包含OHLCV列
    timeframe (backtrader.TimeFrame): 时间框架
    start_date (str or datetime, optional): 回测开始日期
    end_date (str or datetime, optional): 回测结束日期
    
    返回:
    backtrader.feed.DataFeed: 回测数据
    """
    # 确保索引是日期时间
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    # 如果有日期过滤
    if start_date is not None:
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        df = df[df.index >= start_date]
    
    if end_date is not None:
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        df = df[df.index <= end_date]
    
    # 将DataFrame转换为backtrader可用的DataFeed
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,  # 使用索引作为日期
        open='Open',
        high='High',
        low='Low',
        close='Close',
        volume='Volume',
        openinterest=-1  # 不使用openinterest
    )
    
    return data 