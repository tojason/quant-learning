# RSI 策略回测框架

这是一个基于 Backtrader 的 RSI 策略回测框架，用于演示如何构建和测试交易策略。

## 项目结构

```
.
├── data_processing/       # 数据处理模块
│   ├── __init__.py
│   └── data_processing.py
├── strategy/             # 策略模块
│   ├── __init__.py
│   └── rsi_strategy.py
├── back_test/           # 回测模块
│   ├── __init__.py
│   └── backtesting.py
├── plotting/            # 可视化模块
│   ├── __init__.py
│   └── plotting.py
├── main.py             # 主程序入口
├── requirements.txt    # 项目依赖
└── README.md          # 项目说明
```

## 功能特点

- 使用 yfinance 下载股票数据
- 实现了 RSI 策略的回测
- 支持数据预处理和标准化
- 提供基本的可视化功能
- 模块化设计，易于扩展

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

1. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

2. 运行回测：
   ```bash
   python main.py
   ```

## RSI 策略说明

该策略基于相对强弱指标（RSI）进行交易：
- RSI < 30：超卖信号，执行买入
- RSI > 70：超买信号，执行卖出

## 注意事项

- Yahoo Finance 的分钟级数据仅提供最近 60 天的数据
- 建议使用 Python 3.8 或更高版本
- 如需更好的可视化效果，请安装 backtrader-plotting 