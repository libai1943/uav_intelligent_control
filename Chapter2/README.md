# 第二章：PID控制器及其在低空飞行器高度控制中的应用

两个子目录分别提供能够独立计算的程序。选择一种语言即可开始实验。

## Python

进入 `Python` 子目录，首次使用安装依赖：

```bash
python -m pip install -r requirements.txt
python RunMe.py
```

## MATLAB

将 MATLAB 当前文件夹切换到 `MATLAB` 子目录，运行 `RunMe`。无需调用 Python，也不需要附加控制工具箱。

两个入口均完成 P、PI、PID、前馈与反馈、推力限幅以及高度—速度级联实验，输出高度、速度、控制输入等数据和曲线。Python 结果写入 `Python/results`，MATLAB 结果写入 `MATLAB/results_matlab`。

## 修改实验

Python 主线参数在 `progressive.py`，限幅与级联对照在 `revision_experiments.py`。MATLAB 参数统一在 `experiment_cases.json`。两个目录的同名配置文件记录同一组实验的参数。改变增益、参考高度或持续外力后，再次运行即可观察响应。

模型采用质量 1.6 kg 的竖直通道、重力前馈和单步显式欧拉更新，默认步长 0.002 s。高度与速度采用理想反馈；PID 的 D 作用采用负的竖直速度反馈。

## 双语言核对

分别运行两个入口后，在 `Chapter2` 目录执行：

```bash
python CheckResults.py
```

检查脚本比较19组逐时刻数据，记录结果到 `Python/results/cross_language_check.json`。
