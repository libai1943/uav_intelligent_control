"""Recompute constraints from CSV, then compare independent MATLAB/Python runs.

Run both entry points first. This script does not trust a solver success flag.
All checks concern the stated single-step Euler planning model, not real flight.
"""
from pathlib import Path
import json
import numpy as np

ROOT=Path(__file__).resolve().parent
SETTINGS=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
CFG=SETTINGS['config'];SX=np.array([600,150,150,20,.3,.6,.6]);SU=np.array([2,.08,.4])
CASES=['two_straight','two_north','two_south','two_corridor','four_direct','four_corridor','five_corridor','four_grid100']

def read(path):
    return np.loadtxt(path,delimiter=',',skiprows=1,ndmin=2)

def dynamics(x,u):
    v,ga,ch,phi=x[:,3],x[:,4],x[:,5],x[:,6]
    return np.column_stack([v*np.cos(ga)*np.cos(ch),v*np.cos(ga)*np.sin(ch),v*np.sin(ga),
                            u[:,0],u[:,1],9.81*np.tan(phi)/v,u[:,2]])

def verify(folder,case):
    state=read(folder/'state.csv');control=read(folder/'control.csv')
    t=state[:,0];x=state[:,1:];u=control[:,1:];N=len(u);dt=CFG['duration_s']/N
    assert x.shape==(N+1,7) and u.shape==(N,3) and np.all(np.isfinite(x)) and np.all(np.isfinite(u))
    assert np.allclose(t,np.arange(N+1)*dt,atol=1e-11) and np.allclose(control[:,0],t[:-1],atol=1e-11)
    scene=SETTINGS['scenes'][case.split('_')[0]];obs=np.array(scene['columns'],float)
    lo=np.tile(CFG['state_lower'],(N+1,1)).astype(float);hi=np.tile(CFG['state_upper'],(N+1,1)).astype(float)
    lo[:,3:]+=[.15,.02,.02,.02];hi[:,3:]-=[.15,.02,.02,.02]
    corridor='corridor' in case or case=='four_grid100'
    obstacle_violation=0.
    if corridor:
        boxes=read(folder/'boxes.csv');assert boxes.shape==(20,6);group=N//20
        for i,b in enumerate(boxes):
            ids=slice(i*group,(i+1)*group+1)
            lo[ids,:3]=np.maximum(lo[ids,:3],b[:3]+CFG['corridor_node_buffer_m'])
            hi[ids,:3]=np.minimum(hi[ids,:3],b[3:]-CFG['corridor_node_buffer_m'])
            d=np.maximum(np.maximum(b[:2]-obs[:,:2],obs[:,:2]-b[3:5]),0)
            assert np.min(np.linalg.norm(d,axis=1)-obs[:,2])>CFG['safety_margin_m']
        assert np.all(lo<=hi)
    else:
        for cx,cy,r in obs:
            g=((x[:,0]-cx)**2+(x[:,1]-cy)**2)/(r+CFG['safety_margin_m']+CFG['corridor_node_buffer_m'])**2-1
            obstacle_violation=max(obstacle_violation,float(np.max(-g)))
    lo[0]=hi[0]=CFG['start_state'];lo[-1]=hi[-1]=scene['goal']
    defect=(x[1:]-x[:-1]-dt*dynamics(x[:-1],u))/SX
    eta=max(0.,np.max(abs(defect)),obstacle_violation,np.max((lo-x)/SX),np.max((x-hi)/SX),
            np.max((np.array(CFG['input_lower'])-u)/SU),np.max((u-np.array(CFG['input_upper']))/SU))
    assert eta<1e-6,(case,'scaled violation',eta)
    rollout=np.empty_like(x);rollout[0]=CFG['start_state']
    for k in range(N):rollout[k+1]=rollout[k]+dt*dynamics(rollout[k:k+1],u[k:k+1])[0]
    position_error=np.max(np.linalg.norm(rollout[:,:3]-x[:,:3],axis=1))
    assert position_error<1e-3
    assert np.linalg.norm(rollout[-1,:3]-np.array(scene['goal'])[:3])<1e-3
    assert np.max(abs(rollout[-1,3:]-np.array(scene['goal'])[3:]))<1e-5
    clear=np.inf
    for a,b in zip(rollout[:-1,:2],rollout[1:,:2]):
        v=b-a;w=obs[:,:2]-a;lam=np.clip(w@v/max(v@v,1e-30),0,1)
        clear=min(clear,float(np.min(np.linalg.norm(w-lam[:,None]*v,axis=1)-obs[:,2])))
    assert clear>=CFG['safety_margin_m'],(case,'segment clearance',clear)
    objective=dt*np.sum((u/SU)**2*np.array([.3,1,1]))
    meta=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    assert meta['solver_success'] and meta['accepted']
    assert abs(objective-meta['objective'])<1e-9
    return dict(eta=float(eta),objective=float(objective),min_segment_clearance_m=clear,
                reconstruction_position_error_m=float(position_error)),state,control

def main():
    records=[]
    for case in CASES:
        pa=ROOT/'results_kinematic'/case;pb=ROOT/'results_matlab'/case
        assert (pa/'state.csv').is_file() and (pb/'state.csv').is_file(),f'Run both entry points first: missing {case}'
        a,xa,ua=verify(pa,case);b,xb,ub=verify(pb,case)
        dx=float(np.max(abs(xa-xb)));du=float(np.max(abs(ua-ub)))
        assert dx<2e-6 and du<2e-7,(case,dx,du)
        assert abs(a['objective']-b['objective'])<1e-8
        for name in ['raw_path.csv','initial_state.csv','initial_control.csv']:
            x,y=read(pa/name),read(pb/name);assert x.shape==y.shape and np.max(abs(x-y))<2e-7,(case,name)
        records.append(dict(case=case,python=a,matlab=b,max_state_csv_difference=dx,max_control_csv_difference=du))
        print(case, 'PASS', f'state difference={dx:.3g}, input difference={du:.3g}')
    a=read(ROOT/'results_kinematic/forward_example.csv');b=read(ROOT/'results_matlab/forward_example.csv')
    assert np.max(abs(a-b))<1e-9
    a=json.loads((ROOT/'results_kinematic/gradient_example.json').read_text());b=json.loads((ROOT/'results_matlab/gradient_example.json').read_text())
    assert len(a)==len(b)==4
    for x,y in zip(a,b):
        assert x['iterations']==y['iterations'] and abs(x['solution']-y['solution'])<1e-12
    report=dict(passed=True,scope='8 independent MATLAB/Python single-step Euler OCPs plus forward and gradient illustrations',
                criterion='Each language independently passes physical/normalized checks; then CSV comparison',results=records)
    (ROOT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('All Chapter 3 checks passed.')

if __name__=='__main__':main()
