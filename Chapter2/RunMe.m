function RunMe
% 第二章独立 MATLAB 实现：无需 Python 或 Control System Toolbox。
% MATLAB R2021b 测试；所有模型均采用单步显式欧拉法。
root=fileparts(mfilename('fullpath')); out=fullfile(root,'results_matlab');
if ~exist(out,'dir'), mkdir(out); end
cfg=jsondecode(fileread(fullfile(root,'experiment_cases.json')));
S=struct; checks=struct;
for j=1:numel(cfg)
    c=cfg(j); d=simulate(c,.002); S.(c.name)=d;
    assert(all(isfinite(d(:))),'Nonfinite data');
    assert(all(d(:,8)>=0 & d(:,8)<=c.tmax+1e-9),'Thrust bounds');
    names={'time_s','reference_m','height_m','velocity_m_s','error_m','integral','raw_thrust_N','thrust_N','disturbance_N','velocity_reference_m_s','reference_derivative_m_s','integral_derivative'};
    writetable(array2table(d,'VariableNames',names),fullfile(out,[c.name '.csv']));
    checks.(c.name)=struct('final_height_m',d(end,3),'final_error_m',d(end,5),'peak_height_m',max(d(:,3)),'peak_thrust_N',max(d(:,8)));
end
set(groot,'defaultFigureVisible','off','defaultAxesFontName','Microsoft YaHei',...
    'defaultTextFontName','Microsoft YaHei','defaultAxesFontSize',10);
pair(S,{'stage_p','stage_no_drag'},{'有竖直阻尼','忽略竖直阻尼'},[3 4 8],{'高度 / m','竖直速度 / (m/s)','总推力 / N'},out,'stage1_p',14);
pair(S,{'stage_p_wind','stage_p8_wind'},{'P: Kp=4','P: Kp=8'},[3 8],{'高度 / m','总推力 / N'},out,'stage2_bias',40);
f=newfig(2); ax=subplot(2,1,1); hold(ax,'on');
lineplot(ax,S.stage_p_wind,3,1,'P控制');lineplot(ax,S.stage_pi,3,2,'PI控制');yline(ax,3,':');ylabel(ax,'高度 / m');legend(ax,'Location','best','Box','off');
ax=subplot(2,1,2);hold(ax,'on');d=S.stage_pi;
plot(ax,d(:,1),4*d(:,5),'Color',[.13 .49 .54],'DisplayName','比例修正');
plot(ax,d(:,1),1.2*d(:,6),'--','Color',[.66 .43 .21],'DisplayName','积分补偿');ylabel(ax,'修正推力 / N');xlabel(ax,'时间 / s');legend(ax,'Location','best','Box','off');savefigs(f,out,'stage3_integral');
pair(S,{'stage_pi','stage_pid'},{'PI控制','PID控制'},[3 8],{'高度 / m','总推力 / N'},out,'stage4_derivative',40);
f=newfig(3);d=S.stage_cascade;
for q=1:3
 ax=subplot(3,1,q);hold(ax,'on');
 if q==1,lineplot(ax,d,2,2,'参考高度');lineplot(ax,d,3,1,'实际高度');ylabel(ax,'高度 / m');
 elseif q==2,lineplot(ax,d,10,2,'参考速度');lineplot(ax,d,4,1,'实际速度');ylabel(ax,'竖直速度 / (m/s)');
 else,lineplot(ax,d,8,1,'总推力');ylabel(ax,'总推力 / N');xlabel(ax,'时间 / s');end
 legend(ax,'Location','best','Box','off');
end
savefigs(f,out,'stage5_cascade');
pair(S,{'feedforward_open','feedback_hover'},{'仅重力前馈','同一前馈加反馈'},[3 8],{'高度 / m','总推力 / N'},out,'stage6_feedforward_feedback',12);
pair(S,{'limit_plain','limit_conditional'},{'普通积分','条件积分'},[3 6 7 8],{'高度 / m','积分状态 / (m s)','限幅前推力 / N','实际推力 / N'},out,'stage7_antiwindup',40);
f=newfig(3);
ax=subplot(3,1,1);hold(ax,'on');lineplot(ax,S.stage_cascade,4,1,'基准速度内环');lineplot(ax,S.cascade_slow_inner,4,2,'减小内环增益');lineplot(ax,S.stage_cascade,10,3,'基准参考速度');ylabel(ax,'竖直速度 / (m/s)');
ax=subplot(3,1,2);hold(ax,'on');lineplot(ax,S.stage_cascade,3,1,'Kh=0.8');lineplot(ax,S.cascade_slow_outer,3,2,'Kh=0.4');ylabel(ax,'高度 / m');
ax=subplot(3,1,3);hold(ax,'on');lineplot(ax,S.stage_cascade,3,1,'级联控制');lineplot(ax,S.tune_pid,3,2,'单环PID');ylabel(ax,'高度 / m');xlabel(ax,'时间 / s');
for ax=findall(f,'Type','axes')',xlim(ax,[0 14]);legend(ax,'Location','best','Box','off');end
savefigs(f,out,'stage8_cascade_comparison');
f=newfig(2);d=S.cascade_large;ax=subplot(2,1,1);hold(ax,'on');lineplot(ax,d,3,1,'实际高度');yline(ax,3,':','参考高度');ylabel(ax,'高度 / m');
ax=subplot(2,1,2);hold(ax,'on');plot(ax,d(:,1),.8*d(:,5),':','DisplayName','未限幅要求');lineplot(ax,d,10,1,'限幅后速度参考');lineplot(ax,d,4,2,'实际速度');ylabel(ax,'竖直速度 / (m/s)');xlabel(ax,'时间 / s');
for ax=findall(f,'Type','axes')',xlim(ax,[0 14]);legend(ax,'Location','best','Box','off');end
savefigs(f,out,'stage9_velocity_limit');
% 章首阶跃图及性能指标，使用与Python相同的两个数值案例。
f=newfig(1);ax=axes(f);hold(ax,'on');d=S.gain4;
plot(ax,[-1.5 0 0 9],[2 2 3 3],'--','DisplayName','参考高度');
plot(ax,[-1.5;d(:,1)],[2;d(:,3)],'DisplayName','实际高度');xlim(ax,[-1.5 9]);ylabel(ax,'高度 / m');xlabel(ax,'时间 / s');legend(ax,'Location','best');savefigs(f,out,'height_step');
d=S.intro_performance; t=d(:,1); h=d(:,3);hf=2.9;
i10=find(h>=2.09,1);i90=find(h>=2.81,1);[hp,ip]=max(h);ib=find(abs(h-hf)>.018,1,'last');
f=newfig(1);ax=axes(f);hold(ax,'on');fill(ax,[0 12 12 0],[2.882 2.882 2.918 2.918],[.88 .94 .94],'EdgeColor','none');
plot(ax,t,h,'Color',[.13 .49 .54],'LineWidth',1.5);yline(ax,3,'--','参考高度');yline(ax,2.9,':','高度终值');
plot(ax,t([i10 i90 ip]),h([i10 i90 ip]),'.','MarkerSize',10);
text(ax,t(i10),2.04,'10%');text(ax,t(i90),2.74,'90%');text(ax,t(ip)+.15,hp,'峰值');
xline(ax,t(ib+1),'--','2%调节时间');xlabel(ax,'时间 / s');ylabel(ax,'高度 / m');xlim(ax,[0 12]);savefigs(f,out,'performance_overview');
metrics=struct;
for key={'tune_p','tune_pd','tune_pid'}
 name=key{1};d=S.(name);early=d(d(:,1)<14,:);metrics.(name)=stepmetrics(early,2,3);
 metrics.(name).final_mean_error_m=mean(d(d(:,1)>=38,5));
end
fid=fopen(fullfile(out,'checks.json'),'w','n','UTF-8');fprintf(fid,'%s',jsonencode(struct('dt_s',.002,'checks',checks,'tuning_metrics',metrics)));fclose(fid);
fprintf('完成第二章 MATLAB 独立计算：%d 组数据，11 幅图\n%s\n',numel(cfg),out);
end

function d=simulate(c,dt)
g=9.81;n=round(c.t_end/dt);d=zeros(n+1,12);y=[c.h0;c.v0;0];
for k=0:n
 t=k*dt;ref=c.r;rd=0;
 if c.smooth,ref=3+.6*(1-cos(.45*t));rd=.27*sin(.45*t);end
 e=ref-y(1);
 if c.cascade
  vr=min(max(rd+c.kh*e,-c.vmax),c.vmax);ei=vr-y(2);raw=c.m0*g+c.kv*ei+c.kiv*y(3);
 else
  vr=rd;ei=e;raw=c.m0*g+c.kp*e+c.ki*y(3)-c.kd*y(2);
 end
 T=min(max(raw,0),c.tmax);di=ei;
 if c.antiwindup && ((raw>=c.tmax && ei>0)||(raw<=0 && ei<0)),di=0;end
 force=0;if t>=c.wind_at-1e-10,force=c.wind;end
 d(k+1,:)=[t ref y(1) y(2) e y(3) raw T force vr rd di];
 if k<n,y=y+dt*[y(2);(T-c.m*g-c.drag*y(2)+force)/c.m;di];end
end
end

function f=newfig(n)
f=figure('Visible','off','Color','w','Units','centimeters','Position',[1 1 18 5+4*n]);
end
function lineplot(ax,d,col,i,label)
colors=[.13 .49 .54;.66 .43 .21;.35 .35 .35];styles={'-','--',':'};
plot(ax,d(:,1),d(:,col),'Color',colors(i,:),'LineStyle',styles{i},'LineWidth',1.3,'DisplayName',label);
end
function pair(S,keys,labels,cols,ylabs,out,name,tend)
f=newfig(numel(cols));
for q=1:numel(cols)
 ax=subplot(numel(cols),1,q);hold(ax,'on');
 for j=1:numel(keys),lineplot(ax,S.(keys{j}),cols(q),j,labels{j});end
 if cols(q)==3,yline(ax,S.(keys{1})(1,2),':','HandleVisibility','off');end
 ylabel(ax,ylabs{q});xlim(ax,[0 tend]);if q==1,legend(ax,'Location','best','Box','off');end
end
xlabel(ax,'时间 / s');savefigs(f,out,name);
end
function savefigs(f,out,name)
for ax=findall(f,'Type','axes')',grid(ax,'on');ax.GridAlpha=.12;ax.Box='off';end
exportgraphics(f,fullfile(out,[name '.pdf']),'ContentType','vector');
exportgraphics(f,fullfile(out,[name '.png']),'Resolution',220);close(f);
end
function m=stepmetrics(d,h0,target)
t=d(:,1);h=d(:,3);q=(h-h0)/(target-h0);a=crossing(t,q,.1);b=crossing(t,q,.9);
bad=find(abs(h-target)>.02*abs(target-h0));ts=0;
if ~isempty(bad),if bad(end)==size(d,1),ts=NaN;else,ts=t(bad(end)+1);end,end
m=struct('rise_10_90_s',b-a,'overshoot_percent',100*max(0,max(q)-1),'settling_2percent_observed_s',ts);
end
function v=crossing(t,q,level)
j=find(q>=level,1);if isempty(j),v=NaN;elseif j==1,v=t(1);else,v=t(j-1)+(level-q(j-1))*(t(j)-t(j-1))/(q(j)-q(j-1));end
end
