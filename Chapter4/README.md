# 第四章：模型预测控制与固定翼航迹跟踪

沿第三章优化得到的交错双柱S形名义航迹，比较开环执行与闭环MPC。状态为x,y,z,V,gamma,chi,phi，输入为a,omega_gamma,omega_phi。预测与仿真均采用单步显式欧拉，步长0.18秒。

## Python一键运行

进入Python目录，安装依赖后运行：

```text
python -m pip install -r requirements.txt
python RunMe.py
```

依赖NumPy、SciPy、OSQP、Matplotlib、Pillow和pypdf；实测Python 3.12、OSQP 1.1.3。结果写入Python/results。

## MATLAB一键运行

从[CasADi官网](https://web.casadi.org/get/)下载对应平台的MATLAB工具包，将含+casadi的目录加入MATLAB路径，或用CASADI_MATLAB_PATH指定该目录。进入MATLAB目录，执行RunMe。实测MATLAB R2021b、CasADi 3.7.2及其OSQP插件；不需要Optimization Toolbox，不调用Python。结果写入MATLAB/results。

## 五组实验与控制流程

open_loop为名义输入开环执行；mpc5、mpc20、mpc40分别采用5、20、40步预测；ideal20在无扰动且初始状态准确时核对模型与程序连接。主实验为mpc20。reference目录包含名义状态与输入，可独立运行本章，不需要先运行第三章。

第一次在名义运动处线性化。后续周期将旧输入修正移位，末段补零修正并限幅，从新状态反馈按非线性模型重建完整展开运动，再建立一次QP。速度代价在名义状态处作一阶近似，目标始终是同一时刻的名义航迹。每次只执行首段输入。QP没有障碍约束，窗口末端自由，状态与输入幅值仍受限制。

初始y、z、chi偏差为5米、3米、3度；8.10至12.06秒叠加[0,1,0.3]米每秒位置变化率，转弯变化率乘1.06。角度内部均用弧度。两版分别保存状态、输入、跟踪指标和QP残差，并生成航迹、误差、输入图。

## 复核

两版全部运行后，在Chapter4目录执行python CheckResults.py。脚本从CSV独立重算非线性对象的运动递推、输入与状态范围、初值和误差指标，再比较两种实现。允许状态差1e-5、输入差1e-6，默认实验实测差约1e-12。核验结果保存在validation.json。

计时包含本周期矩阵构建、求解与检查。MATLAB第一次加载求解器有额外开销，本次首周期约459毫秒；后续周期明显缩短。此处记录桌面离线实验运行时间。几何间隔单独检查：短时域mpc5未保持8米余量，open_loop进入原始障碍，mpc20与mpc40保持本次要求。控制器没有隐式加入避障功能。
