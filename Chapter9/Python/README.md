# Python一键入口

Windows双击RunMe.bat；macOS/Linux运行bash RunMe.sh。已安装依赖时运行`python RunMe.py --profile book --parallel`。

默认从随机网络训练2种方案、3个种子；结果写入outputs。`python RunMe.py --profile quick`只作小预算流程检查，写入outputs_quick。需要Python 3.10或更新版本、NumPy和Matplotlib。当前实测环境详见上级docs/IMPLEMENTATION_STATUS.md。

固定参考数据位于上级reference_results/python_book。绘图可单独执行：

```
python plot_results.py ../reference_results/python_book
```

该命令只由CSV重建图与表，不重新训练。完整包中加`--sync`可同步到LaTeX；代码分包没有LaTeX时不要加该参数。

保留上级validation目录，入口依赖其中的验证资料组织。修改参数后不要把quick结果与书中500批、3种子的统计直接比较。
