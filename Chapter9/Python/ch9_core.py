"""Chapter 9: transparent NumPy PPO and a two-vehicle gate-racing simulator.

No RL framework or pretrained controller is used.  The learned action is a
reference speed plus two gate offsets; an explicit acceleration-limited
velocity loop advances the point-mass teaching model.  All statistics include
failed and timed-out episodes.  See docs/MODEL_AND_VALIDATION.md.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import numpy as np


class PortableRNG:
    """Park--Miller generator; row-major draws match the supplied MATLAB code."""
    def __init__(self, seed: int):
        self.state = int(seed) % 2147483647 or 1
    def uniform(self, shape):
        n = int(np.prod(shape)); out = np.empty(n)
        s = self.state
        for j in range(n):
            s = (16807 * s) % 2147483647
            out[j] = s / 2147483647.0
        self.state = s
        return out.reshape(shape)
    def normal(self, shape):
        n = int(np.prod(shape)); m = (n+1)//2
        u = self.uniform((m,2))
        r = np.sqrt(-2*np.log(np.maximum(u[:,0],1e-15)))
        a = 2*np.pi*u[:,1]
        z = np.column_stack((r*np.cos(a),r*np.sin(a))).ravel()[:n]
        return z.reshape(shape)
    def permutation(self, n):
        # Sorting independent uniforms gives a reproducible random permutation.
        return np.argsort(self.uniform((n,)), kind='stable')


@dataclass
class Config:
    dt: float = 0.05
    substeps: int = 4
    time_limit: float = 24.0
    speed_mid: float = 4.5
    speed_scale: float = 2.0
    accel_max: float = 6.0
    velocity_tau: float = 0.35
    lateral_gain: float = 2.2
    lateral_speed_max: float = 2.2
    vertical_speed_max: float = 1.6
    gate_margin: float = 0.30
    separation: float = 0.80
    offset_fraction: float = 0.80
    beta: float = 1.0
    gamma: float = 1.0
    hidden: int = 24
    actor_lr: float = 5e-4
    critic_lr: float = 1.5e-3
    ppo_clip: float = 0.20
    epochs: int = 4
    minibatch: int = 256
    grad_clip: float = 0.70
    initial_std: float = 0.45
    std_min: float = 0.07
    std_max: float = 0.65
    batch_episodes: int = 64
    iterations: int = 500
    snapshot_every: int = 10
    pool_capacity: int = 6
    eval_every: int = 10
    eval_episodes: int = 400
    max_kl: float = 0.03


GATES = np.array([[10.,0.,2.5,3.6,2.2],
                  [20.,1.5,3.0,3.2,2.0],
                  [30.,-1.,2.4,1.2,1.0],
                  [40.,1.0,3.0,3.2,2.0],
                  [50.,0.,2.5,2.6,1.8]])
OBS_DIM = 24


def net_init(rng, d, h, out, last_scale=0.02):
    return dict(W1=(2*rng.uniform((d,h))-1)*np.sqrt(3/d),
                b1=np.zeros(h),
                W2=(2*rng.uniform((h,out))-1)*last_scale,
                b2=np.zeros(out))


def net_forward(net, x):
    h = np.tanh(x@net['W1']+net['b1'])
    return h@net['W2']+net['b2'], h


def net_backward(net,x,h,dy):
    dh=(dy@net['W2'].T)*(1-h*h)
    return dict(W1=x.T@dh,b1=dh.sum(axis=0),W2=h.T@dy,b2=dy.sum(axis=0))


def clone(net):
    return {k:v.copy() for k,v in net.items()}


def actor_init(rng,cfg):
    net=net_init(rng,OBS_DIM,cfg.hidden,3)
    net['logstd']=np.full(3,np.log(cfg.initial_std))
    return net


def logprob(mu,logstd,b):
    z=(b-mu)*np.exp(-logstd)
    return -0.5*np.sum(z*z+2*logstd+np.log(2*np.pi),axis=1)


def policy(actor,obs,rng=None,deterministic=False):
    mu,_=net_forward(actor,obs)
    b=mu.copy() if deterministic else mu+np.exp(actor['logstd'])*rng.normal(mu.shape)
    return np.tanh(b),b,logprob(mu,actor['logstd'],b)


def actor_loss_grad(actor,x,b,oldlp,adv,clip):
    mu,h=net_forward(actor,x)
    lp=logprob(mu,actor['logstd'],b)
    # Numerical guard only; normal updates are checked well inside this range.
    lr=np.clip(lp-oldlp,-40,40); ratio=np.exp(lr)
    cr=np.clip(ratio,1-clip,1+clip)
    loss=-np.mean(np.minimum(ratio*adv,cr*adv))
    live=((adv>=0)&(ratio<=1+clip))|((adv<0)&(ratio>=1-clip))
    dlp=-(live*adv*ratio)/len(x)
    invvar=np.exp(-2*actor['logstd']); diff=b-mu
    grads=net_backward(actor,x,h,dlp[:,None]*diff*invvar)
    grads['logstd']=np.sum(dlp[:,None]*(diff*diff*invvar-1),axis=0)
    approx_kl=np.mean(np.exp(lr)-1-lr)
    return float(loss),grads,float(approx_kl),float(np.mean(np.abs(ratio-1)>clip))


class Adam:
    def __init__(self,net):
        self.m={k:np.zeros_like(v) for k,v in net.items()}
        self.v={k:np.zeros_like(v) for k,v in net.items()};self.t=0
    def step(self,net,grad,lr,maxnorm):
        norm=np.sqrt(sum(np.sum(v*v) for v in grad.values()))
        scale=min(1.,maxnorm/(norm+1e-12));self.t+=1
        for k in net:
            g=grad[k]*scale
            self.m[k]=.9*self.m[k]+.1*g
            self.v[k]=.999*self.v[k]+.001*g*g
            mh=self.m[k]/(1-.9**self.t);vh=self.v[k]/(1-.999**self.t)
            net[k]-=lr*mh/(np.sqrt(vh)+1e-8)


class RaceBatch:
    """A batch of independent races. Positions are linearly interpolated in
    each Euler interval for chronological gate/boundary/contact event checks.
    The race ends at the FIRST terminal event, never at a later sampled point.
    Reason: 1 A finishes, 2 B finishes, 3 tie, 4 collision, 5 A DQ,
    6 B DQ, 7 both DQ, 8 timeout. Gate numbering in storage is zero-based.
    """
    def __init__(self,cfg:Config,n:int,rng:PortableRNG,mirror=False):
        if cfg.gamma!=1.0:
            raise ValueError('The finite-race reward implementation requires gamma=1; the Q-learning toy uses a separate discount.')
        if cfg.dt<=0 or cfg.substeps<1 or cfg.velocity_tau<=0:
            raise ValueError('Time steps and velocity time constant must be positive.')
        self.c=cfg;self.n=n;self.gates=GATES.copy()
        if mirror:self.gates[:,1]*=-1
        u=rng.uniform((n,6));self.p=np.zeros((n,2,3));self.v=np.zeros_like(self.p)
        gap=4*(u[:,0]-.5); side=np.where(u[:,1]<.5,-1.,1.)
        self.p[:,0,0]=-.5*gap;self.p[:,1,0]=.5*gap
        self.p[:,0,1]=side*(.80+.1*(u[:,2]-.5));self.p[:,1,1]=-side*(.80+.1*(u[:,3]-.5))
        self.p[:,:,2]=2.5+.08*(u[:,4:6]-.5)
        self.v[:,:,0]=3.5
        # Pair adjacent races by exactly exchanging starting positions.
        if n%2==0:
            self.p[1::2]=self.p[0::2,::-1].copy()
        self.g=np.zeros((n,2),dtype=int);self.t=np.zeros(n);self.prev=np.zeros((n,2,3))
        self.done=np.zeros(n,dtype=bool);self.reason=np.zeros(n,dtype=int)
        self.score=np.zeros((n,2));self.min_sep=np.linalg.norm(self.p[:,0]-self.p[:,1],axis=1)
        self.accel_peak=np.zeros(n);self.phi0=self.potential();self.reward_sum=np.zeros((n,2))
        self.initial_p=self.p.copy()
    def potential(self):
        j=np.minimum(self.g,len(self.gates)-1)
        finishx=self.gates[j,0]
        startx=np.where(j==0,-2.,self.gates[np.maximum(j-1,0),0])
        frac=np.clip((self.p[:,:,0]-startx)/(finishx-startx),0,1)
        val=(j+frac)/len(self.gates)
        val[self.done]=0
        return val
    def obs(self,who=0):
        q=1-who;g=np.minimum(self.g[:,who],len(self.gates)-1)
        c=self.gates[g,:3];c2=self.gates[np.minimum(g+1,len(self.gates)-1),:3]
        # 3 velocity + 3 next gate + 3 following gate + 3 opponent displacement
        # +3 relative velocity + 3 progress/time +3 previous actions +2 gate sizes
        # +1 signed own lateral position; every input is available at execution.
        x=np.column_stack((self.v[:,who]/7.,(c-self.p[:,who])/[15.,3.,2.],
          (c2-self.p[:,who])/[25.,3.,2.],(self.p[:,q]-self.p[:,who])/[8.,3.,2.],
          (self.v[:,q]-self.v[:,who])/7.,self.g[:,who]/5.,self.g[:,q]/5.,
          (self.c.time_limit-self.t)/self.c.time_limit,self.prev[:,who],
          (self.gates[g,3]/2-self.c.gate_margin)/2,
          (self.gates[g,4]/2-self.c.gate_margin),self.p[:,who,1]/5.))
        assert x.shape[1]==OBS_DIM
        return np.clip(x,-5,5)
    def action_physical(self,z):
        j=np.minimum(self.g,4);gw=self.gates[j,3]/2-self.c.gate_margin
        gh=self.gates[j,4]/2-self.c.gate_margin
        a=np.empty_like(z);a[:,:,0]=self.c.speed_mid+self.c.speed_scale*z[:,:,0]
        a[:,:,1]=self.c.offset_fraction*gw*z[:,:,1]
        a[:,:,2]=self.c.offset_fraction*gh*z[:,:,2]
        return a
    def step(self,z):
        if z.shape!=(self.n,2,3) or not np.all(np.isfinite(z)):
            raise ValueError('Expected finite [batch,2,3] normalized actions')
        z=np.clip(z,-1,1);phi_old=self.potential();was_done=self.done.copy()
        aphys=self.action_physical(z);self.prev[~self.done]=z[~self.done]
        for _ in range(self.c.substeps):
            active=~self.done
            if not active.any():break
            j=np.minimum(self.g,4);aphys=self.action_physical(z);target=self.gates[j,:3].copy()
            target[:,:,1:]+=aphys[:,:,1:]
            vr=np.empty_like(self.v);vr[:,:,0]=aphys[:,:,0]
            vr[:,:,1]=np.clip(self.c.lateral_gain*(target[:,:,1]-self.p[:,:,1]),-self.c.lateral_speed_max,self.c.lateral_speed_max)
            vr[:,:,2]=np.clip(self.c.lateral_gain*(target[:,:,2]-self.p[:,:,2]),-self.c.vertical_speed_max,self.c.vertical_speed_max)
            acc=(vr-self.v)/self.c.velocity_tau
            an=np.linalg.norm(acc,axis=2)
            acc*=np.minimum(1.,self.c.accel_max/np.maximum(an,1e-12))[:,:,None]
            dt=self.c.dt;dp=dt*self.v;pn=self.p+dp;vn=self.v+dt*acc
            # Gate plane event within a microstep.
            gx=self.gates[j,0]
            cross=(self.p[:,:,0]<gx)&(pn[:,:,0]>=gx)
            f=np.where(cross,(gx-self.p[:,:,0])/np.maximum(dp[:,:,0],1e-12),np.inf)
            fsafe=np.where(cross,f,0.)
            gp=self.p+fsafe[:,:,None]*dp
            good=cross&(np.abs(gp[:,:,1]-self.gates[j,1])<=self.gates[j,3]/2-self.c.gate_margin+1e-12)&(np.abs(gp[:,:,2]-self.gates[j,2])<=self.gates[j,4]/2-self.c.gate_margin+1e-12)
            bad=np.where(cross&~good,f,np.inf)
            # Arena exit times, using the SAME interpolated interval.
            lo=np.array([-4.,-5.,.5]);hi=np.array([52.,5.,5.])
            for d in range(3):
                fl=np.where((pn[:,:,d]<lo[d])&(dp[:,:,d]<0),(lo[d]-self.p[:,:,d])/np.where(dp[:,:,d]!=0,dp[:,:,d],1.),np.inf)
                fh=np.where((pn[:,:,d]>hi[d])&(dp[:,:,d]>0),(hi[d]-self.p[:,:,d])/np.where(dp[:,:,d]!=0,dp[:,:,d],1.),np.inf)
                bad=np.minimum(bad,np.minimum(fl,fh))
            finish=np.where(good&(j==4),f,np.inf)
            # First contact time of two linearly interpolated center trajectories.
            r=self.p[:,0]-self.p[:,1];dr=dp[:,0]-dp[:,1]
            aa=np.sum(dr*dr,axis=1);bb=2*np.sum(r*dr,axis=1);cc=np.sum(r*r,axis=1)-self.c.separation**2
            disc=bb*bb-4*aa*cc;root=(-bb-np.sqrt(np.maximum(disc,0)))/(2*np.maximum(aa,1e-24))
            col=np.where((aa>1e-20)&(disc>=0)&(root>=0)&(root<=1),root,np.inf)
            col=np.where(cc<=0,0.,col)
            first=np.minimum.reduce((col,bad[:,0],bad[:,1],finish[:,0],finish[:,1]))
            terminal=active&(first<=1)
            frac=np.where(terminal,first,1.);frac=np.where(active,frac,0.)
            # Minimum separation only until the actual stopping event.
            closest=np.clip(-np.sum(r*dr,axis=1)/np.maximum(aa,1e-24),0,frac)
            ds=np.linalg.norm(r+closest[:,None]*dr,axis=1)
            self.min_sep=np.where(active,np.minimum(self.min_sep,ds),self.min_sep)
            self.accel_peak=np.where(active,np.maximum(self.accel_peak,np.max(np.linalg.norm(acc,axis=2),axis=1)),self.accel_peak)
            self.p+=frac[:,None,None]*dp;self.v+=frac[:,None,None]*dt*acc
            self.t+=frac*dt
            passed=good&(f<=frac[:,None]+1e-10)&active[:,None]
            self.g+=passed.astype(int)
            collision=terminal&(col<=first+1e-10)
            ba=terminal&(bad[:,0]<=first+1e-10)&~collision
            bc=terminal&(bad[:,1]<=first+1e-10)&~collision
            fa=terminal&(finish[:,0]<=first+1e-10)&~collision&~ba&~bc
            fb=terminal&(finish[:,1]<=first+1e-10)&~collision&~ba&~bc
            self.reason[collision]=4;self.score[collision]=-1
            self.reason[ba&~bc]=5;self.score[ba&~bc,0]=-1
            self.reason[bc&~ba]=6;self.score[bc&~ba,1]=-1
            self.reason[ba&bc]=7;self.score[ba&bc]=-1
            self.reason[fa&~fb]=1;self.score[fa&~fb,0]=1
            self.reason[fb&~fa]=2;self.score[fb&~fa,1]=1
            self.reason[fa&fb]=3;self.score[fa&fb]=.5
            self.done|=terminal
            timeout=(~self.done)&(self.t>=self.c.time_limit-1e-10)
            self.reason[timeout]=8;self.done|=timeout
        reward=self.c.beta*(self.potential()-phi_old)
        newly=self.done&~was_done;reward[newly]+=self.score[newly]
        reward[was_done]=0.;self.reward_sum+=reward
        return reward,self.done.copy()


def rule_actions(env,kind=0,who=1):
    """Rules use current measured geometry, never the learner's future action.
    0 center cruise, 1 reactive yielding, 2 reactive passing,
    3 fast center (held-out), 4 alternating gate line (held-out).
    """
    n=env.n;z=np.zeros((n,3));other=1-who
    d=env.p[:,other]-env.p[:,who]
    ahead=(d[:,0]>0)&(d[:,0]<3.0)&(np.linalg.norm(d[:,1:],axis=1)<1.0)
    sign=np.where(env.p[:,who,1]>=env.p[:,other,1],1.,-1.)
    if kind==0:
        speed=np.full(n,4.6);z[:,1]=-.20
    elif kind==1:
        speed=np.where(ahead,3.1,4.4);z[:,1]=.25*sign
    elif kind==2:
        speed=np.where(ahead,4.0,5.1);z[:,1]=.65*sign
        # Yield at the narrow gate if behind in a close encounter.
        near=(env.g[:,who]==2)&(30-env.p[:,who,0]<5)&ahead
        speed[near]=2.8
    elif kind==3:
        speed=np.full(n,5.6);z[:,1]=.15
    elif kind==4:
        speed=np.full(n,5.1);z[:,1]=.65*np.sin(.8*env.t+.7*env.g[:,who])
        z[:,2]=.2*np.cos(.5*env.t)
    elif kind==5:
        speed=np.full(n,6.5);z[:,1]=0.0
    else:
        raise ValueError('Unknown rule opponent')
    z[:,0]=(speed-env.c.speed_mid)/env.c.speed_scale
    z=np.clip(z,-.98,.98)
    if kind==5:z[:,0]=1.0  # deterministic baseline may attain the closed speed bound
    return z


def opponent_actions(env,ids,pool,rng):
    acts=np.zeros((env.n,3));obs=env.obs(1)
    for ident in np.unique(ids):
        ix=np.where(ids==ident)[0]
        if ident>=0:
            acts[ix]=rule_actions(env,int(ident),1)[ix]
        else:
            acts[ix]=policy(pool[-int(ident)-1],obs[ix],rng)[0]
    return acts


def evaluate(actor,cfg,seed,n=160,kinds=(0,1,2,3,4),deterministic=False,mirror=False,trace=False,rule=None,blind=False):
    rng=PortableRNG(seed);env=RaceBatch(cfg,n,rng,mirror)
    ids=np.array(kinds,dtype=int)[(np.arange(n)//2)%len(kinds)]
    logs=[]
    while not env.done.all():
        o=env.obs(0)
        if blind:o[:,9:15]=0 # deployment ablation; explicitly labelled as such
        if rule is not None:za=rule_actions(env,rule,0)
        else:za=policy(actor,o,rng,deterministic)[0]
        zb=opponent_actions(env,ids,[],rng)
        if trace:
            logs.append(np.column_stack((np.arange(n),env.t,env.p.reshape(n,6),env.v.reshape(n,6),env.g,za,zb,env.done.astype(int))))
        env.step(np.stack((za,zb),axis=1))
    if trace:logs.append(np.column_stack((np.arange(n),env.t,env.p.reshape(n,6),env.v.reshape(n,6),env.g,za,zb,env.done.astype(int))))
    wins=(env.reason==1);ties=env.reason==3;failed=np.isin(env.reason,[4,5,7]);valid=np.isin(env.reason,[1,3])
    audit=np.max(np.abs(env.reward_sum-env.score+cfg.beta*env.phi0))
    row=dict(win=float(np.mean(wins)),tie=float(np.mean(ties)),violation=float(np.mean(failed)),separation_violation=float(np.mean(env.reason==4)),
             score=float(np.mean(env.score[:,0])),valid_finish=float(np.mean(valid)),timeout=float(np.mean(env.reason==8)),
             finish_time=float(np.mean(env.t[valid])) if valid.any() else None,
             progress=float(np.mean(np.minimum(env.g[:,0],5)/5)),min_separation=float(env.min_sep.min()),
             potential_audit=float(audit),n=n)
    details=np.column_stack((np.arange(n),ids,env.reason,env.score,env.t,env.g,env.min_sep,env.accel_peak,env.reward_sum,env.phi0))
    return row,details,logs


def collect(actor,critic,cfg,rng,mode,pool):
    env=RaceBatch(cfg,cfg.batch_episodes,rng)
    if mode=='fixed':ids=np.zeros(env.n,dtype=int)
    else:
        q=rng.uniform((env.n,));ids=np.where(q<.25,0,2)
        if pool:
            choose=q>=.5
            q2=rng.uniform((env.n,));ids[choose]=-1-np.minimum((q2[choose]*len(pool)).astype(int),len(pool)-1)
    obs=[];raw=[];lp=[];rewards=[];alive=[];vold=[]
    while not env.done.all():
        o=env.obs(0);za,b,lpa=policy(actor,o,rng);zb=opponent_actions(env,ids,pool,rng)
        alive.append(~env.done.copy());obs.append(o);raw.append(b);lp.append(lpa)
        vold.append(net_forward(critic,o)[0][:,0])
        reward,_=env.step(np.stack((za,zb),axis=1));rewards.append(reward[:,0])
    R=np.asarray(rewards);mask=np.asarray(alive);G=np.zeros_like(R);future=np.zeros(env.n)
    for t in range(len(R)-1,-1,-1):
        future=R[t]+cfg.gamma*future;G[t]=future
    x=np.asarray(obs)[mask];b=np.asarray(raw)[mask];oldlp=np.asarray(lp)[mask]
    target=G[mask];oldv=np.asarray(vold)[mask]
    adv=target-oldv;adv=(adv-adv.mean())/(adv.std()+1e-8)
    audit=float(np.max(np.abs(env.reward_sum-env.score+cfg.beta*env.phi0)))
    stats=dict(train_score=float(env.score[:,0].mean()),train_win=float(np.mean(env.reason==1)),
               train_violation=float(np.mean(np.isin(env.reason,[4,5,7]))),samples=len(x),audit=audit)
    return x,b,oldlp,target,adv,stats


def train(cfg,seed,mode,outdir=None,verbose=True):
    import time
    rng=PortableRNG(seed);actor=actor_init(rng,cfg);critic=net_init(rng,OBS_DIM,cfg.hidden,1,.05)
    initial=clone(actor);ao=Adam(actor);co=Adam(critic);pool=[];records=[];start=time.perf_counter();nsteps=0
    for it in range(1,cfg.iterations+1):
        x,b,ol,target,adv,stats=collect(actor,critic,cfg,rng,mode,pool)
        nsteps+=len(x);stop=False;aloss=vloss=kl=cf=0.
        for ep in range(cfg.epochs):
            order=rng.permutation(len(x))
            for first in range(0,len(x),cfg.minibatch):
                ix=order[first:first+cfg.minibatch]
                aloss,ag,kl,cf=actor_loss_grad(actor,x[ix],b[ix],ol[ix],adv[ix],cfg.ppo_clip)
                if kl>cfg.max_kl:stop=True;break
                ao.step(actor,ag,cfg.actor_lr,cfg.grad_clip)
                actor['logstd']=np.clip(actor['logstd'],np.log(cfg.std_min),np.log(cfg.std_max))
                val,h=net_forward(critic,x[ix]);err=val[:,0]-target[ix]
                vloss=float(np.mean(err*err)/2)
                cg=net_backward(critic,x[ix],h,err[:,None]/len(ix))
                co.step(critic,cg,cfg.critic_lr,cfg.grad_clip)
            if stop:break
        # Independent validation conditions, never the final test seeds.
        val_score=val_vio=val_win=np.nan
        if it%cfg.eval_every==0 or it==1:
            vr,_,_=evaluate(actor,cfg,600000+seed,40,kinds=(0,2),deterministic=False)
            val_score=vr['score'];val_vio=vr['violation'];val_win=vr['win']
        if mode=='league' and it%cfg.snapshot_every==0:
            if not np.isfinite(val_vio):
                vr,_,_=evaluate(actor,cfg,600000+seed,40,kinds=(0,2));val_vio=vr['violation']
            # Gate based only on held-out validation, not final test performance.
            if val_vio<=.30:
                pool.append(clone(actor));pool=pool[-cfg.pool_capacity:]
        row=dict(iteration=it,steps=nsteps,**stats,actor_loss=aloss,critic_loss=vloss,kl=kl,clip_fraction=cf,
                 validation_score=val_score,validation_win=val_win,validation_violation=val_vio,pool_size=len(pool),seconds=time.perf_counter()-start)
        records.append(row)
        if verbose and (it==1 or it%10==0):
            print(f'{mode} seed={seed} iter={it:3d} steps={nsteps} trainJ={stats["train_score"]:+.3f} valJ={val_score:+.3f} pool={len(pool)}',flush=True)
    return actor,initial,critic,pool,records


def save_net(net,path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w',encoding='utf-8') as f:json.dump({k:v.tolist() for k,v in net.items()},f,indent=2)


def load_net(path):
    with open(path,encoding='utf-8') as f:data=json.load(f)
    return {k:np.array(v,dtype=float) for k,v in data.items()}
