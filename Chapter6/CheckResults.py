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
training_report={}
for name in ('training_samples','single_parameters','mini_parameters','full_parameters','single_loss','mini_loss','full_loss'):
    a=np.loadtxt(root/'Python/results/training_modes'/f'{name}.csv',delimiter=',',skiprows=1)
    b=np.loadtxt(root/'MATLAB/results/training_modes'/f'{name}.csv',delimiter=',',skiprows=1)
    assert a.shape==b.shape
    assert np.allclose(a,b,rtol=1e-9,atol=1e-8),name
    training_report[name]={'rows':len(a),'columns':a.shape[1],'max_abs_difference':float(np.max(np.abs(a-b)))}
report['training_modes']=training_report
report['passed']=True
(root/'cross_language_validation.json').write_text(json.dumps(report,indent=2),'utf-8')
print(json.dumps(report,indent=2))
