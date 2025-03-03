"""
数据加载与处理工具
"""
import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

def load_data_from_yahoo(tickers, start_date, end_date=None, interval='1d', save_to_csv=True, data_dir='../data'):
    """
    从Yahoo Finance下载股票数据
    
    参数:
    tickers (list or str): 股票代码或代码列表
    start_date (str): 开始日期，格式为 'YYYY-MM-DD'
    end_date (str): 结束日期，格式为 'YYYY-MM-DD'，默认为当前日期
    interval (str): 数据间隔，可选值: '1d', '1wk', '1mo'等
    save_to_csv (bool): 是否保存数据到CSV文件
    data_dir (str): 保存数据的目录
    
    返回:
    pandas DataFrame: 历史价格数据
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    if isinstance(tickers, str):
        tickers = [tickers]
    
    all_data = {}
    for ticker in tickers:
        try:
            print(f"获取 {ticker} 的数据...")
            stock = yf.Ticker(ticker)
            data = stock.history(start=start_date, end=end_date, interval=interval)
            
            if len(data) == 0:
                print(f"警告: 没有找到 {ticker} 的数据")
                continue
                
            all_data[ticker] = data
            
            if save_to_csv:
                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)
                filename = os.path.join(data_dir, f"{ticker}_{start_date}_{end_date}_{interval}.csv")
                data.to_csv(filename)
                print(f"数据已保存到 {filename}")
        except Exception as e:
            print(f"获取 {ticker} 数据时出错: {e}")
    
    if len(tickers) == 1:
        return all_data.get(tickers[0], pd.DataFrame())
    return all_data

def calculate_returns(prices, method='simple'):
    """
    计算收益率
    
    参数:
    prices (pandas Series or DataFrame): 价格数据
    method (str): 计算方法，可选值: 'simple', 'log'
    
    返回:
    pandas Series or DataFrame: 收益率数据
    """
    if method == 'simple':
        return prices.pct_change().dropna()
    elif method == 'log':
        return np.log(prices / prices.shift(1)).dropna()
    else:
        raise ValueError("method must be either 'simple' or 'log'")

def calculate_indicators(df):
    """
    计算常用技术指标
    
    参数:
    df (pandas DataFrame): 包含OHLCV数据的DataFrame
    
    返回:
    pandas DataFrame: 包含原始数据和计算的指标
    """
    # 确保列名符合要求
    if not all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume']):
        # 尝试将第一个字母大写
        df = df.rename(columns={col: col.capitalize() for col in df.columns})
    
    # 复制数据，避免修改原始数据
    result = df.copy()
    
    # 移动平均线
    result['SMA5'] = result['Close'].rolling(window=5).mean()
    result['SMA10'] = result['Close'].rolling(window=10).mean()
    result['SMA20'] = result['Close'].rolling(window=20).mean()
    result['SMA50'] = result['Close'].rolling(window=50).mean()
    result['SMA200'] = result['Close'].rolling(window=200).mean()
    
    # 指数移动平均线
    result['EMA12'] = result['Close'].ewm(span=12, adjust=False).mean()
    result['EMA26'] = result['Close'].ewm(span=26, adjust=False).mean()
    
    # MACD
    result['MACD'] = result['EMA12'] - result['EMA26']
    result['MACD_signal'] = result['MACD'].ewm(span=9, adjust=False).mean()
    result['MACD_hist'] = result['MACD'] - result['MACD_signal']
    
    # RSI (14天)
    delta = result['Close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    rs = ema_up / ema_down
    result['RSI14'] = 100 - (100 / (1 + rs))
    
    # 布林带 (20,2)
    result['BB_middle'] = result['Close'].rolling(window=20).mean()
    result['BB_upper'] = result['BB_middle'] + (result['Close'].rolling(window=20).std() * 2)
    result['BB_lower'] = result['BB_middle'] - (result['Close'].rolling(window=20).std() * 2)
    
    # 成交量变化
    result['Volume_Change'] = result['Volume'].pct_change()
    
    # 波动率 (20天)
    result['Volatility'] = result['Close'].pct_change().rolling(window=20).std() * np.sqrt(20)
    
    return result

def resample_data(df, freq='W'):
    """
    重采样数据到指定频率
    
    参数:
    df (pandas DataFrame): 股票数据
    freq (str): 频率字符串，如 'W' 表示周，'M' 表示月
    
    返回:
    pandas DataFrame: 重采样后的数据
    """
    # 确保索引是日期时间类型
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    # 对常见的OHLCV数据进行重采样
    resampled = df.resample(freq)
    
    result = pd.DataFrame({
        'Open': resampled['Open'].first(),
        'High': resampled['High'].max(),
        'Low': resampled['Low'].min(),
        'Close': resampled['Close'].last(),
        'Volume': resampled['Volume'].sum()
    })
    
    return result 