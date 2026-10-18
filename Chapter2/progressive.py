"""第二章正文递进实验：P -> 持续外力 -> PI -> PID -> 高度/速度双环。

所有主线实验 m=1.6 kg，b=1.6 N*s/m。b 为教学模型的局部线性阻力系数，
并非实际机型辨识参数。直接运行 RunMe.py 生成全部结果。
"""
import json
from dataclasses import asdict
import numpy as np
import matplotlib.pyplot as plt
import RunMe as r


def compare(ds, labels, name, quantities=(2,7), ylabel=('高度 $h$ / m','总推力 $T$ / N'), wind=False, xlim=None):
    fig,axs=plt.subplots(2,1,figsize=(7,4.65),sharex=True,layout='constrained')
    axs[0].plot(ds[0][:,0],ds[0][:,1],':',color='#888',lw=1.1,label='参考高度')
    for i,(d,l) in enumerate(zip(ds,labels)):
        for ax,col in zip(axs,quantities): ax.plot(d[:,0],d[:,col],color=r.C[i],ls=r.LS[i],label=l)
    for ax,lab in zip(axs,ylabel):
        ax.set_ylabel(lab)
        if wind: ax.axvline(14,color='#aaa',lw=.8,ls=':')
        if xlim: ax.set_xlim(xlim)
    axs[0].legend(ncol=3,frameon=False,fontsize=9,loc='lower center',bbox_to_anchor=(.5,1.01))
    axs[-1].set_xlabel('时间 $t$ / s')
    r.finish(fig,name)


def generate():
    r.setup_style()
    common=dict(drag=1.6,kp=4,kd=0,ki=0,t_end=40,wind_at=14)
    cases=[r.Case('stage_p',**common),
           r.Case('stage_p_wind',**{**common,'wind':-2}),
           r.Case('stage_p8_wind',**{**common,'kp':8,'wind':-2}),
           r.Case('stage_pi',**{**common,'ki':1.2,'wind':-2}),
           r.Case('stage_pid',**{**common,'ki':1.2,'kd':1.5,'wind':-2}),
           r.Case('stage_no_drag',**{**common,'drag':0,'t_end':14}),
           r.Case('stage_cascade',cascade=True,drag=1.6,h0=2,r=3,wind=-2,wind_at=14,t_end=40,antiwindup=True)]
    results={}; checks={}; metrics={}
    for c in cases:
        d=r.simulate(c); fine=r.simulate(c,.0025)
        err=float(np.max(np.abs(d[:,2]-fine[::2,2])))
        assert err<1e-5,(c.name,err)
        assert np.isfinite(d).all()
        assert np.all(d[:,7]>=0) and np.all(d[:,7]<=c.tmax+1e-10)
        assert np.max(np.abs(d[:,6]-d[:,7]))<1e-10, '主线对照不应触发推力限幅'
        results[c.name]=d;r.save_series(c.name,d)
        checks[c.name]={'halved_step_height_error_m':err}
        early=d[d[:,0]<14]
        metrics[c.name]={'initial_step':r.step_metrics(early,c.h0,c.r),
                         'final_2s_mean_error_m':float(np.mean(d[d[:,0]>=c.t_end-2,4])),
                         'minimum_height_m':float(d[:,2].min()),
                         'maximum_thrust_N':float(d[:,7].max())}
    d=results['stage_p']; t=d[:,0]
    alpha=1.6/(2*r.M); omega=np.sqrt(4/r.M-alpha**2)
    exact=3-np.exp(-alpha*t)*(np.cos(omega*t)+alpha/omega*np.sin(omega*t))
    checks['analytic_p_max_height_error_m']=float(np.max(np.abs(d[:,2]-exact)))
    assert checks['analytic_p_max_height_error_m']<1e-6
    assert abs(metrics['stage_p_wind']['final_2s_mean_error_m']-.5)<1e-5
    assert abs(metrics['stage_p8_wind']['final_2s_mean_error_m']-.25)<1e-5
    assert abs(metrics['stage_pi']['final_2s_mean_error_m'])<.003
    assert abs(metrics['stage_pid']['final_2s_mean_error_m'])<.003
    for key,kd in [('stage_pi',0),('stage_pid',1.5)]:
        poles=np.roots([r.M,1.6+kd,4,1.2]); assert np.all(poles.real<0)
        checks[key]['closed_loop_poles']=[[float(v.real),float(v.imag)] for v in poles]
    compare([results['stage_p'],results['stage_no_drag']],['有竖直阻尼','忽略竖直阻尼'],
            'stage1_p',xlim=(0,14))
    compare([results['stage_p_wind'],results['stage_p8_wind']],['P：$K_p=4$','P：$K_p=8$'],
            'stage2_bias',wind=True)
    fig,axs=plt.subplots(2,1,figsize=(7,4.65),sharex=True,layout='constrained')
    axs[0].plot(d[:,0],d[:,1],':',color='#888',label='参考高度')
    for i,(key,label) in enumerate([('stage_p_wind','P 控制'),('stage_pi','PI 控制')]):
        dd=results[key];axs[0].plot(dd[:,0],dd[:,2],color=r.C[i],ls=r.LS[i],label=label)
    dd=results['stage_pi']
    axs[1].plot(dd[:,0],4*dd[:,4],color=r.C[0],label='比例修正 $K_p e$')
    axs[1].plot(dd[:,0],1.2*dd[:,5],color=r.C[1],ls='--',label='积分补偿 $K_i I$')
    for ax in axs:
        ax.axvline(14,color='#aaa',lw=.8,ls=':')
        ax.legend(frameon=False,ncol=3,fontsize=9,loc='lower center',bbox_to_anchor=(.5,1.01))
    axs[0].set_ylabel('高度 $h$ / m');axs[1].set_ylabel('修正推力 / N');axs[1].set_xlabel('时间 $t$ / s')
    r.finish(fig,'stage3_integral')
    compare([results['stage_pi'],results['stage_pid']],['PI 控制','PID 控制'],
            'stage4_derivative',wind=True)
    dd=results['stage_cascade']
    fig,axs=plt.subplots(3,1,figsize=(7,6.0),sharex=True,layout='constrained')
    for ax,cols,labels in [(axs[0],[1,2],['参考高度','实际高度']),
                           (axs[1],[9,3],['外环给出的参考速度','实际竖直速度'])]:
        for i,(col,label) in enumerate(zip(cols,labels)):
            ax.plot(dd[:,0],dd[:,col],color=r.C[i],ls=r.LS[i],label=label)
        ax.legend(frameon=False,ncol=2,fontsize=9,loc='lower center',bbox_to_anchor=(.5,1.01))
    axs[2].plot(dd[:,0],dd[:,7],color=r.C[0])
    for ax in axs:ax.axvline(14,color='#aaa',lw=.8,ls=':')
    axs[0].set_ylabel('高度 / m');axs[1].set_ylabel('竖直速度 / (m/s)');axs[2].set_ylabel('总推力 $T$ / N')
    axs[2].set_xlabel('时间 $t$ / s');r.finish(fig,'stage5_cascade')
    # 相同的悬停任务：预置重力前馈，或在同一前馈上加入反馈。
    cfg=r.Case('feedback_hover',h0=3,r=3,drag=1.6,kp=4,ki=1.2,kd=1.5,wind=-.4,wind_at=2,t_end=12)
    fb=r.simulate(cfg);r.save_series(cfg.name,fb)
    tt=fb[:,0];dt=np.maximum(tt-2,0);d0=-.4;b=1.6
    ho=3+(d0/b)*(dt-(r.M/b)*(1-np.exp(-b*dt/r.M)))
    vo=(d0/b)*(1-np.exp(-b*dt/r.M))
    np.savetxt(r.OUT/'feedforward_open.csv',np.column_stack([tt,ho,vo]),delimiter=',',
               header='time_s,height_m,velocity_m_s',comments='',fmt='%.10g')
    fig,axs=plt.subplots(2,1,figsize=(7,4.65),sharex=True,layout='constrained')
    axs[0].axhline(3,color='#888',lw=1,ls=':',label='参考高度')
    axs[0].plot(tt,ho,color=r.C[1],ls='--',label='仅预置重力前馈')
    axs[0].plot(tt,fb[:,2],color=r.C[0],label='同一前馈加反馈修正')
    axs[1].plot(tt,np.full_like(tt,r.M*r.G),color=r.C[1],ls='--')
    axs[1].plot(tt,fb[:,7],color=r.C[0])
    for ax in axs:ax.axvline(2,color='#aaa',ls=':',lw=.8)
    axs[0].legend(frameon=False,ncol=1,fontsize=9,loc='lower left')
    axs[0].set_ylabel('高度 $h$ / m');axs[1].set_ylabel('总推力 $T$ / N');axs[1].set_xlabel('时间 $t$ / s')
    r.finish(fig,'stage6_feedforward_feedback')
    info={'model':'m*h_ddot=T-m*g-b*h_dot+d_z','dt_s':.005,'refined_dt_s':.0025,
          'parameters':[asdict(c) for c in cases]+[asdict(cfg)],'checks':checks,'metrics':metrics,
          'feedforward_feedback':{'open_final_height_m':float(ho[-1]),'closed_final_height_m':float(fb[-1,2])}}
    (r.OUT/'progressive_results.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    return info


if __name__=='__main__':print(json.dumps(generate(),ensure_ascii=False,indent=2))
