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
cent=np.arange(-6,7,2);q=np.arange(-6,7)
# label indices NB NM NS ZO PS PM PB
rules=np.array([[0,0,0,0,1,3,3],[0,0,0,0,1,3,3],[1,1,1,1,3,4,4],[1,1,2,3,4,5,5],[2,2,3,5,5,5,5],[3,3,5,6,6,6,6],[3,3,5,6,6,6,6]])
outmf=np.maximum(0,1-np.abs(q[None,:]-cent[:,None])/2)
def rnd(x):return np.sign(x)*np.floor(abs(x)+.5)
def fuzzy(e,ec,mode):
 E=np.clip(5*e,-6,6);EC=np.clip(10*ec,-6,6)
 if mode=='quantized':E=rnd(E);EC=rnd(EC)
 me=np.maximum(0,1-np.abs(E-cent)/2);mc=np.maximum(0,1-np.abs(EC-cent)/2)
 fire=np.minimum(me[:,None],mc[None,:]);C=np.minimum(fire[:,:,None],outmf[rules]).max(axis=(0,1))
 U=q@C/C.sum()
 if mode=='quantized':U=rnd(U)
 return .5*U
# keep repeated quantized calculations in 13x13 table, same relation
lut=np.array([[fuzzy(i/5,j/10,'quantized') for j in range(-6,7)] for i in range(-6,7)])
def sim5(mode,h0,force,dt=.01,tf=30):
 t=np.arange(round(tf/dt)+1)*dt;N=len(t);h=np.zeros(N);v=np.zeros(N);T=np.zeros(N);h[0]=h0
 for k in range(N):
  e=3-h[k];ec=-v[k]
  if mode=='quantized':u=lut[int(np.clip(rnd(5*e),-6,6))+6,int(np.clip(rnd(10*ec),-6,6))+6]
  else:u=fuzzy(e,ec,mode)
  T[k]=np.clip(14.7+u,0,22)
  if k<N-1:h[k+1]=h[k]+dt*v[k];v[k+1]=v[k]+dt*(T[k]-14.7-1.5*v[k]+force)/1.5
 return np.column_stack([t,h,v,3-h,T])

def main():
    cases={};report={}
    for case,h0,force in [('rise',2.6,0),('small',2.91,0),('force',3,-.2)]:
        for mode in ['quantized','continuous']:
            name=case+'_'+mode;d=sim5(mode,h0,force);cases[name]=d;save(name,d,'t,h,v,e,T');report[name]=metrics(d)
        panel(case,[(s,cases[case+'_'+m]) for m,s in [('quantized','整数输入与输出'),('continuous','连续输入与实数输出')]],[1,2,4],['高度 / m','速度 / (m/s)','推力 / N'])
    assert np.max(np.abs(cases['small_quantized'][:,3]-.09))<1e-10
    assert abs(cases['force_continuous'][-1,3]-1/35)<1e-4
    assert abs(cases['rise_continuous'][-1,3])<1e-4
    assert abs(fuzzy(.4,0,'quantized')-2)<1e-12
    report['checks']='single-step inference, dead zone, steady balance and finite states passed'
    (OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Chapter 5: all three comparisons and checks completed.')
if __name__=='__main__':main()
