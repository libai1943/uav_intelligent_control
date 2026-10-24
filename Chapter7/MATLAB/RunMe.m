function RunMe
% Independent MATLAB textbook implementation. One entry runs all comparisons.
out=fullfile(fileparts(mfilename('fullpath')),'results');if ~exist(out,'dir'),mkdir(out);end

names={'light_down','heavy_down','heavy_up','varying_force','noise_phi005','noise_phi002','limited'};
cfg={1.6,'down',.2,.05,false,28,12;1.92,'down',.2,.05,false,28,12;1.92,'up',-.2,.05,false,28,12;1.92,'sine',.2,.05,false,28,12;1.92,'down',.2,.05,true,28,12;1.92,'down',.2,.02,true,28,12;1.6,'down',0,.05,false,17.8,4};all={};
for i=1:7,d=sim7(cfg{i,1:6},.002,cfg{i,7});all{i}=d;savecsv(out,names{i},d,'t,h,v,e,T,Tcmd,s,F,s_meas,n_h,n_v');if i<=4,assert(max(abs(d(:,4)))<=.200001);assert(max(abs(d(:,7)))<=.200001);assert(max(abs(d(d(:,1)>=4,4)))<.05);assert(max(abs(d(:,5)-d(:,6)))<1e-12);end,end
panel(out,'range_comparison',all(1:4),{'1.6 kg, downward force','1.92 kg, downward force','1.92 kg, upward force','1.92 kg, varying force'},[4 7 5],{'Height error / m','Combined error / (m/s)','Thrust / N'});
panel(out,'measurement_comparison',all([2 5 6]),{'Exact feedback','Noise, width 0.05','Noise, width 0.02'},[4 5],{'True height error / m','Actual thrust / N'});
panel(out,'limited_thrust',all(7),{'Limit 17.8 N'},[2 5],{'Height / m','Thrust / N'});
fine=sim7(1.92,'down',.2,.05,false,28,.001,12);assert(max(abs(all{2}(:,2)-fine(1:2:end,2)))<.002);assert(abs(all{2}(end,4)-((1.92-1.6)*9.81+2.6)/(1.6*92.5))<1e-4);report(out,names,all);

fprintf('Chapter 7: all comparisons and checks completed.\n');
end

function d=sim7(m,fmode,e0,phi,noisy,tmax,dt,tf)
t=(0:round(tf/dt))'*dt;d=zeros(numel(t),11);h=3-e0;v=0;
for k=1:numel(t)
 tk=t(k);F=-2.6;if strcmp(fmode,'up'),F=2.6;elseif strcmp(fmode,'sine'),F=2.6*sin(2*pi*.6*tk);end
 nh=0;nv=0;if noisy,nh=.002*sin(2*pi*8*tk);nv=.01*sin(2*pi*11*tk+.4);end
 em=3-h-nh;ev=-v-nv;s=ev+em;u=ev+2.5*s+4.5*max(-1,min(1,s/phi));cmd=1.6*(9.81+u);T=max(0,min(tmax,cmd));d(k,:)=[tk h v 3-h T cmd -v+3-h F s nh nv];
 an=(T-m*9.81+F)/m;h=h+dt*v;v=v+dt*an;
end
end

function savecsv(out,name,d,headers)
assert(all(isfinite(d(:))));p=fullfile(out,[name '.csv']);f=fopen(p,'w');fprintf(f,'%s\n',headers);fclose(f);dlmwrite(p,d,'-append','delimiter',',','precision','%.17g');
end
function panel(out,name,series,labels,cols,ylabs)
f=figure('Visible','off','Color','w','Position',[100 100 850 220*numel(cols)]);tl=tiledlayout(numel(cols),1,'TileSpacing','compact','Padding','compact');
cc=[.13 .49 .54;.66 .43 .21;.42 .34 .59;.32 .32 .32;.30 .50 .28];styles={'-','--','-.',':','--'};
for j=1:numel(cols)
 ax=nexttile;hold(ax,'on');
 for k=1:numel(series),d=series{k};plot(ax,d(:,1),d(:,cols(j)),'Color',cc(mod(k-1,5)+1,:),'LineStyle',styles{mod(k-1,5)+1},'LineWidth',1.3);end
 ylabel(ylabs{j});grid on;box off;if j==1,legend(labels,'Location','northoutside','NumColumns',min(3,numel(series)),'Box','off');end
end
xlabel(tl,'Time / s');exportgraphics(f,fullfile(out,[name '.pdf']),'ContentType','vector');exportgraphics(f,fullfile(out,[name '.png']),'Resolution',160);close(f);
end
function report(out,names,all)
q=struct;for k=1:numel(names),d=all{k};q.(names{k})=struct('final_error_m',d(end,4),'peak_error_m',max(abs(d(:,4))),'end_time_s',d(end,1));end
q.checks='Analytical balances, finite states and execution limits verified';f=fopen(fullfile(out,'validation.json'),'w');fprintf(f,'%s',jsonencode(q));fclose(f);
end
