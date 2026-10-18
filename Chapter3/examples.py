"""Two independently reproducible examples used before the planning experiments."""
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
from model import motion
from figures import style,finish,BLUE,WARM,GRAY

def function(x):
    return np.tanh(x)+.2*x*np.exp(-.1*x*x)+.3*np.sin(2.5*x)

def derivative(x):
    return 1/np.cosh(x)**2+.2*(1-.2*x*x)*np.exp(-.1*x*x)+.75*np.cos(2.5*x)

def make_examples(out):
    style();out=Path(out);tables=out/'tables';tables.mkdir(parents=True,exist_ok=True)
    book=out.parent.parent/'chapter3_figures'
    dt=.01;x=np.array([0,0,100,20,0,0,0.],float)
    tt=np.arange(201)*dt;xx=[x.copy()]
    uu=np.c_[.4*tt,.015*tt,.02*tt]
    for u in uu[:-1]:
        x=x+dt*motion(x,u);xx.append(x.copy())
    xx=np.array(xx)
    assert np.max(np.abs(xx[:,6]-.01*(tt**2-dt*tt)))<1e-12
    np.savetxt(out/'forward_example.csv',np.c_[tt,uu,xx],delimiter=',',
               header='t,a,omega_gamma,omega_phi,x,y,z,V,gamma,chi,phi',comments='')
    fig,axes=plt.subplots(2,3,figsize=(10,5.3),sharex=True)
    labels=[r'速率变化率 $a$ / (m/s$^2$)',r'航迹倾角变化率 $\omega_\gamma$ / (°/s)',r'倾侧角变化率 $\omega_\phi$ / (°/s)',
            r'速率 $V$ / (m/s)',r'航迹倾角 $\gamma$ / °',r'倾侧角 $\phi$ / °']
    values=[uu[:,0],np.rad2deg(uu[:,1]),np.rad2deg(uu[:,2]),xx[:,3],np.rad2deg(xx[:,4]),np.rad2deg(xx[:,6])]
    for ax,y,label in zip(axes.flat,values,labels):
        ax.plot(tt,y,color=BLUE,lw=1.8);ax.set_ylabel(label);ax.grid(alpha=.15)
    for ax in axes[1]:ax.set_xlabel('时间 $t$ / s')
    fig.tight_layout();finish(fig,out,'forward_example')
    tex=[r'\begin{table}[!htbp]\centering\small',r'\caption{时变输入前向模拟的部分结果（长度单位：米；角度单位：度）}\label{tab:fwforward}',
         r'\begin{tabularx}{\textwidth}{|Y|Y|Y|Y|Y|Y|}\hline\hline',
         r'\tablehead\textbf{时刻 $t$/s}&\textbf{位置 $x$}&\textbf{位置 $y$}&\textbf{高度 $z$}&\textbf{方位角 $\chi$}&\textbf{倾侧角 $\phi$}\\\hline']
    for t in [0,.5,1,1.5,2]:
        z=xx[round(t/dt)];tex.append(f'{t:.1f}&{z[0]:.3f}&{z[1]:.3f}&{z[2]:.3f}&{np.rad2deg(z[5]):.3f}&{np.rad2deg(z[6]):.3f}'+r'\\\hline')
    tex[-1]=tex[-1].replace(r'\hline',r'\lastline');tex +=[r'\end{tabularx}\end{table}']
    (tables/'forward_table.tex').write_text('\n'.join(tex),encoding='utf-8')
    if book.is_dir(): (book/'forward_table.tex').write_text('\n'.join(tex),encoding='utf-8')
    starts=[-6,-3.2,-1,-.2,.05,.8,1.8,2.3,3.14,3.5,4.2,5.5];results=[];traces=[]
    for start in starts:
        x=start;trace=[x];count=0
        while abs(derivative(x))>=1e-4 and count<500:
            x-=.1*derivative(x);trace.append(x);count+=1
        assert abs(derivative(x))<1e-4
        results.append(dict(initial=start,solution=x,cost=float(function(x)),iterations=count));traces.append(np.array(trace))
    (out/'gradient_example.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    grid=np.linspace(-6.5,6,1000);axes[0].plot(grid,function(grid),color=GRAY,lw=1.6)
    for idx,c,ls in [(0,BLUE,'-'),(3,WARM,'--'),(9,'#635b80',':')]:
        tr=traces[idx];axes[0].plot(tr[::max(1,len(tr)//10)],function(tr[::max(1,len(tr)//10)]),'o',ms=3,color=c)
        axes[0].plot(tr[0],function(tr[0]),'o',ms=7,mfc='white',mec=c)
        axes[0].plot(tr[-1],function(tr[-1]),'*',ms=10,color=c)
        axes[1].plot(np.arange(len(tr)),tr,color=c,ls=ls,label=f'初始解 {starts[idx]:g}')
    axes[0].set(xlabel=r'变量 $\xi$',ylabel=r'代价 $f(\xi)$');axes[1].set(xlabel='迭代次数',ylabel=r'当前解 $\xi$')
    axes[1].legend(frameon=False)
    for ax in axes:ax.grid(alpha=.15)
    fig.tight_layout();finish(fig,out,'gradient_example')
    tex=[r'\begin{table}[!htbp]\centering\small',r'\caption{同一函数在不同初始解下的计算结果}\label{tab:fwgradient}',
         r'\begin{tabularx}{\textwidth}{|Y|Y|Y|Y|}\hline\hline',
         r'\tablehead\textbf{初始解}&\textbf{收敛位置}&\textbf{终止代价}&\textbf{迭代次数}\\\hline']
    for r in results:tex.append(f"{r['initial']:g}&{r['solution']:.4f}&{r['cost']:.4f}&{r['iterations']}"+r'\\\hline')
    tex[-1]=tex[-1].replace(r'\hline',r'\lastline');tex +=[r'\end{tabularx}\end{table}']
    (tables/'gradient_table.tex').write_text('\n'.join(tex),encoding='utf-8')
    if book.is_dir(): (book/'gradient_table.tex').write_text('\n'.join(tex),encoding='utf-8')
