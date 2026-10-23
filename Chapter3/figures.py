"""Reproducible figures for the textbook. Chinese labels, vector PDF, equal 3-D units."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Circle,Rectangle,Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pathlib import Path

BLUE,WARM,GRAY='#217d8a','#a86e36','#50565b'

def style():
    for p in ['C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/msyhbd.ttc']:
        if Path(p).exists():font_manager.fontManager.addfont(p)
    available={f.name for f in font_manager.fontManager.ttflist}
    families=[f for f in ['Microsoft YaHei','Noto Sans CJK SC','DejaVu Sans'] if f in available]
    plt.rcParams.update({'font.family':families,
        'font.size':11,'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,
        'mathtext.fontset':'stix','pdf.fonttype':42,'savefig.facecolor':'white'})

def finish(fig,out,name):
    fig.savefig(out/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(out/(name+'.png'),dpi=190,bbox_inches='tight');plt.close(fig)
    if name.endswith('_3d'):
        # Remove only the blank plot canvas; PDF paths and embedded fonts stay vector.
        from PIL import Image
        from pypdf import PdfReader,PdfWriter
        from io import BytesIO
        im=Image.open(out/(name+'.png')).convert('RGB');a=np.asarray(im)
        ys,xs=np.where(np.min(a,axis=2)<240)
        l=max(0,int(xs.min())-12);rr=min(im.width,int(xs.max())+13)
        top=max(0,int(ys.min())-12);bottom=min(im.height,int(ys.max())+13)
        reader=PdfReader(BytesIO((out/(name+'.pdf')).read_bytes()));page=reader.pages[0]
        w,h=float(page.mediabox.width),float(page.mediabox.height)
        page.mediabox.lower_left=(l/im.width*w,(1-bottom/im.height)*h)
        page.mediabox.upper_right=(rr/im.width*w,(1-top/im.height)*h)
        page.cropbox=page.mediabox
        writer=PdfWriter();writer.add_page(page)
        with (out/(name+'.pdf')).open('wb') as f:writer.write(f)
        im.crop((l,top,rr,bottom)).save(out/(name+'.png'))

def faces(box):
    v=np.array([[box[d+3] if q>>d&1 else box[d] for d in range(3)] for q in range(8)])
    return [v[f] for f in ([0,1,3,2],[4,5,7,6],[0,1,5,4],[2,3,7,6],[0,2,6,4],[1,3,7,5])]

def obstacles2d(ax,obs):
    for x,y,r in obs:
        ax.add_patch(Circle((x,y),r,fc='.86',ec='.4',lw=.8))
        ax.add_patch(Circle((x,y),r+8,fill=False,ec='.4',ls=':',lw=1))

def plan3d(r,out,name):
    fig=plt.figure(figsize=(10,4.9));ax=fig.add_axes([-.015,-.04,.79,1.05],projection='3d',proj_type='ortho')
    t,z=np.meshgrid(np.linspace(0,2*np.pi,64),[60,185])
    for cx,cy,rad in r['columns']:
        ax.plot_surface(cx+rad*np.cos(t),cy+rad*np.sin(t),z,color='.6',alpha=.22,shade=False,lw=0)
        for h in [60,185]:ax.plot(cx+rad*np.cos(t[0]),cy+rad*np.sin(t[0]),h,color='.5',lw=.65)
    for b in r['boxes']:
        ax.add_collection3d(Poly3DCollection(faces(b),facecolors=(.13,.49,.54,.025),edgecolors=(.13,.49,.54,.45),linewidths=.5))
    ax.plot(*r['raw'].T,color='.5',lw=.9)
    ax.plot(*r['initial_X'][:,:3].T,color=WARM,ls='--',lw=1.6)
    ax.plot(*r['X'][:,:3].T,color=BLUE,lw=2.5)
    ax.scatter(*r['X'][0,:3],c=BLUE,s=35);ax.scatter(*r['X'][-1,:3],c=BLUE,marker='*',s=80)
    ax.set(xlim=(-20,640),ylim=(-220,220),zlim=(60,185),xlabel='位置 $x$ / m',ylabel='位置 $y$ / m',zlabel='高度 $z$ / m')
    ax.set_box_aspect((660,440,125),zoom=1.15);ax.view_init(elev=32,azim=-62)
    ax.set_xticks([0,200,400,600]);ax.set_yticks([-200,0,200]);ax.set_zticks([80,120,160])
    for a in [ax.xaxis,ax.yaxis,ax.zaxis]:a.pane.fill=False
    hs=[Line2D([],[],color='.5',label='三维A*搜索算法\n生成的空间折线'),Line2D([],[],color=WARM,ls='--',label='初始解对应的航迹'),
        Line2D([],[],color=BLUE,lw=2.5,label='优化航迹')]
    if len(r['boxes']):hs.append(Patch(fc=BLUE,alpha=.2,label='安全走廊碎片'))
    fig.legend(handles=hs,loc='center left',bbox_to_anchor=(.82,.52),ncol=1,
               frameon=False,labelspacing=1.4,handlelength=2.1,fontsize=10)
    finish(fig,out,name)

def plot_all(results,out):
    style()
    for key in ('two_north','two_corridor','four_corridor','five_corridor'):
        if key in results:plan3d(results[key],out,key+'_3d')
    if all(k in results for k in ['two_north','two_south']):
        fig,ax=plt.subplots(figsize=(10,4.6));obstacles2d(ax,results['two_north']['columns'])
        if 'two_straight' in results:
            ax.plot(*results['two_straight']['initial_X'][:,:2].T,':',color='.4',lw=1.4,label='直连初始解（不可行）')
        for name,col,label in [('two_north',BLUE,'北侧初始解'),('two_south',WARM,'南侧初始解')]:
            r=results[name];ax.plot(*r['initial_X'][:,:2].T,'--',color=col,lw=1.3,label=label)
            ax.plot(*r['X'][:,:2].T,color=col,lw=2.4,label=label[:2]+'优化结果')
        ax.set(xlabel='位置 $x$ / m',ylabel='位置 $y$ / m',xlim=(-10,610),ylim=(-220,220))
        ax.set_aspect('equal');ax.grid(alpha=.16);ax.legend(ncol=1,frameon=False,loc='center left',bbox_to_anchor=(1,.5))
        fig.subplots_adjust(right=.72);finish(fig,out,'route_classes')
        fig,axs=plt.subplots(1,2,figsize=(10.5,3.8))
        for name,col,ls,label in [('two_straight',GRAY,':','直连初始解'),('two_north',BLUE,'-','北侧初始解'),('two_south',WARM,'--','南侧初始解')]:
            if name not in results:continue
            h=results[name]['history'];i=np.arange(1,len(h)+1)
            axs[0].plot(i,h[:,0],color=col,ls=ls,label=label)
            axs[1].semilogy(i,np.maximum(h[:,1],1e-12),color=col,ls=ls,label=label)
        for a,l in zip(axs,['离散代价 $J_N$','IPOPT原始约束不可行度']):
            a.set(xlabel='迭代次数',ylabel=l);a.grid(alpha=.15)
        axs[0].legend(frameon=False);fig.tight_layout();finish(fig,out,'convergence_compare')
    if 'four_corridor' in results:
        r=results['four_corridor'];fig,ax=plt.subplots(figsize=(10,4.8))
        for b in r['boxes']:
            ax.add_patch(Rectangle(b[:2],b[3]-b[0],b[4]-b[1],fc=BLUE,ec='none',alpha=.035))
            ax.add_patch(Rectangle(b[:2],b[3]-b[0],b[4]-b[1],fill=False,ec=BLUE,alpha=.4,lw=.6))
        obstacles2d(ax,r['columns']);ax.plot(*r['X'][:,:2].T,color=BLUE,lw=2.2,label='走廊内优化')
        if 'four_direct' in results:ax.plot(*results['four_direct']['X'][:,:2].T,'--',color=WARM,lw=1.6,label='直接距离约束优化')
        ax.plot(*r['initial_X'][:,:2].T,':',color=GRAY,lw=1.2,label='初始解')
        ax.set(xlabel='位置 $x$ / m',ylabel='位置 $y$ / m',xlim=(-15,620),ylim=(-180,180));ax.set_aspect('equal');ax.grid(alpha=.12)
        ax.legend(ncol=1,frameon=False,loc='center left',bbox_to_anchor=(1,.5))
        fig.subplots_adjust(right=.72);finish(fig,out,'corridor_top')
        X,U,t=r['X'],r['U'],r['time']
        fig,axes=plt.subplots(2,2,figsize=(10,5.6),sharex=True)
        for ax,j,label,bd in zip(axes.flat,[3,4,5,6],
            [r'速率 $V$ / (m/s)',r'航迹倾角 $\gamma$ / °',r'航迹方位角 $\chi$ / °',r'倾侧角 $\phi$ / °'],
            [(15,25),(-.2,.2),(-.9,.9),(-.6,.6)]):
            factor=1 if j==3 else 180/np.pi
            ax.plot(t,X[:,j]*factor,color=BLUE,lw=1.8);ax.set_ylabel(label);ax.grid(alpha=.15)
            for bound in bd:ax.axhline(bound*factor,color='.5',ls=':',lw=.8)
        for ax in axes[-1]:ax.set_xlabel('时间 $t$ / s')
        fig.tight_layout();finish(fig,out,'states')
        fig,axes=plt.subplots(1,3,figsize=(10,3.5),sharex=True)
        for ax,j,label,bound in zip(axes,range(3),
            [r'速率变化率 $a$ / (m/s$^2$)',r'航迹倾角变化率 $\omega_\gamma$ / (°/s)',r'倾侧角变化率 $\omega_\phi$ / (°/s)'],[2,.08,.4]):
            factor=1 if j==0 else 180/np.pi
            ax.step(t,np.r_[U[:,j],U[-1,j]]*factor,where='post',color=BLUE,lw=1.5)
            for sign in [-1,1]:ax.axhline(sign*bound*factor,color='.5',ls=':',lw=.8)
            ax.set(xlabel='时间 $t$ / s',ylabel=label);ax.grid(alpha=.15)
        fig.tight_layout();finish(fig,out,'inputs')
    if 'five_corridor' in results:
        r=results['five_corridor'];fig,axes=plt.subplots(1,2,figsize=(10,3.7),gridspec_kw={'width_ratios':[1.35,1]})
        obstacles2d(axes[0],r['columns'])
        axes[0].plot(*r['X'][:,:2].T,color=BLUE,lw=2)
        axes[0].set(xlabel='位置 $x$ / m',ylabel='位置 $y$ / m');axes[0].set_aspect('equal')
        axes[1].plot(r['time'],r['X'][:,2],color=BLUE,lw=2)
        axes[1].set(xlabel='时间 $t$ / s',ylabel='高度 $z$ / m')
        for ax in axes:ax.grid(alpha=.15)
        fig.tight_layout();finish(fig,out,'five_views')
    if all(k in results for k in ['four_grid100','four_corridor']):
        a,b=results['four_grid100'],results['four_corridor'];fig,axes=plt.subplots(1,2,figsize=(10,3.7))
        obstacles2d(axes[0],b['columns'])
        for r,col,ls in [(a,WARM,'--'),(b,BLUE,'-')]:
            axes[0].plot(*r['X'][:,:2].T,color=col,ls=ls,label=f"{r['intervals']}个区间")
        axes[0].set(xlabel='位置 $x$ / m',ylabel='位置 $y$ / m');axes[0].set_aspect('equal');axes[0].legend(frameon=False)
        interp=np.column_stack([np.interp(b['time'],a['time'],a['X'][:,j]) for j in range(3)])
        delta=np.linalg.norm(interp-b['X'][:,:3],axis=1)
        axes[1].plot(b['time'],delta,color=BLUE);axes[1].set(xlabel='时间 $t$ / s',ylabel='两组离散航迹的位置差 / m')
        np.savetxt(out/'grid_position_difference.csv',np.c_[b['time'],delta],delimiter=',',header='t,position_difference_m',comments='')
        for ax in axes:ax.grid(alpha=.15)
        fig.tight_layout();finish(fig,out,'grid_comparison')
    m=np.array([2,4,10,50,100]);fig,ax=plt.subplots(figsize=(8.8,3.7))
    ax.plot(m,201*m,'o-',color=WARM,label='距离避障：$201M$ 条')
    ax.axhline(1206,color=BLUE,label=r'廊内边界：$6\times201=1206$ 个标量边界')
    ax.set(xlabel='障碍物数量 $M$',ylabel='避障约束或边界数量',xlim=(0,102));ax.grid(alpha=.16);ax.legend(frameon=False);fig.tight_layout();finish(fig,out,'constraint_count')
