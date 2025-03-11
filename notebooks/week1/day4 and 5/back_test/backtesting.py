import backtrader as bt

class MoneyDrawDownAnalyzer(bt.Analyzer):
    """
    自定义分析器：在回测过程中记录资金峰值，并计算最大回撤的“金额”。
    """
    def create_analysis(self):
        self.max_value = None
        self.max_drawdown = 0.0

    def next(self):
        current_value = self.strategy.broker.getvalue()
        if self.max_value is None or current_value > self.max_value:
            self.max_value = current_value
        current_drawdown = self.max_value - current_value
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown

    def get_analysis(self):
        return {'max_drawdown_money': self.max_drawdown}


def run_backtest(ticker, df, start_date, end_date, strategy, initial_cash=100000, 
                 strategy_params=None, print_log=True, date_column='datetime'):
    if strategy_params is None:
        strategy_params = {}

    cerebro = bt.Cerebro()

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', 
                        timeframe=bt.TimeFrame.Minutes, annualize=True, factor=19656)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(MoneyDrawDownAnalyzer, _name='mydd')

    # Add strategy with parameters
    cerebro.addstrategy(strategy, **strategy_params)

    # Load data using the flexible column name for the datetime index
    data_feed = bt.feeds.PandasData(
        dataname=df,
        datetime=date_column,  # This can now be 'date' or 'datetime'
        timeframe=bt.TimeFrame.Minutes,
        compression=5,
        fromdate=start_date,
        todate=end_date
    )
    data_feed._name = ticker
    cerebro.adddata(data_feed)

    # Set initial cash and broker settings
    cerebro.broker.setcash(initial_cash)
    if print_log:
        print(f"Initial cash: {cerebro.broker.getvalue():.2f}")

    cerebro.broker.setcommission(commission=0.001)
    cerebro.broker.set_slippage_fixed(0.05, slip_open=True)

    # Run backtest
    results = cerebro.run()
    strat = results[0]
    
    final_value = cerebro.broker.getvalue()
    if print_log:
        print(f"Final cash: {final_value:.2f}")
        # (Other logging code remains unchanged)

    # Extract results from analyzers
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    mydd = strat.analyzers.mydd.get_analysis()

    sharpe_ratio = sharpe.get('sharperatio', None)
    max_dd_pct = drawdown.get('max', {}).get('drawdown', None)
    max_dd_money = mydd.get('max_drawdown_money', 0)
    rtot = returns.get('rtot', None)
    rnorm = returns.get('rnorm', None)

    if print_log:
        if sharpe_ratio is not None:
            print(f"Sharpe Ratio: {sharpe_ratio:.4f}")
        else:
            print("Sharpe Ratio: N/A")
        if max_dd_pct is not None:
            print(f"Max Drawdown %: {max_dd_pct:.2f}%")
        else:
            print("Max Drawdown %: N/A")
        print(f"Max Drawdown Money: {max_dd_money:.2f}")
        if rtot is not None:
            print(f"Total Return: {rtot*100:.2f}%")
        else:
            print("Total Return: N/A")
        if rnorm is not None:
            print(f"Annualized Return: {rnorm*100:.2f}%")
        else:
            print("Annualized Return: N/A")
        total_trades = trades.get('total', {}).get('total', 0)
        won_trades = trades.get('won', {}).get('total', 0)
        print("Trade details:")
        print(f"Total trades: {total_trades}")
        print(f"Winning trades: {won_trades} / {total_trades}")

    result_dict = {
        'final_value': final_value,
        'sharpe_ratio': sharpe_ratio,
        'max_dd_pct': max_dd_pct,
        'max_dd_money': max_dd_money,
        'rtot': rtot,
        'rnorm': rnorm
    }

    return result_dict, cerebro
