# 低空飞行器智能控制技术：教材配套代码

本仓库按章节组织仿真实验。每章有独立的 `RunMe.py`、依赖清单和说明，下载后无需教材源文件即可运行。

| 目录 | 内容 | 主要输出 |
| --- | --- | --- |
| [Chapter2](Chapter2) | PID 控制器及其在低空飞行器高度控制中的应用 | 高度响应、前馈与反馈比较、P/PI/PID 对照、级联控制、CSV 数据及数值核验 |
| [Chapter3](Chapter3) | 最优控制及其在低空飞行器航迹规划中的应用 | 三维 A* 搜索初始路径、完整初始解、最优航迹、安全走廊碎片、状态与输入曲线及数值核验 |

## 快速运行

需要 Python 3.10 或更新版本。建议先创建虚拟环境；依赖安装需要联网，实验本身无需联网。

第二章：

```bash
cd Chapter2
python -m pip install -r requirements.txt
python RunMe.py
```

第三章：

```bash
cd Chapter3
python -m pip install -r requirements.txt
python RunMe.py
```

也可以在仓库根目录安装相应依赖后，直接执行 `python Chapter2/RunMe.py` 或 `python Chapter3/RunMe.py`。两章的结果分别保存在 `Chapter2/results/`、`Chapter3/results_euler/`，与启动命令时所在目录无关。重复运行会更新同名结果。

第三章默认运行八组优化实验并生成全部图表。先体验一个四柱走廊算例，可执行：

```bash
python Chapter3/RunMe.py --case four_corridor
```

图中文字使用 Microsoft YaHei 或 Noto Sans CJK SC 等中文字体。无中文字体时应先安装字体，否则图片可能缺字。第三章采用 CasADi 自带的 IPOPT 求解器，无需另外安装商业优化软件；LaTeX 表格只是附加输出，运行仿真不需要安装 LaTeX。

## 模型与验证

两章均是教材中的简化模型。第二章模拟近水平多旋翼的竖直运动；第三章采用固定翼协调飞行模型，求解静态障碍环境中的开环规划问题。具体假设、参数、检查阈值、输出格式和修改方法见各章 README。

代码包含解析关系对照、步长减半、约束残差以及独立前向复核等检查。程序保留实验数据及诊断信息，便于核对。数值检查不等于全局最优性证明，也不代表实机验证。这里不包含飞控固件或实机控制接口。

测试记录见 [VALIDATION.md](VALIDATION.md)。本次提供 Python 版本。
