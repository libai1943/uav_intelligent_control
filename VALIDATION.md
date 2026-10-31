# 当前实验的验证范围

两种语言的实现分别计算，比较记录保存在各章目录。本表汇集现有验证结果；模型、参数和结果字段以各章说明为准。

| 章节 | 已执行的检查 | 结果记录 |
|---|---|---|
| 1 | 四组侧风与路径时间安排数据，双语言逐项比较 | [validation.json](Chapter1/validation.json) |
| 2 | 19组高度控制主线数据，双语言比较 | [cross_language_validation.json](Chapter2/cross_language_validation.json) |
| 3 | 十一组规划，独立检查运动连接、边界、代价与避障，再比较双语言数据 | [validation.json](Chapter3/validation.json) |
| 4 | 五组跟踪，检查运动递推、状态输入边界、QP残差和双语言数据 | [validation.json](Chapter4/validation.json) |
| 5 | 六组量化与连续模糊控制，检查静态平衡、死区与双语言数据 | [cross_language_validation.json](Chapter5/cross_language_validation.json) |
| 6 | 两组10秒高度控制，独立运行Python与MATLAB；各1001行、14列，最大绝对差5.16×10⁻¹⁴以内 | [cross_language_validation.json](Chapter6/cross_language_validation.json) |
| 7 | 七组鲁棒控制，检查工作区域、误差范围、推力及双语言数据 | [cross_language_validation.json](Chapter7/cross_language_validation.json) |
| 8 | 五组容错控制，检查诊断时序、效能估计、能力不足与双语言数据 | [cross_language_validation.json](Chapter8/cross_language_validation.json) |
| 9 | Python完整训练参考记录；两种语言的固定样本、80场比赛及20批短训练 | [验证说明](Chapter9/docs/IMPLEMENTATION_STATUS.md) |
| 10 | 提示词生成、任务样本与输入输出约定检查；不调用外部模型服务 | [章节说明](Chapter10/README.md) |
| 11 | 装载、运输、调度、独立枚举与不可行检查；包括基础MATLAB求解路径 | [章节说明](Chapter11/README.md) |

已有运行环境为Windows、Python 3.12与MATLAB R2021b；第三章使用CasADi 3.7.2/IPOPT，第四章Python使用OSQP 1.1.3，MATLAB使用CasADi的OSQP插件。计时依赖运行环境，第四章首次加载求解器的开销另见章节说明。

第六章采用手写反向传播，已核对七个参数的解析梯度与中央差分。仅常规反馈时末端高度误差0.163332945 m；加入学习时为0.000014704 m，网络补偿0.979986636 N。两组推力均处于0—24 N内。

第九章MATLAB完整500批、三个种子的长训练未完成验证；当前已验证范围为固定样本和短训练。其完整统计使用随库的Python参考记录。数值复核不代替真实飞行试验。
