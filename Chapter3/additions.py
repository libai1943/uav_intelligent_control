"""First-solve/obstacle-count and alternating-column teaching figures."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from figures import style,finish,BLUE,WARM

def plot_additions(results,out):
    style()
    keys=['two_north','crowd10_direct','crowd20_direct']
    book=out.parent.parent/'chapter3_figures'
    if all(k in results for k in keys):
        rr=[results[k] for k in keys];counts=[len(r['columns']) for r in rr]
        fig,ax=plt.subplots(1,2,figsize=(10,3.7))
        ax[0].bar(range(3),[r['nonlinear_obstacle_constraints'] for r in rr],color=BLUE,width=.55)
        ax[0].set(xticks=range(3),xticklabels=counts,xlabel='障碍物数量',ylabel='非线性避障不等式数量')
        for j,r in enumerate(rr):ax[0].text(j,r['nonlinear_obstacle_constraints']+70,str(r['nonlinear_obstacle_constraints']),ha='center',fontsize=10)
        ax[0].set_ylim(0,4600)
        for j,r in enumerate(rr):
            values=np.array(r['solve_times_s'])*1000
            ax[1].scatter(np.full(len(values),j),values,s=18,color='.55',zorder=3)
            ax[1].plot([j-.22,j+.22],[r['seconds']*1000]*2,color=BLUE,lw=3)
        ax[1].set(xticks=range(3),xticklabels=counts,xlabel='障碍物数量',ylabel='求解耗时 / ms')
        for a in ax:a.grid(axis='y',alpha=.18)
        fig.tight_layout();finish(fig,out,'obstacle_benchmark')
        rows=[]
        for r,m in zip(rr,counts):
            rows.append(f"{m}&{r['nonlinear_obstacle_constraints']}&{r['iterations']}&{r['seconds']*1000:.1f}&{r['objective']:.5f}"+r"\\\hline")
        text=r"\begin{table}[!htbp]\centering\small"+'\n'+r"\caption{仅增加远处障碍的求解对照}\label{tab:fwobstaclebenchmark}"+'\n'
        text+=r"\begin{tabularx}{\textwidth}{|Y|Y|Y|Y|Y|}\hline\hline"+'\n'+r"\tablehead 障碍物数&避障不等式数&迭代次数&耗时中位数/ms&离散代价\\\hline"+'\n'
        text+='\n'.join(rows)+'\n'+r"\end{tabularx}\end{table}"+'\n'
        # Store LaTeX beside results; copy to manuscript when its directory exists.
        (out/'obstacle_benchmark_table.tex').write_text(text,encoding='utf-8')
        diff=max(np.max(abs(r['X']-rr[0]['X'])) for r in rr)
        trend='随障碍数量增加而上升' if all(rr[i+1]['seconds']>rr[i]['seconds'] for i in range(2)) else '随障碍数量变化，呈现出不同的计算开销'
        analysis=f"本次三组结果的代价均约为{rr[0]['objective']:.5f}，航迹位置与状态也非常接近。求解耗时中位数分别为{rr[0]['seconds']*1000:.1f}、{rr[1]['seconds']*1000:.1f}和{rr[2]['seconds']*1000:.1f}毫秒，{trend}。这说明，几何上不影响本次航迹的约束，仍然会增加数值求解的处理工作。耗时还受到迭代次数、线性方程求解和运行环境影响，因此应结合重复记录判断，而不能只按障碍数量推算时间。\n"
        (out/'obstacle_benchmark_analysis.tex').write_text(analysis,encoding='utf-8')
        if book.is_dir():
            (book/'obstacle_benchmark_table.tex').write_text(text,encoding='utf-8');(book/'obstacle_benchmark_analysis.tex').write_text(analysis,encoding='utf-8')
    if 'slalom_direct' in results:
        r=results['slalom_direct'];x=r['X'];t=r['time']
        fig=plt.figure(figsize=(10.6,5.1));gs=fig.add_gridspec(2,2,width_ratios=[1.55,1],wspace=.33,hspace=.42)
        ax=fig.add_subplot(gs[:,0]);ax.axhspan(-220,220,color='#f6f6f3',zorder=0)
        for cx,cy,rad in r['columns']:
            ax.add_patch(Circle((cx,cy),rad,fc='.84',ec='.4',lw=.8));ax.add_patch(Circle((cx,cy),rad+8,fill=False,ec='.4',ls=':',lw=.9))
        ax.plot(r['initial_X'][:,0],r['initial_X'][:,1],'--',color=WARM,label='初始航迹')
        ax.plot(x[:,0],x[:,1],color=BLUE,lw=2,label='优化航迹')
        for k in [35,100,165]:ax.annotate('',xy=x[k+2,:2],xytext=x[k-2,:2],arrowprops=dict(arrowstyle='->',color=BLUE,lw=1.4))
        ax.scatter(x[[0,-1],0],x[[0,-1],1],s=16,color=BLUE)
        ax.axhline(-220,color='.4',lw=.7);ax.axhline(220,color='.4',lw=.7)
        ax.set(xlim=(-5,605),ylim=(-225,225),xlabel='位置 $x$ / m',ylabel='位置 $y$ / m');ax.set_aspect('equal');ax.legend(frameon=False,loc='upper center',fontsize=10);ax.grid(alpha=.12)
        a=fig.add_subplot(gs[0,1]);a.plot(t,x[:,2],color=BLUE);a.set(xlabel='时间 / s',ylabel='高度 $z$ / m');a.grid(alpha=.15)
        a=fig.add_subplot(gs[1,1]);a.plot(t,np.rad2deg(x[:,5]),color=BLUE,label='航迹方位角');a.plot(t,np.rad2deg(x[:,6]),color=WARM,ls='--',label='倾侧角');a.set(xlabel='时间 / s',ylabel='角度 / 度');a.grid(alpha=.15);a.legend(frameon=False,fontsize=9)
        finish(fig,out,'slalom_views')
        fig,ax=plt.subplots(2,2,figsize=(10,5.8));labels=['速率 / (m/s)','航迹倾角 / 度','航迹方位角 / 度','倾侧角 / 度']
        bounds=[[15,25],[-.2,.2],[-.9,.9],[-.6,.6]]
        for j,a in enumerate(ax.flat):
            factor=1 if j==0 else 180/np.pi;a.plot(t,x[:,j+3]*factor,color=BLUE)
            for b in bounds[j]:a.axhline(b*factor,color='.5',ls=':',lw=.8)
            a.set(xlabel='时间 / s',ylabel=labels[j]);a.grid(alpha=.15)
        fig.tight_layout();finish(fig,out,'slalom_states')
        fig,ax=plt.subplots(1,3,figsize=(10.5,3.1));labels=['加速度 / (m/s²)','航迹倾角变化率 / (度/s)','倾侧角变化率 / (度/s)']
        for j,a in enumerate(ax):
            fac=1 if j==0 else 180/np.pi;a.step(t,np.r_[r['U'][:,j],r['U'][-1,j]]*fac,where='post',color=BLUE)
            for b in [-1,1]:a.axhline(b*[2,.08,.4][j]*fac,color='.5',ls=':',lw=.8)
            a.set(xlabel='时间 / s',ylabel=labels[j]);a.grid(alpha=.15)
        fig.tight_layout();finish(fig,out,'slalom_inputs')
