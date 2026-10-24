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

def simulate(m=1.92,force_mode='down',e0=.2,phi=.05,noisy=False,tmax=28,dt=.002,tf=12):
    t=np.arange(round(tf/dt)+1)*dt;d=np.zeros((len(t),11));h=3-e0;v=0.
    for k,tk in enumerate(t):
        force=-2.6 if force_mode=='down' else (2.6 if force_mode=='up' else 2.6*math.sin(2*math.pi*.6*tk))
        nh=.002*math.sin(2*math.pi*8*tk) if noisy else 0
        nv=.01*math.sin(2*math.pi*11*tk+.4) if noisy else 0
        em=3-h-nh;ev=-v-nv;s=ev+em
        u=ev+2.5*s+4.5*np.clip(s/phi,-1,1);cmd=1.6*(9.81+u);T=np.clip(cmd,0,tmax)
        d[k]=[tk,h,v,3-h,T,cmd,-v+3-h,force,s,nh,nv]
        if k<len(t)-1:h,v=h+dt*v,v+dt*(T-m*9.81+force)/m
    return d
def main():
    specs={'light_down':dict(m=1.6),'heavy_down':{},'heavy_up':dict(force_mode='up',e0=-.2),'varying_force':dict(force_mode='sine'),'noise_phi005':dict(noisy=True),'noise_phi002':dict(noisy=True,phi=.02),'limited':dict(m=1.6,tmax=17.8,e0=0,tf=4)}
    cases={};report={}
    for name,kwargs in specs.items():
        d=simulate(**kwargs);cases[name]=d;save(name,d,'t,h,v,e,T,Tcmd,s,F,s_meas,n_h,n_v');report[name]=metrics(d)
        report[name].update({'thrust_min_N':float(d[:,4].min()),'thrust_max_N':float(d[:,4].max()),'TV_N':float(np.abs(np.diff(d[:-1,4])).sum()),'peak_error_after4_m':float(np.abs(d[d[:,0]>=4,3]).max())})
        if name in ['light_down','heavy_down','heavy_up','varying_force']:
            assert np.abs(d[:,3]).max()<=.200001
            assert np.abs(d[:,6]).max()<=.200001
            assert np.abs(d[d[:,0]>=4,3]).max()<.05
            assert np.max(abs(d[:,4]-d[:,5]))<1e-12
    panel('range_comparison',[(l,cases[n]) for n,l in [('light_down','1.6 kg，向下外力'),('heavy_down','1.92 kg，向下外力'),('heavy_up','1.92 kg，向上外力'),('varying_force','1.92 kg，时变外力')]],[3,6,4],['高度误差 / m','组合误差 / (m/s)','推力 / N'],{0:[-.05,.05],1:[-.05,.05]})
    panel('measurement_comparison',[(l,cases[n]) for n,l in [('heavy_down','准确反馈'),('noise_phi005','测量误差，半宽0.05'),('noise_phi002','测量误差，半宽0.02')]],[3,4],['真实高度误差 / m','实际推力 / N'])
    panel('limited_thrust',[('上限17.8 N',cases['limited'])],[1,4],['高度 / m','推力 / N'],{1:[18.296]})
    fine=simulate(dt=.001);report['step_refinement_max_h_m']=float(np.max(abs(cases['heavy_down'][:,1]-fine[::2,1])))
    assert report['step_refinement_max_h_m']<.002
    report['steady_error_formula_m']=((1.92-1.6)*9.81+2.6)/(1.6*92.5)
    assert abs(cases['heavy_down'][-1,3]-report['steady_error_formula_m'])<1e-4
    (OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Chapter 7: range, noise, capacity and step-refinement checks completed.')
if __name__=='__main__':main()
