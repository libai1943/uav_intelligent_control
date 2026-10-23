第二章：独立Python与MATLAB实现

一、运行
Python：安装requirements.txt所列依赖，执行 python RunMe.py，结果写入results。
MATLAB：MATLAB R2021b或更新版本，在本目录执行 RunMe，结果写入results_matlab。
MATLAB实现只使用基础MATLAB函数，不需要Control System Toolbox，不调用Python。
experiment_cases.json是随源码提供的显式实验参数，不是Python计算结果。直接运行MATLAB无需先运行Python。

二、理论与代码
运动模型：m h''=T-mg-b v_z+d_z。
控制器：Tcmd=m0*g+Kp*(r-h)+Ki*I-Kd*v_z；级联结构另按正文给出的速度PI计算。
每周期先用已有I计算推力，再限幅、更新I及运动状态。
h和v_z同时使用旧时刻值作单步显式欧拉更新，dt=0.002 s。
原始数值实验默认理想状态反馈与瞬时推力执行。
条件积分在指令已超限且误差会加重超限时暂停积分，不改变实际推力上限。
0.002 s是教学程序设置，不是实机高度外环频率建议。

三、正文曲线的对应文件
height_step / performance_overview：章首参考阶跃和性能指标。
stage1_p：有阻尼与无阻尼P，包含高度、竖直速度和总推力。
stage2_bias：持续外力下Kp=4与Kp=8。
stage3_integral：P与PI，以及比例修正/积分补偿。
stage4_derivative：PI与PID。
stage5_cascade：高度、参考及实际速度、推力。
stage6_feedforward_feedback：同一重力前馈，有无反馈修正。
stage7_antiwindup：同一高度阶跃与推力上限，普通积分/条件积分。
stage8_cascade_comparison：改变内环、改变外环、单环PID/级联。
stage9_velocity_limit：初始高度1米，参考3米，观察速度限幅。
以上11组图形均有独立MATLAB实现。Python还保留exp开头的早期扩展图，不属于本版正文必需结果。
两种绘图工具的字体和标注位置可以不同，但数值案例一致。

四、复核
两个入口都运行后，执行 python CheckResults.py。
脚本检查19组CSV的形状和逐元素数值差（默认最大绝对差要求小于1e-7）。
其中feedforward_open在Python保留原来的时间/高度/速度三列接口，核验时映射到MATLAB同名数据的相应列。
JSON与CSV保存实际计算值。正文的参数调整和前馈反馈记录均来自这些结果。
数值容差仅用于两种实现的一致性核对，不表示真实飞行精度保证。

五、修改参数
Python主线：progressive.py中的cases；补充实验：revision_experiments.py中的cases。
MATLAB：experiment_cases.json中的同名案例参数。
Python重新运行时会根据当前Python案例定义重写experiment_cases.json，使其与Python设置对应；如需保留自行修改的MATLAB参数，应先另存一份。
不要同时修改多项条件后把全部响应差异归因于一个参数。
教材的数值表和文字按默认参数编写；修改参数后的输出不会自动改写教材正文。

本目录实现的是一维、近水平的教学模型，不包含真实飞控接口。
