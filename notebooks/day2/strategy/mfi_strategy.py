import backtrader as bt
from .base_strategy import BaseStrategy
from indicator.mfi import MFI

class MFIStrategy(BaseStrategy):
    """
    改进后的MFI背离策略主要优化点：
    1. 动态止盈止损机制
    2. 极值检测灵敏度提升
    3. 增加趋势过滤
    4. 优化信号间隔逻辑
    """
    params = (
        ('mfi_period', 14),
        ('mfi_oversold', 25),         # 放宽超卖阈值
        ('mfi_overbought', 75),       # 放宽超买阈值
        ('divergence_lookback', 50),  # 延长背离检测窗口
        ('swing_lookback', 3),        # 缩短极值检测窗口
        ('stop_loss', 0.03),          # 收紧止损
        ('take_profit', 0.15),        # 扩大止盈
        ('trailing_stop', 0.03),      # 新增跟踪止损比例
        ('min_bars_between_signals', 3),  # 缩短信号间隔
        ('use_trend_filter', True),   # 启用趋势过滤
        # 继承参数
        ('log_level', BaseStrategy.LOG_LEVEL_INFO),
        ('collect_signals', True),
    )

    def __init__(self):
        super().__init__()
        
        # 核心指标
        self.mfi = MFI(self.data, period=self.params.mfi_period)
        self.swing_low = bt.indicators.Lowest(self.data.close, 
                            period=self.params.swing_lookback+1)
        self.swing_high = bt.indicators.Highest(self.data.close,
                            period=self.params.swing_lookback+1)
        
        # 趋势过滤指标
        if self.params.use_trend_filter:
            self.ma200 = bt.indicators.SMA(self.data.close, period=200)
            self.ma50 = bt.indicators.SMA(self.data.close, period=50)
        
        # 状态变量
        self.peak_price = None  # 用于跟踪止损
        self.order = None
        self.last_signal_bar = -self.params.min_bars_between_signals

    def next(self):
        current_bar = len(self)
        
        # 订单处理优先
        if self.order:
            return
        
        # 信号间隔检查
        if current_bar - self.last_signal_bar < self.params.min_bars_between_signals:
            return
        
        # 主逻辑
        if not self.position:
            if self.check_entry_signals():  # 移除了current_bar参数
                self.execute_buy()
        else:
            if self.check_exit_signals():  # 移除了current_bar参数
                self.execute_sell()
            self.check_stop_conditions()

    def check_entry_signals(self):
        """综合入场条件检查"""
        # 趋势过滤
        if self.params.use_trend_filter:
            if self.data.close[0] < self.ma200[0] or self.ma50[0] < self.ma200[0]:
                return False
        
        # MFI超卖区域突破
        mfi_cross_up = (self.mfi[0] > self.params.mfi_oversold and 
                       self.mfi[-1] <= self.params.mfi_oversold)
        
        # 有效看涨背离
        bullish_div = self.check_bullish_divergence()
        
        return mfi_cross_up and bullish_div

    def check_exit_signals(self):
        """综合出场条件检查"""
        # 常规止盈止损
        if self.check_stop_conditions():
            return True
        
        # MFI超买区域突破
        mfi_cross_down = (self.mfi[0] < self.params.mfi_overbought and 
                         self.mfi[-1] >= self.params.mfi_overbought)
        
        # 有效看跌背离
        bearish_div = self.check_bearish_divergence()
        
        return mfi_cross_down or bearish_div

    def update_swings(self):
        """改进的极值检测：价格极值+MFI确认"""
        # 价格低点且MFI低于超卖阈值
        if self.data.close[0] == self.swing_low[0] and self.mfi[0] < self.params.mfi_oversold+5:
            self._add_swing_point(self.price_lows, self.mfi_lows)
        
        # 价格高点且MFI高于超买阈值
        if self.data.close[0] == self.swing_high[0] and self.mfi[0] > self.params.mfi_overbought-5:
            self._add_swing_point(self.price_highs, self.mfi_highs)

    def check_bullish_divergence(self):
        """改进的看涨背离检测"""
        if len(self.price_lows) < 2:
            return False
        
        (curr_bar, curr_price), (prev_bar, prev_price) = self.price_lows[-2:]
        (_, curr_mfi), (_, prev_mfi) = self.mfi_lows[-2:]
        
        # 时间有效性+价格新低+MFI抬高
        return (curr_bar - prev_bar <= self.params.divergence_lookback and
                curr_price < prev_price and 
                curr_mfi > prev_mfi)

    def update_trailing_stop(self):
        """动态更新跟踪止损点"""
        if self.peak_price is None or self.data.high[0] > self.peak_price:
            self.peak_price = self.data.high[0]
            
    def check_stop_conditions(self):
        """综合止损检查"""
        current_price = self.data.close[0]
        
        # 硬止损
        if current_price <= self.buy_price * (1 - self.params.stop_loss):
            self.log(f'触发硬止损@ {current_price:.2f}')
            return True
        
        # 止盈
        if current_price >= self.buy_price * (1 + self.params.take_profit):
            self.log(f'触发止盈@ {current_price:.2f}')
            return True
        
        # 跟踪止损
        if self.peak_price and current_price <= self.peak_price * (1 - self.params.trailing_stop):
            self.log(f'触发跟踪止损@ {current_price:.2f}')
            return True
        
        return False

    # 保留其他辅助方法...