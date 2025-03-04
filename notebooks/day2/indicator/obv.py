import backtrader as bt

class OnBalanceVolume(bt.Indicator):
    """
    自定义 On-Balance Volume (OBV) 指标
    
    计算公式:
    OBV(i) = OBV(i-1) + volume(i),   if close(i) > close(i-1)
           = OBV(i-1) - volume(i),   if close(i) < close(i-1)
           = OBV(i-1),              otherwise
    
    * 在第一根可计算的bar上，可以将 OBV(0) 设为 0 或者把第一根的 volume 作为起点，
      这里演示从 0 开始累计。
    """
    
    # 定义输出线（Backtrader中的指标必须至少定义一条 lines）
    lines = ('obv',)
    
    # 可选: 这里可以定义指标参数（params），如果需要的话
    params = (
        # 例如是否从 volume(0) 开始累计
        ('use_volume_at_first_bar', False),
    )

    def __init__(self):
        # 为了确保我们可以访问到 data.close[-1]，必须要在 init 里指定最小周期
        self.addminperiod(1)
        
        # 也可以在这里设置初始值
        # 例如: self.lines.obv[0] = 0 (但要注意这里还没有 0 索引的值)
        pass

    def nextstart(self):
        """
        nextstart() 会在第一根真正有数据可计算的 bar 时被调用，仅调用一次。
        我们可以在这里初始化 OBV 的起始值。
        """
        # 让 OBV(0) = 0（或初始 volume），以下示例以0为起点
        if self.p.use_volume_at_first_bar:
            self.lines.obv[0] = self.data.volume[0]
        else:
            self.lines.obv[0] = 0

        # nextstart()执行完后，后续计算会在 next() 中
        super().nextstart()

    def next(self):
        """
        每跟新 bar 会调用 next() 来计算新的 OBV 值。
        """
        if self.data.close[0] > self.data.close[-1]:
            self.lines.obv[0] = self.lines.obv[-1] + self.data.volume[0]
        elif self.data.close[0] < self.data.close[-1]:
            self.lines.obv[0] = self.lines.obv[-1] - self.data.volume[0]
        else:
            # 收盘价相同，OBV 不变
            self.lines.obv[0] = self.lines.obv[-1]
