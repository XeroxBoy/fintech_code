import os

import numpy as np
import pandas as pd
import baostock as bs
import talib


def get_stock_data(stock_code, interval='daily', start_date='2000-01-01', end_date='2024-03-24'):
    # Check if stock data is available locally
    csv_path = f"../data/stock/{stock_code}_{interval}_{start_date}_{end_date}.csv"
    if os.path.exists(csv_path):
        # Load data from CSV if it exists and the time range is correct
        existing_data = pd.read_csv(csv_path, index_col='date', parse_dates=True)
        existing_start_date = existing_data.index[0].date().isoformat()
        existing_end_date = existing_data.index[-1].date().isoformat()
        print(f"{existing_start_date}, {existing_end_date}")
        if existing_start_date <= start_date and existing_end_date >= end_date:
            result = existing_data.loc[start_date:end_date]
            print("Using local CSV file.")
            return result

    # Login to the system
    lg = bs.login()

    # Get historical K-line data
    if interval == 'daily':
        frequency = "d"
    elif interval == 'weekly':
        frequency = "w"
    elif interval == 'monthly':
        frequency = "m"
    else:
        print("Invalid interval parameter.")
        return

    fields = "date,code,open,high,low,close"
    rs = bs.query_history_k_data(stock_code, fields,
                                 start_date, end_date,
                                 frequency=frequency, adjustflag="2")

    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    result = pd.DataFrame(data_list, columns=rs.fields)
    result.index = pd.to_datetime(result.date)

    # Logout from the system
    bs.logout()

    # Save data to CSV for future use
    result.to_csv(csv_path)

    return result


def analyze_stock_data(stock_data):
    # Convert object columns to numeric
    stock_data = stock_data.apply(pd.to_numeric, errors='ignore')

    # Calculate MACD indicator
    stock_data['macd'], stock_data['macdsignal'], stock_data['macdhist'] = \
        talib.MACD(stock_data['close'], fastperiod=12, slowperiod=26, signalperiod=9)

    # Calculate KDJ indicator
    stock_data['k'], stock_data['d'] = \
        talib.STOCH(stock_data['high'], stock_data['low'], stock_data['close'],
                    fastk_period=9, slowk_period=3, slowd_period=3)

    stock_data['j'] = 3 * stock_data['k'] - 2 * stock_data['d']

    # Determine golden cross
    stock_data['macd_golden_cross'] = (stock_data['macd'] > stock_data['macdsignal']) & \
                                      (stock_data['macd'].shift(1) < stock_data['macdsignal'].shift(1))
    stock_data['kdj_golden_cross'] = (stock_data['k'] > stock_data['d']) & \
                                     (stock_data['k'].shift(1) < stock_data['d'].shift(1))

    # Calculate returns
    stock_data['returns'] = stock_data['close'].pct_change() * 100

    # Calculate returns for the next 10 days after golden cross
    stock_data['returns_next_10_days'] = stock_data['returns'].shift(-10)

    # Output
    is_golden_cross = stock_data['macd_golden_cross'].iloc[-1] or stock_data['kdj_golden_cross'].iloc[-1]
    golden_cross_returns = stock_data[stock_data['macd_golden_cross'] | stock_data['kdj_golden_cross']][
        'returns_next_10_days']
    positive_returns = golden_cross_returns[~golden_cross_returns.isna() & (golden_cross_returns > 0)]
    negative_returns = golden_cross_returns[~golden_cross_returns.isna() & (golden_cross_returns < 0)]
    total_trades = len(golden_cross_returns)
    if total_trades > 0:
        positive_probability = len(positive_returns) / total_trades * 100
    else:
        positive_probability = 0
    max_gain = golden_cross_returns.max()
    max_loss = golden_cross_returns.min()
    median_return = golden_cross_returns.median()

    print()
    print(f"当前是否金叉：{is_golden_cross}")
    print("金叉后的收益情况：")
    # print(golden_cross_returns)
    print("收益概率：{:.2f}%".format(positive_probability))
    print("数学期望（平均收益）：{:.2f}%".format(golden_cross_returns.mean()))
    print("最大收益：{:.2f}%".format(max_gain))
    print("最大亏损：{:.2f}%".format(max_loss))
    print("中位数收益：{:.2f}%".format(median_return))

def analyze_trend_break(stock_data, days=10):
    # Convert 'close' column to numeric
    stock_data['close'] = pd.to_numeric(stock_data['close'], errors='coerce')

    # Calculate x-day moving average
    stock_data['x_5_day_avg'] = stock_data['close'].rolling(window=5).mean()
    stock_data['x_10_day_avg'] = stock_data['close'].rolling(window=10).mean()

    # Determine if the stock has broken the upward trend for x-day average
    stock_data['5_trend_break'] = stock_data['close'] < stock_data['x_5_day_avg']
    stock_data['10_trend_break'] = stock_data['close'] < stock_data['x_10_day_avg']

    # Calculate consecutive days above x-day average
    stock_data['consecutive_days_5_day'] = stock_data['5_trend_break'].rolling(window=5).sum()
    stock_data['consecutive_days_10_day'] = stock_data['10_trend_break'].rolling(window=5).sum()

    # Calculate returns after trend break
    stock_data['returns_after_break'] = stock_data['close'].pct_change() * 100

    # Calculate returns for the next X days after trend break for 10-day average
    stock_data['returns_next_X_days_10_day'] = stock_data['returns_after_break'].rolling(window=days).sum().shift(-days)

    # Calculate returns for the next X days after trend break for 5-day average
    stock_data['returns_next_X_days_5_day'] = stock_data['returns_after_break'].rolling(window=days).sum().shift(-days)

    # Output
    is_5_trend_break = stock_data['consecutive_days_5_day'].iloc[-1] == 5
    is_10_trend_break = stock_data['consecutive_days_10_day'].iloc[-1] == 5

    trend_break_X_day_returns_10_day = stock_data[stock_data['10_trend_break']]['returns_next_X_days_10_day']
    trend_break_X_day_returns_5_day = stock_data[stock_data['5_trend_break']]['returns_next_X_days_5_day']

    positive_probability_5_day = len(trend_break_X_day_returns_5_day[trend_break_X_day_returns_5_day > 0]) / len(trend_break_X_day_returns_5_day) * 100 if len(trend_break_X_day_returns_5_day) != 0 else 0
    positive_probability_10_day = len(trend_break_X_day_returns_10_day[trend_break_X_day_returns_10_day > 0]) / len(trend_break_X_day_returns_10_day) * 100 if len(trend_break_X_day_returns_10_day) != 0 else 0

    average_return_5_day = trend_break_X_day_returns_5_day.mean()
    average_return_10_day = trend_break_X_day_returns_10_day.mean()

    max_gain_X_day_5_day = trend_break_X_day_returns_5_day.max()
    max_gain_X_day_10_day = trend_break_X_day_returns_10_day.max()
    max_loss_X_day_5_day = trend_break_X_day_returns_5_day.min()
    max_loss_X_day_10_day = trend_break_X_day_returns_10_day.min()
    median_return_X_day_5_day = trend_break_X_day_returns_5_day.median()
    median_return_X_day_10_day = trend_break_X_day_returns_10_day.median()

    print()
    print("当前是否跌破上升趋势：")
    print(f"MA5：{is_5_trend_break}, MA10：{is_10_trend_break}")
    print(f"跌破MA5线后的{days}(天或周或月)收益情况：")
    #print(trend_break_X_day_returns_5_day)
    print("收益概率（跌破MA5线）：{:.2f}%".format(positive_probability_5_day))
    print("数学期望（平均收益，跌破MA5线）：{:.2f}%".format(average_return_5_day))
    print("最大收益（跌破MA5线，{}天后）：{:.2f}%".format( days, max_gain_X_day_5_day))
    print("最大亏损（跌破MA5线，{}天后）：{:.2f}%".format(days, max_loss_X_day_10_day))
    print("中位数收益（跌破MA5线，{}天后）：{:.2f}%".format(days, median_return_X_day_5_day))
    print()
    print(f"跌破MA10线后的{days}(天或周或月)收益情况：")
    # print(trend_break_X_day_returns_10_day)
    print("收益概率（跌破MA10线）：{:.2f}%".format(positive_probability_10_day))
    print("数学期望（平均收益，跌破MA10线）：{:.2f}%".format(average_return_10_day))
    print("最大收益（跌破MA10线，{}天后）：{:.2f}%".format(days, max_gain_X_day_10_day))
    print("最大亏损（跌破MA10线，{}天后）：{:.2f}%".format(days, max_loss_X_day_10_day))
    print("中位数收益（跌破MA10线，{}天后）：{:.2f}%".format(days, median_return_X_day_10_day))
    print()

def analyze_trend_start(stock_data, x=5, m=10, stock_name=''):
    # Convert 'close' column to numeric
    stock_data['close'] = pd.to_numeric(stock_data['close'], errors='coerce')

    # Calculate x-day moving average
    stock_data['x_day_avg'] = stock_data['close'].rolling(window=x).mean()

    # Determine if the stock has broken the upward trend for x-day average
    stock_data['trend_break'] = stock_data['close'] > stock_data['x_day_avg']

    # Calculate returns after first breaking the x-day average
    stock_data['returns_after_break'] = stock_data['close'].pct_change() * 100
    stock_data['returns_m_days_after_break'] = stock_data['returns_after_break'].shift(-m)

    # Output
    is_trend_break = stock_data['trend_break'].iloc[-1]
    returns_m_days_after_break = stock_data[stock_data['trend_break']]['returns_m_days_after_break']
    positive_returns = returns_m_days_after_break[returns_m_days_after_break > 0]
    positive_probability = len(positive_returns) / len(returns_m_days_after_break) * 100 if len(
        returns_m_days_after_break) != 0 else 0
    average_return = returns_m_days_after_break.mean()
    max_gain = returns_m_days_after_break.max()
    max_loss = returns_m_days_after_break.min()
    median_return = returns_m_days_after_break.median()

    print()
    print("股票名称：{}".format(stock_name))
    print("首次站上 MA{} 后的 {} (天或周或月)收益情况：".format(x, m))
    #print(returns_m_days_after_break)
    print("收益概率：{:.2f}%".format(positive_probability))
    print("数学期望（平均收益）：{:.2f}%".format(average_return))
    print("最大收益：{:.2f}%".format(max_gain))
    print("最大亏损：{:.2f}%".format(max_loss))
    print("中位数收益：{:.2f}%".format(median_return))


def analyze_macd_divergence_top(stock_data, m=5, stock_name=''):
    # Calculate MACD
    stock_data['ema12'] = stock_data['close'].ewm(span=12, adjust=False).mean()
    stock_data['ema26'] = stock_data['close'].ewm(span=26, adjust=False).mean()
    stock_data['macd'] = stock_data['ema12'] - stock_data['ema26']

    # Find MACD top divergences
    stock_data['macd_divergence'] = np.where(
        (stock_data['macd'].shift(1) > stock_data['macd']) & (
            stock_data['macd'].shift(1) > stock_data['macd'].shift(2)),
        '顶背离',
        ''
    )

    # Calculate returns after MACD top divergence
    stock_data['returns_after_divergence'] = stock_data['close'].pct_change() * 100
    stock_data['returns_m_days_after_divergence'] = stock_data['returns_after_divergence'].shift(-m)

    # Output
    macd_divergences = stock_data[stock_data['macd_divergence'] != '']
    macd_divergence_type = macd_divergences['macd_divergence'].iloc[-1]
    returns_m_days_after_divergence = macd_divergences['returns_m_days_after_divergence']
    positive_returns = returns_m_days_after_divergence[returns_m_days_after_divergence > 0]
    positive_probability = len(positive_returns) / len(returns_m_days_after_divergence) * 100 if len(
        returns_m_days_after_divergence) != 0 else 0
    average_return = returns_m_days_after_divergence.mean()
    max_gain = returns_m_days_after_divergence.max()
    max_loss = returns_m_days_after_divergence.min()
    median_return = returns_m_days_after_divergence.median()

    print()
    print("股票名称：{}".format(stock_name))
    print("当前是否顶背离：{}".format(macd_divergence_type == '顶背离'))
    print("MACD顶背离后的 {} (天或周或月)收益情况：".format(m))
    #print(returns_m_days_after_divergence)
    print("当前MACD背离类型：{}".format(macd_divergence_type))
    print("收益概率：{:.2f}%".format(positive_probability))
    print("数学期望（平均收益）：{:.2f}%".format(average_return))
    print("最大收益：{:.2f}%".format(max_gain))
    print("最大亏损：{:.2f}%".format(max_loss))
    print("中位数收益：{:.2f}%".format(median_return))


def analyze_macd_divergence_bottom(stock_data, m=5, stock_name=''):
    # Calculate MACD
    stock_data['ema12'] = stock_data['close'].ewm(span=12, adjust=False).mean()
    stock_data['ema26'] = stock_data['close'].ewm(span=26, adjust=False).mean()
    stock_data['macd'] = stock_data['ema12'] - stock_data['ema26']

    # Find MACD bottom divergences
    stock_data['macd_divergence'] = np.where(
        (stock_data['macd'].shift(1) < stock_data['macd']) & (
                    stock_data['macd'].shift(1) < stock_data['macd'].shift(2)),
        '底背离',
        ''
    )

    # Calculate returns after MACD bottom divergence
    stock_data['returns_after_divergence'] = stock_data['close'].pct_change() * 100
    stock_data['returns_m_days_after_divergence'] = stock_data['returns_after_divergence'].shift(-m)

    # Output
    macd_divergences = stock_data[stock_data['macd_divergence'] != '']
    macd_divergence_type = macd_divergences['macd_divergence'].iloc[-1]
    returns_m_days_after_divergence = macd_divergences['returns_m_days_after_divergence']
    positive_returns = returns_m_days_after_divergence[returns_m_days_after_divergence > 0]
    positive_probability = len(positive_returns) / len(returns_m_days_after_divergence) * 100 if len(
        returns_m_days_after_divergence) != 0 else 0
    average_return = returns_m_days_after_divergence.mean()
    max_gain = returns_m_days_after_divergence.max()
    max_loss = returns_m_days_after_divergence.min()
    median_return = returns_m_days_after_divergence.median()

    print()
    print("股票名称：{}".format(stock_name))
    print("MACD底背离后的 {} (天或周或月)收益情况：".format(m))
    #print(returns_m_days_after_divergence)
    print("当前MACD背离类型：{}".format(macd_divergence_type))
    print("是否底背离：{}".format(macd_divergence_type == '底背离'))  # Added line
    print("收益概率：{:.2f}%".format(positive_probability))
    print("数学期望（平均收益）：{:.2f}%".format(average_return))
    print("最大收益：{:.2f}%".format(max_gain))
    print("最大亏损：{:.2f}%".format(max_loss))
    print("中位数收益：{:.2f}%".format(median_return))

stock_code = "sh.600733"
stock_data = get_stock_data(stock_code, interval='monthly', start_date='2000-01-01')
analyze_stock_data(stock_data)
analyze_trend_break(stock_data)
analyze_trend_start(stock_data, x=5, stock_name=stock_code)
analyze_macd_divergence_top(stock_data, m=5, stock_name=stock_code)
analyze_macd_divergence_bottom(stock_data, m=5, stock_name=stock_code)
