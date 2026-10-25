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

def simulate(kind='active',alpha=.65,delay=0,force=0,dt=.01,tf=10):
    h=5.;v=0.;prev_v=0.;prev_u=1.6*9.81;fy=prev_u;fu=prev_u;ahat=1.;count=0;alarm=False;td=None;rows=[]
    qr=math.exp(-dt/.12);qa=math.exp(-dt/.20)
    for k in range(round(tf/dt)+1):
        t=k*dt
        if k:
            y=1.6*((v-prev_v)/dt+9.81);fy=qr*fy+(1-qr)*y;fu=qr*fu+(1-qr)*prev_u
            res=fu-fy
            if fu>=5:ahat=qa*ahat+(1-qa)*np.clip(fy/fu,.3,1.1)
            count=count+1 if res>1.6 else 0
            if count>=12 and not alarm:alarm=True;td=t
        else:res=0
        estimate_valid=bool(k and fu>=5 and np.isfinite(fy) and np.isfinite(fu))
        enabled=kind=='active' and alarm and estimate_valid and t>=td+delay-1e-12
        used=ahat if enabled else 1.
        desired=1.6*9.81+40*(5-h)-16*v
        raw=desired/used;U=np.clip(raw,0,28);a=alpha if t>=3 else 1.;F=force if t>=3 else 0.;T=a*U
        rows.append([t,h,v,5-h,U,T,a,ahat,res,int(alarm),int(enabled),raw])
        if k==round(tf/dt):break
        an=(T-1.6*9.81+F)/1.6;newh=h+dt*v;newv=v+dt*an
        if newh<=0:
            frac=-h/v;terminal=rows[-1].copy();terminal[0]=t+frac;terminal[1]=0.;terminal[2]=v+frac*an;terminal[3]=5.;rows.append(terminal);break
        prev_v=v;prev_u=U;h,v=newh,newv
    return np.array(rows)
def main():
    specs={'passive':dict(kind='passive'),'active':{},'delayed':dict(delay=.5),'force_ambiguity':dict(alpha=1,force=-5.4936),'capacity_loss':dict(alpha=.5)};cases={};report={}
    for name,kw in specs.items():
        d=simulate(**kw);cases[name]=d;save(name,d,'t,h,v,e,U,T,alpha,alpha_hat,residual,alarm,reconfigured,U_raw');report[name]=metrics(d)
        alarms=d[d[:,9]>0,0];report[name]['alarm_s']=float(alarms[0]) if len(alarms) else None
        report[name]['final_alpha_hat']=float(d[-1,7]);report[name]['max_command_N']=float(d[:,4].max())
        assert np.max(d[:,4])<=28 and np.min(d[:,4])>=0
        assert np.all(d[d[:,0]<3,9]==0)
    panel('fault_response',[(l,cases[n]) for n,l in [('passive','固定PD'),('active','检测后补偿'),('delayed','额外延迟0.5秒')]],[1,2,4],['高度 / m','速度 / (m/s)','名义推力指令 / N'])
    panel('diagnosis',[(l,cases[n]) for n,l in [('active','效能下降至0.65'),('force_ambiguity','健康执行机构受外力')]],[8,7,1],['残差 / N','效能估计','高度 / m'],{0:[1.6]})
    panel('capacity_loss',[('效能下降至0.50',cases['capacity_loss'])],[1,4,5],['高度 / m','名义指令 / N','实际推力 / N'],{2:[15.696]})
    assert abs(cases['passive'][-1,3]-(1-.65)*15.696/(.65*40))<1e-4
    assert abs(cases['active'][-1,3])<1e-4
    assert cases['capacity_loss'][-1,1]==0
    assert report['force_ambiguity']['alarm_s'] is not None
    fig,ax=plt.subplots(figsize=(7,4),layout='constrained')
    for alpha,color,label in [(1,'#217d8a','健康'),(.8,'#a86e36','左侧效能0.8'),(.5,'#6c5797','左侧效能0.5')]:
        ul=np.array([0,14,14,0,0]);ur=np.array([0,0,14,14,0]);T=alpha*ul+ur;q=ur-alpha*ul
        ax.fill(T,q,color=color,alpha=.07);ax.plot(T,q,color=color,label=label)
    ax.axhline(0,color='gray',lw=.7);ax.plot(15.696,0,'ko',label='悬停要求');ax.set(xlabel='总推力 / N',ylabel='滚转力矩 / 力臂（N）');ax.legend(frameon=False,loc='upper left');ax.grid(alpha=.2)
    fig.savefig(OUT/'allocation.pdf',bbox_inches='tight');fig.savefig(OUT/'allocation.png',dpi=170,bbox_inches='tight');plt.close(fig)
    (OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Chapter 8: causal diagnosis, reconfiguration, ambiguity and capacity checks completed.')
if __name__=='__main__':main()
