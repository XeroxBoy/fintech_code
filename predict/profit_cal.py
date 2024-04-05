def calculate_profit(down_payment, total_price, interest_rate, loan_term, investment_years, expected_growth_rate):
    # 计算贷款金额
    loan_amount = total_price - down_payment

    # 计算每月还款金额
    monthly_interest_rate = interest_rate / 12 / 100
    number_of_payments = loan_term * 12
    monthly_payment = loan_amount * monthly_interest_rate * (1 + monthly_interest_rate) ** number_of_payments / \
                      ((1 + monthly_interest_rate) ** number_of_payments - 1)

    # 计算贷款总利息
    total_interest = monthly_payment * number_of_payments - loan_amount

    # 计算房屋升值后的价值
    future_value = total_price * (1 + expected_growth_rate / 100)

    # 计算收益
    return future_value - down_payment - total_interest

# 示例用法
down_payment = 1000000  # 首付
total_price = 3000000  # 总价
interest_rate = 3.9  # 房贷利率
loan_term = 30  # 贷款年限
investment_years = 3  # 收益年份
expected_growth_rate = 50.0  # 预期涨幅

profit = calculate_profit(down_payment, total_price, interest_rate, loan_term, investment_years, expected_growth_rate)
print("收益：", profit)