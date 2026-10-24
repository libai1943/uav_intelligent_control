"""章首高度阶跃与性能指标图；由 RunMe.py 统一调用。

性能指标示例使用同一竖直通道模型，并记录步长减半的数值差异。
终值口径的超调/调节时间和参考口径分别记录，不混用。
"""
from dataclasses import asdict
import json
import math
import numpy as np
import matplotlib.pyplot as plt


def generate(out, cases, simulate, Case, save_series, finish):
    # 参考发生阶跃，飞行高度保持连续。使用已有无扰动响应。
    d = cases['gain4']
    fig, ax = plt.subplots(figsize=(7.2, 3.2), layout='constrained')
    ax.plot([-1.5, 0, 0, 9], [2, 2, 3, 3], '--', color='#555555',
            lw=1.25, label='参考高度 $r(t)$')
    ax.plot(np.r_[-1.5, d[:, 0]], np.r_[2, d[:, 2]], color='#217D8A',
            lw=1.9, label='实际高度 $h(t)$')
    ax.axvline(0, color='#bbbbbb', lw=.7, ls=':')
    ax.annotate('参考切换', xy=(0, 3), xytext=(.65, 3.19), fontsize=10,
                arrowprops={'arrowstyle':'->','color':'#555555','lw':.9})
    ax.text(-1.35, 2.13, '原高度保持', fontsize=9)
    ax.text(5.45, 2.83, '接近新高度并保持', fontsize=9)
    ax.set(xlim=(-1.5, 9), ylim=(1.94, 3.28), xlabel='时间 $t$ / s', ylabel='高度 / m')
    ax.legend(loc='lower right', frameon=False, fontsize=9)
    finish(fig, 'height_step')

    cfg = Case('intro_performance', kp=4, kd=2.4, ki=0,
               wind=-.4, wind_at=0, t_end=12)
    d = simulate(cfg)
    fine = simulate(cfg, dt=.001)
    t, h = d[:, 0], d[:, 2]
    h0, r = cfg.h0, cfg.r
    hf = r + cfg.wind/cfg.kp
    delta = hf-h0
    halving = float(np.max(np.abs(h-fine[::2, 2])))
    assert halving < .01

    assert d[:, 7].min() > 0 and d[:, 7].max() < cfg.tmax
    assert abs(h[-1]-hf) < 2e-4

    def crossing(level):
        j = int(np.flatnonzero(h >= level)[0])
        return float(t[j-1]+(level-h[j-1])*(t[j]-t[j-1])/(h[j]-h[j-1]))
    t10, t90 = crossing(h0+.1*delta), crossing(h0+.9*delta)
    peak_index=int(np.argmax(h))
    tp=float(t[peak_index]);hp=float(h[peak_index])
    tol = .02*delta
    bad = np.flatnonzero(np.abs(h-hf) > tol)
    ts = float(t[bad[-1]+1])


    save_series(cfg.name, d)

    fig, ax = plt.subplots(figsize=(7.4, 4.6), layout='constrained')
    ax.fill_between([0, 12], hf-tol, hf+tol, color='#DFECEC', zorder=0)
    ax.plot(t, h, color='#217D8A', lw=1.9)
    ax.axhline(r, color='#444444', lw=1, ls='--')
    ax.axhline(hf, color='#777777', lw=.9, ls=':')
    guide = dict(color='#999999', lw=.7, ls='--')
    for level, tx in [(h0+.1*delta, t10), (h0+.9*delta, t90)]:
        ax.plot([0, tx], [level, level], **guide)
        ax.plot([tx, tx], [1.87, level], **guide)
        ax.plot(tx, level, 'o', ms=3, color='#217D8A')
    ax.text(t10+.09, h0+.1*delta+.025, '10%', fontsize=9)
    ax.text(t90+.09, h0+.9*delta-.075, '90%', fontsize=9)
    arrows = {'arrowstyle':'<->','color':'#A86E36','lw':1,'mutation_scale':11}
    ax.annotate('', xy=(t10, 1.87), xytext=(t90, 1.87), arrowprops=arrows)
    ax.text((t10+t90)/2, 1.76, '上升时间 $t_r$', ha='center', fontsize=9, color='#8F5C2A')
    ax.plot([tp,tp], [h0,hp], **guide)
    ax.plot(tp, hp, 'o', color='#217D8A', ms=3)
    ax.text(tp+.08, 2.04, '峰值时间 $t_p$', fontsize=9)
    ax.text(tp-.4, hp+.09, r'峰值高度 $h_{\mathrm{peak}}$', fontsize=9)
    ax.plot([tp,3.65], [hp,hp], **guide)
    ax.annotate('', xy=(3.65,hf), xytext=(3.65,hp), arrowprops=arrows)
    ax.text(3.85, hp+.025, '超出终值\n的高度', fontsize=9, ha='left')
    ax.plot([ts,ts], [h0,hf+tol], color='#A86E36', lw=.9, ls='--')
    ax.text(ts+.13, 2.49, '调节时间 $t_s$', fontsize=9, color='#8F5C2A')
    ax.text(8.7, r+.045, '参考高度 $r_1$', fontsize=9)
    ax.text(8.5, hf-.09, r'高度终值 $h_\infty$', fontsize=9)
    ax.annotate('', xy=(11.2,hf), xytext=(11.2,r), arrowprops=arrows)
    ax.annotate(r'稳态误差 $e_{\mathrm{ss}}$', xy=(11.2,(hf+r)/2), xytext=(9.0,3.22),
                fontsize=9, arrowprops={'arrowstyle':'-','color':'#777777','lw':.8})
    ax.set(xlim=(0,12), ylim=(1.70,3.33), yticks=np.arange(2,3.21,.2),
           xlabel='时间 $t$ / s', ylabel='高度 $h$ / m')
    finish(fig,'performance_overview')
    info = {'parameters':asdict(cfg), 'terminal_height_m':hf,
            'steady_error_m':r-hf, 'rise_10_90_terminal_s':t90-t10,
            'first_peak_time_s':tp, 'peak_height_m':hp,
            'overshoot_terminal_percent':100*(hp-hf)/delta,
            'overshoot_reference_percent':100*max(0,hp-r)/(r-h0),
            'settling_terminal_2percent_observed_s':ts,
            'settling_reference_2percent_observed_s':None,
            'step_halving_max_height_difference_m':halving}
    (out/'intro_checks.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    return info
