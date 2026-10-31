"""Compare both independently generated chapter-6 trajectories."""
from pathlib import Path
import json
import numpy as np

root=Path(__file__).resolve().parent
report={}
for name in ('feedback','learning'):
    a=np.loadtxt(root/'Python/results'/f'{name}.csv',delimiter=',',skiprows=1)
    b=np.loadtxt(root/'MATLAB/results'/f'{name}.csv',delimiter=',',skiprows=1)
    assert a.shape==b.shape==(1001,14)
    assert np.allclose(a,b,rtol=1e-9,atol=1e-8),name
    report[name]={'rows':len(a),'columns':a.shape[1],
                  'max_abs_difference':float(np.max(np.abs(a-b)))}
report['passed']=True
(root/'cross_language_validation.json').write_text(json.dumps(report,indent=2),'utf-8')
print(json.dumps(report,indent=2))
