"""Small-angle fixed-wing model. SI units; controls T, alpha, omega_mu."""
import numpy as np
PAR=dict(m=8.,g=9.81,rho=1.225,S=.8,CL0=.2,CLalpha=4.8,CD0=.04,k=.06)
def aero(V,alpha):
 p=PAR;qS=.5*p['rho']*V**2*p['S'];CL=p['CL0']+p['CLalpha']*alpha
 return qS*CL,qS*(p['CD0']+p['k']*CL**2)
def trim(V=20.):
 p=PAR;CL=p['m']*p['g']/(.5*p['rho']*V**2*p['S']);a=(CL-p['CL0'])/p['CLalpha'];_,T=aero(V,a)
 return float(T),float(a)
def motion(x,u):
 V,ga,ch,mu=(x[...,i] for i in (3,4,5,6));T,a,om=(u[...,i] for i in (0,1,2));L,D=aero(V,a);m,g=PAR['m'],PAR['g']
 return np.stack((V*np.cos(ga)*np.cos(ch),V*np.cos(ga)*np.sin(ch),V*np.sin(ga),(T-D)/m-g*np.sin(ga),
  (L*np.cos(mu)-m*g*np.cos(ga))/(m*V),L*np.sin(mu)/(m*V*np.cos(ga)),om),axis=-1)
def symbolic_motion(x,u,ca):
 p=PAR;V,ga,ch,mu=x[3,:],x[4,:],x[5,:],x[6,:];T,a,om=u[0,:],u[1,:],u[2,:]
 qS=.5*p['rho']*V**2*p['S'];CL=p['CL0']+p['CLalpha']*a;L=qS*CL;D=qS*(p['CD0']+p['k']*CL**2);m,g=p['m'],p['g']
 return ca.vertcat(V*ca.cos(ga)*ca.cos(ch),V*ca.cos(ga)*ca.sin(ch),V*ca.sin(ga),(T-D)/m-g*ca.sin(ga),
  (L*ca.cos(mu)-m*g*ca.cos(ga))/(m*V),L*ca.sin(mu)/(m*V*ca.cos(ga)),om)
def forward_euler(x0,U,dt,substeps=1):
 x=np.array(x0,float).copy();rows=[x.copy()]
 for u in U:
  for _ in range(substeps):
   x=x+dt/substeps*motion(x,u);rows.append(x.copy())
 return np.array(rows)
