"""Rate-input Dubins airplane. z upward, SI units.
States: x,y,z,V,gamma,chi,phi. Inputs: a,omega_gamma,omega_phi.
Near-level coordinated bank-to-turn approximation with ideal low-level tracking.
Basis: Adajania et al., IROS 2021, eqs.(1)-(2), arXiv:2109.12609;
Beard/McLain, Implementing Dubins Airplane Paths on Fixed-wing UAVs.
"""
import numpy as np
G=9.81
PAR=dict(g=G,model='rate-input Dubins airplane',z_positive='up')

def motion(x,u):
    V,ga,ch,phi=(x[...,i] for i in (3,4,5,6))
    a,og,op=(u[...,i] for i in (0,1,2))
    return np.stack((V*np.cos(ga)*np.cos(ch),V*np.cos(ga)*np.sin(ch),
                     V*np.sin(ga),a,og,G*np.tan(phi)/V,op),axis=-1)

def symbolic_motion(x,u,ca):
    V,ga,ch,phi=x[3,:],x[4,:],x[5,:],x[6,:]
    return ca.vertcat(V*ca.cos(ga)*ca.cos(ch),V*ca.cos(ga)*ca.sin(ch),
                      V*ca.sin(ga),u[0,:],u[1,:],G*ca.tan(phi)/V,u[2,:])

def forward_euler(x0,U,dt):
    """ONE explicit Euler update per interval; no internal substeps."""
    x=np.asarray(x0,dtype=float).copy();rows=[x.copy()]
    for u in U:
        x=x+dt*motion(x,u)
        rows.append(x.copy())
    return np.asarray(rows)
