# MATLAB一键入口

已在MATLAB R2021b Update 7运行验证，使用基础MATLAB，无需强化学习、深度学习或优化工具箱。

打开RunMe.m并运行，完成：本地数值自检→从随机初始化训练→最终评价→输出CSV、网络权重和PDF/PNG/FIG图。RunQuick.m采用小预算检查流程；RunTests.m仅运行验证。

程序独立使用MATLAB矩阵计算和手写反向传播，没有调用Python。必须保留上级validation目录；其中cross_language_fixture.json提供固定网络、PPO梯度和80个冻结策略比赛的比较基准。

已实际执行 RunTests 和 RunQuick：固定网络与80场比赛基准通过；20批次、种子101的训练、评价和绘图流程通过。与Python相同短训练流程的14组评价记录相比，最大绝对差为3.20e-14。完整500批次、3种子的MATLAB长训练尚未完成验证；正文保留随库保存的完整Python参考结果。

正文数据及reference_results来自实际Python运行。MATLAB重跑后会产生自己的outputs、运行版本和测试记录。即使固定样本吻合，长期浮点训练仍可能有差异，应结合多个种子比较。

