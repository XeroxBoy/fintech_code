import initial
import pandas as pd
#获取当前上市的股票代码、简称、注册地、行业、上市时间等数据
basic= initial.pro.stock_basic(list_status='L')
#查看前五行数据
#basic.head(5)

#获取平安银行日行情数据
pa= initial.pro.daily(ts_code='000001.SZ', start_date='20180101',
                      end_date='20190106')
#pa.head()

#K线图可视化
from pyecharts import Kline
pa.index=pd.to_datetime(pa.trade_date)
pa=pa.sort_index()
v1=list(pa.loc[:,['open','close','low','high']].values)
t=pa.index
v0=list(t.strftime('%Y%m%d'))
kline = Kline("平安银行K线图",title_text_size=15)
kline.add("", v0, v1,is_datazoom_show=True,
         mark_line=["average"],
         mark_point=["max", "min"],
         mark_point_symbolsize=60,
         mark_line_valuedim=['highest', 'lowest'] )
#kline.render("上证指数图.html")
kline