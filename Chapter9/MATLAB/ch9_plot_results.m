function ch9_plot_results(out,seeds)
%CH9_PLOT_RESULTS Rebuild plots only from numerical records; one axes per plot.
figdir=fullfile(out,'figures');if ~exist(figdir,'dir'),mkdir(figdir);end
font='Arial';available=listfonts;
if any(strcmp(available,'Microsoft YaHei')),font='Microsoft YaHei';elseif any(strcmp(available,'Noto Sans CJK SC')),font='Noto Sans CJK SC';end
set(groot,'defaultAxesFontName',font,'defaultTextFontName',font,'defaultAxesFontSize',10);
modes={'fixed','league'};labels={'固定对手 PPO','历史对手 PPO'};
f=figure('Visible','off','Position',[100 100 790 340]);ax=axes(f);hold(ax,'on');
for k=1:2
    values=[];
    for s=seeds
        t=readtable(fullfile(out,sprintf('training_%s_%d.csv',modes{k},s)));
        good=isfinite(t.validation_score);xx=t.iteration(good);values(:,end+1)=t.validation_score(good); %#ok<AGROW>
    end
    mu=mean(values,2);sd=std(values,0,2);errorbar(ax,xx,mu,sd,'LineWidth',1.1,'DisplayName',labels{k});
end
xlabel(ax,'策略更新批次');ylabel(ax,'验证得分 J');ylim(ax,[-1.05 1.05]);legend(ax,'Location','southeast');saveone(f,ax,figdir,'training_score');
f=figure('Visible','off','Position',[100 100 790 330]);ax=axes(f);hold(ax,'on');
for k=1:2
    values=[];
    for s=seeds
        t=readtable(fullfile(out,sprintf('training_%s_%d.csv',modes{k},s)));
        good=isfinite(t.validation_violation);xx=t.iteration(good);values(:,end+1)=t.validation_violation(good); %#ok<AGROW>
    end
    plot(ax,xx,100*mean(values,2),'LineWidth',1.4,'DisplayName',labels{k});
end
xlabel(ax,'策略更新批次');ylabel(ax,'验证违规率 / %');ylim(ax,[0 100]);legend(ax);saveone(f,ax,figdir,'training_violation');
a=readmatrix(fullfile(out,'trajectory_example.csv'),'NumHeaderLines',1);
g=[10 0 2.5 3.6 2.2;20 1.5 3 3.2 2;30 -1 2.4 1.2 1;40 1 3 3.2 2;50 0 2.5 2.6 1.8];
f=figure('Visible','off','Position',[100 100 790 340]);ax=axes(f);hold(ax,'on');
plot(ax,a(:,3),a(:,4),'LineWidth',1.5,'DisplayName','学习策略 A');
plot(ax,a(:,6),a(:,7),'--','LineWidth',1.5,'DisplayName','快速规则对手 B');
for j=1:5
    plot(ax,[g(j,1) g(j,1)],g(j,2)+[-1 1]*g(j,4)/2,'LineWidth',3,'HandleVisibility','off');
    text(ax,g(j,1),g(j,2)+g(j,4)/2+.15,sprintf('门%d',j),'HorizontalAlignment','center');
end
xlabel(ax,'纵向位置 x / m');ylabel(ax,'横向位置 y / m');xlim(ax,[-2.5 52]);ylim(ax,[-3.1 4.2]);legend(ax,'Location','southeast');saveone(f,ax,figdir,'trajectory_xy');
f=figure('Visible','off','Position',[100 100 790 400]);ax=axes(f);hold(ax,'on');
plot3(ax,a(:,3),a(:,4),a(:,5),'LineWidth',1.5,'DisplayName','学习策略 A');
plot3(ax,a(:,6),a(:,7),a(:,8),'--','LineWidth',1.5,'DisplayName','快速规则对手 B');
for j=1:5
    yy=g(j,2)+[-1 1 1 -1 -1]*g(j,4)/2;zz=g(j,3)+[-1 -1 1 1 -1]*g(j,5)/2;
    plot3(ax,repmat(g(j,1),1,5),yy,zz,'LineWidth',1.1,'HandleVisibility','off');
end
xlabel(ax,'x / m');ylabel(ax,'y / m');zlabel(ax,'z / m');pbaspect(ax,[4 1.3 1.2]);view(ax,-65,20);legend(ax);saveone(f,ax,figdir,'trajectory_xyz');
f=figure('Visible','off','Position',[100 100 790 330]);ax=axes(f);hold(ax,'on');
plot(ax,a(:,2),a(:,3)-a(:,6),'LineWidth',1.5);yline(ax,0,':');
xlabel(ax,'时间 t / s');ylabel(ax,'纵向领先量 x_A - x_B / m');saveone(f,ax,figdir,'relative_lead');
f=figure('Visible','off','Position',[100 100 790 340]);ax=axes(f);hold(ax,'on');
plot(ax,a(:,2),a(:,9),'LineWidth',1.5,'DisplayName','A 实际纵向速度');
plot(ax,a(:,2),a(:,12),'--','LineWidth',1.5,'DisplayName','B 实际纵向速度');
plot(ax,a(:,2),4.5+2*a(:,17),':','LineWidth',1.1,'DisplayName','A 策略参考速度');
xlabel(ax,'时间 t / s');ylabel(ax,'纵向速度 / (m/s)');legend(ax);saveone(f,ax,figdir,'speed_response');
f=figure('Visible','off','Position',[100 100 790 330]);ax=axes(f);hold(ax,'on');
d=sqrt(sum((a(:,3:5)-a(:,6:8)).^2,2));plot(ax,a(:,2),d,'LineWidth',1.5,'DisplayName','节点间距');
yline(ax,.8,'--','DisplayName','间隔违规阈值');xlabel(ax,'时间 t / s');ylabel(ax,'两机中心距离 / m');legend(ax);saveone(f,ax,figdir,'separation');
p=fullfile(out,'trajectory_failure.csv');
if exist(p,'file')
    a=readmatrix(p,'NumHeaderLines',1);f=figure('Visible','off','Position',[100 100 790 330]);ax=axes(f);hold(ax,'on');
    plot(ax,a(:,2),sqrt(sum((a(:,3:5)-a(:,6:8)).^2,2)),'LineWidth',1.5,'DisplayName','失败回合的实际间距');
    yline(ax,.8,'--','DisplayName','间隔违规阈值');xlabel(ax,'时间 t / s');ylabel(ax,'两机中心距离 / m');legend(ax);saveone(f,ax,figdir,'failure_separation');
end
s=readtable(fullfile(out,'summary.csv'),'TextType','string');methods=["fixed_holdout","fixed_mirror","league_holdout","league_mirror"];
vals=zeros(4,1);for k=1:4,vals(k)=100*s.violation(s.method==methods(k));end
f=figure('Visible','off','Position',[100 100 790 330]);ax=axes(f);bar(ax,1:4,vals);
xticks(ax,1:4);xticklabels(ax,{'固定：原赛道','固定：镜像','历史：原赛道','历史：镜像'});ylabel(ax,'自身违规率 / %');ylim(ax,[0 100]);
for k=1:4,text(ax,k,vals(k)+2,sprintf('%.1f',vals(k)),'HorizontalAlignment','center');end
saveone(f,ax,figdir,'generalization');
end
function saveone(f,ax,out,name)
grid(ax,'on');savefig(f,fullfile(out,[name '.fig']));
exportgraphics(ax,fullfile(out,[name '.pdf']),'ContentType','vector');
exportgraphics(ax,fullfile(out,[name '.png']),'Resolution',180);close(f);
end
