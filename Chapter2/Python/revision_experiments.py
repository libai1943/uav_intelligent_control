"""前两章修订补充：同一高度模型的参数、限幅、双环与量化记录。
不调用外部求解器；RunMe.py 自动执行本文件。CSV 列定义与主线一致。
"""
from dataclasses import asdict, replace
import json
import numpy as np
import matplotlib.pyplot as plt
import RunMe as r


def generate():
    r.setup_style()
    base=r.Case('tune_p',drag=1.6,kp=4,kd=0,ki=0,wind=-2,wind_at=14,t_end=40)
    cases=[base,replace(base,name='tune_pd',kd=1.5),replace(base,name='tune_pid',kd=1.5,ki=1.2),
           replace(base,name='limit_plain',kd=1.5,ki=1.2,wind=0,tmax=r.M*r.G+.6),
           replace(base,name='limit_conditional',kd=1.5,ki=1.2,wind=0,tmax=r.M*r.G+.6,antiwindup=True),
           replace(base,name='cascade_large',cascade=True,h0=1,antiwindup=True),
           replace(base,name='cascade_slow_inner',cascade=True,kv=2,kiv=.8,antiwindup=True),
           replace(base,name='cascade_slow_outer',cascade=True,kh=.4,antiwindup=True)]
    ds={}
    for c in cases:
        d=r.simulate(c);r.save_series(c.name,d);ds[c.name]=d
        assert np.isfinite(d).all()
        assert np.all((d[:,7]>=0)&(d[:,7]<=c.tmax+1e-9))
        # 单步显式欧拉的残差核验；不是另一套积分算法。
        expected=np.column_stack([d[:-1,3],(d[:-1,7]-c.m*r.G-c.drag*d[:-1,3]+d[:-1,8])/c.m,d[:-1,11]])
        assert np.max(np.abs(np.diff(d[:,[2,3,5]],axis=0)-.002*expected))<1e-11
    fig,axs=plt.subplots(4,1,figsize=(7,7.1),sharex=True,layout='constrained')
    for i,(key,label) in enumerate([('limit_plain','普通积分'),('limit_conditional','条件积分')]):
        d=ds[key]
        for ax,col in zip(axs,[2,5,6,7]):ax.plot(d[:,0],d[:,col],color=r.C[i],ls=r.LS[i],label=label)
    axs[0].axhline(3,color='#888',ls=':',lw=.8)
    for ax in axs[2:]:ax.axhline(r.M*r.G+.6,color='#888',ls=':',lw=.8)
    axs[0].legend(frameon=False,ncol=2,fontsize=9,loc='lower center',bbox_to_anchor=(.5,1.01))
    for ax,label in zip(axs,['高度 / m','积分状态 / (m·s)','限幅前推力 / N','实际推力 / N']):ax.set_ylabel(label)
    axs[-1].set_xlabel('时间 $t$ / s');r.finish(fig,'stage7_antiwindup')
    # 三个受控对照分别回答内环、外环和结构接口问题。
    baseline=np.loadtxt(r.OUT/'stage_cascade.csv',delimiter=',',skiprows=1)
    fig,axs=plt.subplots(3,1,figsize=(7,6.4),sharex=True,layout='constrained')
    d=ds['cascade_slow_inner']
    axs[0].plot(baseline[:,0],baseline[:,3],color=r.C[0],label='速度内环 $K_v=5, K_{iv}=2$')
    axs[0].plot(d[:,0],d[:,3],color=r.C[1],ls='--',label='速度内环 $K_v=2, K_{iv}=0.8$')
    axs[0].plot(baseline[:,0],baseline[:,9],color=r.C[0],ls=':',lw=1,label='基准内环对应的参考速度')
    d=ds['cascade_slow_outer']
    axs[1].plot(baseline[:,0],baseline[:,2],color=r.C[0],label='高度外环 $K_h=0.8$')
    axs[1].plot(d[:,0],d[:,2],color=r.C[1],ls='--',label='高度外环 $K_h=0.4$')
    d=ds['tune_pid']
    axs[2].plot(baseline[:,0],baseline[:,2],color=r.C[0],label='高度—速度级联')
    axs[2].plot(d[:,0],d[:,2],color=r.C[1],ls='--',label='单环 PID')
    for ax in axs:
        ax.set_xlim(0,14);ax.legend(frameon=False,ncol=1,fontsize=8.5,loc='lower right')
    for ax,label in zip(axs,['竖直速度 / (m/s)','高度 / m','高度 / m']):ax.set_ylabel(label)
    axs[-1].set_xlabel('时间 $t$ / s');r.finish(fig,'stage8_cascade_comparison')
    d=ds['cascade_large']
    fig,axs=plt.subplots(2,1,figsize=(7,4.7),sharex=True,layout='constrained')
    axs[0].plot(d[:,0],d[:,2],color=r.C[0],label='实际高度');axs[0].axhline(3,ls=':',color='#888',label='参考高度')
    for val,label,color,style in [(.8*d[:,4],'未限幅速度要求',r.C[1],':'),(d[:,9],'限幅后参考速度',r.C[0],'-'),(d[:,3],'实际速度',r.C[2],'--')]:
        axs[1].plot(d[:,0],val,color=color,ls=style,label=label)
    for ax in axs:ax.set_xlim(0,14);ax.legend(frameon=False,fontsize=9,ncol=1,loc='lower right')
    axs[0].set_ylabel('高度 / m');axs[1].set_ylabel('竖直速度 / (m/s)');axs[-1].set_xlabel('时间 $t$ / s')
    r.finish(fig,'stage9_velocity_limit')
    metrics={c.name:r.step_metrics(ds[c.name][ds[c.name][:,0]<14],c.h0,c.r) for c in cases}
    for c in cases:metrics[c.name]['final_mean_error_m']=float(np.mean(ds[c.name][-1001:,4]))
    lines=[]
    def fmt(v,n=2):return '未进入' if v is None else f'{v:.{n}f}'
    for name,label,kp,ki,kd in [('tune_p','P',4,0,0),('tune_pd','PD',4,0,1.5),('tune_pid','PID',4,1.2,1.5)]:
        q=metrics[name]
        lines.append(f'{label}&{kp:g}, {ki:g}, {kd:g}&{q["overshoot_percent"]:.2f}&{fmt(q["settling_2percent_observed_s"])}&{q["final_mean_error_m"]:.3f}'+r'\\\hline')
    (r.OUT/'tuning_rows.tex').write_text('\n'.join(lines),encoding='utf-8')
    op=np.loadtxt(r.OUT/'feedforward_open.csv',delimiter=',',skiprows=1)
    fb=np.loadtxt(r.OUT/'feedback_hover.csv',delimiter=',',skiprows=1)
    recovery=None;bad=np.flatnonzero((fb[:,0]>=2)&(np.abs(fb[:,4])>.02))
    if len(bad) and bad[-1]<len(fb)-1:recovery=float(fb[bad[-1]+1,0]-2)
    ff={'open_final_error_m':float(3-op[-1,1]),'closed_final_error_m':float(fb[-1,4]),
        'open_max_error_m':float(np.max(np.abs(3-op[:,1]))),'closed_max_error_m':float(np.max(np.abs(fb[:,4]))),
        'closed_max_correction_N':float(np.max(np.abs(fb[:,7]-r.M*r.G))),'recovery_s':recovery}
    rows=[f'仅重力前馈&{ff["open_final_error_m"]:.3f}&{ff["open_max_error_m"]:.3f}&0&未恢复'+r'\\\hline',
          f'前馈加PID反馈&{ff["closed_final_error_m"]:.3f}&{ff["closed_max_error_m"]:.3f}&{ff["closed_max_correction_N"]:.3f}&{fmt(recovery)}'+r'\\\lastline']
    (r.OUT/'feedforward_rows.tex').write_text('\n'.join(rows),encoding='utf-8')
    summary={'parameters':[asdict(c) for c in cases],'metrics':metrics,'feedforward_feedback':ff,
             'antiwindup_peak_height_m':{k:float(ds[k][:,2].max()) for k in ['limit_plain','limit_conditional']}}
    (r.OUT/'revision_results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    # MATLAB独立实现只共享显式列出的参数；不读取Python计算结果。
    manifest=json.loads((r.OUT/'progressive_results.json').read_text(encoding='utf-8'))['parameters']
    manifest += [asdict(replace(r.Case('feedforward_open'),h0=3,r=3,drag=1.6,kp=0,ki=0,kd=0,wind=-.4,wind_at=2,t_end=12))]
    manifest += [asdict(c) for c in cases]
    manifest += [asdict(r.Case('intro_performance',drag=0,kp=4,kd=2.4,wind=-.4,wind_at=0,t_end=12)),
                 asdict(r.Case('gain4',kp=4,kd=3,t_end=24))]
    (r.ROOT/'experiment_cases.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary
