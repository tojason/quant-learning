import backtrader as bt

def run_backtest(ticker, df, start_date, end_date, strategy, initial_cash=100000):
    """
    设置 Backtrader，加载数据，执行策略回测，并输出初始资金、回测结束资金、
    夏普比率、最大回撤和收益率等指标。
    
    同时模拟交易成本（手续费）和滑点。
    
    返回 Cerebro 引擎实例，可用于后续可视化。
    """
    cerebro = bt.Cerebro()

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    # 添加策略
    cerebro.addstrategy(strategy)

    # 使用 PandasData 加载数据
    data_feed = bt.feeds.PandasData(
        dataname=df,
        datetime='datetime',
        timeframe=bt.TimeFrame.Minutes,
        compression=5,
        fromdate=start_date,
        todate=end_date
    )
    # 设置数据名称及绘图名称
    data_feed._name = ticker
    data_feed.plotinfo.plotname = ticker
    cerebro.adddata(data_feed)

    # 设置初始资金
    cerebro.broker.setcash(initial_cash)
    print(f"初始资金: {cerebro.broker.getvalue():.2f}")

    # 设置交易成本（例如：0.1% 的手续费）
    cerebro.broker.setcommission(commission=0.001)

    # 设置固定滑点（例如：每笔交易价格偏差 0.05，且在开盘时也应用滑点）
    cerebro.broker.set_slippage_fixed(0.05, slip_open=True)

    # 运行回测，并获取策略实例（注意：返回的是一个列表）
    results = cerebro.run()
    strat = results[0]

    print(f"回测结束资金: {cerebro.broker.getvalue():.2f}")

    # 输出分析器的结果
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()

    print("夏普比率:", sharpe)
    print("最大回撤:", drawdown)
    print("收益率:", returns)

    return cerebro