from pathlib import Path
import numpy as np, json
r=Path(__file__).resolve().parent
checks={}
left=sorted((r/'Python/results').glob('*.csv'))
right=sorted((r/'MATLAB/results').glob('*.csv'))
assert left and {p.name for p in left}=={p.name for p in right}
for p in left:
 q=r/'MATLAB/results'/p.name
 assert p.read_text(encoding='utf8').splitlines()[0]==q.read_text(encoding='utf8').splitlines()[0]
 a=np.loadtxt(p,delimiter=',',skiprows=1);b=np.loadtxt(q,delimiter=',',skiprows=1)
 assert a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all()
 delta=float(np.max(np.abs(a-b)));assert np.allclose(a,b,atol=1e-8,rtol=1e-9),(p.name,delta)
 checks[p.name]={'rows':len(a),'columns':a.shape[1],'max_absolute_difference':delta}
report={'passed':True,'cases':checks,'atol':1e-8,'rtol':1e-9,'date':'2026-10-25'}
(r/'cross_language_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(f'{r.name}: {len(checks)} comparisons passed; largest difference {max(x["max_absolute_difference"] for x in checks.values()):.3g}')
