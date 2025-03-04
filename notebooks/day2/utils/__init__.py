"""
Backtrader回测工具包

这个包包含了Backtrader回测相关的工具函数和类。
"""

from .data import get_ts_data, df_to_btfeed
from .backtest import run_backtest
from .strategy import BaseStrategy, VolumeBreakoutStrategy
from .visualization import plot_performance_analysis, plot_backtest_results
from .optimization import optimize_ma_strategy

# 版本信息
__version__ = '0.1.0' 