function RunMe
% Independent MATLAB textbook implementation. One entry runs all comparisons.
out=fullfile(fileparts(mfilename('fullpath')),'results');if ~exist(out,'dir'),mkdir(out);end

names={'off','frozen','online'};all={};for i=1:3,d=sim6(names{i});all{i}=d;savecsv(out,names{i},d,'t,h,v,e,T,u_nn,u_fb,W1,W2,b1,b2,v1,v2,c');end
panel(out,'learning_comparison',all,{'No learning','Freeze after 50 s','Online learning'},[4 6 7 5],{'Height error / m','Neural correction / N','Feedback correction / N','Thrust / N'});
d=all{3};series={};labels={};for j=8:14,series{end+1}=[d(:,1) d(:,j)];labels{end+1}=sprintf('Parameter %d',j-7);end;panel(out,'weights',series,labels,2,{'Network parameters'});
assert(abs(all{1}(end,4)-.23)<1e-6);assert(abs(all{2}(end,4)-.4/6)<1e-6);assert(abs(all{3}(end,4))<1e-4);assert(abs(all{3}(end,6)-1.38)<1e-4);assert(max(abs(all{2}(5001:end,8:14)-all{2}(5001,8:14)),[],'all')==0);report(out,names,all);

fprintf('Chapter 6: all comparisons and checks completed.\n');
end

function d=sim6(mode)
dt=.01;t=(0:round(100/dt))'*dt;d=zeros(numel(t),14);h=3;v=0;theta=[.3;-.3;.2;-.2;0;0;0];
for k=1:numel(t)
 H=tanh(theta(1:2)+theta(3:4));un=theta(5:6)'*H+theta(7);uf=6*(3-h)-5*v;T=max(0,min(24,14.7+un+uf));d(k,:)=[t(k) h v 3-h T un uf theta'];
 F=0;if t(k)>=60,F=-.4;end;an=(T-1.6*9.8-1.6*v+F)/1.6;h=h+dt*v;v=v+dt*an;
 learn=strcmp(mode,'online')||(strcmp(mode,'frozen')&&t(k)<50);
 if learn,dh=theta(5:6).*(1-H.^2);grad=[dh;dh;H;1];theta=theta+.006*uf*grad;end
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
