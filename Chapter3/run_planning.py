"""Explicit-Euler full-space OCP. No RK method or flight-hardware interface."""
import os
for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ.setdefault(key,'1')
from pathlib import Path
import argparse,json,time,sys
import numpy as np
import casadi as ca
from model import PAR,aero,trim,motion,symbolic_motion,forward_euler
from geometry import astar_3d,spline_seed,build_corridors,box_clearance
ROOT=Path(__file__).resolve().parent
CFG=dict(intervals=200,euler_substeps=8,fragment_steps=10,duration_s=36.,safety_margin_m=8.,astar_extra_clearance_m=30.,
 grid_step_m=[20,20,10],search_lower_m=[0,-220,80],search_upper_m=[600,220,180],
 state_lower=[-30,-220,75,15,-.3,-.9,-.6],state_upper=[650,220,180,25,.3,.9,.6],
 input_lower=[0,-.03,-.4],input_upper=[40,.18,.4],start_state=[0,0,100,20,0,0,0],
 max_reconstruction_error_m=3.,corridor_node_buffer_m=3.)
SCENES={
 'two':dict(columns=[[250,0,55],[430,-10,45]],goal=[600,0,130,20,0,0,0]),
 'four':dict(columns=[[180,-30,32],[270,15,35],[360,-35,32],[450,20,30]],goal=[600,0,150,20,0,0,0]),
 'five':dict(columns=[[150,65,28],[225,-65,28],[300,70,30],[375,-65,28],[450,65,28]],goal=[600,0,160,20,0,0,0])}

def inverse_seed(p,dt):
    v=np.gradient(p,dt,axis=0,edge_order=2);V=np.linalg.norm(v,axis=1)
    ga=np.arctan2(v[:,2],np.linalg.norm(v[:,:2],axis=1));ch=np.unwrap(np.arctan2(v[:,1],v[:,0]))
    gd=np.gradient(ga,dt,edge_order=2);cd=np.gradient(ch,dt,edge_order=2)
    A=PAR['m']*(V*gd+PAR['g']*np.cos(ga));B=PAR['m']*V*np.cos(ga)*cd
    mu=np.unwrap(np.arctan2(B,A));L=np.hypot(A,B)
    CL=L/(.5*PAR['rho']*V**2*PAR['S']);alpha=(CL-PAR['CL0'])/PAR['CLalpha']
    _,D=aero(V,alpha);T=PAR['m']*(np.gradient(V,dt,edge_order=2)+PAR['g']*np.sin(ga))+D
    om=np.gradient(mu,dt,edge_order=2)
    return np.column_stack((p,V,ga,ch,mu)),np.column_stack((T,alpha,om))[:-1]

class Problem:
    def __init__(self,scene='two',seed_kind='astar',corridor=False,intervals=200):
        self.scene,self.seed_kind,self.corridor=scene,seed_kind,corridor
        self.cfg=dict(CFG,intervals=intervals,fragment_steps=intervals//20)
        self.N=intervals;self.M=intervals+1;self.dt=CFG['duration_s']/intervals
        self.obs=np.array(SCENES[scene]['columns'],float)
        start=np.array(CFG['start_state'],float);goal=np.array(SCENES[scene]['goal'],float)
        self.sx=np.array([600,150,150,20,.3,.6,.6]);self.su=np.array([20,.1,.4])
        self.scale=np.r_[np.tile(self.sx,self.M),np.tile(self.su,self.N)]
        self.raw,self.expanded=astar_3d(start[:3],goal[:3],self.obs,self.cfg)
        if seed_kind in ('north','south'):
            point=np.array([300,160 if seed_kind=='north' else -160,120.])
            a,ea=astar_3d(start[:3],point,self.obs,self.cfg);b,eb=astar_3d(point,goal[:3],self.obs,self.cfg)
            self.raw=np.vstack((a,b[1:]));self.expanded=ea+eb
        p,self.spline,self.knots,self.spline_clearance=spline_seed(self.raw,self.obs,self.cfg)
        if seed_kind=='straight':p=np.linspace(start[:3],goal[:3],self.M);self.spline=p.copy()
        X,U=inverse_seed(p,self.dt);X[0],X[-1]=start,goal
        lx=np.tile(CFG['state_lower'],(self.M,1)).astype(float);hx=np.tile(CFG['state_upper'],(self.M,1)).astype(float)
        lx[:,3:]+=[.15,.02,.02,.02];hx[:,3:]-=[.15,.02,.02,.02]
        self.boxes=np.empty((0,6));self.owner=np.empty(0,int)
        if corridor:self.boxes,self.owner,lx[:,:3],hx[:,:3]=build_corridors(p,self.obs,self.cfg)
        assert np.all(start>=lx[0]) and np.all(start<=hx[0]);assert np.all(goal>=lx[-1]) and np.all(goal<=hx[-1])
        lx[0]=hx[0]=start;lx[-1]=hx[-1]=goal
        self.lb=np.r_[lx.ravel(),np.tile(CFG['input_lower'],self.N)]/self.scale
        self.ub=np.r_[hx.ravel(),np.tile(CFG['input_upper'],self.N)]/self.scale
        self.z0=np.clip(np.r_[X.ravel(),U.ravel()]/self.scale,self.lb,self.ub)

    def unpack(self,z):
        q=np.asarray(z).reshape(-1)*self.scale
        return q[:7*self.M].reshape(-1,7),q[7*self.M:].reshape(-1,3)

    def solve(self):
        z=ca.MX.sym('z',len(self.scale));q=z*ca.DM(self.scale)
        X=ca.reshape(q[:7*self.M],7,self.M);U=ca.reshape(q[7*self.M:],3,self.N)
        # Apply the same first-order explicit Euler formula on eight small steps.
        # These internal states are expressions, not additional decision variables.
        prediction=X[:,:-1]
        for _ in range(CFG['euler_substeps']):
            prediction=prediction+self.dt/CFG['euler_substeps']*symbolic_motion(prediction,U,ca)
        eq=ca.vec((X[:,1:]-prediction)/ca.repmat(ca.DM(self.sx),1,self.N))
        T0,a0=trim();J=self.dt*(.15*ca.sumsqr((U[0,:]-T0)/20)+2*ca.sumsqr((U[1,:]-a0)/.1)
            +.8*ca.sumsqr(U[2,:]/.4)+.02*ca.sumsqr(X[1,:-1]/100))
        gs=[eq];lbg=[np.zeros(7*self.N)];ubg=[np.zeros(7*self.N)]
        if not self.corridor:
            for cx,cy,r in self.obs:
                dist=((X[0,:]-cx)**2+(X[1,:]-cy)**2)/(r+11)**2-1
                gs.append(ca.vec(dist));lbg.append(np.zeros(self.M));ubg.append(np.full(self.M,np.inf))
        g=ca.vertcat(*gs);gf=ca.Function('g',[z],[g]);of=ca.Function('J',[z],[J])
        jf=ca.Function('derivatives',[z],[ca.jacobian(g,z)]);grad=ca.Function('grad',[z],[ca.gradient(J,z)])
        jac=np.asarray(jf(self.z0));og=np.array(grad(self.z0)).ravel();err=0.
        for j in np.unique(np.linspace(7,len(self.scale)-4,18).astype(int)):
            d=np.zeros(len(self.z0));d[j]=1e-6
            err=max(err,float(np.max(np.abs((np.array(gf(self.z0+d)).ravel()-np.array(gf(self.z0-d)).ravel())/2e-6-jac[:,j]))),
                    abs((float(of(self.z0+d))-float(of(self.z0-d)))/2e-6-og[j]))
        assert err<3e-5,err
        solver=ca.nlpsol('plan','ipopt',dict(x=z,f=J,g=g),{'print_time':False,'ipopt.print_level':0,
            'ipopt.sb':'yes','ipopt.tol':1e-8,'ipopt.constr_viol_tol':1e-8,'ipopt.max_iter':700,
            'ipopt.bound_relax_factor':0.,'ipopt.fixed_variable_treatment':'make_parameter'})
        begin=time.perf_counter();res=solver(x0=self.z0,lbx=self.lb,ubx=self.ub,lbg=np.concatenate(lbg),ubg=np.concatenate(ubg));seconds=time.perf_counter()-begin
        zz=np.array(res['x']).ravel();XX,UU=self.unpack(zz);stats=solver.stats()
        gv=np.array(gf(zz)).ravel();residual=max(np.max(np.abs(gv[:7*self.N])),max(-gv[7*self.N:],default=0),np.max(self.lb-zz),np.max(zz-self.ub),0)
        passed,checks,dense=self.validate(XX,UU,residual)
        it=stats.get('iterations',{});history=np.c_[it.get('obj',[]),it.get('inf_pr',[])]
        X0,U0=self.unpack(self.z0)
        return dict(scene=self.scene,seed_kind=self.seed_kind,corridor=self.corridor,intervals=self.N,
          solver_success=bool(stats['success']),accepted=bool(stats['success'] and passed),message=stats['return_status'],
          objective=float(res['f']),iterations=int(stats['iter_count']),seconds=seconds,checks=checks,
          derivative_check_max_error=err,initial_max_scaled_defect=float(np.max(np.abs(np.array(gf(self.z0)).ravel()[:7*self.N]))),
          nonlinear_obstacle_constraints=0 if self.corridor else len(self.obs)*self.M,
          position_box_bounds=6*self.M if self.corridor else 0,X=XX,U=UU,initial_X=X0,initial_U=U0,
          time=np.arange(self.M)*self.dt,history=history,dense=dense,raw=self.raw,spline=self.spline,
          knots=self.knots,boxes=self.boxes,owner=self.owner,columns=self.obs,astar_expanded=self.expanded)

    def validate(self,X,U,residual):
        validation_steps=160
        dense=forward_euler(X[0],U,self.dt,validation_steps);fine=forward_euler(X[0],U,self.dt,2*validation_steps)
        clear=min(np.min(np.linalg.norm(dense[:,:2]-o[:2],axis=1)-o[2]) for o in self.obs)
        sampled_bound=float(clear-26*self.dt/validation_steps/2)
        violation=max(np.max(np.array(CFG['state_lower'])-dense),np.max(dense-np.array(CFG['state_upper'])),0.)
        enderr=float(np.linalg.norm(dense[-1,:3]-X[-1,:3]))
        nodeerr=float(np.max(np.linalg.norm(dense[::validation_steps,:3]-X[:,:3],axis=1)))
        refinement=float(np.max(np.linalg.norm(dense[:,:3]-fine[::2,:3],axis=1)))
        bv=0.
        if self.corridor:
            for k in range(self.N):
                b=self.boxes[self.owner[k]];d=dense[k*validation_steps:(k+1)*validation_steps+1,:3]
                bv=max(bv,float(np.max(b[:3]-d)),float(np.max(d-b[3:])))
        checks=dict(max_scaled_constraint_violation=float(residual),min_rollout_clearance_m=float(clear),
          sampled_clearance_lower_bound_m=sampled_bound,terminal_position_error_m=enderr,
          max_node_reconstruction_error_m=nodeerr,refined_rollout_difference_m=refinement,
          max_rollout_corridor_violation_m=max(0,bv),dense_state_bound_violation=float(violation))
        if self.corridor:checks['whole_box_clearance_m']=float(min(box_clearance(b[:3],b[3:],self.obs) for b in self.boxes))
        passed=residual<1e-6 and sampled_bound>=8 and nodeerr<CFG['max_reconstruction_error_m'] and refinement<.05 and bv<1e-5 and violation<1e-5
        return bool(passed),checks,np.c_[np.linspace(0,CFG['duration_s'],len(dense)),dense]

def save(r,folder):
    folder.mkdir(parents=True,exist_ok=True);meta={k:v for k,v in r.items() if not isinstance(v,np.ndarray)}
    (folder/'result.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    np.savez_compressed(folder/'data.npz',**{k:v for k,v in r.items() if isinstance(v,np.ndarray)})
    np.savetxt(folder/'state.csv',np.c_[r['time'],r['X']],delimiter=',',header='t,x,y,h,V,gamma,chi,mu',comments='')
    np.savetxt(folder/'control.csv',np.c_[r['time'][:-1],r['U']],delimiter=',',header='t,T,alpha,omega_mu',comments='')

def main():
    ap=argparse.ArgumentParser(description='Fixed-wing trajectory planning experiments')
    ap.add_argument('--case',default='all',choices=['all','two_straight','two_north','two_south',
        'two_corridor','four_direct','four_corridor','five_corridor','four_grid100'])
    ap.add_argument('--plots-only',action='store_true')
    ap.add_argument('--no-plots',action='store_true')
    args=ap.parse_args()
    out=ROOT/'results_euler';out.mkdir(exist_ok=True)
    jobs=[('two_straight','two','straight',False,200),('two_north','two','north',False,200),
      ('two_south','two','south',False,200),('two_corridor','two','astar',True,200),
      ('four_direct','four','astar',False,200),('four_corridor','four','astar',True,200),
      ('five_corridor','five','astar',True,200),('four_grid100','four','astar',True,100)]
    results={}
    for name,scene,seed,cor,N in jobs:
        if args.case!='all' and args.case!=name:continue
        if args.plots_only:
            r=json.loads((out/name/'result.json').read_text(encoding='utf-8'));r.update(dict(np.load(out/name/'data.npz')))
        else:
            print(name+': constructing and solving',flush=True);r=Problem(scene,seed,cor,N).solve();save(r,out/name)
            print(json.dumps({k:r[k] for k in ('accepted','iterations','seconds','objective','checks')},indent=2),flush=True)
        results[name]=r
    report=[{k:v for k,v in r.items() if not isinstance(v,np.ndarray)} for r in results.values()]
    (out/'summary.json').write_text(json.dumps(dict(config=CFG,aircraft=PAR,scenes=SCENES,python=sys.version,
        casadi=ca.__version__,results=report),ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.no_plots:
        from examples import make_examples
        make_examples(out)
        from figures import plot_all
        plot_all(results,out)
        from tables import make_tables
        make_tables(results)
    assert all(r['accepted'] for r in results.values()),'Inspect result.json: failed independent checks.'
    print(f'Finished: {out}',flush=True)

if __name__=='__main__':main()
