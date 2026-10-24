"""One command runs every textbook comparison, exports curves and checks."""
from pathlib import Path
import json, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
def save(name,data,header):
    assert np.isfinite(data).all(),name
    np.savetxt(OUT/(name+'.csv'),data,delimiter=',',header=header,comments='',fmt='%.17g')
def panel(name,series,columns,ylabels,limits=None):
    fig,axs=plt.subplots(len(columns),1,figsize=(8,2.0*len(columns)),sharex=True,squeeze=False,layout='constrained')
    colors=['#217d8a','#a86e36','#6c5797','#525252','#4d8049'];styles=['-','--','-.',':','--']
    for ax,col,yl in zip(axs[:,0],columns,ylabels):
        for j,(label,d) in enumerate(series):ax.plot(d[:,0],d[:,col],color=colors[j%5],ls=styles[j%5],label=label,lw=1.5)
        ax.set_ylabel(yl);ax.grid(alpha=.2)
    axs[0,0].legend(loc='lower left',bbox_to_anchor=(0,1.01),ncol=min(3,len(series)),frameon=False,fontsize=8.5)
    axs[-1,0].set_xlabel('时间 / s')
    if limits:
        for idx,values in limits.items():
            for val in values:axs[idx,0].axhline(val,color='#999',ls=':',lw=.8)
    fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight');fig.savefig(OUT/(name+'.png'),dpi=170,bbox_inches='tight');plt.close(fig)
def metrics(d):
    return {'final_error_m':float(d[-1,3]),'peak_error_m':float(np.max(np.abs(d[:,3]))),'end_time_s':float(d[-1,0])}
def sim6(mode,dt=.01,tf=100):
 t=np.arange(round(tf/dt)+1)*dt;N=len(t);h=np.zeros(N);v=np.zeros(N);h[0]=3
 # W1,W2,b1,b2,v1,v2,c
 theta=np.array([.3,-.3,.2,-.2,0.,0.,0.]);rec=np.zeros((N,7));un=np.zeros(N);uf=np.zeros(N);T=np.zeros(N)
 for k in range(N):
  act=np.tanh(theta[:2]+theta[2:4]);un[k]=theta[4:6]@act+theta[6]
  uf[k]=6*(3-h[k])-5*v[k];T[k]=np.clip(14.7+un[k]+uf[k],0,24);rec[k]=theta
  if k<N-1:
   h[k+1]=h[k]+dt*v[k];v[k+1]=v[k]+dt*(T[k]-1.6*9.8-1.6*v[k]+(-.4 if t[k]>=60 else 0))/1.6
   learn=mode=='online' or (mode=='frozen' and t[k]<50)
   if learn:
    dh=theta[4:6]*(1-act**2);grad=np.r_[dh,dh,act,1]
    theta=theta+.006*(dt/.01)*uf[k]*grad
 return np.column_stack([t,h,v,3-h,T,un,uf,rec])

def main():
    cases={};report={}
    for mode in ['off','frozen','online']:
        d=sim6(mode);cases[mode]=d;save(mode,d,'t,h,v,e,T,u_nn,u_fb,W1,W2,b1,b2,v1,v2,c');report[mode]=metrics(d)
    panel('learning_comparison',[(l,cases[m]) for m,l in [('off','不学习'),('frozen','50秒后冻结'),('online','持续在线学习')]],[3,5,6,4],['高度误差 / m','网络补偿 / N','反馈修正 / N','推力 / N'])
    d=cases['online'];panel('weights',[(f'参数 {i-6}',np.column_stack([d[:,0],d[:,i]])) for i in range(7,14)],[1],['网络参数'])
    assert abs(cases['off'][-1,3]-.23)<1e-6
    assert abs(cases['frozen'][-1,3]-.4/6)<1e-6
    assert abs(cases['online'][-1,3])<1e-4
    assert abs(cases['online'][-1,5]-1.38)<1e-4
    assert np.max(abs(cases['frozen'][5000:,7:]-cases['frozen'][5000,7:]))==0
    report['checks']='steady balances, frozen weights and learned compensation passed'
    (OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Chapter 6: all three learning modes and checks completed.')
if __name__=='__main__':main()
