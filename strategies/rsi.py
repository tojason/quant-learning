"""
相对强弱指数(RSI)策略模块

RSI是一种动量振荡指标，用来衡量价格变化的速度和变化的幅度。
RSI取值范围在0-100之间:
- 通常RSI高于70被认为是超买状态，可能会下跌
- 通常RSI低于30被认为是超卖状态，可能会上涨
"""

import backtrader as bt
import backtrader.indicators as btind
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class RSIStrategy(bt.Strategy):
    """
    RSI策略 - 基于RSI指标的超买超卖策略
    
    参数:
    - rsi_period: RSI计算周期
    - rsi_upper: RSI上限阈值，超过则卖出(默认70)
    - rsi_lower: RSI下限阈值，低于则买入(默认30)
    """
    params = (
        ('rsi_period', 14),
        ('rsi_upper', 70),
        ('rsi_lower', 30),
        ('printlog', False),
    )
    
    def __init__(self):
        # 保存对收盘价的引用
        self.dataclose = self.datas[0].close
        
        # 跟踪挂单和成交价格
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # 计算RSI指标
        self.rsi = btind.RSI(self.dataclose, period=self.p.rsi_period)
        
        # 用于绘图的指标
        self.rsi_upper_line = btind.LineNum(self.p.rsi_upper)
        self.rsi_lower_line = btind.LineNum(self.p.rsi_lower)
        
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
        # 记录RSI值
        self.log(f'收盘价: {self.dataclose[0]:.2f}, RSI: {self.rsi[0]:.2f}')
        
        # 检查是否有待处理的订单
        if self.order:
            return
            
        # 检查是否持仓
        if not self.position:
            # 如果没有持仓，检查是否有买入信号
            if self.rsi[0] < self.p.rsi_lower:  # RSI低于下限，超卖信号
                self.log(f'买入信号, RSI: {self.rsi[0]:.2f}, 价格: {self.dataclose[0]:.2f}')
                self.order = self.buy()
        else:
            # 如果已持仓，检查是否有卖出信号
            if self.rsi[0] > self.p.rsi_upper:  # RSI高于上限，超买信号
                self.log(f'卖出信号, RSI: {self.rsi[0]:.2f}, 价格: {self.dataclose[0]:.2f}')
                self.order = self.sell()
    
    def stop(self):
        """策略结束时执行"""
        self.log(f'(RSI周期 {self.p.rsi_period}, 上限 {self.p.rsi_upper}, 下限 {self.p.rsi_lower}) 期末价值: {self.broker.getvalue():.2f}', doprint=True) 