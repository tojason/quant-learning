"""
策略工具模块

这个模块包含了不同类型的交易策略实现。
"""

import backtrader as bt

class BaseStrategy(bt.Strategy):
    """
    通用策略基类，集成信号收集和日志记录功能
    """
    # 日志等级
    LOG_LEVEL_DEBUG = 0
    LOG_LEVEL_INFO = 1
    LOG_LEVEL_WARNING = 2
    LOG_LEVEL_ERROR = 3
    
    params = (
        ('log_level', LOG_LEVEL_INFO),  # 日志级别
        ('collect_signals', True),       # 是否收集交易信号
    )
    
    def __init__(self):
        # 初始化交易信号列表
        self.buy_signals = []    # 买入信号列表，格式为 (datetime, price)
        self.sell_signals = []   # 卖出信号列表，格式为 (datetime, price)
        self.position_size = []  # 持仓变化列表，格式为 (datetime, size)
        self.logs = []           # 日志列表，格式为 (datetime, log_level, message)
        
        # 跟踪持仓和买入价格
        self.bar_executed = None
        self.buy_price = None
        self.position_value = 0
        
    def log(self, txt, dt=None, level=None):
        """记录日志"""
        if level is None:
            level = self.params.log_level
        
        if level >= self.params.log_level:
            dt = dt or self.datas[0].datetime.date(0)
            # 记录日志到列表
            self.logs.append((dt, level, txt))
            # 打印日志
            print(f'{dt.isoformat()}: {txt}')
    
    def notify_order(self, order):
        """订单状态更新通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或已接受，无需操作
            return

        # 检查订单是否已完成
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行: 价格={order.executed.price:.2f}, 数量={order.executed.size}, 成本={order.executed.value:.2f}, 手续费={order.executed.comm:.2f}')
                # 记录买入信号
                if self.params.collect_signals:
                    self.buy_signals.append((self.datas[0].datetime.datetime(0), order.executed.price))
                # 记录持仓变化
                self.position_value = order.executed.size
                self.position_size.append((self.datas[0].datetime.datetime(0), self.position_value))
                
            elif order.issell():
                self.log(f'卖出执行: 价格={order.executed.price:.2f}, 数量={abs(order.executed.size)}, 收入={order.executed.value:.2f}, 手续费={order.executed.comm:.2f}')
                # 记录卖出信号
                if self.params.collect_signals:
                    self.sell_signals.append((self.datas[0].datetime.datetime(0), order.executed.price))
                # 记录持仓变化
                self.position_value = 0
                self.position_size.append((self.datas[0].datetime.datetime(0), self.position_value))
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'订单被拒绝或取消: {order.status}', level=self.LOG_LEVEL_WARNING)
    
    def notify_trade(self, trade):
        """交易完成通知"""
        if trade.isclosed:
            self.log(f'交易利润: 毛利={trade.pnl:.2f}, 净利={trade.pnlcomm:.2f}')
    
    def calc_max_shares(self, price):
        """计算在当前价格下能够购买的最大股票数量（考虑手续费）"""
        cash = self.broker.getcash()
        commission_rate = self.broker.getcommissioninfo(self.data).p.commission
        
        # 计算最大可购买股数 (留出手续费)
        # 满足方程：cash = shares * price * (1 + commission_rate)
        # 因此：shares = cash / (price * (1 + commission_rate))
        max_shares = int(cash / (price * (1 + commission_rate)))
        return max_shares
    
    def next(self):
        """
        策略核心逻辑，在每个bar调用
        这个方法需要在子类中实现
        """
        pass
    
    def stop(self):
        """策略结束时调用"""
        # 可以在这里进行最终的总结和统计
        self.log(f'策略结束: 最终资金={self.broker.getvalue():.2f}')
    
    def get_signals(self):
        """获取所有交易信号"""
        return {
            'buy_signals': self.buy_signals,
            'sell_signals': self.sell_signals,
            'position_size': self.position_size
        }
    
    def get_logs(self):
        """获取所有日志"""
        return self.logs


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