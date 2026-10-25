# 第11章：运筹优化与指派调度

Python/RunMe.py 与 MATLAB/RunMe.m 分别独立运行全部装载、运输和调度对照，输出求解结果、独立枚举核查与时间表。Python 需要 NumPy、SciPy；MATLAB 优先调用可用的 Optimization Toolbox；未安装时，自动使用随附的两阶段单纯形与分支定界实现，仅需基础 MATLAB。

结果保存到 results/python 与 results/matlab，程序会核对最优值、不可行情形、编码性质与约束残差。已在 Python 3.12 与 MATLAB R2021b 实际执行并对照；基础 MATLAB 求解路径也已通过全部算例。
