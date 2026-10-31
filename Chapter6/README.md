# 第六章：神经网络学习与控制

本章包含两项实验，Python与MATLAB均提供独立实现。运行一次入口，生成两项实验的全部结果。

## 运行

- Python：安装`Python/requirements.txt`中的依赖，运行`python Python/RunMe.py`。
- MATLAB：运行`MATLAB/RunMe.m`，不需要额外工具箱或Python。
- 两种实现都运行后，在本章目录运行`python CheckResults.py`核对逐项结果。

## 三种训练方式

`TrainingModes`实现一个输入、一个tanh隐含单元、一个线性输出的网络。两层偏置为0，两个权重均通过真实BP更新。训练集含1000个输入输出样本，目标为`1.6*tanh(2.4*x)`叠加幅值不超过0.2的独立均匀噪声。初值为`[1,1.2]`，学习率0.3，三种批量分别为1、10、1000，均更新1500次。

三种方式共用数据、初值、学习率及打乱记录的序列。每次更新消耗的样本数量不同，参数路径用于比较调整方向，不作为等耗时的性能排行。线段连接实际相邻参数，没有曲线平滑处理。噪声种子为20261101，排列种子为456；两种语言采用相同整数序列生成器以便复核。

各自的`results/training_modes/`保存：
- `training_modes.pdf/png`：中文参数轨迹对比图。
- `training_loss.pdf`：每次更新后在固定全训练集上计算的平均损失。
- `training_samples.csv/png`：训练数据与生成函数。
- `*_parameters.csv`：包括初值的1501组权重；`*_loss.csv`：更新次数、累计使用样本数与损失。
- `summary.json`：设置、训练结果；Python版本还包含解析BP与中央差分核对。

可以单独运行`Python/TrainingModes.py`，或在MATLAB中调用`TrainingModes`。

## 高度学习控制

沿用相同的实际质量、初始状态与反馈增益，对比仅常规反馈和加入神经网络学习控制。控制器只能读取名义质量和运动反馈，不能读取真实质量差作为标签。固定反馈增益，网络学习持续推力补偿。

各自的`results/`保存高度实验的`learning_control.pdf/png`、两组逐周期CSV和`summary.json`。`sample_results/`提供结果摘要，`cross_language_validation.json`记录两种实现的核验结果。
