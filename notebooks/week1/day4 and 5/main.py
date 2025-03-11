import datetime
import pandas as pd

# 从自定义模块中导入
from data_processing.data_processing import load_data, flatten_yf_columns, standardize_columns
from strategy.rsi_strategy import RsiStrategy
from back_test.backtesting import run_backtest
from plotting.plotting import plot_results

def main():
    # 设定日期范围（最近 30 天）
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=30)

    print(f"Downloading data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # 下载 AAPL 5 分钟级数据
    df = load_data("AAPL", start_date, end_date, interval="5m")

    # 判断是否成功下载数据
    if df.empty:
        print("未能下载数据。请确认所请求的日期范围在最近 60 天内且 Yahoo Finance 提供 AAPL 的5分钟数据。")
        return

    # 扁平化列名
    df = flatten_yf_columns(df)
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)

    print("Data head after flattening:")
    print(df.head())

    # 将索引转换回普通列
    df.reset_index(inplace=True)
    # 全部列名转小写
    df.columns = [col.lower() for col in df.columns]
    # 确保 datetime 列为 datetime 类型
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])

    # 标准化列名
    df = standardize_columns(df)
    print("Data head after standardizing columns:")
    print(df.head())

    # 运行回测
    cerebro = run_backtest(df, start_date, end_date, RsiStrategy, initial_cash=100000)

    # 可视化回测结果
    plot_results(cerebro)

if __name__ == "__main__":
    main() 