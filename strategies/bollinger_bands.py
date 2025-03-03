"""
布林带(Bollinger Bands)策略模块

布林带是一种基于统计的波动率通道，由三条线组成：
- 中轨：通常是N周期的简单移动平均线
- 上轨：中轨 + K倍标准差
- 下轨：中轨 - K倍标准差

当价格接近上轨时，表明可能超买；当价格接近下轨时，表明可能超卖。
"""

import backtrader as bt
import backtrader.indicators as btind
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class BollingerBandsStrategy(bt.Strategy):
    """
    布林带策略 - 当价格触及或接近布林带边界时产生交易信号
    
    参数:
    - bb_period: 布林带周期
    - bb_devfactor: 布林带标准差倍数
    - position_size: 仓位大小(0-1)，表示每次交易使用的资金比例
    """
    params = (
        ('bb_period', 20),
        ('bb_devfactor', 2.0),  # 标准差倍数
        ('position_size', 1.0),  # 默认使用全部可用资金
        ('printlog', False),
    )
    
    def __init__(self):
        # 保存对收盘价的引用
        self.dataclose = self.datas[0].close
        
        # 跟踪挂单和成交价格
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # 计算布林带指标
        self.bb = btind.BollingerBands(
            self.dataclose, 
            period=self.p.bb_period, 
            devfactor=self.p.bb_devfactor
        )
        
        # 为方便访问，分别保存布林带的三条线
        self.bb_top = self.bb.top  # 上轨
        self.bb_mid = self.bb.mid  # 中轨
        self.bb_bot = self.bb.bot  # 下轨
        
        # 计算收盘价与布林带的相对位置 (0-100)
        # 当收盘价位于下轨时为0，位于上轨时为100
        self.bb_pct = btind.DivByZero(
            (self.dataclose - self.bb_bot), 
            (self.bb_top - self.bb_bot), 
            100
        )
        
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
        # 记录价格和布林带位置
        self.log(f'收盘价: {self.dataclose[0]:.2f}, BB%位置: {self.bb_pct[0]:.2f}%, 上轨: {self.bb_top[0]:.2f}, 中轨: {self.bb_mid[0]:.2f}, 下轨: {self.bb_bot[0]:.2f}')
        
        # 检查是否有待处理的订单
        if self.order:
            return
            
        # 检查是否持仓
        if not self.position:
            # 如果没有持仓，检查是否有买入信号
            if self.dataclose[0] <= self.bb_bot[0]:  # 价格触及下轨
                # 计算买入数量 (基于资金和仓位大小参数)
                size = self.broker.getcash() * self.p.position_size / self.dataclose[0]
                size = int(size)  # 确保是整数
                
                if size > 0:
                    self.log(f'买入信号, 价格: {self.dataclose[0]:.2f}, 数量: {size}')
                    self.order = self.buy(size=size)
        else:
            # 如果已持仓，检查是否有卖出信号
            if self.dataclose[0] >= self.bb_top[0]:  # 价格触及上轨
                self.log(f'卖出信号, 价格: {self.dataclose[0]:.2f}')
                self.order = self.sell()
            elif self.dataclose[0] >= self.bb_mid[0] and self.bb_pct[0] >= 80:
                # 额外的平仓条件：价格高于中轨且靠近上轨 (80%位置)
                self.log(f'平仓信号(BB中上区), 价格: {self.dataclose[0]:.2f}')
                self.order = self.sell()
    
    def stop(self):
        """策略结束时执行"""
        self.log(f'(BB周期 {self.p.bb_period}, 偏差倍数 {self.p.bb_devfactor}) 期末价值: {self.broker.getvalue():.2f}', doprint=True) 