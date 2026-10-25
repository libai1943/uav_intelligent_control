# 2026-10-25 运行核验

Python与MATLAB R2021b均完成固定网络损失、梯度、80场比赛记录检查。两种语言均从随机初始化完成quick配置的20批训练、评价和绘图。逐回合数值差见validation/short_profile_comparison.json。

原稿提供的500批、三个种子的完整Python训练记录保留在reference_results，本轮未重跑完整训练。MATLAB完整训练入口与短训练共用模型、梯度和训练代码，完整训练统计尚未在本轮执行。
