# 低空飞行器智能控制技术：教材配套代码

本仓库按章节组织独立教学实验，无需教材的 LaTeX 源文件即可运行。前三章同时提供独立的 Python 和 MATLAB 实现，统一入口分别为 `RunMe.py` 和 `RunMe.m`。第四章现有程序仍使用 Python。

| 目录 | 内容 | 主要输出 |
| --- | --- | --- |
| [Chapter1](Chapter1) | 侧风、空速与地速；路径的时间安排 | 四组 CSV、速度向量与参考航迹图 |
| [Chapter2](Chapter2) | PID 控制器与低空飞行器高度控制 | P/PI/PID、前馈反馈、积分抗饱和、级联控制及 19 组主线数据 |
| [Chapter3](Chapter3) | 最优控制方法与固定翼航迹规划 | 三维 A* 搜索、完整初始解、八组优化、走廊、状态与输入、独立结果核验 |
| [Chapter4](Chapter4) | 模型预测控制与固定翼航迹跟踪 | 名义输入与闭环对照、5/20/40 步预测、反馈更新图及 CSV |

## 前三章的运行方式

第一、三章进入章节目录，第二章进入 `Chapter2/Python` 子目录。安装依赖后运行 Python 入口：

```bash
python -m pip install -r requirements.txt
python RunMe.py
```

MATLAB 的第二章入口位于 `Chapter2/MATLAB`，其余章按对应目录说明切换当前文件夹，执行 `RunMe`。第一、二章不需要附加工具箱；第三章需要 CasADi 3.7.2 的 MATLAB 发行包及其附带的 IPOPT，安装方法见 [Chapter3/README.md](Chapter3/README.md)。MATLAB 实现自行计算全部结果，不调用 Python。Windows 上建议将 Python 环境及 CasADi 二进制依赖安装在英文路径。

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

第三章默认完成八组算例。初次体验可运行 `python RunMe.py --case four_corridor`；完整双语言核验需要先完成全部八组。图片采用中文字体，建议安装 Microsoft YaHei 或 Noto Sans CJK SC。生成附加 LaTeX 表格不要求安装 LaTeX。

## 模型与验证

第二章采用近水平多旋翼的竖直运动模型；第三章采用固定翼简化运动学规划模型，三路输入为飞行速率、航迹倾角和倾侧角的变化率。每个区间只使用一次显式欧拉更新，第三章没有积分子步或 RK4。详见各章模型、参数与结果说明。

2026 年 10 月修订已在 Windows、Python 3.12.14 与 MATLAB R2021b 下实际运行前三章。第一章四份数据、第二章 19 组逐时刻数据、第三章八个优化算例均通过独立核验。第三章修正了走廊边界数组使用整数类型导致小数截断的问题，结果已经重新生成。测试记录见 [VALIDATION.md](VALIDATION.md)。这些程序用于数值教学，不含飞控固件或实机控制接口。

## 第四章：模型预测控制

```bash
cd Chapter4
python -m pip install -r requirements.txt
python RunMe.py
```

也可在仓库根目录运行 `python Chapter4/RunMe.py`。参考数据已随代码提供，不必先求解第三章。结果写入 `Chapter4/results/`。

第四章沿用第三章的七状态固定翼模型和四柱场景名义航迹，按固定参考时间匹配，采用一阶线性化与单步显式欧拉预测，每周期调用 OSQP 求解跟踪 QP，只执行第一段输入。受扰仿真对象保留非线性运动关系；代码演示模型预测、滚动优化、反馈校正及暖启动的区别。

默认完成开环对照、5/20/40步预测及无扰动一致性对照。它不含显式避障约束，也不提供实机接口；模型条件、输入限制、失败处理与验证边界见 [Chapter4/README.md](Chapter4/README.md)。
