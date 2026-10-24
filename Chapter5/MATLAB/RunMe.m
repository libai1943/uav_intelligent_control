function RunMe
% Independent MATLAB textbook implementation. One entry runs all comparisons.
out=fullfile(fileparts(mfilename('fullpath')),'results');if ~exist(out,'dir'),mkdir(out);end

names={};all={};cs={'rise','small','force'};hs=[2.6 2.91 3];fs=[0 0 -.2];modes={'quantized','continuous'};
for i=1:3
 series={};for j=1:2,name=[cs{i} '_' modes{j}];d=sim5(j==1,hs(i),fs(i));names{end+1}=name;all{end+1}=d;series{j}=d;savecsv(out,name,d,'t,h,v,e,T');end
 panel(out,cs{i},series,{'Integer quantization','Continuous calculation'},[2 3 5],{'Height / m','Velocity / (m/s)','Thrust / N'});
end
assert(max(abs(all{3}(:,4)-.09))<1e-10);assert(abs(all{6}(end,4)-1/35)<1e-4);assert(abs(all{2}(end,4))<1e-4);assert(abs(fuzzy(.4,0,true)-2)<1e-12);
report(out,names,all);

fprintf('Chapter 5: all comparisons and checks completed.\n');
end

function u=fuzzy(e,ec,quantized)
c=-6:2:6;q=-6:6;rules=[1 1 1 1 2 4 4;1 1 1 1 2 4 4;2 2 2 2 4 5 5;2 2 3 4 5 6 6;3 3 4 6 6 6 6;4 4 6 7 7 7 7;4 4 6 7 7 7 7];
E=max(-6,min(6,5*e));EC=max(-6,min(6,10*ec));if quantized,E=round(E);EC=round(EC);end
me=max(0,1-abs(E-c)/2);mc=max(0,1-abs(EC-c)/2);C=zeros(1,13);
for i=1:7,for j=1:7,fire=min(me(i),mc(j));mf=max(0,1-abs(q-c(rules(i,j)))/2);C=max(C,min(fire,mf));end,end
U=sum(q.*C)/sum(C);if quantized,U=round(U);end;u=.5*U;
end
function d=sim5(quantized,h,force)
dt=.01;t=(0:round(30/dt))'*dt;d=zeros(numel(t),5);v=0;lut=zeros(13);
if quantized,for i=-6:6,for j=-6:6,lut(i+7,j+7)=fuzzy(i/5,j/10,true);end,end,end
for k=1:numel(t)
 e=3-h;ec=-v;if quantized,i=max(-6,min(6,round(5*e)));j=max(-6,min(6,round(10*ec)));u=lut(i+7,j+7);else,u=fuzzy(e,ec,false);end
 T=max(0,min(22,14.7+u));d(k,:)=[t(k) h v 3-h T];an=(T-14.7-1.5*v+force)/1.5;h=h+dt*v;v=v+dt*an;
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
