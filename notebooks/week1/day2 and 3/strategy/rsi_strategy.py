import backtrader as bt
from .base_strategy import BaseStrategy

class RSIStrategy(BaseStrategy):
    """
    基于RSI指标的交易策略

    策略逻辑：
    1. 当RSI指标从超卖区域（低于设定的rsi_oversold）向上突破时，产生买入信号；
    2. 当RSI指标从超买区域（高于设定的rsi_overbought）向下突破时，产生卖出信号；
    3. 为防止频繁交易，信号之间需要满足一定的间隔（min_bars_between_signals）。
    
    参数说明：
      - rsi_period: RSI计算周期，默认14
      - rsi_oversold: 超卖阈值，默认30
      - rsi_overbought: 超买阈值，默认70
      - min_bars_between_signals: 信号间至少等待的Bar数量，默认3
      - log_level, collect_signals: 继承自BaseStrategy的日志及信号收集参数
    """
    params = (
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('min_bars_between_signals', 3),
        ('log_level', BaseStrategy.LOG_LEVEL_INFO),
        ('collect_signals', True),
    )
    
    def __init__(self):
        super().__init__()
        # 初始化RSI指标
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        # 用于限制信号间隔，防止过于频繁的交易
        self.last_signal_bar = -self.params.min_bars_between_signals

    def next(self):
        super().next()  # 记录资产净值
        current_bar = len(self)
        
        # 如果距离上次信号未达到设定间隔，则不生成信号
        if current_bar - self.last_signal_bar < self.params.min_bars_between_signals:
            return
        
        # 没有持仓时检查买入信号
        if not self.position:
            # 当RSI从超卖区域向上突破（当前RSI > rsi_oversold且前一BarRSI<=rsi_oversold）时，买入
            if self.rsi[0] > self.params.rsi_oversold and self.rsi[-1] <= self.params.rsi_oversold:
                self.execute_buy()
        else:
            # 持仓时检查卖出信号：RSI从超买区域向下突破（当前RSI < rsi_overbought且前一BarRSI>=rsi_overbought）时，卖出
            if self.rsi[0] < self.params.rsi_overbought and self.rsi[-1] >= self.params.rsi_overbought:
                self.execute_sell()
    
    def execute_buy(self):
        """
        执行买入操作：计算可买数量并下买单，同时记录信号和日志
        """
        price = self.data.close[0]
        size = self.calc_max_shares(price)
        if size <= 0:
            return
        self.order = self.buy(size=size)
        self.last_signal_bar = len(self)
        self.log(f'RSI买入信号: 价格={price:.2f}, 数量={size}')

    def execute_sell(self):
        """
        执行卖出操作：全仓卖出，并记录信号和日志
        """
        if self.position:
            price = self.data.close[0]
            size = self.position.size
            self.order = self.sell(size=size)
            self.last_signal_bar = len(self)
            self.log(f'RSI卖出信号: 价格={price:.2f}, 数量={size}')
