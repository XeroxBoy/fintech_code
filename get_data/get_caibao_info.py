# 获取股票代码名称信息
import baostock as bs
import pandas as pd
from tqdm import tqdm
lg = bs.login()
rs = bs.query_all_stock(day="2024-03-25")
data_list = []
while (rs.error_code == '0') & rs.next():
    data_list.append(rs.get_row_data())
result = pd.DataFrame(data_list, columns=rs.fields)
result
code_ = list(result["code"])
lg = bs.login()
data_list = []
for i in tqdm(code_):
    rs = bs.query_stock_basic(code=i)
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())

result2 = pd.DataFrame(data_list, columns=rs.fields)
print(result2.head())

# 盈利能力
lg = bs.login()

profit_list = []
rs_profit = bs.query_profit_data(code="sh.600938", year=2023,
                                 quarter=4  # 此处还是季度：可选1 2 3 4
                                 )
while (rs_profit.error_code == '0') & rs_profit.next():
    profit_list.append(rs_profit.get_row_data())
result_profit = pd.DataFrame(profit_list, columns=rs_profit.fields)
