"""Explicit-Euler full-space OCP. No RK method or flight-hardware interface."""
import os
for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ.setdefault(key,'1')
from pathlib import Path
import argparse,json,time,sys,platform
import numpy as np
import casadi as ca
from model import PAR,motion,symbolic_motion,forward_euler
from geometry import astar_3d,spline_seed,build_corridors,box_clearance,segment_clearance
ROOT=Path(__file__).resolve().parent
SETTINGS=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
CFG,SCENES=SETTINGS['config'],SETTINGS['scenes']

def inverse_seed(p,dt):
    v=np.gradient(p,dt,axis=0,edge_order=2);V=np.linalg.norm(v,axis=1)
    ga=np.arctan2(v[:,2],np.linalg.norm(v[:,:2],axis=1));ch=np.unwrap(np.arctan2(v[:,1],v[:,0]))
    cd=np.gradient(ch,dt,edge_order=2)
    phi=np.arctan(V*cd/PAR['g'])
    a=np.gradient(V,dt,edge_order=2)
    omega_gamma=np.gradient(ga,dt,edge_order=2)
    omega_phi=np.gradient(phi,dt,edge_order=2)
    return np.column_stack((p,V,ga,ch,phi)),np.column_stack((a,omega_gamma,omega_phi))[:-1]

class Problem:
    def __init__(self,scene='two',seed_kind='astar',corridor=False,intervals=200):
        self.scene,self.seed_kind,self.corridor=scene,seed_kind,corridor
        self.cfg=dict(CFG,intervals=intervals,fragment_steps=intervals//20)
        self.N=intervals;self.M=intervals+1;self.dt=CFG['duration_s']/intervals
        self.obs=np.array(SCENES[scene]['columns'],float)
        start=np.array(CFG['start_state'],float);goal=np.array(SCENES[scene]['goal'],float)
        self.sx=np.array([600,150,150,20,.3,.6,.6]);self.su=np.array([2,.08,.4])
        self.scale=np.r_[np.tile(self.sx,self.M),np.tile(self.su,self.N)]
        self.raw,self.expanded=astar_3d(start[:3],goal[:3],self.obs,self.cfg)
        if seed_kind in ('north','south'):
            point=np.array([300,160 if seed_kind=='north' else -160,120.])
            a,ea=astar_3d(start[:3],point,self.obs,self.cfg);b,eb=astar_3d(point,goal[:3],self.obs,self.cfg)
            self.raw=np.vstack((a,b[1:]));self.expanded=ea+eb
        p,self.spline,self.knots,self.spline_clearance=spline_seed(self.raw,self.obs,self.cfg)
        self.seed_average_speed=float(np.sum(np.linalg.norm(np.diff(self.spline,axis=0),axis=1))/CFG['duration_s'])
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
        # Identical single-step Euler connection in the book and solver.
        prediction=X[:,:-1]+self.dt*symbolic_motion(X[:,:-1],U,ca)
        eq=ca.vec((X[:,1:]-prediction)/ca.repmat(ca.DM(self.sx),1,self.N))
        J=self.dt*(.3*ca.sumsqr(U[0,:]/2)+ca.sumsqr(U[1,:]/.08)+ca.sumsqr(U[2,:]/.4))
        gs=[eq];lbg=[np.zeros(7*self.N)];ubg=[np.zeros(7*self.N)]
        if not self.corridor:
            for cx,cy,r in self.obs:
                dist=((X[0,:]-cx)**2+(X[1,:]-cy)**2)/(r+CFG['safety_margin_m']+CFG['corridor_node_buffer_m'])**2-1
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
          seed_average_speed_m_s=self.seed_average_speed,knots=self.knots,boxes=self.boxes,owner=self.owner,columns=self.obs,astar_expanded=self.expanded)

    def validate(self,X,U,residual):
        # DISCRETE model consistency only, not full-aircraft/continuous validation.
        rollout=forward_euler(X[0],U,self.dt)
        clear=min(segment_clearance(a,b,self.obs) for a,b in zip(rollout[:-1,:3],rollout[1:,:3]))
        violation=max(np.max(np.array(CFG['state_lower'])-rollout),np.max(rollout-np.array(CFG['state_upper'])),0.)
        terminal=rollout[-1]-np.asarray(SCENES[self.scene]['goal'])
        nodeerr=float(np.max(np.linalg.norm(rollout[:,:3]-X[:,:3],axis=1)))
        bv=0.
        if self.corridor:
            for k in range(self.N):
                box=self.boxes[self.owner[k]];d=rollout[k:k+2,:3]
                bv=max(bv,float(np.max(box[:3]-d)),float(np.max(d-box[3:])))
        checks=dict(max_scaled_constraint_violation=float(residual),
          min_discrete_segment_clearance_m=float(clear),
          remaining_geometric_margin_m=float(clear-CFG['safety_margin_m']),
          terminal_position_error_m=float(np.linalg.norm(terminal[:3])),
          terminal_speed_error_m_s=float(abs(terminal[3])),
          terminal_direction_error_deg=float(np.max(np.abs(np.rad2deg(terminal[4:6])))),
          terminal_bank_error_deg=float(abs(np.rad2deg(terminal[6]))),
          max_node_reconstruction_error_m=nodeerr,
          max_discrete_corridor_violation_m=max(0.,bv),discrete_state_bound_violation=float(violation))
        if self.corridor:checks['whole_box_clearance_m']=float(min(box_clearance(b[:3],b[3:],self.obs) for b in self.boxes))
        passed=(residual<1e-6 and clear>=CFG['safety_margin_m'] and nodeerr<1e-3
                and np.linalg.norm(terminal[:3])<1e-3 and np.max(np.abs(terminal[3:]))<1e-5
                and bv<1e-4 and violation<1e-4)
        return bool(passed),checks,np.c_[np.arange(self.M)*self.dt,rollout]


def save(r,folder):
    folder.mkdir(parents=True,exist_ok=True);meta={k:v for k,v in r.items() if not isinstance(v,np.ndarray)}
    (folder/'result.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    np.savez_compressed(folder/'data.npz',**{k:v for k,v in r.items() if isinstance(v,np.ndarray)})
    np.savetxt(folder/'state.csv',np.c_[r['time'],r['X']],delimiter=',',header='t,x,y,z,V,gamma,chi,phi',comments='')
    np.savetxt(folder/'control.csv',np.c_[r['time'][:-1],r['U']],delimiter=',',header='t,a,omega_gamma,omega_phi',comments='')
    np.savetxt(folder/'initial_state.csv',np.c_[r['time'],r['initial_X']],delimiter=',',header='t,x,y,z,V,gamma,chi,phi',comments='')
    np.savetxt(folder/'initial_control.csv',np.c_[r['time'][:-1],r['initial_U']],delimiter=',',header='t,a,omega_gamma,omega_phi',comments='')
    np.savetxt(folder/'raw_path.csv',r['raw'],delimiter=',',header='x,y,z',comments='')
    np.savetxt(folder/'boxes.csv',r['boxes'],delimiter=',',header='xmin,ymin,zmin,xmax,ymax,zmax',comments='')

def environment():
    # IPOPT version is emitted by the solver banner; keep package provenance too.
    info=dict(os=platform.platform(),machine=platform.machine(),processor=platform.processor(),
              python=platform.python_version(),casadi=ca.__version__,
              numpy=np.__version__,deterministic=True,random_initialization=False,
              threads={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS')},
              solver='IPOPT bundled with CasADi '+ca.__version__)
    if os.name=='nt':
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as k:
            info['cpu']=winreg.QueryValueEx(k,'ProcessorNameString')[0].strip()
    return info


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',default='all',choices=['all','two_straight','two_north','two_south','two_corridor','four_direct','four_corridor','five_corridor','four_grid100']);ap.add_argument('--plots-only',action='store_true');ap.add_argument('--no-plots',action='store_true');args=ap.parse_args()
    out=ROOT/'results_kinematic';out.mkdir(exist_ok=True)
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
        casadi=ca.__version__,environment=environment(),results=report),ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.no_plots:
        from examples import make_examples
        make_examples(out)
        from figures import plot_all
        plot_all(results,out)
        from tables import make_tables
        make_tables(results)
    assert all(r['accepted'] for r in results.values()),'Inspect result.json: failed discrete-model checks.'
    print(f'Finished: {out}',flush=True)

if __name__=='__main__':main()
