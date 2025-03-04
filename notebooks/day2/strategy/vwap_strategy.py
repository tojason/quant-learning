"""
VWAP策略模块 - 基于成交量加权平均价格实现的交易策略
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class VWAP(bt.Indicator):
    """
    VWAP (Volume Weighted Average Price) 指标实现
    Σ(成交价 × 成交量) / Σ(成交量)
    """
    lines = ('vwap',)
    params = (('period', 20),)  # 默认20天周期
    
    def __init__(self):
        # 初始化累计值
        self.cum_vol = 0
        self.cum_vol_price = 0
        
        # 存储历史数据
        self.volume_prices = []  # 存储 (volume, price) 对
    
    def next(self):
        # 计算典型价格 (TP)
        typical_price = (self.data.high[0] + self.data.low[0] + self.data.close[0]) / 3
        
        # 计算当前bar的交易量和交易量*价格
        current_vol = self.data.volume[0]
        current_vol_price = current_vol * typical_price
        
        # 添加当前数据到历史队列
        self.volume_prices.append((current_vol, current_vol_price))
        
        # 如果队列超过周期长度，移除最早的数据
        if len(self.volume_prices) > self.params.period:
            old_vol, old_vol_price = self.volume_prices.pop(0)
            self.cum_vol -= old_vol
            self.cum_vol_price -= old_vol_price
        
        # 累加当前数据
        self.cum_vol += current_vol
        self.cum_vol_price += current_vol_price
        
        # 计算VWAP
        if self.cum_vol > 0:
            self.lines.vwap[0] = self.cum_vol_price / self.cum_vol
        else:
            self.lines.vwap[0] = typical_price  # 如果没有交易量，使用典型价格


class VWAPStrategy(BaseStrategy):
    """
    基于成交量加权平均价(VWAP)的交易策略
    
    策略逻辑:
    1. 计算VWAP指标
    2. 当价格从下方突破VWAP且成交量增加时买入
    3. 当价格从上方跌破VWAP时卖出
    4. 同时使用止盈止损管理风险
    """
    params = (
        ('vwap_period', 20),       # VWAP计算周期
        ('volume_thresh', 1.5),    # 成交量阈值倍数
        ('stop_loss', 0.05),       # 止损比例
        ('take_profit', 0.10),     # 止盈比例
        # 继承BaseStrategy的参数
        ('log_level', BaseStrategy.LOG_LEVEL_INFO),
        ('collect_signals', True),
    )
    
    def __init__(self):
        # 调用父类初始化
        BaseStrategy.__init__(self)
        
        # 创建自定义的VWAP指标
        self.vwap = VWAP(self.data, period=self.params.vwap_period)
        
        # 创建成交量移动平均线指标
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.vwap_period)
            
        # 交叉信号
        self.price_cross_up_vwap = bt.indicators.CrossUp(self.data.close, self.vwap)
        self.price_cross_down_vwap = bt.indicators.CrossDown(self.data.close, self.vwap)
    
    def next(self):
        # 如果没有持仓
        if not self.position:
            # 当价格从下方突破VWAP且成交量放大时买入
            if (self.price_cross_up_vwap[0] and 
                self.data.volume[0] > self.volume_ma[0] * self.params.volume_thresh):
                
                price = self.data.close[0]
                max_shares = self.calc_max_shares(price)
                
                if max_shares > 0:
                    self.log(f'买入信号(VWAP上穿): 价格={price:.2f}, 数量={max_shares}, '
                            f'VWAP={self.vwap[0]:.2f}, 成交量={self.data.volume[0]}')
                    self.buy(size=max_shares)
                    self.buy_price = price
                    self.bar_executed = len(self)
                    
        # 如果有持仓
        else:
            # 当价格从上方跌破VWAP时卖出
            if self.price_cross_down_vwap[0]:
                self.log(f'卖出信号(VWAP下穿): 价格={self.data.close[0]:.2f}, '
                        f'VWAP={self.vwap[0]:.2f}, 持仓={self.position.size}')
                self.close()
                return
                
            # 止损
            if self.data.close[0] < self.buy_price * (1 - self.params.stop_loss):
                self.log(f'卖出信号(止损): 价格={self.data.close[0]:.2f}, 持仓={self.position.size}')
                self.close()
                return
                
            # 止盈
            if self.data.close[0] > self.buy_price * (1 + self.params.take_profit):
                self.log(f'卖出信号(止盈): 价格={self.data.close[0]:.2f}, 持仓={self.position.size}')
                self.close()
                return