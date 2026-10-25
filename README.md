# 低空飞行器智能控制技术：教材配套代码

本仓库按章节组织独立教学实验，无需教材的 LaTeX 源文件即可运行。十一章均提供独立的 Python 和 MATLAB 实现，统一入口分别为 `RunMe.py` 和 `RunMe.m`。

| 目录 | 内容 | 主要输出 |
| --- | --- | --- |
| [Chapter1](Chapter1) | 侧风、空速与地速；路径的时间安排 | 四组 CSV、速度向量与参考航迹图 |
| [Chapter2](Chapter2) | PID 控制器与低空飞行器高度控制 | P/PI/PID、前馈反馈、积分抗饱和、级联控制及 19 组主线数据 |
| [Chapter3](Chapter3) | 最优控制方法与固定翼航迹规划 | 三维 A* 搜索、完整初始解、十一组优化、走廊、状态与输入、独立结果核验 |
| [Chapter4](Chapter4) | 模型预测控制与固定翼航迹跟踪 | 名义输入与闭环对照、5/20/40 步预测、反馈更新图及 CSV |
| [Chapter5](Chapter5) | 模糊控制 | 同一49条规则下量化/连续计算、上升、小偏差、恒力对照 |
| [Chapter6](Chapter6) | 神经网络反馈误差学习 | 不学习、学习后冻结、持续在线学习，参数与补偿记录 |
| [Chapter7](Chapter7) | 鲁棒高度控制 | 质量与外力范围、测量误差、边界层、推力受限 |
| [Chapter8](Chapter8) | 主动容错控制 | 固定反馈、效能补偿、诊断延迟、外力歧义与能力不足 |
| [Chapter9](Chapter9) | 强化学习与双机竞速 | PPO训练、不同对手评价、三维航迹及固定样本核验 |
| [Chapter10](Chapter10) | 专家系统与任务理解 | 完整提示词、任务样本及输入输出约定检查 |
| [Chapter11](Chapter11) | 运筹优化与指派调度 | 装载、运输、调度、枚举核对及不可行分析 |

## 各章运行方式

第一、三章进入章节目录，第二、四至八章进入各自的 `Python` 子目录。安装依赖后运行 Python 入口：

```bash
python -m pip install -r requirements.txt
python RunMe.py
```

MATLAB 的第二、四章入口分别位于 `Chapter2/MATLAB`、`Chapter4/MATLAB`，其余章按对应目录说明切换当前文件夹，执行 `RunMe`。第一、二章不需要附加工具箱；第三章需要 CasADi 3.7.2 的 MATLAB 发行包及其附带的 IPOPT，安装方法见 [Chapter3/README.md](Chapter3/README.md)。第四章同样需要 CasADi MATLAB 发行包，使用其 OSQP 插件。MATLAB 实现自行计算全部结果，不调用 Python。Windows 上建议将 Python 环境及 CasADi 二进制依赖安装在英文路径。

两种实现都完成后，在章节目录执行：

```bash
python CheckResults.py
```

检查脚本比较逐时刻 CSV。第三章还分别重新计算两种语言结果的运动残差、变量边界、目标值、前向重算及线段避障间隔。检查记录写入各章的 JSON 文件。程序可以从其他目录启动，输出路径相对于程序文件确定。

| 章节 | Python 输出 | MATLAB 输出 | 核验记录 |
| --- | --- | --- | --- |
| 第一章 | `results/` | `results_matlab/` | `validation.json` |
| 第二章 | `Python/results/` | `MATLAB/results_matlab/` | `Python/results/cross_language_check.json`；随库保存 `cross_language_validation.json` |
| 第三章 | `results_kinematic/` | `results_matlab/` | `validation.json` |
| 第四章 | `Python/results/` | `MATLAB/results/` | `validation.json` |

第三章默认完成十一组算例。初次体验可运行 `python RunMe.py --case four_corridor`；完整双语言核验需要先完成全部十一组。图片采用中文字体，建议安装 Microsoft YaHei 或 Noto Sans CJK SC。生成附加 LaTeX 表格不要求安装 LaTeX。

## 模型与验证

第二章采用近水平多旋翼的竖直运动模型；第三章采用固定翼简化运动学规划模型，三路输入为飞行速率、航迹倾角和倾侧角的变化率。每个区间只使用一次显式欧拉更新，第三章没有积分子步或 RK4。详见各章模型、参数与结果说明。

2026 年 10 月修订已在 Windows、Python 3.12.14 与 MATLAB R2021b 下实际运行前四章。第一章四份数据、第二章 19 组逐时刻数据、第三章十一个优化算例均通过独立核验。第三章修正了走廊边界数组使用整数类型导致小数截断的问题，结果已经重新生成。测试记录见 [VALIDATION.md](VALIDATION.md)。这些程序用于数值教学，不含飞控固件或实机控制接口。

## 第四章：模型预测控制

进入 `Chapter4/Python` 执行 `python RunMe.py`，或进入 `Chapter4/MATLAB` 执行 `RunMe`。两版独立计算，不需要先运行第三章。参考数据随 `reference/` 提供。

第四章跟踪第三章新生成的交错双柱 S 形航迹。初次沿名义运动线性化，后续将旧输入修正移位、补齐末段，从新反馈重建完整展开运动，再求解跟踪 QP；每次只执行首段输入。目标仍为同一时刻的名义状态，窗口末端自由，不加入显式障碍约束。

默认完成开环对照、5/20/40步预测及理想一致性对照。两种语言共1600次QP均成功，五组状态与输入通过独立递推和双语言核验。主实验位置RMSE约1.918米，最终偏差约0.064米。五步短时域未保持8米安全间隔，开环组进入柱体；这些差别在结果中如实记录。详见 [第四章说明](Chapter4/README.md)。


## 第五至八章：一次运行全部对照

各章进入 `Python` 目录安装 requirements.txt，运行 `python RunMe.py`；或进入 `MATLAB` 目录执行 `RunMe`。每个入口一次完成本章全部实验、绘图、CSV 保存及计算检查，不需要逐个启动实验。MATLAB 版本独立计算，不调用 Python，也不需要附加工具箱。

两版运行后，可在章节目录运行 `python CheckResults.py`，逐项比较全部状态、控制、学习参数或诊断数据。默认参数固定，没有随机初始化。具体模型、初值、扰动和尺度见各章说明。

2026-10-25 已实际运行第5—8章两种入口，共21组逐时刻数据通过比对；最大绝对差约2.27e-13。核验阈值为绝对1e-8、相对1e-9。该阈值用于本组数值实现对齐，与物理跟踪误差指标分别记录。

## 第九至十一章

新版配套材料位于各自 Chapter 目录，均提供 Python/RunMe.py 与 MATLAB/RunMe.m。
第九章默认重新训练完整模型，另有短训练入口；正文的完整训练记录随 reference_results 保留。第十章演示任务输入与完整提示词的构造，不要求外部模型账户。第十一章运行全部优化对照，MATLAB 无优化工具箱时使用随附的小规模求解器。具体依赖和验证范围见各章 README。
