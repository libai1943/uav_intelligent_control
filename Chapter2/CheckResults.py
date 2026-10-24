"""两个入口都运行后，执行 python CheckResults.py 核验独立实现的逐时刻数据。
数值容差只用于CSV存储精度核对，不是实机飞行精度指标。
"""
from pathlib import Path
import json
import numpy as np
R=Path(__file__).resolve().parent
report={}
for c in json.loads((R/'Python'/'experiment_cases.json').read_text(encoding='utf-8')):
    name=c['name'];a=np.loadtxt(R/'Python'/'results'/f'{name}.csv',delimiter=',',skiprows=1)
    b=np.loadtxt(R/'MATLAB'/'results_matlab'/f'{name}.csv',delimiter=',',skiprows=1)
    if name=='feedforward_open':b=b[:,[0,2,3]]
    assert a.shape==b.shape,(name,a.shape,b.shape)
    error=float(np.max(np.abs(a-b)))
    assert error<1e-7,(name,error)
    report[name]=error
(R/'Python'/'results'/'cross_language_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(f'{len(report)}组逐时刻数据通过：最大绝对差 {max(report.values()):.3g}')
