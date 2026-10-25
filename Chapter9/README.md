# 第九章：强化学习及其在低空飞行器竞速博弈中的应用

本目录包含第九章两套独立的一键训练程序、完整训练参考记录，以及固定样本与数值检查。

## 先看验证范围

- **随新版材料提供的Python完整运行记录已保留**：从随机初始化训练两种PPO方案、三个训练种子、独立评价、绘图和数值自检。正文的实验数字来自这些运行。
- **MATLAB版是独立的基础MATLAB实现**，不调用Python，也不依赖强化学习或深度学习工具箱。已在MATLAB R2021b执行固定样本检查和20批短训练、评价与绘图，并与Python逐回合比较。完整500批、三种子训练仍采用随原稿提供的Python参考记录。`RunMe.m`启动后首先执行本地自检，比较固定梯度和80个完整比赛的跨语言基准，再开始训练。
- MATLAB与Python使用同一自定义随机数发生器、模型和训练规则，便于定位差异。两种运行时的浮点计算可能在长时间训练后产生差异，因此**不承诺训练后的网络逐位一致**。
- 仿真是三维质点与受限速度回路，包含三维赛门和两机交互；没有六自由度气动力、真实相机感知或实机试飞。仍有违规和跨赛道失败，均保留在正文与数据中。

## 一键运行

### Python

Windows：进入`Python`目录，双击`RunMe.bat`。脚本使用已安装的Python创建本地虚拟环境，并在依赖缺失时安装NumPy和Matplotlib；首次安装依赖需要网络。

macOS/Linux：在该目录执行`bash RunMe.sh`。

已有Python环境也可直接运行：

```bash
python -m pip install -r requirements.txt
python RunMe.py --profile book --parallel
```

默认`book`模式从随机网络重新训练，**不会读入随包的已训练模型来冒充训练**。每种训练组织运行3个种子，每个种子500批、每批64个回合。`--parallel`仅并行相互独立的种子。

快速检查流程可运行：

```bash
python RunMe.py --profile quick
```

快速模式只有1个种子、20批、每批32回合，结果写入`outputs_quick`，不用于复现正文性能。

### MATLAB

已测试MATLAB R2021b或更新版本。进入`MATLAB`目录，打开并运行`RunMe.m`，或命令行输入`RunMe`。

- `RunMe.m`：自检、从随机网络训练、独立评价、导出数据和绘图。
- `RunQuick.m`：较小预算的流程检查，写入`outputs_quick`。
- `RunTests.m`：只进行数值与跨语言固定样本检查。

只使用基础MATLAB的矩阵计算、文件读写和绘图函数。MATLAB版的训练与神经网络梯度均在`.m`文件中实现；不要求安装Python、PyTorch或额外训练工具箱。必须保留与`MATLAB`并列的`validation`目录。

## 文件组织

| 目录 | 内容 |
|---|---|
| `Python` | NumPy版PPO、三维竞速环境、规则对手、训练评价与绘图入口 |
| `MATLAB` | 独立MATLAB版的同名功能模块与一键入口 |
| `reference_results/python_book` | 新版材料所附完整Python实验的冻结副本，含权重、逐回合CSV与训练记录；图形由入口程序生成 |
| `validation` | 数值测试结果、跨语言固定网络与比赛基准数据 |
| `docs` | 模型与验证说明、实验说明、修改记录 |

`reference_results`不被默认训练入口覆盖。自行重跑的结果写入相应语言的`outputs`目录。

## 主要输出

- `training_<方法>_<种子>.csv`：全部训练批次的回报、胜负、违规、梯度优化指标和验证记录。
- `evaluation_<条件>_<种子>.csv`：全部评价回合，包含失败和超时，避免只统计成功比赛。
- `metrics_by_seed.csv`、`metrics_by_opponent.csv`、`summary.csv`：分种子、分对手与汇总指标。
- `models/`：行动者、评价者、初始网络和保留的历史对手权重。
- `trajectory_all_episodes.csv`：固定展示种子的100场完整记录。
- `trajectory_example.csv`、`trajectory_failure.csv`：按明确规则选取的成功与失败回合。
- `figures/`：训练过程、三维航迹、速度、领先量、间距及跨赛道结果。Python导出PDF/PNG；MATLAB另保留FIG。
- `configuration.json`：运行版本、参数、种子与赛门数据。
- `run_status.json`：只有流程全部结束后才写入`complete`。

两版的规则、参数、原始数据列顺序与指标定义见`docs/MODEL_AND_VALIDATION.md`。

## 教材编译与合入全书

进入`latex`目录，双击`build.bat`，或执行`bash build.sh`，使用XeLaTeX编译。整章和答案均可独立输入全书，具体见`latex/README.md`。

本次正文使用新版材料所附的Python参考图与表，重跑实验不会悄悄覆盖教材。需要用新的完整实验替换图表时，在`Python`目录执行：

```bash
python plot_results.py outputs --sync
```

然后重新编译LaTeX。该命令只同步图与数据表，**不会自动改写正文中的解释和手写数值**；改变模型、预算或种子后，应一并核对正文讨论。

## 学术使用注意

固定对手与历史对手方案比较的是同一网络、同一PPO更新下的对手组织。历史对手池包含冻结的旧学习策略，因此具有真实自我对弈过程。主结果不是从测试集上挑选最好的训练检查点；采用统一的最后一批策略。

随机策略评价与高斯均值执行分别报告。屏蔽对手信息属于已有策略的输入干预，不能解释为重新训练后的无对手信息策略能力上限。镜像赛道测试保留明显失败，不将单一赛道成绩推广到任意环境。模型权重不直接用于真实飞行器。

本包不包含字体文件，不增设教材参考文献章节。
