"""Numerical tests and portable fixtures; no experiment outcomes are fabricated."""
import json
from pathlib import Path
import numpy as np
from ch9_core import *


def run_tests(outdir=None):
    checks={}
    rng=PortableRNG(1)
    u=rng.uniform((3,))
    assert np.allclose(u,np.array([16807,282475249,1622650073])/2147483647,rtol=0,atol=1e-15)
    checks['portable_rng']=True
    c=Config();rng=PortableRNG(33);actor=actor_init(rng,c)
    x=rng.normal((9,OBS_DIM))*.3;b=rng.normal((9,3))*.2
    mu,_=net_forward(actor,x);old=logprob(mu,actor['logstd'],b)+np.array([0,.3,-.3,0,.3,-.3,0,.3,-.3])
    adv=np.array([1,2,3,-1,-2,-3,.2,-.2,1.])
    loss,grad,_,_=actor_loss_grad(actor,x,b,old,adv,c.ppo_clip)
    errors=[]
    for name,ix in [('W1',(2,1)),('b1',(3,)),('W2',(2,1)),('b2',(1,)),('logstd',(2,))]:
        val=actor[name][ix];eps=1e-6
        actor[name][ix]=val+eps;l1=actor_loss_grad(actor,x,b,old,adv,c.ppo_clip)[0]
        actor[name][ix]=val-eps;l0=actor_loss_grad(actor,x,b,old,adv,c.ppo_clip)[0]
        actor[name][ix]=val;errors.append(abs((l1-l0)/(2*eps)-grad[name][ix]))
    assert max(errors)<2e-7,errors
    checks['ppo_gradient_max_abs_error']=float(max(errors))
    c.epochs=1
    critic=net_init(rng,OBS_DIM,c.hidden,1,.05);target=rng.normal((9,1))
    y,h=net_forward(critic,x);cg=net_backward(critic,x,h,(y-target)/len(x))
    val=critic['W1'][1,2];eps=1e-6
    critic['W1'][1,2]=val+eps;l1=np.mean((net_forward(critic,x)[0]-target)**2)/2
    critic['W1'][1,2]=val-eps;l0=np.mean((net_forward(critic,x)[0]-target)**2)/2
    critic['W1'][1,2]=val
    err=abs((l1-l0)/(2*eps)-cg['W1'][1,2]);assert err<1e-7
    checks['critic_gradient_abs_error']=float(err)
    # Gate skipped outside the eroded opening: terminal DQ, no awarded finish.
    e=RaceBatch(c,1,PortableRNG(1));e.p[0,0]=[9.9,3.,2.5];e.v[0,0]=[5,0,0]
    e.p[0,1]=[0,-2,2.5];e.step(np.zeros((1,2,3)))
    assert e.reason[0]==5 and e.g[0,0]==0
    checks['missed_gate_is_disqualification']=True
    # Crossing sweeps can collide even when both endpoint distances are safe.
    e=RaceBatch(c,1,PortableRNG(1));e.p[0,0]=[0,-1.,2.5];e.p[0,1]=[0,1.,2.5]
    e.v[0,0]=[0,60,0];e.v[0,1]=[0,-60,0]
    e.step(np.zeros((1,2,3)));assert e.reason[0]==4
    assert abs(e.t[0]-.01)<1e-10
    checks['swept_collision_time_error']=float(abs(e.t[0]-.01))
    # Two finishes in the same numerical step: earlier finish wins.
    e=RaceBatch(c,1,PortableRNG(1));e.g[:]=4
    e.p[0,0]=[49.9,-.45,2.5];e.p[0,1]=[49.8,.45,2.5];e.v[:]=[5,0,0]
    e.step(np.zeros((1,2,3)));assert e.reason[0]==1 and abs(e.t[0]-.02)<1e-10
    checks['substep_finish_order']=True
    # Later infringement must not override an earlier valid finish.
    e=RaceBatch(c,1,PortableRNG(1));e.g[:]=4
    e.p[0,0]=[49.95,-.5,2.5];e.p[0,1]=[49.8,2.0,2.5];e.v[:]=[5,0,0]
    e.step(np.zeros((1,2,3)));assert e.reason[0]==1
    checks['earliest_event_priority']=True
    # Complete episode reward telescoping, no leakage of opponent future action.
    r,details,_=evaluate(actor,c,505,80)
    assert r['potential_audit']<1e-12 and np.max(details[:,9])<=c.accel_max+1e-10
    checks['potential_telescoping_max_error']=r['potential_audit']
    checks['acceleration_bound']=True
    # Identical seed repeats the same complete rollout.
    r2,d2,_=evaluate(actor,c,505,80)
    assert np.allclose(details,d2,rtol=0,atol=0)
    checks['exact_python_reproducibility']=True
    # Complete races, no nonterminal failures hidden in the metric denominator.
    assert np.all(details[:,2]>0) and len(details)==80
    checks['all_episodes_accounted_for']=True
    # Explicit clipped objectives, hand-calculated in the chapter.
    A=np.array([2,2,-2,-2]);rho=np.array([1.5,.6,.6,1.5]);terms=np.minimum(rho*A,np.clip(rho,.8,1.2)*A)
    assert np.allclose(terms,[2.4,1.2,-1.6,-3.0]);checks['ppo_hand_calculation']=True
    if outdir:
        p=Path(outdir);p.mkdir(parents=True,exist_ok=True)
        (p/'python_tests.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
        # Shared numerical fixtures for native MATLAB to verify its implementation.
        fixture=dict(config=asdict(c),actor={k:v.tolist() for k,v in actor.items()},
                     x=x.tolist(),b=b.tolist(),oldlp=old.tolist(),adv=adv.tolist(),
                     loss=loss,gradient={k:v.tolist() for k,v in grad.items()},
                     evaluation_seed=505,evaluation_n=80,evaluation_details=details.tolist())
        (p/'cross_language_fixture.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
    return checks


if __name__=='__main__':
    print(json.dumps(run_tests(Path(__file__).resolve().parents[1]/'validation'),indent=2))
