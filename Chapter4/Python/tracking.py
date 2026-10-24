"""Linear time-varying MPC tracking a saved Chapter 3 fixed-wing trajectory.

Error convention: e = reference - predicted/estimated state.
Each prediction interval and plant update uses ONE explicit Euler step.
The measured plant is nonlinear; no flight hardware interface is provided.
"""
from pathlib import Path
from time import perf_counter
import argparse
import json
import sys
import numpy as np
import scipy
from scipy import sparse
import osqp
from model import motion

ROOT = Path(__file__).resolve().parent
DT = .18
U_MAX = np.array([2., .08, .4])
X_MIN = np.array([-np.inf, -np.inf, -np.inf, 15., -.2, -.9, -.6])
X_MAX = np.array([np.inf, np.inf, np.inf, 25., .2, .9, .6])
POS_SCALE, VEL_SCALE = 5., 2.
INPUT_WEIGHT = .05
INITIAL_OFFSET = np.array([0., 5., 3., 0., 0., np.deg2rad(3), 0.])
COLUMNS = np.array([[200., -140., 155.], [400., 140., 155.]])


def derivatives(x):
    """Analytic continuous-time Jx, Ju; Jx[:3] is the velocity Jacobian."""
    V, ga, chi, phi = x[3:]
    cg, sg, cc, sc = np.cos(ga), np.sin(ga), np.cos(chi), np.sin(chi)
    J = np.zeros((7, 7))
    J[0, 3:6] = [cg*cc, -V*sg*cc, -V*cg*sc]
    J[1, 3:6] = [cg*sc, -V*sg*sc, V*cg*cc]
    J[2, 3:5] = [sg, V*cg]
    J[5, 3] = -9.81*np.tan(phi)/V**2
    J[5, 6] = 9.81/(V*np.cos(phi)**2)
    B = np.zeros((7, 3))
    B[[3, 4, 6], [0, 1, 2]] = 1.
    return J, B


def reference(extra=50):
    states = np.loadtxt(ROOT.parent/'reference/state.csv', delimiter=',', skiprows=1)
    controls = np.loadtxt(ROOT.parent/'reference/control.csv', delimiter=',', skiprows=1)
    assert np.max(np.abs(np.diff(states[:, 0])-DT)) < 1e-12
    X, U = states[:, 1:].copy(), controls[:, 1:].copy()
    # End state is continuing level, straight flight; do not freeze its position.
    for _ in range(extra):
        U = np.vstack([U, np.zeros(3)])
        X = np.vstack([X, X[-1]+DT*motion(X[-1], U[-1])])
    return X, U, len(states)-1


def state_cost(x):
    C = np.vstack([np.eye(7)[:3]/POS_SCALE, derivatives(x)[0][:3]/VEL_SCALE])
    return C.T@C


def solve_mpc(xhat, xr, ur, previous=None):
    """One fixed-linearization QP; no nonlinear optimizer or inner SQP loop."""
    started = perf_counter()
    H = len(ur); nx = 7*(H+1); nv = nx+3*H
    # Shift the previous correction, append zero at the new tail, and rebuild
    # every expansion state from the new measured initial state.
    dU_seed = np.zeros_like(ur) if previous is None else np.vstack([previous[1:], np.zeros(3)])
    barU = np.clip(ur+dU_seed, -U_MAX, U_MAX)
    dU_seed = barU-ur
    barX = xr.copy()
    if previous is not None:
        barX[0] = xhat
        for i in range(H):
            barX[i+1] = barX[i]+DT*motion(barX[i],barU[i])
    As, Bs, cs = [], [], []
    for i in range(H):
        J, B = derivatives(barX[i])
        A = np.eye(7)+DT*J; B = DT*B
        affine = barX[i]+DT*motion(barX[i],barU[i])-A@barX[i]-B@barU[i]
        As.append(A); Bs.append(B)
        cs.append(xr[i+1]-A@xr[i]-B@ur[i]-affine)
    P = sparse.block_diag([np.zeros((7, 7))]+
        [2*state_cost(xr[i]) for i in range(1, H+1)]+
        [2*INPUT_WEIGHT*np.diag(1/U_MAX**2)]*H, format='csc')
    Aeq = sparse.lil_matrix((nx, nv))
    Aeq[:7, :7] = np.eye(7)
    rhs = np.zeros(nx); rhs[:7] = xr[0]-xhat
    for i in range(H):
        rows = slice(7*(i+1), 7*(i+2))
        Aeq[rows, 7*i:7*(i+1)] = -As[i]
        Aeq[rows, 7*(i+1):7*(i+2)] = np.eye(7)
        Aeq[rows, nx+3*i:nx+3*(i+1)] = Bs[i]
        rhs[rows] = cs[i]
    lower = np.r_[(xr-X_MAX).ravel(), (-U_MAX-ur).ravel()]
    upper = np.r_[(xr-X_MIN).ravel(), (U_MAX-ur).ravel()]
    A = sparse.vstack([Aeq.tocsc(), sparse.eye(nv)], format='csc')
    lo, hi = np.r_[rhs, lower], np.r_[rhs, upper]
    solver = osqp.OSQP()
    solver.setup(P=sparse.triu(P, format='csc'), q=np.zeros(nv), A=A, l=lo, u=hi,
                 verbose=False, eps_abs=1e-6, eps_rel=1e-6, max_iter=10000,
                 polishing=True, warm_starting=True)
    if previous is not None:
        # Overlapping reference samples are identical; shift correction sequence.
        dU = dU_seed
        E = [rhs[:7]]
        for i in range(H):
            E.append(As[i]@E[-1]-Bs[i]@dU[i]+cs[i])
        solver.warm_start(x=np.r_[np.asarray(E).ravel(), dU.ravel()])
    answer = solver.solve(raise_error=False)
    elapsed = perf_counter()-started
    if answer.info.status != 'solved':
        raise RuntimeError(f'QP failed: {answer.info.status}; no new command issued')
    values = A@answer.x
    violation = float(max(np.max(lo-values), np.max(values-hi), 0.))
    if not np.isfinite(violation) or violation > 1e-4:
        raise RuntimeError(f'QP constraint residual {violation}; command rejected')
    E = answer.x[:nx].reshape(H+1, 7)
    dU = answer.x[nx:].reshape(H, 3)
    return ur+dU, xr-E, dU, dict(cycle_s=elapsed, solver_s=float(answer.info.solve_time),
        iterations=int(answer.info.iter), qp_violation=violation)


def plant_step(x, u, k, disturbed):
    rate = motion(x, u).copy()
    if disturbed:
        rate[5] *= 1.06
        if 45 <= k < 67:  # 8.10 <= t < 12.06 s
            rate[:3] += [0., 1., .3]
    return x+DT*rate


def line_clearance(X):
    result = float('inf')
    for center in COLUMNS:
        a, b = X[:-1, :2], X[1:, :2]
        d = b-a
        s = np.clip(np.sum((center[:2]-a)*d, axis=1)/
                    np.maximum(np.sum(d*d, axis=1), 1e-15), 0, 1)
        result = min(result, float(np.min(np.linalg.norm(a+s[:, None]*d-center[:2], axis=1)-center[2])))
    return result


def experiment(name, H, xr, ur, steps, ideal=False):
    x = xr[0].copy() if ideal else xr[0]+INITIAL_OFFSET
    X, U, records, snaps = [x.copy()], [], [], {}
    previous = None
    for k in range(steps):
        if H:
            plan, prediction, previous, record = solve_mpc(x, xr[k:k+H+1], ur[k:k+H], previous)
            u = plan[0]
            records.append(record)
            if k in (0, 45, 46, 90):
                snaps[str(k)] = dict(prediction=prediction.tolist(), plan=plan.tolist())
        else:
            u = ur[k].copy()
        assert np.all(np.abs(u) <= U_MAX+1e-5)
        x = plant_step(x, u, k, disturbed=not ideal)
        X.append(x.copy()); U.append(u.copy())
    X, U = np.asarray(X), np.asarray(U)
    error = xr[:steps+1, :3]-X[:, :3]
    velocity_error = motion(xr[:steps+1], np.zeros((steps+1, 3)))[:, :3]-motion(X, np.zeros((steps+1, 3)))[:, :3]
    e = np.linalg.norm(error, axis=1)
    timings = np.array([r['cycle_s'] for r in records])
    state_excess = max(0., float(np.max(X_MIN[3:]-X[:, 3:])), float(np.max(X[:, 3:]-X_MAX[3:])))
    metrics = dict(position_rmse_m=float(np.sqrt(np.mean(e**2))), position_max_m=float(e.max()),
        position_final_m=float(e[-1]), position_after20_rmse_m=float(np.sqrt(np.mean(e[np.arange(len(e))*DT>=20]**2))),
        model_velocity_rmse_m_s=float(np.sqrt(np.mean(np.sum(velocity_error**2, axis=1)))),
        min_segment_clearance_m=line_clearance(X), state_violation=state_excess,
        max_abs_input=np.max(np.abs(U), axis=0).tolist())
    if H:
        metrics.update(cycle_median_ms=float(np.median(timings)*1000),
            cycle_p95_ms=float(np.percentile(timings, 95)*1000),
            cycle_max_ms=float(timings.max()*1000),
            max_qp_violation=max(r['qp_violation'] for r in records),
            solved_qps=len(records))
    out=ROOT/'results';out.mkdir(exist_ok=True)
    np.savetxt(out/(name+'_state.csv'), np.c_[np.arange(steps+1)*DT, X], delimiter=',',
               header='t,x,y,z,V,gamma,chi,phi', comments='')
    np.savetxt(out/(name+'_control.csv'), np.c_[np.arange(steps)*DT, U], delimiter=',',
               header='t,a,omega_gamma,omega_phi', comments='')
    np.savez_compressed(out/(name+'.npz'), X=X, U=U, reference=xr[:steps+1], timings=timings)
    record = dict(name=name, horizon_steps=H, metrics=metrics, cycles=records, snapshots=snaps)
    (out/(name+'.json')).write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(name, json.dumps(metrics), flush=True)
    return record


def verify_math(xr, ur):
    errors=[]
    for k in (0, 60, 120, 180):
        x, u = xr[k], ur[k]; J, B=derivatives(x); eps=1e-6
        numeric=np.column_stack([(motion(x+eps*np.eye(7)[j],u)-motion(x-eps*np.eye(7)[j],u))/(2*eps) for j in range(7)])
        errors.append(float(np.max(np.abs(J-numeric))))
        numericB=np.column_stack([(motion(x,u+eps*np.eye(3)[j])-motion(x,u-eps*np.eye(3)[j]))/(2*eps) for j in range(3)])
        errors.append(float(np.max(np.abs(B-numericB))))
    defect=max(float(np.max(np.abs(xr[k+1]-xr[k]-DT*motion(xr[k],ur[k])))) for k in range(200))
    assert max(errors)<1e-7 and defect<1e-6
    return dict(jacobian_max_error=max(errors), reference_euler_defect=defect)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plots-only', action='store_true')
    args=parser.parse_args();out=ROOT/'results';out.mkdir(exist_ok=True)
    xr, ur, steps=reference()
    specs=[('open_loop',0,False),('mpc20',20,False),('mpc5',5,False),('mpc40',40,False),('ideal20',20,True)]
    checks=verify_math(xr,ur);runs=[]
    for name,H,ideal in specs:
        runs.append(json.loads((out/(name+'.json')).read_text()) if args.plots_only else experiment(name,H,xr,ur,steps,ideal))
    mainrun=runs[1]['metrics']
    assert mainrun['position_rmse_m']<runs[0]['metrics']['position_rmse_m']
    assert mainrun['position_final_m']<.5
    assert runs[-1]['metrics']['position_max_m']<1e-4
    assert all(r['metrics']['state_violation']<1e-4 for r in runs)
    report=dict(date='2026-10-24', dt_s=DT, model='same seven-state rate-input kinematics as Chapter3',
        horizon_steps=[5,20,40], position_scale_m=POS_SCALE, velocity_scale_m_s=VEL_SCALE,
        input_weight=INPUT_WEIGHT, initial_offset=INITIAL_OFFSET.tolist(),
        disturbance=dict(course_rate_gain=1.06, wind_m_s=[0,1,.3], wind_start_s=45*DT,wind_end_s=67*DT),
        numerical_checks=checks, python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
        osqp=osqp.__version__, results=[{k:r[k] for k in ('name','horizon_steps','metrics')} for r in runs])
    (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    from plots import make_figures
    make_figures(out, xr, ur, runs)
    print(f'All experiments completed: {out}',flush=True)


if __name__ == '__main__':
    main()
