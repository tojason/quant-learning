import backtrader as bt

class RsiStrategy(bt.Strategy):
    """
    基于 RSI 指标的简单交易策略。
    """
    params = (
        ("period", 14),      # RSI 计算周期
        ("overbought", 70),  # 超买阈值
        ("oversold", 30),    # 超卖阈值
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()} {txt}")

    def __init__(self):
        self.dataclose = self.datas[0].close
        # 初始化 RSI 指标
        self.rsi = bt.indicators.RelativeStrengthIndex(
            self.datas[0], 
            period=self.params.period
        )

    def next(self):
        if not self.position:
            if self.rsi[0] < self.params.oversold:
                size_to_buy = int(self.broker.getcash() / self.dataclose[0])
                self.log(
                    f"BUY CREATE, Price: {self.dataclose[0]:.2f}, "
                    f"Size: {size_to_buy}"
                )
                self.buy(size=size_to_buy)
        else:
            if self.rsi[0] > self.params.overbought:
                self.log(
                    f"SELL CREATE, Price: {self.dataclose[0]:.2f}, "
                    f"Size: {self.position.size}"
                )
                self.sell(size=self.position.size)
