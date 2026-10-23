"""Compare the independent MATLAB and Python introductory experiments."""
from pathlib import Path
import json
import numpy as np
root=Path(__file__).resolve().parent
records=[]
for name in ['wind_0.csv','wind_3.csv','wind_5.csv','time_schedules.csv']:
    a=np.loadtxt(root/'results'/name,delimiter=',',skiprows=1)
    b=np.loadtxt(root/'results_matlab'/name,delimiter=',',skiprows=1)
    assert a.shape==b.shape and np.all(np.isfinite(a)) and np.all(np.isfinite(b))
    delta=float(np.max(abs(a-b)));assert delta<1e-8,(name,delta)
    records.append(dict(file=name,max_absolute_difference=delta))
(root/'validation.json').write_text(json.dumps(dict(passed=True,results=records),indent=2),encoding='utf-8')
print('Chapter 1: MATLAB/Python data agree for all four experiments.')
