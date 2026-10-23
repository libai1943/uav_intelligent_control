"""第一章：侧风下的地面航迹、同一路径的两种时间安排。
运行 python RunMe.py；仅需 numpy 与 matplotlib。
坐标 x 向东、y 向北；所有速度均在同一坐标系表示。
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
fontnames={f.name for f in font_manager.fontManager.ttflist}
cn=next((n for n in ['Microsoft YaHei','Noto Sans CJK SC','SimHei'] if n in fontnames),'DejaVu Sans')
plt.rcParams.update({'font.family':cn,'font.size':10,'axes.unicode_minus':False,'pdf.fonttype':42})
AIR_NORTH=10.0
WINDS_EAST=[0.0,3.0,5.0]  # 修改此处观察侧风影响。
T=10.0

def finish(fig,name):
    fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(OUT/(name+'.png'),dpi=220,bbox_inches='tight');plt.close(fig)

def main():
    t=np.linspace(0,T,101);fig,axs=plt.subplots(1,2,figsize=(8.2,4),layout='constrained')
    rows=[]
    for wind in WINDS_EAST:
        vg=np.array([wind,AIR_NORTH]);pos=t[:,None]*vg
        np.savetxt(OUT/f'wind_{wind:g}.csv',np.c_[t,pos],delimiter=',',header='time_s,east_m,north_m',comments='',fmt='%.12g')
        axs[0].plot(pos[:,0],pos[:,1],label=f'向东风速 {wind:g} m/s')
        rows.append({'wind_east_m_s':wind,'groundspeed_m_s':float(np.linalg.norm(vg)),
                     'course_east_of_north_deg':float(np.degrees(np.arctan2(wind,AIR_NORTH)))})
    axs[0].set(xlabel='向东位置 / m',ylabel='向北位置 / m',title='机头始终朝北');axs[0].set_aspect('equal');axs[0].legend(fontsize=8)
    for start,delta,color,label in [([0,0],[0,10],'#217D8A','空速'),([0,10],[3,0],'#A86E36','风速'),([0,0],[3,10],'#333333','地速')]:
        axs[1].annotate('',xy=np.array(start)+delta,xytext=start,arrowprops=dict(arrowstyle='->',color=color,lw=1.4))
        mid=np.array(start)+np.array(delta)*.5;axs[1].text(mid[0]+.25,mid[1],label,color=color)
    axs[1].set(xlim=(-1,5),ylim=(-1,12),xlabel='向东速度 / (m/s)',ylabel='向北速度 / (m/s)');axs[1].set_aspect('equal')
    for ax in axs:ax.grid(alpha=.2)
    finish(fig,'wind_groundtrack')
    # 两组位置都落在同一Bezier曲线上，仅改变时间参数。
    q=t/T
    def curve(a):return np.c_[3*(1-a)**2*a+9*(1-a)*a*a+5.7*a**3,5.4*(1-a)**2*a-2.1*(1-a)*a*a+1.4*a**3]
    A=curve(q);B=curve(2*q-q*q)
    np.savetxt(OUT/'time_schedules.csv',np.c_[t,A,B],delimiter=',',header='time_s,x_A,y_A,x_B,y_B',comments='',fmt='%.12g')
    fig,axs=plt.subplots(2,1,figsize=(7,4.9),layout='constrained')
    for ax,data,name in zip(axs,[A,B],['甲：时间参数均匀变化','乙：时间参数先快后慢']):
        ax.plot(A[:,0],A[:,1],color='#bbb');ax.scatter(data[::20,0],data[::20,1],s=15,color='#217D8A')
        for i,point in enumerate(data[::20]):ax.annotate(f'{i*2}s',point,xytext=(0,6),textcoords='offset points',fontsize=9)
        ax.set(title=name,xlabel='东向位置（相对尺度）',ylabel='北向位置（相对尺度）');ax.set_aspect('equal');ax.grid(alpha=.15)
    finish(fig,'path_time_schedules')
    for row in rows:
        assert abs(row['groundspeed_m_s']-np.hypot(row['wind_east_m_s'],AIR_NORTH))<1e-12
    assert np.allclose(A[[0,-1]],B[[0,-1]])
    (OUT/'checks.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print('第一章实验完成：',OUT)

if __name__=='__main__':main()
