# 运行验证范围

Python与MATLAB R2021b均通过固定网络损失、梯度及80场比赛记录检查，并从随机初始化完成quick配置的20批训练、评价和绘图。逐回合数值差见 `validation/short_profile_comparison.json`。

500批、三个种子的完整Python训练记录保存在 `reference_results`。MATLAB完整训练入口与短训练共用模型、梯度和训练代码；MATLAB完整长训练尚未完成验证。
