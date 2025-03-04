"""
数据处理工具模块

这个模块包含了数据获取和预处理相关的函数。
"""

import os
import pandas as pd
import backtrader as bt
import tushare as ts

def get_ts_data(ts_token, ts_code, start_date, end_date, freq='30min'):
    """
    从Tushare获取股票数据，如果本地已有则直接加载
    
    参数:
    ts_token (str): Tushare API Token
    ts_code (str): 股票代码（如：'000001.SZ'）
    start_date (str): 开始日期（如：'2020-01-01'）
    end_date (str): 结束日期（如：'2021-01-01'）
    freq (str): 数据频率，默认为30分钟
    
    返回:
    pandas.DataFrame: 包含OHLCV数据的DataFrame
    """
    # 文件路径
    file_path = f'./data/{ts_code}-{start_date}-{end_date}-{freq}.csv'
    
    # 检查本地是否已存在该文件
    if os.path.exists(file_path):
        print(f"从本地文件加载数据: {file_path}")
        df = pd.read_csv(file_path, parse_dates=['trade_time'])  # 读取并解析时间列
        return df
    
    # 设置Tushare token
    ts.set_token(ts_token)
    pro = ts.pro_api()

    # 获取数据
    df = ts.pro_bar(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        freq=freq,  
        asset='E',       # 股票类型
        adj='qfq',       # 前复权
    )

    if df is None or df.empty:
        print("从 Tushare 获取的数据为空，请检查权限或参数设置。")
        return None

    # 创建目录（如果不存在）
    os.makedirs('./data', exist_ok=True)

    # 保存数据到本地文件
    df.to_csv(file_path, index=False)
    print(f"数据已保存至: {file_path}")

    return df

def df_to_btfeed(df):
    """
    将Pandas DataFrame转换为Backtrader的数据源
    
    参数:
    df (pandas.DataFrame): 包含OHLCV数据的DataFrame
    
    返回:
    backtrader.feeds.PandasData: 可用于Backtrader的数据源
    """
    # 确保索引是datetime类型
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        df['datetime'] = pd.to_datetime(df['trade_time'])
        df.set_index('datetime', inplace=True)
    
    # 创建用于backtrader的PandasData类
    class PandasDataCustom(bt.feeds.PandasData):
        params = (
            ('datetime', None),  # 已设置为索引
            ('open', 'open'),
            ('high', 'high'),
            ('low', 'low'),
            ('close', 'close'),
            ('volume', 'vol'),
            ('openinterest', None)  # 不使用持仓量数据
        )
    
    # 返回backtrader的数据源
    return PandasDataCustom(dataname=df)

def load_data_from_csv(file_path):
    """
    从CSV文件加载数据
    
    参数:
    file_path (str): CSV文件路径
    
    返回:
    pandas.DataFrame: 包含OHLCV数据的DataFrame
    """
    # 读取CSV文件
    df = pd.read_csv(file_path)
    
    # 将日期列转换为datetime类型
    if 'trade_time' in df.columns:
        df['trade_time'] = pd.to_datetime(df['trade_time'])
    elif 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    return df 