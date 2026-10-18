"""第二章：多旋翼竖直通道 PID 教学实验。

运行 python RunMe.py，生成 results 下的 PDF/PNG、逐时刻 CSV 和核验 JSON。
仅使用 NumPy、Matplotlib；采样反馈与对象均用单步显式欧拉推进，并以步长减半作数值对照。
这是一维、近水平、推力瞬时执行的教学模型，不是可上传飞控的程序。
"""
from pathlib import Path
from dataclasses import dataclass, asdict, replace
import csv
import json
import math
import platform
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
OUT.mkdir(exist_ok=True)
M, G = 1.6, 9.81
C = ['#217D8A', '#A86E36', '#444444', '#865979']
LS = ['-', '--', '-.', ':']


def setup_style():
    names = {f.name for f in font_manager.fontManager.ttflist}
    chinese = next((n for n in ['Microsoft YaHei', 'Noto Sans CJK SC',
                                'SimHei', 'Arial Unicode MS'] if n in names), None)
    # 无中文字体时仍能完成数值实验；建议按 README 安装 Noto Sans CJK SC。
    if chinese is None:
        print('提示：未找到中文字体，图中文字可能缺字；可安装 Noto Sans CJK SC 后重跑。')
    roman = 'Times New Roman' if 'Times New Roman' in names else 'DejaVu Serif'
    plt.rcParams.update({'font.family': [chinese or 'DejaVu Sans'],
                         'font.size': 10, 'axes.labelsize': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.unicode_minus': False, 'axes.linewidth': .65,
                         'pdf.fonttype': 42, 'savefig.dpi': 220,
                         'mathtext.fontset': 'custom', 'mathtext.rm': roman,
                         'mathtext.it': roman+':italic', 'mathtext.bf': roman+':bold',
                         'mathtext.fallback': 'stix', 'lines.linewidth': 1.8})


@dataclass
class Case:
    name: str
    kp: float = 4.0
    ki: float = 0.0
    kd: float = 5.5
    h0: float = 2.0
    r: float = 3.0
    v0: float = 0.0
    m: float = M
    m0: float = M
    drag: float = 0.0  # 竖直线性阻力系数，单位 N*s/m；0 为无阻尼对照。
    t_end: float = 24.0
    tmax: float = 2.2 * M * G
    wind: float = 0.0
    wind_at: float = 6.0
    antiwindup: bool = False
    cascade: bool = False
    smooth: bool = False
    kh: float = .8
    kv: float = 5.0
    kiv: float = 2.0
    vmax: float = 1.0


def reference(t, cfg):
    if cfg.smooth:
        # 初始参考及其一阶导数与 h0=3, v0=0 相容。
        return 3 + .6 * (1 - math.cos(.45*t)), .27 * math.sin(.45*t)
    return cfg.r, 0.0


def signals(t, y, cfg):
    h, v, integ = y
    r, rd = reference(t, cfg)
    e = r - h
    if cfg.cascade:
        vref = float(np.clip(rd + cfg.kh*e, -cfg.vmax, cfg.vmax))
        error_i = vref-v
        raw = cfg.m0*G + cfg.kv*error_i + cfg.kiv*integ
    else:
        vref = rd
        error_i = e
        # D 对反馈速度作用，参考阶跃不会直接进入微分项。
        raw = cfg.m0*G + cfg.kp*e + cfg.ki*integ - cfg.kd*v
    thrust = float(np.clip(raw, 0.0, cfg.tmax))
    di = error_i
    if cfg.antiwindup:
        if (raw >= cfg.tmax and error_i > 0) or (raw <= 0 and error_i < 0):
            di = 0.0
    return r, rd, e, vref, raw, thrust, di


def simulate(cfg, dt=.002):
    n = int(round(cfg.t_end/dt))
    times = np.arange(n+1)*dt
    y = np.array([cfg.h0, cfg.v0, 0.0], dtype=float)
    data = np.empty((n+1, 12))
    for k, t in enumerate(times):
        r, rd, e, vref, raw, thrust, di = signals(t, y, cfg)
        # 每个采样周期计算一次控制并保持；积分状态在周期末更新。
        d = cfg.wind if t >= cfg.wind_at-1e-10 else 0.0
        data[k] = (t, r, y[0], y[1], e, y[2], raw, thrust, d, vref, rd, di)
        if k == n:
            break
        acceleration = (thrust-cfg.m*G-cfg.drag*y[1]+d)/cfg.m
        y += dt*np.array([y[1], acceleration, di])

    return data


def save_series(name, d):
    header = 'time_s,reference_m,height_m,velocity_m_s,error_m,integral,raw_thrust_N,thrust_N,disturbance_N,velocity_reference_m_s,reference_derivative_m_s,integral_derivative'
    np.savetxt(OUT/(name+'.csv'), d, delimiter=',', header=header, comments='', fmt='%.10g')


def step_metrics(d, h0, target):
    t, h = d[:,0], d[:,2]
    delta = target-h0
    q = (h-h0)/delta
    def crossing(level):
        ix = np.flatnonzero(q >= level)
        if not len(ix): return None
        j = int(ix[0])
        if j == 0: return float(t[0])
        return float(t[j-1]+(level-q[j-1])*(t[j]-t[j-1])/(q[j]-q[j-1]))
    a, b = crossing(.1), crossing(.9)
    bad = np.flatnonzero(np.abs(h-target) > .02*abs(delta))
    ts = 0. if not len(bad) else (float(t[bad[-1]+1]) if bad[-1] < len(t)-1 else None)
    return {'rise_10_90_s': None if a is None or b is None else b-a,
            'overshoot_percent': float(max(0.,np.max(q)-1)*100),
            'settling_2percent_observed_s': ts,
            'tail_mean_error_m': float(np.mean(d[t >= t[-1]-2,4])),
            'peak_thrust_N': float(np.max(d[:,7]))}


def finish(fig, name):
    for ax in fig.axes:
        ax.grid(True, color='#dddddd', lw=.45, alpha=.75)
        ax.tick_params(labelsize=9)
        for tick in ax.get_xticklabels()+ax.get_yticklabels():
            tick.set_fontfamily(plt.rcParams['mathtext.rm'])
    fig.savefig(OUT/(name+'.pdf'), bbox_inches='tight')
    fig.savefig(OUT/(name+'.png'), bbox_inches='tight')
    plt.close(fig)


def compare_plot(series, labels, name, title=None, controls=True):
    fig, axs = plt.subplots(2 if controls else 1, 1, figsize=(7.0,5.0 if controls else 3.3),
                            sharex=True, layout='constrained')
    axs = np.atleast_1d(axs)
    d0 = series[0]
    axs[0].plot(d0[:,0],d0[:,1],color='#888888',lw=1.25,ls=':',label='参考高度')
    for i,(d,label) in enumerate(zip(series, labels)):
        axs[0].plot(d[:,0],d[:,2],C[i],ls=LS[i],label=label)
        if controls: axs[1].plot(d[:,0],d[:,7],C[i],ls=LS[i],label=label)
    axs[0].set_ylabel('高度 $h$ / m')
    axs[0].legend(ncol=len(labels)+1,fontsize=9,frameon=False,
                  loc='lower center',bbox_to_anchor=(.5,1.01))
    if title: axs[0].set_title(title,fontsize=11)
    if controls:
        axs[1].set_ylabel('总推力 $T$ / N')
        axs[1].axhline(M*G,color='#aaaaaa',lw=.8,ls=':')
    axs[-1].set_xlabel('时间 $t$ / s')
    finish(fig,name)


def main():
    setup_style()
    cases = [
        Case('p_only', kd=0, t_end=14),
        Case('pd', t_end=14),
        Case('pd_wind', wind=-2, t_end=40),
        Case('pid_wind', ki=1.2, wind=-2, t_end=40),
        Case('gain2', kp=2, kd=3, t_end=24),
        Case('gain4', kp=4, kd=3, t_end=24),
        Case('gain8', kp=8, kd=3, t_end=24),
        Case('windup', kp=6, ki=2, kd=4, r=8, tmax=1.25*M*G, t_end=40),
        Case('antiwindup', kp=6, ki=2, kd=4, r=8, tmax=1.25*M*G, t_end=40, antiwindup=True),
        Case('cascade', cascade=True, smooth=True, h0=3, wind=-2, t_end=30, antiwindup=True),
    ]
    results = {}
    checks = {}
    for cfg in cases:
        d = simulate(cfg)
        fine = simulate(cfg, dt=.001)
        difference = float(np.max(np.abs(d[:,2]-fine[::2,2])))
        assert np.isfinite(d).all()
        assert difference < .025, (cfg.name,difference)
        assert d[:,7].min() >= -1e-10 and d[:,7].max() <= cfg.tmax+1e-10
        results[cfg.name]=d
        checks[cfg.name]={'step_halving_max_height_difference_m':difference}
        save_series(cfg.name,d)


    assert abs(np.mean(results['pd_wind'][-401:,4])-.5)<1e-5
    assert abs(np.mean(results['pid_wind'][-401:,4]))<.005
    checks['pd_disturbance_theory_error_m']=.5
    checks['pd_disturbance_numeric_tail_error_m']=float(np.mean(results['pd_wind'][-401:,4]))
    checks['pid_disturbance_numeric_tail_error_m']=float(np.mean(results['pid_wind'][-401:,4]))
    compare_plot([results['p_only'],results['pd']],['P 控制','PD 控制'],'exp1_p_pd')
    compare_plot([results['pd_wind'],results['pid_wind']],['PD 控制','PID 控制'],'exp2_disturbance')
    compare_plot([results['gain2'],results['gain4'],results['gain8']],
                 ['$K_p=2$','$K_p=4$','$K_p=8$'],'exp3_gains')
    # 过渡性能图：同一条真实响应上标示时间和幅值。
    d=results['gain4']; met=step_metrics(d,2,3)
    fig,ax=plt.subplots(figsize=(7,3.9),layout='constrained')
    ax.fill_between([0,9],2.98,3.02,color='#dbeaea',label='参考高度的 ±0.02 m 带')
    ax.plot(d[:,0],d[:,2],color=C[0]); ax.axhline(3,color='#888',ls=':',lw=1)
    ax.axhline(2.1,color='#aaa',ls=':',lw=.7);ax.axhline(2.9,color='#aaa',ls=':',lw=.7)
    for level, tag in [(2.1,'10%'),(2.9,'90%')]:
        j=np.flatnonzero(d[:,2]>=level)[0]
        ax.plot([d[j,0],d[j,0]],[2,level],color='#777',lw=.7,ls='--')
        ax.text(d[j,0]+.06,level-.075,tag,fontsize=9)
    t10=d[np.flatnonzero(d[:,2]>=2.1)[0],0]
    t90=d[np.flatnonzero(d[:,2]>=2.9)[0],0]
    ax.annotate('',xy=(t10,2.19),xytext=(t90,2.19),
                arrowprops={'arrowstyle':'<->','color':C[1]})
    ax.text((t10+t90)/2,2.23,'上升时间 $t_r$',ha='center',fontsize=9,color=C[1])
    j=int(np.argmax(d[:,2])); tp=d[j,0];hp=d[j,2]
    ax.annotate('峰值与超调',xy=(tp,hp),xytext=(tp+1,hp+.07),
                arrowprops={'arrowstyle':'->','color':C[1]},fontsize=9)
    ts=met['settling_2percent_observed_s']
    ax.axvline(ts,color=C[1],ls='--',lw=1)
    ax.text(ts+.1,2.4,'调节时间 $t_s$',fontsize=9,color=C[1])
    ax.set(xlim=(0,9),ylim=(1.98,1.13+2.15),xlabel='时间 $t$ / s',ylabel='高度 $h$ / m')
    ax.legend(loc='lower right',frameon=False,fontsize=9)
    finish(fig,'performance')
    fig,axs=plt.subplots(3,1,figsize=(7,6.6),sharex=True,layout='constrained')
    axs[0].axhline(8,color='#888',lw=1,ls=':',label='参考高度')
    for i,(key,label) in enumerate([('windup','不限制积分累积'),('antiwindup','条件积分')]):
        d=results[key]
        axs[0].plot(d[:,0],d[:,2],C[i],ls=LS[i],label=label)
        axs[1].plot(d[:,0],2*d[:,5],C[i],ls=LS[i])
        axs[2].plot(d[:,0],d[:,7],C[i],ls=LS[i])
    axs[0].set_ylabel('高度 $h$ / m');axs[0].legend(frameon=False,ncol=3,fontsize=9,
                     loc='lower center',bbox_to_anchor=(.5,1.01))
    axs[1].set_ylabel('积分补偿 $K_i I$ / N');axs[2].set_ylabel('总推力 $T$ / N')
    axs[2].axhline(1.25*M*G,color='#777',ls=':',lw=1)
    axs[2].set_xlabel('时间 $t$ / s');finish(fig,'exp4_windup')
    d=results['cascade']
    fig,axs=plt.subplots(3,1,figsize=(7,6.3),sharex=True,layout='constrained')
    for ax,cols,labels in [(axs[0],[1,2],['参考高度','实际高度']),
                           (axs[1],[9,3],['参考竖直速度','实际竖直速度'])]:
        for i,(col,label) in enumerate(zip(cols,labels)):
            ax.plot(d[:,0],d[:,col],C[i],ls=LS[i],label=label)
        ax.legend(frameon=False,ncol=2,fontsize=9,loc='lower center',bbox_to_anchor=(.5,1.01))
    axs[2].plot(d[:,0],d[:,7],color=C[0])
    axs[0].set_ylabel('高度 / m');axs[1].set_ylabel('竖直速度 / (m/s)')
    axs[2].set_ylabel('总推力 $T$ / N');axs[2].set_xlabel('时间 $t$ / s')
    finish(fig,'exp5_cascade')
    metrics={c.name:step_metrics(results[c.name],c.h0,c.r) for c in cases if not c.smooth}
    metrics['cascade']={'height_rmse_m':float(np.sqrt(np.mean(d[:,4]**2))),
                       'maximum_absolute_error_m':float(np.max(np.abs(d[:,4]))),
                       'peak_thrust_N':float(np.max(d[:,7]))}
    info={'parameters':[asdict(c) for c in cases],'integration':'sampled feedback and single-step explicit Euler',
          'dt_s':.002,'refined_dt_s':.001,'g_m_s2':G,
          'python':platform.python_version(),'numpy':np.__version__,
          'matplotlib':matplotlib.__version__, 'checks':checks,'metrics':metrics}
    (OUT/'results.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    with (OUT/'metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['case','rise_10_90_s','overshoot_percent','settling_2percent_observed_s','tail_mean_error_m','peak_thrust_N'])
        for name,mm in metrics.items():
            if name!='cascade':writer.writerow([name,*mm.values()])
    from intro_figures import generate
    intro = generate(OUT, results, simulate, Case, save_series, finish)
    from progressive import generate as generate_progressive
    progressive = generate_progressive()
    print(json.dumps({'checks':checks,'metrics':metrics,'intro_checks':intro,'progressive_checks':progressive},ensure_ascii=False,indent=2))
    print('完成：',OUT)


if __name__ == '__main__':
    main()
