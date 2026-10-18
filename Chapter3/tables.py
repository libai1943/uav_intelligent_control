"""Generate textbook tables from saved, actually executed experiments."""
from pathlib import Path

def make_tables(results):
    root=Path(__file__).resolve().parent/'results_euler'/'tables'
    root.mkdir(parents=True,exist_ok=True)
    def table(name,caption,label,head,body):
        s=r'\begin{table}[!htbp]\centering\small'+'\n'
        s+=f'\\caption{{{caption}}}\\label{{{label}}}\n'
        s+=r'\begin{tabularx}{\textwidth}{|'+('|'.join(['Y']*len(head)))+r'|}\hline\hline'+'\n'
        s+=r'\tablehead'+'&'.join(r'\textbf{'+h+'}' for h in head)+r'\\\hline'+'\n'
        for i,row in enumerate(body):s+='&'.join(row)+(r'\\\lastline' if i==len(body)-1 else r'\\\hline')+'\n'
        s+=r'\end{tabularx}\end{table}'+'\n';(root/name).write_text(s,encoding='utf-8')
    names=['two_straight','two_north','two_south']
    if all(n in results for n in names):
        table('initial_table.tex','同一双柱任务中不同初始解的计算结果','tab:fwinitresults',
         ['初始解','迭代次数','优化耗时/s','离散代价','检查结果'],
         [[label,str(r['iterations']),f"{r['seconds']:.2f}",f"{r['objective']:.5f}",'通过' if r['accepted'] else '未通过']
          for label,r in zip(['直连','北侧绕行','南侧绕行'],[results[n] for n in names])])
    names=['four_direct','four_corridor']
    if all(n in results for n in names):
        table('corridor_table.tex','同一四柱任务中两种避障表达的计算结果','tab:fwcorridorresults',
         ['避障表达','迭代次数','优化耗时/s','离散代价','最小间隔/m'],
         [[label,str(r['iterations']),f"{r['seconds']:.2f}",f"{r['objective']:.5f}",f"{r['checks']['min_rollout_clearance_m']:.2f}"]
          for label,r in zip(['直接距离','廊内约束'],[results[n] for n in names])])
    names=['two_corridor','four_corridor','five_corridor']
    if all(n in results for n in names):
        table('check_table.tex','三个走廊算例的欧拉前向复核','tab:fwcheckresults',
         ['场景','最小间隔/m','最大节点位置差/m','步长减半差异/m'],
         [[label,f"{r['checks']['min_rollout_clearance_m']:.2f}",f"{r['checks']['max_node_reconstruction_error_m']:.3f}",f"{r['checks']['refined_rollout_difference_m']:.3f}"]
          for label,r in zip(['两柱','四柱','五柱'],[results[n] for n in names])])
    names=['four_grid100','four_corridor']
    if all(n in results for n in names):
        table('grid_table.tex','同一四柱走廊任务的离散规模比较','tab:fwgridresults',
         ['控制区间数','欧拉步长/s','离散代价','最大节点位置差/m'],
         [[str(r['intervals']),f"{36/r['intervals']/8:.4f}",f"{r['objective']:.5f}",f"{r['checks']['max_node_reconstruction_error_m']:.3f}"] for r in [results[n] for n in names]])
