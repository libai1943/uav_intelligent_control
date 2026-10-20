"""Publication figures drawn from saved computations, without synthetic curves."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from tracking import DT, COLUMNS, U_MAX

TEAL, WARM, GRAY = '#217D8A', '#A86E36', '#64717C'
font_path = Path('C:/Windows/Fonts/msyh.ttc')
if font_path.exists():
    font_manager.fontManager.addfont(str(font_path))
    chinese = font_manager.FontProperties(fname=str(font_path)).get_name()
else:
    chinese = 'Noto Sans CJK SC'
plt.rcParams.update({'font.family': [chinese, 'DejaVu Sans'],
                     'font.size': 10, 'axes.unicode_minus': False,
                     'mathtext.fontset': 'stix', 'pdf.fonttype': 42,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.linewidth': .65, 'lines.linewidth': 1.55,
                     'savefig.facecolor': 'white'})


def make_figures(out, xr, ur, runs):
    dest = out/'figures';dest.mkdir(exist_ok=True)
    loaded = {r['name']:np.load(out/(r['name']+'.npz')) for r in runs}
    times = np.arange(len(loaded['mpc20']['X']))*DT
    def save(fig, name):
        fig.savefig(dest/(name+'.pdf'), bbox_inches='tight', pad_inches=.035)
        fig.savefig(dest/(name+'.png'), dpi=190, bbox_inches='tight', pad_inches=.035)
        if name == 'flight_3d':
            # Trim only the empty outer page margins of this generated plot.
            from PIL import Image, ImageChops
            from pypdf import PdfReader, PdfWriter
            png=dest/(name+'.png')
            im=Image.open(png).convert('RGB')
            box=ImageChops.difference(im,Image.new('RGB',im.size,'white')).getbbox()
            if box:
                left,top,right,bottom=box
                left=max(0,left-7);top=max(0,top-7)
                right=min(im.width,right+7);bottom=min(im.height,bottom+7)
                reader=PdfReader(dest/(name+'.pdf'));page=reader.pages[0]
                w,h=float(page.mediabox.width),float(page.mediabox.height)
                page.cropbox.lower_left=(left/im.width*w,(im.height-bottom)/im.height*h)
                page.cropbox.upper_right=(right/im.width*w,(im.height-top)/im.height*h)
                writer=PdfWriter();writer.add_page(page)
                with (dest/(name+'.pdf')).open('wb') as stream: writer.write(stream)
                im.crop((left,top,right,bottom)).save(png)
        plt.close(fig)
    def finish(ax):
        ax.grid(alpha=.2, lw=.5)
        ax.tick_params(labelsize=9)
    def shade(ax):
        ax.axvspan(45*DT,67*DT,color=WARM,alpha=.10,lw=0)
    # Equal spatial units: vertical cylinders are obstacle exclusion volumes.
    fig=plt.figure(figsize=(7.1,3.6))
    ax=fig.add_subplot(111,projection='3d')
    theta=np.linspace(0,2*np.pi,50)
    for cx,cy,r in COLUMNS:
        th,zz=np.meshgrid(theta,[80,180])
        ax.plot_surface(cx+r*np.cos(th),cy+r*np.sin(th),zz,color=GRAY,
                        alpha=.13,linewidth=0,shade=False)
        ax.plot(cx+r*np.cos(theta),cy+r*np.sin(theta),np.full(50,180),color=GRAY,lw=.6)
    for name,label,color,ls in [('reference','名义航迹', '#222222','--'),
                                ('open_loop','开环执行',WARM,'-'),
                                ('mpc20','MPC 跟踪',TEAL,'-')]:
        X=loaded['mpc20']['reference'] if name=='reference' else loaded[name]['X']
        ax.plot(*X[:,:3].T,label=label,color=color,ls=ls,lw=1.5)
    ax.set(xlim=(0,610),ylim=(-100,230),zlim=(80,180),
           xlabel='位置 $x$ / m',ylabel='位置 $y$ / m',zlabel='高度 $z$ / m')
    ax.set_box_aspect((610,330,100))
    ax.view_init(elev=29,azim=-65)
    ax.legend(loc='upper right',bbox_to_anchor=(1.2,.94),frameon=False,fontsize=9)
    ax.tick_params(labelsize=8,pad=1)
    fig.subplots_adjust(left=0,right=.83,bottom=.01,top=.99)
    save(fig,'flight_3d')
    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(7.1,2.65),gridspec_kw={'width_ratios':[1.65,1]})
    for cx,cy,r in COLUMNS:
        ax1.add_patch(plt.Circle((cx,cy),r,facecolor='#e1e4e6',edgecolor=GRAY,lw=.65))
    for name,label,color,ls in [('reference','名义航迹','#222222','--'),
                                ('open_loop','开环执行',WARM,'-'),('mpc20','MPC 跟踪',TEAL,'-')]:
        X=loaded['mpc20']['reference'] if name=='reference' else loaded[name]['X']
        ax1.plot(X[:,0],X[:,1],color=color,ls=ls,label=label)
        ax2.plot(times,X[:,2],color=color,ls=ls)
    ax1.set_aspect('equal',adjustable='box')
    ax1.set_xlim(-10,615);ax1.set_ylim(-90,210)
    ax1.set(xlabel='位置 $x$ / m',ylabel='位置 $y$ / m',title='(a) 俯视航迹')
    ax2.set(xlabel='时间 $t$ / s',ylabel='高度 $z$ / m',title='(b) 高度随时间变化')
    ax1.legend(frameon=False,fontsize=8,loc='upper left')
    shade(ax2)
    finish(ax1);finish(ax2)
    fig.tight_layout(w_pad=1.4)
    save(fig,'flight_views')
    fig,axes=plt.subplots(1,2,figsize=(7.1,2.9))
    for name,label,color,ls in [('open_loop','开环执行',WARM,'-'),('mpc20','MPC，$H=20$',TEAL,'-')]:
        d=loaded[name]
        axes[0].plot(times,np.linalg.norm(d['reference'][:,:3]-d['X'][:,:3],axis=1),
                     label=label,color=color,ls=ls)
    for name,label,color,ls in [('mpc5','$H=5$，0.9 s',GRAY,':'),
                              ('mpc20','$H=20$，3.6 s',TEAL,'-'),
                              ('mpc40','$H=40$，7.2 s',WARM,'--')]:
        d=loaded[name]
        axes[1].plot(times,np.linalg.norm(d['reference'][:,:3]-d['X'][:,:3],axis=1),
                     label=label,color=color,ls=ls)
    for i,ax in enumerate(axes):
        shade(ax);finish(ax)
        ax.set(xlabel='时间 $t$ / s',ylabel='位置误差的模 / m',
               title=['(a) 开环与闭环','(b) 不同预测长度'][i])
        ax.legend(frameon=False,fontsize=9)
    fig.tight_layout()
    save(fig,'errors')
    fig,axes=plt.subplots(3,1,figsize=(7.1,4.45),sharex=True)
    names=['速率变化率 $a$ / (m/s$^2$)',
           '航迹倾角变化率\n$\\omega_\\gamma$ / (rad/s)',
           '倾侧角变化率\n$\\omega_\\phi$ / (rad/s)']
    for j,ax in enumerate(axes):
        ax.step(times[:-1],ur[:len(times)-1,j],where='post',color='#333333',ls='--',label='名义输入')
        ax.step(times[:-1],loaded['mpc20']['U'][:,j],where='post',color=TEAL,label='MPC 输入')
        ax.axhline(U_MAX[j],color=WARM,lw=.8,ls=':')
        ax.axhline(-U_MAX[j],color=WARM,lw=.8,ls=':')
        ax.set_ylabel(names[j],fontsize=9)
        ax.set_ylim(-1.12*U_MAX[j],1.12*U_MAX[j])
        shade(ax);finish(ax)
    axes[0].legend(frameon=False,fontsize=9,ncol=2,loc='upper right')
    axes[-1].set_xlabel('时间 $t$ / s')
    fig.tight_layout(h_pad=.45)
    save(fig,'inputs')
    # Tangent approximation for one term in the same flight model.
    fig,ax=plt.subplots(figsize=(5.5,2.4))
    angle=np.linspace(-.75,.75,201)
    ax.plot(angle,20*np.sin(angle),color=TEAL,label=r'原关系 $20\sin\chi$')
    ax.plot(angle,20*angle,color=WARM,ls='--',label=r'一阶近似 $20\chi$')
    ax.plot([0],[0],'o',color='#333333',ms=4)
    ax.annotate('展开点',xy=(0,0),xytext=(.13,-4),
                arrowprops={'arrowstyle':'->','color':'#333333'},fontsize=9)
    ax.set(xlabel='航迹方位角 $\\chi$ / rad',ylabel='横向速度 $\\dot y$ / (m/s)')
    finish(ax);ax.legend(frameon=False,fontsize=9)
    fig.tight_layout()
    save(fig,'linearization')
    # Real snapshot: old prediction, measured state and newly optimized prediction.
    snap=json.loads((out/'mpc20.json').read_text())['snapshots']
    old=np.array(snap['45']['prediction']);new=np.array(snap['46']['prediction'])
    fig,axes=plt.subplots(1,2,figsize=(7.1,2.7))
    for ax,j,label in [(axes[0],1,'横向位置误差 $e_y$ / m'),(axes[1],2,'高度误差 $e_z$ / m')]:
        eold=xr[45:45+len(old),j]-old[:,j]
        enew=xr[46:46+len(new),j]-new[:,j]
        ax.plot((45+np.arange(len(old)))*DT,eold,color=GRAY,ls='--',label='上次预测误差')
        ax.plot((46+np.arange(len(new)))*DT,enew,color=TEAL,label='本次预测误差')
        ax.axhline(0,color='#222222',ls=':',lw=.8)
        ax.scatter([46*DT],[enew[0]],color=TEAL,s=24,zorder=5,label='新反馈误差')
        ax.set(xlabel='绝对时间 $t$ / s',ylabel=label)
        finish(ax)
    axes[0].legend(frameon=False,fontsize=8)
    fig.tight_layout()
    save(fig,'prediction_updates')
    # Tables and a numeric illustration are derived from saved results.
    table=[]
    for name,label in [('open_loop','开环执行'),('mpc5','$H=5$'),
                       ('mpc20','$H=20$'),('mpc40','$H=40$')]:
        r=next(r for r in runs if r['name']==name);m=r['metrics']
        table.append(f"{label} & {m['position_rmse_m']:.2f} & "
                     f"{m['position_final_m']:.2f} & {m['min_segment_clearance_m']:.2f} "
                     r"\\ \hline")
    table[-1]=table[-1].replace(r'\hline',r'\lastline')
    (out/'performance_rows.tex').write_text('\n'.join(table),encoding='utf-8')
    (out/'performance_table.tex').write_text(
        '\\begin{tabularx}{\\linewidth}{|L{2.5cm}|Y|Y|Y|}\\hline\\hline\n'
        '\\tablehead\\textbf{执行方式}&\\textbf{位置均方根误差/m}&'
        '\\textbf{最终位置误差/m}&\\textbf{最小障碍间隔/m}\\\\\\hline\n'
        +'\n'.join(table)+'\n\\end{tabularx}',encoding='utf-8')
    table=[]
    for name in ['mpc5','mpc20','mpc40']:
        r=next(r for r in runs if r['name']==name);m=r['metrics']
        table.append(f"{r['horizon_steps']} & {m['cycle_median_ms']:.2f} & "
                     f"{m['cycle_p95_ms']:.2f} & {m['cycle_max_ms']:.2f} "+r"\\ \hline")
    table[-1]=table[-1].replace(r'\hline',r'\lastline')
    (out/'timing_rows.tex').write_text('\n'.join(table),encoding='utf-8')
    (out/'timing_table.tex').write_text(
        '\\begin{tabularx}{\\linewidth}{|L{2.4cm}|Y|Y|Y|}\\hline\\hline\n'
        '\\tablehead\\textbf{预测步数}&\\textbf{中位耗时/ms}&'
        '\\textbf{95\\%分位耗时/ms}&\\textbf{最大耗时/ms}\\\\\\hline\n'
        +'\n'.join(table)+'\n\\end{tabularx}',encoding='utf-8')
    # Figures stay alongside the program; textbook copies made only when its directory exists.
    book_figs=out.parent.parent/'chapter4_figures'
    if book_figs.is_dir():
        import shutil
        for p in dest.glob('*.pdf'):
            shutil.copy2(p,book_figs/p.name)

