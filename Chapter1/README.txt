第一章：侧风与参考航迹的两个轻量实验

Python：Python 3.10以上，安装 numpy、matplotlib 后，执行 python RunMe.py。
MATLAB：MATLAB R2021b或更新版本，在本目录执行 RunMe。无需额外工具箱，不调用Python。

两种实现分别输出 results 与 results_matlab，均包含 PDF、PNG 和 CSV。
1. wind_groundtrack：保持向北10 m/s空速，比较向东0、3、5 m/s侧风下的地面航迹。
2. path_time_schedules：同一Bezier几何曲线，给出两种时间参数安排。
曲线仅用于路径与时间安排的概念演示，未声称满足某一机型的飞行约束。

修改参数：Python脚本顶部 AIR_NORTH、WINDS_EAST、T；MATLAB脚本顶部 airNorth、windsEast、T。
CSV统一采用x向东、y向北的坐标约定。风矢量与空速必须使用同一坐标系。
默认风速3 m/s时，地速约10.4403 m/s，正北偏东约16.6992度。

验证记录：两个版本均已实际运行，默认参数下逐时刻位置数据一致（CSV存储精度范围内）。
本目录是数值教学实验，不是飞控软件在环、硬件在环或实机程序。
