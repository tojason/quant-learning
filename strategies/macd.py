"""
MACD(Moving Average Convergence Divergence)策略模块

MACD是一种趋势跟踪动量指标，显示了两条移动平均线之间的关系。
MACD由三部分组成：
- MACD线：快速EMA(通常12周期) - 慢速EMA(通常26周期)
- 信号线：MACD线的EMA(通常9周期)
- 柱状图：MACD线 - 信号线

当MACD线上穿信号线时产生买入信号，下穿信号线时产生卖出信号。
"""

import backtrader as bt
import backtrader.indicators as btind
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class MACDStrategy(bt.Strategy):
    """
    MACD策略 - 基于MACD指标的趋势跟踪策略
    
    参数:
    - fast_ema: 快速EMA周期
    - slow_ema: 慢速EMA周期
    - signal_ema: 信号线EMA周期
    """
    params = (
        ('fast_ema', 12),
        ('slow_ema', 26),
        ('signal_ema', 9),
        ('printlog', False),
    )
    
    def __init__(self):
        # 保存对收盘价的引用
        self.dataclose = self.datas[0].close
        
        # 跟踪挂单和成交价格
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # 计算MACD指标
        self.macd = btind.MACD(
            self.dataclose,
            period_me1=self.p.fast_ema,
            period_me2=self.p.slow_ema,
            period_signal=self.p.signal_ema
        )
        
        # 为方便访问，分别保存MACD的三个部分
        self.macd_line = self.macd.macd
        self.signal_line = self.macd.signal
        self.histogram = self.macd.histogram
        
        # 计算信号
        self.crossover = btind.CrossOver(self.macd_line, self.signal_line)
        
    def log(self, txt, dt=None, doprint=False):
        """记录日志"""
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')
            
    def notify_order(self, order):
        """处理订单通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 等待订单执行
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f'卖出执行价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单被取消/拒绝')
            
        # 重置订单引用
        self.order = None
        
    def notify_trade(self, trade):
        """处理交易通知"""
        if not trade.isclosed:
            return
            
        self.log(f'交易利润, 毛利: {trade.pnl:.2f}, 净利: {trade.pnlcomm:.2f}')
    
    def next(self):
        """每个bar执行一次的主要策略逻辑"""
        # 记录MACD值
        self.log(f'收盘价: {self.dataclose[0]:.2f}, MACD: {self.macd_line[0]:.4f}, 信号线: {self.signal_line[0]:.4f}, 柱状图: {self.histogram[0]:.4f}')
        
        # 检查是否有待处理的订单
        if self.order:
            return
            
        # 检查是否持仓
        if not self.position:
            # 如果没有持仓，检查是否有买入信号
            if self.crossover > 0:  # MACD线上穿信号线
                self.log(f'买入信号, MACD上穿信号线, 价格: {self.dataclose[0]:.2f}')
                self.order = self.buy()
        else:
            # 如果已持仓，检查是否有卖出信号
            if self.crossover < 0:  # MACD线下穿信号线
                self.log(f'卖出信号, MACD下穿信号线, 价格: {self.dataclose[0]:.2f}')
                self.order = self.sell()
    
    def stop(self):
        """策略结束时执行"""
        self.log(f'(MACD参数: 快EMA {self.p.fast_ema}, 慢EMA {self.p.slow_ema}, 信号EMA {self.p.signal_ema}) 期末价值: {self.broker.getvalue():.2f}', doprint=True) 