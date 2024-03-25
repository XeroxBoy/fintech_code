#先引入后面分析、可视化等可能用到的库
import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
#正常显示画图时出现的中文和负号
from pylab import mpl
mpl.rcParams['font.sans-serif']=['SimHei']
mpl.rcParams['axes.unicode_minus']=False

#设置token
token='502a0381bef1008df45a4580053769e383de24f2855152dbb200ccc9'
#ts.set_token(token)
pro = ts.pro_api(token)