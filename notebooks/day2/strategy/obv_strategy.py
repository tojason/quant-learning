import backtrader as bt
import numpy as np
from indicator.obv import OnBalanceVolume
from .base_strategy import BaseStrategy

class OBVStrategy(BaseStrategy):
    """
    基于OBV(On-Balance Volume)的交易策略
    
    OBV是一种累积交易量的技术指标，通过将每日成交量根据价格变动的方向进行累加或减去，
    用于确认价格趋势。当价格和OBV同向变动时，表明趋势有效；当出现背离时，可能预示着
    趋势的转变。
    
    策略逻辑：
    1. 买入条件：
       - OBV上穿其EMA且价格在其EMA上方
       - 或者出现正背离（价格下跌但OBV上升）
    
    2. 卖出条件：
       - OBV下穿其EMA且价格在其EMA下方
       - 或者出现负背离（价格上涨但OBV下降）
    """
    
    params = (
        ('obv_ema_period', 20),    # OBV均线周期
        ('price_ema_period', 20),  # 价格均线周期
        ('log_level', BaseStrategy.LOG_LEVEL_INFO),  # 日志级别
        ('collect_signals', True),  # 是否收集交易信号
    )
    
    def __init__(self):
        # 调用父类构造函数
        super(OBVStrategy, self).__init__()
        
        # 计算OBV指标
        self.obv = OnBalanceVolume(self.data)
        
        # 计算OBV的EMA
        self.obv_ema = bt.indicators.ExponentialMovingAverage(self.obv, period=self.params.obv_ema_period)
        
        # 计算价格的EMA
        self.price_ema = bt.indicators.ExponentialMovingAverage(self.data.close, period=self.params.price_ema_period)
        
        # 初始化交易状态
        self.order = None  # 当前挂单
        
    def next(self):
        # 如果已经有挂单，不做任何操作
        if self.order:
            return
            
        # 计算今日和昨日的价格和OBV变化
        today_price = self.data.close[0]
        yesterday_price = self.data.close[-1]
        today_obv = self.obv[0]
        yesterday_obv = self.obv[-1]
        
        # 判断价格和OBV的变化方向
        price_up = today_price > yesterday_price
        obv_up = today_obv > yesterday_obv
        
        # 判断正负背离
        positive_divergence = not price_up and obv_up  # 价格下跌但OBV上升
        negative_divergence = price_up and not obv_up  # 价格上涨但OBV下降
        
        # 买入信号：OBV穿越其EMA向上 + 价格在其EMA上方 或者 正背离
        obv_crossover = today_obv > self.obv_ema[0] and yesterday_obv <= self.obv_ema[-1]
        price_above_ema = today_price > self.price_ema[0]
        
        # 卖出信号：OBV穿越其EMA向下 + 价格在其EMA下方 或者 负背离
        obv_crossunder = today_obv < self.obv_ema[0] and yesterday_obv >= self.obv_ema[-1]
        price_below_ema = today_price < self.price_ema[0]
        
        # 根据当前持仓状态决定交易行为
        if not self.position:  # 如果当前没有持仓
            if (obv_crossover and price_above_ema) or positive_divergence:
                # 计算可以买入的最大股数
                size = self.calc_max_shares(today_price)
                if size > 0:
                    self.log(f'买入信号: OBV穿越={obv_crossover}, 价格位置={price_above_ema}, 正背离={positive_divergence}')
                    self.order = self.buy(size=size)
        
        else:  # 如果当前有持仓
            if (obv_crossunder and price_below_ema) or negative_divergence:
                self.log(f'卖出信号: OBV穿越={obv_crossunder}, 价格位置={price_below_ema}, 负背离={negative_divergence}')
                self.order = self.sell(size=self.position.size)
    
    def notify_order(self, order):
        """订单状态更新通知，覆盖父类方法以清除self.order"""
        # 首先调用父类的方法
        super(OBVStrategy, self).notify_order(order)
        
        # 如果订单已完成或被拒绝/取消，清除当前订单
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None

    def stop(self):
        """策略结束时调用"""
        # 调用父类的stop方法
        super(OBVStrategy, self).stop()
        
        # 输出额外的策略特定信息
        self.log(f'OBV策略参数: OBV EMA周期={self.params.obv_ema_period}, 价格EMA周期={self.params.price_ema_period}')

    def get_strategy_name(self):
        """返回策略名称"""
        return "OBV策略"
    
    def get_strategy_description(self):
        """返回策略描述"""
        return f"""基于OBV(On-Balance Volume)的交易策略
        参数:
        - OBV EMA周期: {self.params.obv_ema_period}天
        - 价格EMA周期: {self.params.price_ema_period}天
        
        交易信号:
        - 买入: OBV上穿其EMA且价格在其EMA上方，或出现正背离（价格下跌但OBV上升）
        - 卖出: OBV下穿其EMA且价格在其EMA下方，或出现负背离（价格上涨但OBV下降）
        """