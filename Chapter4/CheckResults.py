"""Recompute plant motion and metrics from both independent implementations."""
from pathlib import Path
import json
import numpy as np
ROOT=Path(__file__).resolve().parent
CASES=['open_loop','mpc20','mpc5','mpc40','ideal20']

def check(folder,name):
    s=np.loadtxt(folder/(name+'_state.csv'),delimiter=',',skiprows=1)
    u=np.loadtxt(folder/(name+'_control.csv'),delimiter=',',skiprows=1)
    x=s[:,1:];v,ga,ch,phi=x[:-1,3:].T;a,og,op=u[:,1:].T
    f=np.column_stack([v*np.cos(ga)*np.cos(ch),v*np.cos(ga)*np.sin(ch),v*np.sin(ga),a,og,9.81*np.tan(phi)/v,op])
    if name!='ideal20':
        f[:,5]*=1.06;f[45:67,:3]+=[0,1,.3]
    residual=float(np.max(np.abs(x[1:]-x[:-1]-.18*f)))
    assert residual<1e-8,(name,'plant recurrence',residual)
    assert np.all(abs(u[:,1:])<=np.array([2,.08,.4])+1e-5)
    assert np.all(x[:,3:]>=np.array([15,-.2,-.9,-.6])-1e-4)
    assert np.all(x[:,3:]<=np.array([25,.2,.9,.6])+1e-4)
    ref=np.loadtxt(ROOT/'reference/state.csv',delimiter=',',skiprows=1)
    initial=ref[0,1:]+(np.zeros(7) if name=='ideal20' else [0,5,3,0,0,np.deg2rad(3),0])
    assert np.max(abs(x[0]-initial))<1e-9
    err=np.linalg.norm(ref[:,1:4]-x[:,:3],axis=1)
    metrics=json.loads((folder/(name+'.json')).read_text())['metrics']
    assert abs(np.sqrt(np.mean(err**2))-metrics['position_rmse_m'])<1e-8
    assert abs(err[-1]-metrics['position_final_m'])<1e-8
    assert metrics.get('max_qp_violation',0)<1e-4
    if name=='ideal20':assert err.max()<1e-4
    if name=='mpc20':assert err[-1]<.5
    return s,u,residual

def main():
    report={}
    for name in CASES:
        py,pu,pr=check(ROOT/'Python/results',name)
        ma,mu,mr=check(ROOT/'MATLAB/results',name)
        ds=float(np.max(abs(py-ma)));du=float(np.max(abs(pu-mu)))
        assert ds<1e-5 and du<1e-6,(name,ds,du)
        report[name]=dict(python_plant_residual=pr,matlab_plant_residual=mr,max_state_difference=ds,max_input_difference=du,passed=True)
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    print('All five cases passed independent recurrence, bounds, metrics and cross-language checks.')
if __name__=='__main__':main()
