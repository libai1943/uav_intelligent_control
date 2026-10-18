# 第三章：固定翼无人机开环航迹规划

更新日期：2026-10-19

## 运行
  python -m pip install -r requirements.txt
  python RunMe.py
Python 3.10+；实测 Windows、Python 3.12.14、CasADi 3.7.2/IPOPT。
默认执行8组规划和两个入门例子，保存results_kinematic/中的JSON、CSV、NPZ、PDF和PNG。
单例：python RunMe.py --case four_corridor
已有结果重画：python RunMe.py --plots-only
不画图：python RunMe.py --no-plots
需要Microsoft YaHei或Noto Sans CJK SC字体。代码无飞控接口，不访问网络。

## 模型依据及范围
IROS 2021论文“Embedded Hardware Appropriate Fast 3D Trajectory Optimization for
Fixed Wing Aerial Vehicles by Leveraging Hidden Convex Structures”，第II-B节式(1)、(2)：
https://arxiv.org/pdf/2109.12609
DOI: 10.1109/IROS51168.2021.9636337
该论文采用forward acceleration、flight-path angle rate、bank angle rate作为输入。
本例采用相同运动学关系，竖直坐标改为向上，heading符号改为chi。
采用自己的单步Euler全联立/IPOPT和AABB算例，不是复现论文的交替最小化求解算法。
模型背景：Owen、Beard、McLain，Implementing Dubins Airplane Paths on Fixed-wing UAVs，2014。
https://www.et.byu.edu/~beard/papers/preprints/BeardMcLain__.pdf
该规划模型依赖较低层飞控的跟踪能力，不包含完整气动、发动机和姿态内环。
本例限定无风、忽略侧滑、较小爬升角的正常飞行。转向式为近水平协调转弯近似。
不同飞行任务会采用不同模型；此处不声称所有固定翼研究都采用同一个模型。

## 状态与输入（全部采用SI单位，角度为弧度）
x=[x,y,z,V,gamma,chi,phi]：位置、速率、航迹倾角、航迹方位角、倾侧角。
u=[a,omega_gamma,omega_phi]：速率变化率、航迹倾角变化率、倾侧角变化率。
xdot=V*cos(gamma)*cos(chi)；ydot=V*cos(gamma)*sin(chi)；zdot=V*sin(gamma)。
Vdot=a；gammadot=omega_gamma；chidot=g*tan(phi)/V；phidot=omega_phi。
a是切向加速度分量，并非总加速度大小或推力。输入是规划层等效指令。
不强制保持高度；竖直加速度为a*sin(gamma)+V*cos(gamma)*omega_gamma。

## 离散与求解
36秒、200个控制区间、201个状态点，dt=0.18秒。
每个区间只执行一次显式Euler更新：X[k+1]=X[k]+dt*f(X[k],U[k])。
没有区间内小步或RK4。重算输入也采用完全相同的单步更新。
7*(N+1)+3*N个标量决策量，起终14个状态分量固定。
代价为dt*sum(0.3*(a/2)^2+(omega_gamma/0.08)^2+(omega_phi/0.4)^2)。
这是机动变化率代价，不是真实能源消耗。
CasADi自动微分；选18个坐标用有限差分检查导数，误差要求<3e-5。
IPOPT主要容差1e-8，最多700次迭代；计时仅含优化调用。
时间不包含搜索、模型/导数构造、检查和绘图，不是实时性能保证。

## 完整初始解
三维26邻接A*搜索算法，检查每条连接线段；样条平滑后再次检查障碍。
按累计弧长近似均匀取点并分配到固定时间网格，形成位置时间序列。
由位置求导恢复V、gamma、chi，先处理chi的周期跳变。
phi=atan(V*chi_dot/g)，再求a=Vdot、omega_gamma=gammadot、omega_phi=phidot。
补齐所有状态和输入，修正起终边界与变量范围，并记录初始运动残差。
完整初始解不意味着全部约束已经满足。

## 八组实验
two_straight / two_north / two_south：双柱，同一任务的三种完整初始解。
two_corridor：双柱走廊；four_direct / four_corridor：四柱的距离/走廊对比。
five_corridor：五柱走廊；four_grid100：四柱走廊100区间。
本次8组均实际运行通过离散模型检查。非凸求解没有全局最优性保证。
examples.py还生成线性时变输入的前向计算与一维多极值梯度下降例子。

## 几何与检查
机体包络及安全间隔合计8米；距离约束节点另留3米。
走廊盒体整体距物理柱面至少8米，优化节点再距盒面3米。
速率内部边界收紧0.15 m/s，三个角度内部收紧0.02 rad。
20个走廊碎片，交界点用相邻盒交集；构造失败或交集空会明确报错。
accepted要求求解器成功且以下检查通过：
尺度化离散约束违反量<1e-6；节点重算位置差及终端位置差<1e-3 m；
终端速率/角度分量差<1e-5（SI）；状态与走廊边界违反量<1e-4；
相邻位置节点整段连线到柱面的间隔>=8 m。
终端位置、速率、航迹方向、倾侧角偏差分别保存，不混合量纲。
这些是离散模型内部一致性与几何检查，不检验连续积分精度，不是实机安全证明。
一阶Euler误差可累积；真实连续运动、气动包络和闭环跟踪另需验证。

## 结果文件
summary.json：本次参数、环境版本、场景及结果。
各算例/result.json：成功、迭代、时间、代价、残差及各项终端偏差。
data.npz：完整优化解、初始解、路径、走廊与迭代数据。
state.csv：t,x,y,z,V,gamma,chi,phi；control.csv：t,a,omega_gamma,omega_phi。
每行control在随后一个区间内保持；绘图将部分角度转换为度。
results_kinematic/tables/中的LaTeX表由已保存实算结果生成。
若教材目录中的chapter3_figures/已经存在，同时更新其中的同名表格。
