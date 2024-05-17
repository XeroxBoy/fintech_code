def calculate_profit(down_payment, total_price, interest_rate, loan_term, investment_years, zhuangxiu_cost, zujin_return, expected_growth_rate):
    # 计算贷款金额
    loan_amount = total_price - down_payment

    return_amount = loan_amount * investment_years / loan_term

    # 计算每月还款金额
    monthly_interest_rate = interest_rate / 12 / 100
    number_of_payments = loan_term * 12 # 还的总月数
    monthly_payment = loan_amount * monthly_interest_rate * (1 + monthly_interest_rate) ** number_of_payments / \
                      ((1 + monthly_interest_rate) ** number_of_payments - 1)

    money_time_value = down_payment * investment_years * 3 / 100

    if investment_years <= 8:
        zhejiu = zhuangxiu_cost * 0.1 * investment_years
    else:
        zhejiu = zhuangxiu_cost * 0.8

    total_give_bank = monthly_payment * investment_years * 12 # 给银行交的月供
    # 计算贷款总利息
    total_interest = total_give_bank - return_amount

    # 计算房屋升值后的价值
    future_value = total_price * (1 + expected_growth_rate / 100)

    all_zujin_return = zujin_return * investment_years

    # 计算收益
    return future_value + all_zujin_return - total_price - total_interest - zhejiu - money_time_value, total_give_bank

# 示例用法
down_payment = 800000 # 首付
first_pay_percentage = 0.3 # 首付比例
total_price =  down_payment / first_pay_percentage # 总价
interest_rate = 3.75 # 房贷利率
loan_term = 30  # 贷款年限
investment_years = 2  # 收益年份
expected_growth_rate = 40  # 预期涨幅
zhuangxiu_cost = 5 # 装修花费
zujin_return = total_price * 0.014 # 租售比

for i in range(-30, 250, 5):
    expected_growth_rate = i
    profit, total_give_bank = calculate_profit(down_payment, total_price, interest_rate, loan_term, investment_years, zhuangxiu_cost, zujin_return, expected_growth_rate)
    total_return_rate = float(profit) * 100.0 / down_payment
    annual_return = ((1 + total_return_rate / 100) ** (1 / investment_years)) - 1

    print(f"首付{down_payment/10000}万 投资{investment_years}年 期间交月供共{total_give_bank:.2f}元 每个月还{total_give_bank/(investment_years*12):.2f}元 期间涨幅{expected_growth_rate}%  收益：{int(profit/10000)}万元 收益率:{total_return_rate:.2f}% 年化收益率:{annual_return*100:.2f}%")