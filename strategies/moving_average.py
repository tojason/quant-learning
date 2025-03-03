"""
移动平均线策略模块

包含两种基本策略:
1. 简单移动平均线策略 - 价格与单一移动平均线的交叉
2. 移动平均线交叉策略 - 短期与长期移动平均线的交叉
"""

import backtrader as bt
import backtrader.indicators as btind
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class MovingAverageStrategy(bt.Strategy):
    """
    简单移动平均线策略 - 当价格上穿/下穿移动平均线时产生买入/卖出信号
    
    参数:
    - ma_period: 移动平均线周期
    - ma_type: 移动平均线类型 ('SMA', 'EMA', 'WMA')
    """
    params = (
        ('ma_period', 20),
        ('ma_type', 'SMA'),  # 可选: 'SMA', 'EMA', 'WMA'
        ('printlog', False),
    )
    
    def __init__(self):
        # 保存对收盘价的引用
        self.dataclose = self.datas[0].close
        
        # 跟踪挂单和成交价格
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # 选择移动平均线类型
        if self.p.ma_type == 'SMA':
            self.ma = btind.SimpleMovingAverage(self.datas[0], period=self.p.ma_period)
        elif self.p.ma_type == 'EMA':
            self.ma = btind.ExponentialMovingAverage(self.datas[0], period=self.p.ma_period)
        elif self.p.ma_type == 'WMA':
            self.ma = btind.WeightedMovingAverage(self.datas[0], period=self.p.ma_period)
        else:
            raise ValueError(f"不支持的移动平均线类型: {self.p.ma_type}")
        
        # 交叉信号
        self.crossover = bt.indicators.CrossOver(self.dataclose, self.ma)
        
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
        # 记录收盘价
        self.log(f'收盘价, {self.dataclose[0]:.2f}')
        
        # 检查是否有待处理的订单
        if self.order:
            return
            
        # 检查是否持仓
        if not self.position:
            # 如果没有持仓，检查是否有买入信号
            if self.crossover > 0:  # 收盘价上穿MA
                self.log(f'买入信号, 价格: {self.dataclose[0]:.2f}')
                self.order = self.buy()
        else:
            # 如果已持仓，检查是否有卖出信号
            if self.crossover < 0:  # 收盘价下穿MA
                self.log(f'卖出信号, 价格: {self.dataclose[0]:.2f}')
                self.order = self.sell()
    
    def stop(self):
        """策略结束时执行"""
        self.log(f'(MA周期 {self.p.ma_period}) 期末价值: {self.broker.getvalue():.2f}', doprint=True)


class MovingAverageCrossStrategy(bt.Strategy):
    """
    移动平均线交叉策略 - 当短期均线上穿/下穿长期均线时产生买入/卖出信号
    
    参数:
    - fast_period: 短期移动平均线周期
    - slow_period: 长期移动平均线周期
    - ma_type: 移动平均线类型 ('SMA', 'EMA', 'WMA')
    """
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('ma_type', 'SMA'),  # 可选: 'SMA', 'EMA', 'WMA'
        ('printlog', False),
    )
    
    def __init__(self):
        # 保存对收盘价的引用
        self.dataclose = self.datas[0].close
        
        # 跟踪挂单和成交价格
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # 选择移动平均线类型
        if self.p.ma_type == 'SMA':
            self.fast_ma = btind.SimpleMovingAverage(self.dataclose, period=self.p.fast_period)
            self.slow_ma = btind.SimpleMovingAverage(self.dataclose, period=self.p.slow_period)
        elif self.p.ma_type == 'EMA':
            self.fast_ma = btind.ExponentialMovingAverage(self.dataclose, period=self.p.fast_period)
            self.slow_ma = btind.ExponentialMovingAverage(self.dataclose, period=self.p.slow_period)
        elif self.p.ma_type == 'WMA':
            self.fast_ma = btind.WeightedMovingAverage(self.dataclose, period=self.p.fast_period)
            self.slow_ma = btind.WeightedMovingAverage(self.dataclose, period=self.p.slow_period)
        else:
            raise ValueError(f"不支持的移动平均线类型: {self.p.ma_type}")
        
        # 交叉信号
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
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
        # 记录收盘价
        self.log(f'收盘价, {self.dataclose[0]:.2f}')
        
        # 检查是否有待处理的订单
        if self.order:
            return
            
        # 检查是否持仓
        if not self.position:
            # 如果没有持仓，检查是否有买入信号
            if self.crossover > 0:  # 短期均线上穿长期均线
                self.log(f'买入信号, 价格: {self.dataclose[0]:.2f}')
                self.order = self.buy()
        else:
            # 如果已持仓，检查是否有卖出信号
            if self.crossover < 0:  # 短期均线下穿长期均线
                self.log(f'卖出信号, 价格: {self.dataclose[0]:.2f}')
                self.order = self.sell()
    
    def stop(self):
        """策略结束时执行"""
        self.log(f'(快线周期 {self.p.fast_period}, 慢线周期 {self.p.slow_period}) 期末价值: {self.broker.getvalue():.2f}', doprint=True) 