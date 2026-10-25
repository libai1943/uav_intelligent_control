"""Fresh training, independent evaluation, raw data, model weights, and figures."""
from __future__ import annotations
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
from pathlib import Path
import csv,json,platform,sys,time
from dataclasses import asdict
import numpy as np
from ch9_core import *
from test_ch9 import run_tests

DETAIL_HEADER=['episode','opponent','reason','score_A','score_B','stop_time','gates_A','gates_B',
               'minimum_separation','maximum_acceleration','shaped_return_A','shaped_return_B','initial_potential_A','initial_potential_B']
TRACE_HEADER=['episode','time','x_A','y_A','z_A','x_B','y_B','z_B','vx_A','vy_A','vz_A','vx_B','vy_B','vz_B',
              'gate_A','gate_B','action_speed_A','action_y_A','action_z_A','action_speed_B','action_y_B','action_z_B','done']

def write_rows(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:return
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def save_array(path,x,header):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    np.savetxt(path,x,delimiter=',',header=','.join(header),comments='',fmt='%.16g')

def metrics_from_details(d):
    reason=d[:,2].astype(int);valid=np.isin(reason,[1,3]);fail=np.isin(reason,[4,5,7])
    return dict(n=len(d),win=float(np.mean(reason==1)),tie=float(np.mean(reason==3)),violation=float(np.mean(fail)),
       separation_violation=float(np.mean(reason==4)),valid_finish=float(np.mean(valid)),
       timeout=float(np.mean(reason==8)),score=float(d[:,3].mean()),
       finish_time=float(d[valid,5].mean()) if valid.any() else None,
       mean_gates=float(d[:,6].mean()))

def run_seed(seed,cfg,out,verbose=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=[];history=[];initial=None
    for mode in ['fixed','league']:
        actor,initial,critic,pool,records=train(cfg,seed,mode,verbose=verbose)
        modeldir=out/'models';save_net(actor,modeldir/f'{mode}_{seed}.json')
        save_net(critic,modeldir/f'{mode}_{seed}_critic.json')
        for j,a in enumerate(pool):save_net(a,modeldir/f'{mode}_{seed}_history{j}.json')
        write_rows(out/f'training_{mode}_{seed}.csv',records)
        save_net(initial,modeldir/f'initial_{seed}.json')
        # Final iteration, not a test-selected best checkpoint.
        for execution in ['sampled','mean']:
            _,d,_=evaluate(actor,cfg,1800000+seed,cfg.eval_episodes,deterministic=execution=='mean')
            name=f'{mode}_{execution}'
            save_array(out/f'evaluation_{name}_{seed}.csv',d,DETAIL_HEADER)
            row=dict(seed=seed,method=name,**metrics_from_details(d));rows.append(row)
            for kind in range(5):
                dd=d[d[:,1]==kind]
                history.append(dict(seed=seed,method=name,opponent=kind,**metrics_from_details(dd)))
        # A changed track and previously unseen rule policies are held out.
        _,d,_=evaluate(actor,cfg,1900000+seed,cfg.eval_episodes,kinds=(1,3,4),mirror=False)
        save_array(out/f'evaluation_{mode}_holdout_{seed}.csv',d,DETAIL_HEADER)
        rows.append(dict(seed=seed,method=mode+'_holdout',**metrics_from_details(d)))
        _,d,_=evaluate(actor,cfg,1900000+seed,cfg.eval_episodes,kinds=(1,3,4),mirror=True)
        save_array(out/f'evaluation_{mode}_mirror_{seed}.csv',d,DETAIL_HEADER)
        rows.append(dict(seed=seed,method=mode+'_mirror',**metrics_from_details(d)))
        if mode=='league':
            # Fixed observation intervention, not a separately trained architecture.
            _,d,_=evaluate(actor,cfg,1800000+seed,cfg.eval_episodes,blind=True)
            save_array(out/f'evaluation_league_blind_{seed}.csv',d,DETAIL_HEADER)
            rows.append(dict(seed=seed,method='league_blind',**metrics_from_details(d)))
    for name,rule in [('initial',None),('rule_center',0),('rule_reactive',2),('rule_fast',3),('rule_max',5)]:
        _,d,_=evaluate(initial,cfg,1800000+seed,cfg.eval_episodes,rule=rule)
        save_array(out/f'evaluation_{name}_{seed}.csv',d,DETAIL_HEADER)
        rows.append(dict(seed=seed,method=name,**metrics_from_details(d)))
    write_rows(out/f'metrics_{seed}.csv',rows);write_rows(out/f'by_opponent_{seed}.csv',history)
    return rows

def summarize(out,seeds):
    allrows=[];by=[];out=Path(out)
    for seed in seeds:
        with (out/f'metrics_{seed}.csv').open() as f:allrows.extend(list(csv.DictReader(f)))
        with (out/f'by_opponent_{seed}.csv').open() as f:by.extend(list(csv.DictReader(f)))
    write_rows(out/'metrics_by_seed.csv',allrows);write_rows(out/'metrics_by_opponent.csv',by)
    methods=list(dict.fromkeys(r['method'] for r in allrows));agg=[]
    for method in methods:
        rr=[r for r in allrows if r['method']==method];dd=[]
        for seed in seeds:
            dd.append(np.loadtxt(out/f'evaluation_{method}_{seed}.csv',delimiter=',',skiprows=1))
        row=dict(method=method,seeds=len(seeds),**metrics_from_details(np.concatenate(dd)))
        row['win_sd_between_seeds']=float(np.std([float(r['win']) for r in rr],ddof=1)) if len(rr)>1 else 0.
        row['score_sd_between_seeds']=float(np.std([float(r['score']) for r in rr],ddof=1)) if len(rr)>1 else 0.
        agg.append(row)
    write_rows(out/'summary.csv',agg)
    return agg

def trajectory_examples(cfg,out,seed=101):
    out=Path(out);actor=load_net(out/'models'/f'league_{seed}.json')
    # Trace all episodes from a fixed additional evaluation seed. Select by a
    # declared rule: first initially trailing winning episode against fast rule 3.
    _,d,logs=evaluate(actor,cfg,1810101,100,kinds=(3,),trace=True)
    trace=np.concatenate(logs);save_array(out/'trajectory_all_episodes.csv',trace,TRACE_HEADER)
    initial=logs[0];candidates=np.where((d[:,2]==1)&(initial[:,2]<initial[:,5]))[0]
    eid=int(candidates[0]) if len(candidates) else int(np.flatnonzero(d[:,2]==1)[0]) if np.any(d[:,2]==1) else 0
    ep=trace[trace[:,0]==eid];ep=ep[np.r_[True,np.diff(ep[:,1])>1e-10]]
    save_array(out/'trajectory_example.csv',ep,TRACE_HEADER)
    (out/'trajectory_selection.json').write_text(json.dumps(dict(seed=1810101,episode=eid,rule='first initially trailing winner vs held-out fast opponent; otherwise first winner, otherwise episode 0',result=d[eid].tolist()),indent=2))
    # Counterexample: first actual violating episode, preserved as teaching data.
    bad=np.flatnonzero(np.isin(d[:,2],[4,5,7]))
    if len(bad):
        b=trace[trace[:,0]==bad[0]];b=b[np.r_[True,np.diff(b[:,1])>1e-10]]
        save_array(out/'trajectory_failure.csv',b,TRACE_HEADER)

def run_all(profile='book',seeds=None,out=None,parallel=False):
    import concurrent.futures
    root=Path(__file__).resolve().parents[1]
    out=Path(out or root/'Python'/('outputs' if profile=='book' else 'outputs_quick'));out.mkdir(parents=True,exist_ok=True)
    (out/'run_status.json').write_text(json.dumps({'status':'running','profile':profile}),encoding='utf-8')
    cfg=Config()
    if profile=='quick':cfg.iterations=20;cfg.batch_episodes=32;cfg.eval_episodes=80
    elif profile!='book':raise ValueError('profile must be book or quick')
    seeds=seeds or ([101,202,303] if profile=='book' else [101])
    start=time.perf_counter();checks=run_tests(root/'validation')
    from foundations import run as run_foundations
    run_foundations(out)
    meta=dict(profile=profile,training_seeds=seeds,config=asdict(cfg),gates=GATES.tolist(),
      python=sys.version,numpy=np.__version__,platform=platform.platform(),
      runtime='Python (native)',matlab_runtime_verified=False,
      explanation='All PPO policies are trained from random initialization; shipped models are not loaded by this entry point.')
    (out/'configuration.json').write_text(json.dumps(meta,indent=2))
    if parallel and len(seeds)>1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=min(3,len(seeds))) as ex:
            jobs=[ex.submit(run_seed,s,cfg,str(out)) for s in seeds]
            for f in jobs:f.result()
    else:
        for s in seeds:run_seed(s,cfg,out)
    agg=summarize(out,seeds);trajectory_examples(cfg,out,seeds[0])
    meta['elapsed_seconds']=time.perf_counter()-start
    (out/'configuration.json').write_text(json.dumps(meta,indent=2))
    from plot_results import make_all
    make_all(out)
    (out/'run_status.json').write_text(json.dumps(dict(status='complete',runtime='Python',profile=profile,seeds=seeds),indent=2))
    print('\nSaved results to',out)
    for r in agg:print(r)
    return out

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--profile',choices=['book','quick'],default='book')
    p.add_argument('--seeds');p.add_argument('--out');p.add_argument('--parallel',action='store_true')
    a=p.parse_args();run_all(a.profile,[int(s) for s in a.seeds.split(',')] if a.seeds else None,a.out,a.parallel)
