from .base_strategy import BaseStrategy
import backtrader as bt

class VolumeBreakoutStrategy(BaseStrategy):
    """
    交易量突破策略，继承自BaseStrategy
    满仓交易版本，修复卖出逻辑
    """
    params = (
        ('volume_period', 20),   # 计算平均交易量的周期
        ('volume_mult', 2.0),    # 交易量倍数阈值
        ('exit_bars', 5),        # 持有的bar数量
        ('stop_loss', 0.05),     # 止损比例 (0.05 = 5%)
        ('take_profit', 0.10),   # 止盈比例 (0.10 = 10%)
        # 继承BaseStrategy的参数
        ('log_level', BaseStrategy.LOG_LEVEL_INFO),
        ('collect_signals', True),
    )
    
    def __init__(self):
        # 调用父类的初始化方法
        BaseStrategy.__init__(self)
        
        # 计算交易量移动平均线
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.volume_period)
    
    def next(self):
        # 如果没有持仓
        if not self.position:
            # 检查交易量是否突破
            if self.data.volume[0] > self.volume_ma[0] * self.params.volume_mult:
                # 计算当前价格下可购买的最大股票数量
                price = self.data.close[0]
                max_shares = self.calc_max_shares(price)
                
                # 确保购买至少1股
                if max_shares > 0:
                    self.log(f'买入信号: 价格={price:.2f}, 数量={max_shares}, 交易量={self.data.volume[0]:.0f}, 平均交易量={self.volume_ma[0]:.0f}')
                    self.buy(size=max_shares)  # 使用最大可购买数量
                    self.bar_executed = len(self)
                    self.buy_price = price
                else:
                    self.log(f'资金不足无法买入: 价格={price:.2f}, 可用资金={self.broker.getcash():.2f}')
                
        # 如果有持仓，检查是否应该卖出
        else:
            current_position_size = self.position.size
            
            # 基于持有期的退出策略
            if len(self) >= (self.bar_executed + self.params.exit_bars):
                self.log(f'卖出信号(时间退出): 价格={self.data.close[0]:.2f}, 持仓数量={current_position_size}')
                self.close()  # 关闭全部持仓，等同于 self.sell(size=current_position_size)
                return
            
            # 止损退出策略
            if self.data.close[0] < self.buy_price * (1 - self.params.stop_loss):
                self.log(f'卖出信号(止损): 价格={self.data.close[0]:.2f}, 持仓数量={current_position_size}')
                self.close()  # 关闭全部持仓
                return
                
            # 止盈退出策略
            if self.data.close[0] > self.buy_price * (1 + self.params.take_profit):
                self.log(f'卖出信号(止盈): 价格={self.data.close[0]:.2f}, 持仓数量={current_position_size}')
                self.close()  # 关闭全部持仓
                return 