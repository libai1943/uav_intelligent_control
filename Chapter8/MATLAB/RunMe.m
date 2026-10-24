function RunMe
% Independent MATLAB textbook implementation. One entry runs all comparisons.
out=fullfile(fileparts(mfilename('fullpath')),'results');if ~exist(out,'dir'),mkdir(out);end

names={'passive','active','delayed','force_ambiguity','capacity_loss'};cfg={'passive',.65,0,0;'active',.65,0,0;'active',.65,.5,0;'active',1,0,-5.4936;'active',.5,0,0};all={};
for i=1:5,d=sim8(cfg{i,:});all{i}=d;savecsv(out,names{i},d,'t,h,v,e,U,T,alpha,alpha_hat,residual,alarm,reconfigured,U_raw');assert(max(d(:,5))<=28&&min(d(:,5))>=0);assert(~any(d(d(:,1)<3,10)~=0));end
panel(out,'fault_response',all(1:3),{'Fixed PD','Diagnosis and compensation','Extra delay 0.5 s'},[2 3 5],{'Height / m','Velocity / (m/s)','Nominal command / N'});
panel(out,'diagnosis',all([2 4]),{'Effectiveness 0.65','Healthy actuator with force'},[9 8 2],{'Residual / N','Estimated effectiveness','Height / m'});
panel(out,'capacity_loss',all(5),{'Effectiveness 0.50'},[2 5 6],{'Height / m','Nominal command / N','Actual thrust / N'});
assert(abs(all{1}(end,4)-(1-.65)*15.696/(.65*40))<1e-4);assert(abs(all{2}(end,4))<1e-4);assert(all{5}(end,2)==0);assert(any(all{4}(:,10)>0));report(out,names,all);
f=figure('Visible','off','Color','w');hold on;labels={'Healthy','Left effectiveness 0.8','Left effectiveness 0.5'};as=[1 .8 .5];for i=1:3,ul=[0 14 14 0 0];ur=[0 0 14 14 0];plot(as(i)*ul+ur,ur-as(i)*ul,'LineWidth',1.4);end;plot(15.696,0,'ko');yline(0);xlabel('Total thrust / N');ylabel('Roll torque / arm (N)');legend([labels {'Hover target'}],'Location','northwest');grid on;exportgraphics(f,fullfile(out,'allocation.pdf'),'ContentType','vector');exportgraphics(f,fullfile(out,'allocation.png'),'Resolution',160);close(f);

fprintf('Chapter 8: all comparisons and checks completed.\n');
end

function d=sim8(kind,alpha,delay,force)
dt=.01;tf=10;h=5;v=0;prev_v=0;prev_u=1.6*9.81;fy=prev_u;fu=prev_u;ahat=1;count=0;alarm=false;td=Inf;
qr=exp(-dt/.12);qa=exp(-dt/.20);d=zeros(round(tf/dt)+2,12);n=0;
for k=0:round(tf/dt)
 t=k*dt;res=0;
 if k>0
  y=1.6*((v-prev_v)/dt+9.81);fy=qr*fy+(1-qr)*y;fu=qr*fu+(1-qr)*prev_u;res=fu-fy;
  if fu>=5,ahat=qa*ahat+(1-qa)*max(.3,min(1.1,fy/fu));end
  if res>1.6,count=count+1;else,count=0;end
  if count>=12&&~alarm,alarm=true;td=t;end
 end
 enabled=strcmp(kind,'active')&&alarm&&t>=td+delay-1e-12;used=1;if enabled,used=ahat;end
 desired=1.6*9.81+40*(5-h)-16*v;raw=desired/used;U=max(0,min(28,raw));a=1;F=0;if t>=3,a=alpha;F=force;end;T=a*U;
 n=n+1;d(n,:)=[t h v 5-h U T a ahat res double(alarm) double(enabled) raw];if k==round(tf/dt),break,end
 an=(T-1.6*9.81+F)/1.6;newh=h+dt*v;newv=v+dt*an;
 if newh<=0,frac=-h/v;d(n+1,:)=d(n,:);n=n+1;d(n,1)=t+frac;d(n,2)=0;d(n,3)=v+frac*an;d(n,4)=5;break,end
 prev_v=v;prev_u=U;h=newh;v=newv;
end
d=d(1:n,:);
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
