import os
import time

import numpy as np
import pandas as pd
import baostock as bs
import talib

from get_data.clean_data import remove_subset_files
from initial import stock_code_to_company, interval_to_str


class StockStrategySimulator:
    @staticmethod
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

    @staticmethod
    def analyze_stock_data_macd_kdj(stock_data, stock_name, m=5, interval=''):
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

        # Calculate cumulative returns for the next 5 and 10 days after golden cross
        stock_data[f'returns_cumulative_{m}_days'] = stock_data['returns'].rolling(m).sum()

        # Output
        is_golden_cross = stock_data['macd_golden_cross'].iloc[-1] or stock_data['kdj_golden_cross'].iloc[-1]
        golden_cross_returns_m_days = stock_data[stock_data['macd_golden_cross'] | stock_data['kdj_golden_cross']][
            f'returns_cumulative_{m}_days']

        positive_returns_5_days = golden_cross_returns_m_days[
            ~golden_cross_returns_m_days.isna() & (golden_cross_returns_m_days > 0)]

        total_trades = len(golden_cross_returns_m_days)
        if total_trades > 0:
            positive_probability_5_days = len(positive_returns_5_days) / total_trades * 100
        else:
            positive_probability_5_days = 0
        max_gain_m_days = golden_cross_returns_m_days.max()
        max_loss_m_days = golden_cross_returns_m_days.min()
        median_return_m_days = golden_cross_returns_m_days.median()

        print()
        print(f"{stock_name}当前是否金叉：{is_golden_cross}")
        print("金叉后的收益情况：")
        # print(golden_cross_returns)
        print("收益概率：{:.2f}%".format(positive_probability_5_days))
        print("数学期望（平均收益）：{:.2f}%".format(golden_cross_returns_m_days.mean()))
        print("最大收益：{:.2f}%".format(max_gain_m_days))
        print("最大亏损：{:.2f}%".format(max_loss_m_days))
        print("中位数收益：{:.2f}%".format(median_return_m_days))
        return is_golden_cross, positive_probability_5_days, golden_cross_returns_m_days.mean()

    @staticmethod
    def analyze_trend_break(stock_data, stock_name, days=10, interval='daily'):
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
        stock_data['returns_next_X_days_10_day'] = stock_data['returns_after_break'].rolling(window=days).sum().shift(
            -days)

        # Calculate returns for the next X days after trend break for 5-day average
        stock_data['returns_next_X_days_5_day'] = stock_data['returns_after_break'].rolling(window=days).sum().shift(
            -days)

        # Output
        is_5_trend_break = stock_data['consecutive_days_5_day'].iloc[-1] == 5
        is_10_trend_break = stock_data['consecutive_days_10_day'].iloc[-1] == 5

        trend_break_X_day_returns_10_day = stock_data[stock_data['10_trend_break']]['returns_next_X_days_10_day']
        trend_break_X_day_returns_5_day = stock_data[stock_data['5_trend_break']]['returns_next_X_days_5_day']

        positive_probability_5_day = len(trend_break_X_day_returns_5_day[trend_break_X_day_returns_5_day > 0]) / len(
            trend_break_X_day_returns_5_day) * 100 if len(trend_break_X_day_returns_5_day) != 0 else 0
        positive_probability_10_day = len(trend_break_X_day_returns_10_day[trend_break_X_day_returns_10_day > 0]) / len(
            trend_break_X_day_returns_10_day) * 100 if len(trend_break_X_day_returns_10_day) != 0 else 0

        average_return_5_day = trend_break_X_day_returns_5_day.mean()
        average_return_10_day = trend_break_X_day_returns_10_day.mean()

        max_gain_X_day_5_day = trend_break_X_day_returns_5_day.max()
        max_gain_X_day_10_day = trend_break_X_day_returns_10_day.max()
        max_loss_X_day_5_day = trend_break_X_day_returns_5_day.min()
        max_loss_X_day_10_day = trend_break_X_day_returns_10_day.min()
        median_return_X_day_5_day = trend_break_X_day_returns_5_day.median()
        median_return_X_day_10_day = trend_break_X_day_returns_10_day.median()

        print()
        print(f"{stock_name}当前是否跌破上升趋势：")
        print(f"MA5：{is_5_trend_break}, MA10：{is_10_trend_break}")
        print(f"跌破MA5线后的{days}{interval_to_str[interval]}收益情况：")
        # print(trend_break_X_day_returns_5_day)
        print("收益概率（跌破MA5线）：{:.2f}%".format(positive_probability_5_day))
        print("数学期望（平均收益，跌破MA5线）：{:.2f}%".format(average_return_5_day))
        print("最大收益（跌破MA5线，{}{}后）：{:.2f}%".format(days, interval_to_str[interval], max_gain_X_day_5_day))
        print("最大亏损（跌破MA5线，{}{}后）：{:.2f}%".format(days, interval_to_str[interval], max_loss_X_day_5_day))
        print("中位数收益（跌破MA5线，{}{}后）：{:.2f}%".format(days, interval_to_str[interval], median_return_X_day_5_day))
        print()
        print(f"{stock_name}跌破MA10线后的{days}{interval_to_str[interval]}收益情况：")
        # print(trend_break_X_day_returns_10_day)
        print("收益概率（跌破MA10线）：{:.2f}%".format(positive_probability_10_day))
        print("数学期望（平均收益，跌破MA10线）：{:.2f}%".format(average_return_10_day))
        print("最大收益（跌破MA10线，{}{}后）：{:.2f}%".format(days, interval_to_str[interval], max_gain_X_day_10_day))
        print("最大亏损（跌破MA10线，{}{}后）：{:.2f}%".format(days, interval_to_str[interval], max_loss_X_day_10_day))
        print("中位数收益（跌破MA10线，{}{}后）：{:.2f}%".format(days, interval_to_str[interval], median_return_X_day_10_day))
        print()
        return is_5_trend_break, is_10_trend_break, (positive_probability_10_day + positive_probability_5_day) / 2, (
                    average_return_10_day + average_return_5_day) / 2

    @staticmethod
    def analyze_trend_start(stock_data, x=5, m=10, stock_name='', interval='daily'):
        # Convert 'close' column to numeric
        stock_data['close'] = pd.to_numeric(stock_data['close'], errors='coerce')

        # Calculate x-day moving average
        stock_data['x_day_avg'] = stock_data['close'].rolling(window=x).mean()

        # Determine if the stock has broken the upward trend for x-day average
        stock_data['trend_start'] = stock_data['close'] > stock_data['x_day_avg']

        # Calculate returns after first breaking the x-day average
        stock_data['returns_after_start'] = stock_data['close'].pct_change() * 100
        stock_data['returns_m_days_after_start'] = stock_data['returns_after_start'].rolling(m).sum()

        # Output
        is_trend_start = stock_data['trend_start'].iloc[-1]
        returns_m_days_after_break = stock_data[stock_data['trend_start']]['returns_m_days_after_start']
        positive_returns = returns_m_days_after_break[returns_m_days_after_break > 0]
        positive_probability = len(positive_returns) / len(returns_m_days_after_break) * 100 if len(
            returns_m_days_after_break) != 0 else 0
        average_return = returns_m_days_after_break.mean()
        max_gain = returns_m_days_after_break.max()
        max_loss = returns_m_days_after_break.min()
        median_return = returns_m_days_after_break.median()

        print()
        print("股票名称：{}".format(stock_name))
        print("站上 MA{} 后的 {} {}收益情况：".format(x, m, interval_to_str[interval]))
        # print(returns_m_days_after_break)
        print("收益概率：{:.2f}%".format(positive_probability))
        print("数学期望（平均收益）：{:.2f}%".format(average_return))
        print("最大收益：{:.2f}%".format(max_gain))
        print("最大亏损：{:.2f}%".format(max_loss))
        print("中位数收益：{:.2f}%".format(median_return))
        return is_trend_start, positive_probability, average_return

    @staticmethod
    def analyze_macd_divergence_top(stock_data, m=5, stock_name='', interval='daily'):
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
        stock_data['cumulative_returns_after_divergence'] = stock_data['returns_after_divergence'].rolling(m).sum()
        stock_data['cumulative_returns_m_days_after_divergence'] = stock_data[
            'cumulative_returns_after_divergence'].shift(-m)

        # Output
        macd_divergences = stock_data[stock_data['macd_divergence'] != '']
        macd_divergence_type = macd_divergences['macd_divergence'].iloc[-1]
        returns_m_days_after_divergence = macd_divergences['cumulative_returns_m_days_after_divergence']
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
        print("MACD顶背离后的 {} {}收益情况：".format(m, interval_to_str[interval]))
        # print(returns_m_days_after_divergence)
        print("当前MACD背离类型：{}".format(macd_divergence_type))
        print("收益概率：{:.2f}%".format(positive_probability))
        print("数学期望（平均收益）：{:.2f}%".format(average_return))
        print("最大收益：{:.2f}%".format(max_gain))
        print("最大亏损：{:.2f}%".format(max_loss))
        print("中位数收益：{:.2f}%".format(median_return))
        return macd_divergence_type == '顶背离', positive_probability, average_return

    @staticmethod
    def analyze_macd_divergence_bottom(stock_data, m=5, stock_name='', interval='daily'):
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
        stock_data['cumulative_returns_after_divergence'] = stock_data['returns_after_divergence'].rolling(m).sum()
        stock_data['cumulative_returns_m_days_after_divergence'] = stock_data[
            'cumulative_returns_after_divergence'].shift(-m)

        # Output
        macd_divergences = stock_data[stock_data['macd_divergence'] != '']
        macd_divergence_type = macd_divergences['macd_divergence'].iloc[-1]
        cumulative_returns_m_days_after_divergence = macd_divergences['cumulative_returns_m_days_after_divergence']
        positive_returns = cumulative_returns_m_days_after_divergence[cumulative_returns_m_days_after_divergence > 0]
        positive_probability = len(positive_returns) / len(cumulative_returns_m_days_after_divergence) * 100 if len(
            cumulative_returns_m_days_after_divergence) != 0 else 0
        average_return = cumulative_returns_m_days_after_divergence.mean()
        max_gain = cumulative_returns_m_days_after_divergence.max()
        max_loss = cumulative_returns_m_days_after_divergence.min()
        median_return = cumulative_returns_m_days_after_divergence.median()

        print()
        print("股票名称：{}".format(stock_name))
        print("MACD底背离后的 {} {}收益情况：".format(m, interval_to_str[interval]))
        # print(cumulative_returns_m_days_after_divergence)
        print("当前MACD背离类型：{}".format(macd_divergence_type))
        print("是否底背离：{}".format(macd_divergence_type == '底背离'))
        print("收益概率：{:.2f}%".format(positive_probability))
        print("数学期望（平均收益）：{:.2f}%".format(average_return))
        print("最大收益：{:.2f}%".format(max_gain))
        print("最大亏损：{:.2f}%".format(max_loss))
        print("中位数收益：{:.2f}%".format(median_return))
        return macd_divergence_type == '底背离', positive_probability, average_return
    @staticmethod
    def analyze_should_follow(stock_code, m=5, stock_name='', interval_type='daily', start_date='2000-01-01', end_date='2024-03-25'):
        stock_data = StockStrategySimulator.get_stock_data(stock_code, interval=interval_type, start_date=start_date, end_date=end_date)
        results = []
        is_golden_across, prob, eval = StockStrategySimulator.analyze_stock_data_macd_kdj(stock_data, stock_name=stock_name, interval=interval_type)
        if is_golden_across:
            results.append((prob, eval))
        is_5_trend_break, is_10_trend_break, prob, eval = StockStrategySimulator.analyze_trend_break(stock_data, stock_name=stock_name, interval=interval_type)
        if is_5_trend_break or is_10_trend_break:
            results.append((prob, eval))
        is_trend_start, prob, eval = StockStrategySimulator.analyze_trend_start(stock_data, x=5, m=m, stock_name=stock_name, interval=interval_type)
        if is_trend_start:
            results.append((prob, eval))
        is_top_diver, prob, eval = StockStrategySimulator.analyze_macd_divergence_top(stock_data, m=m, stock_name=stock_name, interval=interval_type)
        if is_top_diver:
            results.append((prob, eval))
        is_bottom_diver, prob, eval = StockStrategySimulator.analyze_macd_divergence_bottom(stock_data, m=m, stock_name=stock_name, interval=interval_type)
        if is_bottom_diver:
            results.append((prob, eval))
        expectation = sum(prob * eval for prob, eval in results)
        expectation /= 100
        should_buy = '是'
        if expectation < 0:
            should_buy = '否'
        print(f"预期10{interval_to_str[interval_type]}后收益：{expectation:.2f}%，{interval_to_str[interval_type]}级别判断是否应该买入：{should_buy}")
        return should_buy, expectation, interval_type

# 指定目录进行操作
directory_path = '../data/stock'
remove_subset_files(directory_path)

# stock_code = "sh.600418"
# interval_type = 'daily'
interval_type = 'monthly'

start_date = '2000-01-01'
# start_date = '2018-01-01'
end_date = '2024-04-05'

stock_code_code_list = ['sh.600418', 'sh.600733', 'sh.600863', 'sh.600938', 'sh.601127', 'sz.000333', 'sz.000628', 'sz.301236', 'sz.300570', 'sz.000737', 'sh.601600', 'sz.002714', 'hk.0700']
# stock_data = StockStrategySimulator.get_stock_data(stock_code, interval=interval_type, start_date='2023-01-01', end_date='2024-03-24')
# StockStrategySimulator.analyze_stock_data_macd_kdj(stock_data)
# StockStrategySimulator.analyze_trend_break(stock_data)
# StockStrategySimulator.analyze_trend_start(stock_data, x=5, stock_name=stock_code)
# StockStrategySimulator.analyze_macd_divergence_top(stock_data, m=5, stock_name=stock_code)
# StockStrategySimulator.analyze_macd_divergence_bottom(stock_data, m=5, stock_name=stock_code)
for stock_code in stock_code_code_list:
    try:
        stock_name = str(stock_code)
        if stock_code in stock_code_to_company:
            stock_name = stock_code_to_company[stock_code]
        StockStrategySimulator.analyze_should_follow(stock_code, 5, stock_name, interval_type, start_date, end_date)
        time.sleep(5)
    except Exception as e:
        print(f"{stock_name}:{e}")