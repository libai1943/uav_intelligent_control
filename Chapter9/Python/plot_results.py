"""Rebuild each figure from recorded numerical results (one axes per figure)."""
from pathlib import Path
import csv,json,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager


def setup():
    fonts={f.name for f in font_manager.fontManager.ttflist}
    candidates=['Microsoft YaHei','Noto Sans CJK SC','Noto Sans CJK JP','SimHei','Arial Unicode MS']
    chosen=next((x for x in candidates if x in fonts),'DejaVu Sans')
    plt.rcParams.update({'font.family':chosen,'font.size':10,'axes.unicode_minus':False,
                         'pdf.fonttype':3,'ps.fonttype':3,'axes.labelsize':10,
                         'xtick.labelsize':9,'ytick.labelsize':9,'legend.fontsize':9})

def read_dict(path):
    with open(path,encoding='utf-8') as f:return list(csv.DictReader(f))

def finish(fig,ax,out,name):
    ax.grid(True,alpha=.22)
    if hasattr(ax,'zaxis'):
        ax.set_position([.02,.02,.86,.94]);ax.set_xlabel('');ax.set_ylabel('');ax.set_zlabel('')
        ax.set_yticks([-2,0,2]);ax.set_zticks([1.5,2.5,3.5])
        ax.text2D(.48,.08,'x / m',transform=ax.transAxes,fontsize=10)
        ax.text2D(1.03,.08,'y / m',transform=ax.transAxes,fontsize=10)
        ax.text2D(1.02,.72,'z / m',transform=ax.transAxes,fontsize=10)
    else:fig.tight_layout(pad=.7)
    fig.savefig(out/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(out/(name+'.png'),dpi=180,bbox_inches='tight');plt.close(fig)

def make_all(output):
    setup();out=Path(output);figdir=out/'figures';figdir.mkdir(exist_ok=True)
    meta=json.loads((out/'configuration.json').read_text());seeds=meta['training_seeds']
    # Same fixed validation races at checkpoints; curves are not final-test data.
    fig,ax=plt.subplots(figsize=(6.6,2.9))
    for mode,label in [('fixed','固定对手 PPO'),('league','历史对手 PPO')]:
        values=[]
        for seed in seeds:
            rr=read_dict(out/f'training_{mode}_{seed}.csv')
            rr=[r for r in rr if np.isfinite(float(r['validation_score']))]
            xx=np.array([float(r['iteration']) for r in rr]);values.append([float(r['validation_score']) for r in rr])
        yy=np.array(values);mu=yy.mean(0);sd=yy.std(0,ddof=1) if len(seeds)>1 else np.zeros_like(mu)
        ax.errorbar(xx,mu,yerr=sd,errorevery=max(1,len(xx)//10),capsize=2,lw=1.5,label=label)
    ax.set(xlabel='策略更新批次',ylabel='验证得分 J',ylim=(-1.05,1.05));ax.legend(loc='lower right')
    finish(fig,ax,figdir,'training_score')
    fig,ax=plt.subplots(figsize=(6.6,2.7))
    for mode,label in [('fixed','固定对手 PPO'),('league','历史对手 PPO')]:
        values=[]
        for seed in seeds:
            rr=read_dict(out/f'training_{mode}_{seed}.csv');rr=[r for r in rr if np.isfinite(float(r['validation_violation']))]
            xx=np.array([float(r['iteration']) for r in rr]);values.append([float(r['validation_violation']) for r in rr])
        yy=np.array(values);ax.plot(xx,100*yy.mean(0),label=label,lw=1.5)
    ax.set(xlabel='策略更新批次',ylabel='验证违规率 / %',ylim=(0,100));ax.legend()
    finish(fig,ax,figdir,'training_violation')
    # Actual representative trajectory chosen by the documented deterministic rule.
    tr=np.loadtxt(out/'trajectory_example.csv',delimiter=',',skiprows=1)
    gates=np.array(meta['gates']);dt=meta['config']['dt']
    fig,ax=plt.subplots(figsize=(6.6,2.8))
    ax.plot(tr[:,2],tr[:,3],label='学习策略 A',lw=1.6)
    ax.plot(tr[:,5],tr[:,6],label='快速规则对手 B',lw=1.5,ls='--')
    for j,g in enumerate(gates):
        ax.plot([g[0],g[0]],[g[1]-g[3]/2,g[1]+g[3]/2],lw=3)
        ax.text(g[0],g[1]+g[3]/2+.12,f'门{j+1}',ha='center',fontsize=9)
    ax.scatter([tr[0,2],tr[0,5]],[tr[0,3],tr[0,6]],marker='o',s=20)
    ax.set(xlabel='纵向位置 x / m',ylabel='横向位置 y / m',xlim=(-2.5,52),ylim=(-3.1,4.2))
    ax.legend(loc='lower right');finish(fig,ax,figdir,'trajectory_xy')
    fig=plt.figure(figsize=(6.6,3.3));ax=fig.add_subplot(111,projection='3d')
    ax.plot(tr[:,2],tr[:,3],tr[:,4],label='学习策略 A',lw=1.6)
    ax.plot(tr[:,5],tr[:,6],tr[:,7],label='快速规则对手 B',lw=1.5,ls='--')
    for g in gates:
        yy=g[1]+np.array([-1,1,1,-1,-1])*g[3]/2
        zz=g[2]+np.array([-1,-1,1,1,-1])*g[4]/2
        ax.plot(np.full(5,g[0]),yy,zz,lw=1.1)
    ax.set(xlabel='x / m',ylabel='y / m',zlabel='z / m');ax.set_box_aspect((4,1.3,1.2));ax.view_init(20,-65);ax.legend(loc='upper left')
    finish(fig,ax,figdir,'trajectory_xyz')
    fig,ax=plt.subplots(figsize=(6.6,2.8))
    ax.plot(tr[:,1],tr[:,2]-tr[:,5],lw=1.5)
    ax.axhline(0,lw=.8,ls=':')
    ax.set(xlabel='时间 t / s',ylabel='纵向领先量 x_A − x_B / m');finish(fig,ax,figdir,'relative_lead')
    fig,ax=plt.subplots(figsize=(6.6,2.8))
    ax.plot(tr[:,1],tr[:,8],lw=1.5,label='A 实际纵向速度')
    ax.plot(tr[:,1],tr[:,11],lw=1.5,ls='--',label='B 实际纵向速度')
    ax.plot(tr[:,1],4.5+2*tr[:,16],ls=':',lw=1.1,label='A 策略参考速度')
    ax.set(xlabel='时间 t / s',ylabel='纵向速度 / (m/s)');ax.legend();finish(fig,ax,figdir,'speed_response')
    fig,ax=plt.subplots(figsize=(6.6,2.7))
    dist=np.linalg.norm(tr[:,2:5]-tr[:,5:8],axis=1)
    ax.plot(tr[:,1],dist,lw=1.5,label='节点间距')
    ax.axhline(meta['config']['separation'],lw=1.,ls='--',label='间隔违规阈值')
    ax.set(xlabel='时间 t / s',ylabel='两机中心距离 / m');ax.legend();finish(fig,ax,figdir,'separation')
    # An actual failed race, not a manufactured illustrative curve.
    if (out/'trajectory_failure.csv').exists():
        f=np.loadtxt(out/'trajectory_failure.csv',delimiter=',',skiprows=1)
        fig,ax=plt.subplots(figsize=(6.6,2.7))
        ax.plot(f[:,1],np.linalg.norm(f[:,2:5]-f[:,5:8],axis=1),lw=1.5,label='失败回合的实际间距')
        ax.axhline(meta['config']['separation'],ls='--',lw=1.,label='间隔违规阈值')
        ax.set(xlabel='时间 t / s',ylabel='两机中心距离 / m');ax.legend();finish(fig,ax,figdir,'failure_separation')
    # Original vs mirrored geometry: no post-test fine tuning.
    summary={r['method']:r for r in read_dict(out/'summary.csv')}
    fig,ax=plt.subplots(figsize=(6.6,2.8))
    labels=['固定对手\n原赛道','固定对手\n镜像赛道','历史对手\n原赛道','历史对手\n镜像赛道']
    methods=['fixed_holdout','fixed_mirror','league_holdout','league_mirror']
    vals=[100*float(summary[m]['violation']) for m in methods]
    bars=ax.bar(np.arange(4),vals)
    for b,v in zip(bars,vals):ax.text(b.get_x()+b.get_width()/2,v+1,f'{v:.1f}',ha='center',fontsize=9)
    ax.set(xticks=np.arange(4),xticklabels=labels,ylabel='自身违规率 / %',ylim=(0,100));finish(fig,ax,figdir,'generalization')
    export_tables(out)
    return figdir

def export_tables(out):
    out=Path(out);summary={r['method']:r for r in read_dict(out/'summary.csv')}
    texdir=out/'latex_tables';texdir.mkdir(exist_ok=True)
    names=[('initial','未训练随机策略'),('rule_center','匀速定线规则'),('rule_reactive','响应式规则'),('rule_fast','快速规则'),('rule_max','最大速度规则'),('fixed_sampled','固定对手PPO'),('league_sampled','历史对手PPO')]
    rows=[]
    for key,label in names:
        r=summary[key];ft='---' if not r['finish_time'] else f"{float(r['finish_time']):.2f}"
        rows.append(f"{label} & {100*float(r['win']):.2f} & {100*float(r['violation']):.2f} & {float(r['score']):.3f} & {ft} \\\\ \\hline")
    rows[-1]=rows[-1].replace('\\hline','\\Xhline{0.7pt}')
    (texdir/'main_results.tex').write_text('\\def\\ChNineMainResults{%\n'+'\n'.join(rows)+'%\n}\n',encoding='utf-8')
    rows=[]
    for key,label in [('fixed_sampled','固定对手：随机执行'),('fixed_mean','固定对手：均值执行'),('league_sampled','历史对手：随机执行'),('league_mean','历史对手：均值执行'),('league_blind','历史对手：屏蔽对手运动'),('fixed_holdout','固定对手：原赛道新对手'),('fixed_mirror','固定对手：镜像赛道新对手'),('league_holdout','历史对手：原赛道新对手'),('league_mirror','历史对手：镜像赛道新对手')]:
        r=summary[key];rows.append(f"{label} & {100*float(r['win']):.2f} & {100*float(r['violation']):.2f} & {float(r['score']):.3f} \\\\ \\hline")
    rows[-1]=rows[-1].replace('\\hline','\\Xhline{0.7pt}')
    (texdir/'additional_results.tex').write_text('\\def\\ChNineAdditionalResults{%\n'+'\n'.join(rows)+'%\n}\n',encoding='utf-8')
    # Per training seed: report dispersion, never just the strongest seed.
    rs=read_dict(out/'metrics_by_seed.csv');rows=[]
    for seed in sorted({int(r['seed']) for r in rs}):
        rr={r['method']:r for r in rs if int(r['seed'])==seed}
        rows.append(f"{seed} & {100*float(rr['fixed_sampled']['win']):.2f} & {100*float(rr['fixed_sampled']['violation']):.2f} & {100*float(rr['league_sampled']['win']):.2f} & {100*float(rr['league_sampled']['violation']):.2f} \\\\ \\hline")
    rows[-1]=rows[-1].replace('\\hline','\\Xhline{0.7pt}')
    (texdir/'seed_results.tex').write_text('\\def\\ChNineSeedResults{%\n'+'\n'.join(rows)+'%\n}\n',encoding='utf-8')

def sync_latex(output,root=None):
    output=Path(output);root=Path(root or Path(__file__).resolve().parents[1]);dst=root/'latex'/'chapter9'/'figures'/'experiments';dst.mkdir(parents=True,exist_ok=True)
    for p in (output/'figures').glob('*.pdf'):shutil.copy2(p,dst/p.name)
    td=root/'latex'/'chapter9'/'tables';td.mkdir(exist_ok=True)
    for p in (output/'latex_tables').glob('*.tex'):shutil.copy2(p,td/p.name)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output',nargs='?',default=str(Path(__file__).resolve().parent/'outputs'));p.add_argument('--sync',action='store_true')
    a=p.parse_args();make_all(a.output)
    if a.sync:sync_latex(a.output)
