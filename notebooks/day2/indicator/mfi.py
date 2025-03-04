import backtrader as bt

class MFI(bt.Indicator):
    """
    自定义 Money Flow Index (MFI) 指标
    计算流程：
      1. 计算典型价格：TP = (High + Low + Close) / 3
      2. 计算资金流：MF = TP * Volume
      3. 判断正负资金流：若TP大于前一期TP，则为正资金流，否则为负资金流
      4. 计算过去周期内正、负资金流的累加和，并计算资金流比率 MFR
      5. 计算 MFI = 100 - 100/(1 + MFR)
    """
    lines = ('mfi',)
    params = (('period', 14),)

    def __init__(self):
        tp = (self.data.high + self.data.low + self.data.close) / 3.0
        mf = tp * self.data.volume
        tp_prev = tp(-1)

        # 判断正负资金流
        pos_flow = bt.If(tp > tp_prev, mf, 0.0)
        neg_flow = bt.If(tp < tp_prev, mf, 0.0)

        # 累计正负资金流，避免除零
        pos_flow_sum = bt.indicators.SumN(pos_flow, period=self.p.period)
        neg_flow_sum = bt.indicators.SumN(neg_flow, period=self.p.period)

        mfr = pos_flow_sum / (neg_flow_sum + 1e-10)
        self.lines.mfi = 100 - (100 / (1 + mfr))