function RunMe
% Independent MATLAB implementation of the Chapter 4 tracking experiments.
% Install CasADi for MATLAB, then add its folder to the MATLAB path.
root=fileparts(mfilename('fullpath')); addpath(root);
dependency=getenv('CASADI_MATLAB_PATH');
if ~isempty(dependency), addpath(dependency); end
assert(exist('casadi.DM','class')==8,'Add the CasADi MATLAB package to your path.');
import casadi.*
assert(has_conic('osqp'),'This CasADi build must include the OSQP plugin.');
out=fullfile(root,'results'); if ~exist(out,'dir'), mkdir(out); end
S=readmatrix(fullfile(root,'..','reference','state.csv'));
C=readmatrix(fullfile(root,'..','reference','control.csv'));
dt=.18; xr=S(:,2:end); ur=C(:,2:end); steps=size(ur,1);
assert(max(abs(diff(S(:,1))-dt))<1e-12);
for j=1:50
 ur(end+1,:)=zeros(1,3); xr(end+1,:)=xr(end,:)+dt*motion(xr(end,:),ur(end,:));
end
names={'open_loop','mpc20','mpc5','mpc40','ideal20'}; horizons=[0,20,5,40,20];
allruns=cell(1,numel(names));
for j=1:numel(names)
 ideal=strcmp(names{j},'ideal20'); H=horizons(j);
 x=xr(1,:); if ~ideal, x=x+[0,5,3,0,0,3*pi/180,0]; end
 X=zeros(steps+1,7);U=zeros(steps,3);X(1,:)=x;
 times=zeros(steps,1);violations=zeros(steps,1);prev=[];
 for k=0:steps-1
  if H>0
   [plan,~,prev,record]=solve_mpc(x,xr(k+1:k+H+1,:),ur(k+1:k+H,:),prev,dt);
   u=plan(1,:);times(k+1)=record.seconds;violations(k+1)=record.violation;
  else
   u=ur(k+1,:);
  end
  assert(all(abs(u)<=[2,.08,.4]+1e-5),'Input limit failed');
  rate=motion(x,u);
  if ~ideal
   rate(6)=1.06*rate(6);
   if k>=45 && k<67,rate(1:3)=rate(1:3)+[0,1,.3];end
  end
  x=x+dt*rate;X(k+2,:)=x;U(k+1,:)=u;
 end
 err=sqrt(sum((xr(1:steps+1,1:3)-X(:,1:3)).^2,2));
 m=struct('position_rmse_m',sqrt(mean(err.^2)), 'position_final_m',err(end),...
  'position_max_m',max(err),'min_segment_clearance_m',clearance(X),...
  'max_qp_violation',max(violations),'cycle_median_ms',median(times)*1000,...
  'cycle_max_ms',max(times)*1000,'solved_qps',steps*(H>0));
 assert(all(all(X(:,4:7)>=[15,-.2,-.9,-.6]-1e-4)) && all(all(X(:,4:7)<=[25,.2,.9,.6]+1e-4)));
 writetable(array2table([(0:steps)'*dt,X],'VariableNames',{'t','x','y','z','V','gamma','chi','phi'}),fullfile(out,[names{j},'_state.csv']));
 writetable(array2table([(0:steps-1)'*dt,U],'VariableNames',{'t','a','omega_gamma','omega_phi'}),fullfile(out,[names{j},'_control.csv']));
 record=struct('name',names{j},'horizon_steps',H,'metrics',m);
 fid=fopen(fullfile(out,[names{j},'.json']),'w');fprintf(fid,'%s',jsonencode(record));fclose(fid);
 allruns{j}=struct('name',names{j},'X',X,'U',U,'error',err,'metrics',m);
 fprintf('%s %s\n',names{j},jsonencode(m));
end
assert(allruns{2}.metrics.position_rmse_m<allruns{1}.metrics.position_rmse_m);
assert(allruns{2}.metrics.position_final_m<.5);
assert(allruns{5}.metrics.position_max_m<1e-4);
plot_results(out,xr(1:steps+1,:),ur(1:steps,:),allruns,dt);
env=struct('matlab',version,'casadi',casadi.CasadiMeta.version(),'solver','OSQP via CasADi',...
 'dt',dt,'results',{cellfun(@(q)q.metrics,allruns,'UniformOutput',false)});
fid=fopen(fullfile(out,'summary.json'),'w');fprintf(fid,'%s',jsonencode(env));fclose(fid);
fprintf('All five independent MATLAB experiments passed.\n');
end

function y=motion(x,u)
V=x(:,4);ga=x(:,5);ch=x(:,6);phi=x(:,7);
y=[V.*cos(ga).*cos(ch),V.*cos(ga).*sin(ch),V.*sin(ga),u(:,1),u(:,2),9.81*tan(phi)./V,u(:,3)];
end

function [J,B]=jacobian_motion(x)
V=x(4);ga=x(5);ch=x(6);phi=x(7);J=zeros(7);B=zeros(7,3);
J(1,4:6)=[cos(ga)*cos(ch),-V*sin(ga)*cos(ch),-V*cos(ga)*sin(ch)];
J(2,4:6)=[cos(ga)*sin(ch),-V*sin(ga)*sin(ch),V*cos(ga)*cos(ch)];
J(3,4:5)=[sin(ga),V*cos(ga)];J(6,4)=-9.81*tan(phi)/V^2;J(6,7)=9.81/(V*cos(phi)^2);
B(4,1)=1;B(5,2)=1;B(7,3)=1;
end

function [plan,prediction,dU,rec]=solve_mpc(xhat,xr,ur,previous,dt)
import casadi.*
tic;H=size(ur,1);nx=7*(H+1);nv=nx+3*H;umax=[2,.08,.4];
if isempty(previous),seed=zeros(H,3);else,seed=[previous(2:end,:);zeros(1,3)];end
barU=min(umax,max(-umax,ur+seed));seed=barU-ur;barX=xr;
if ~isempty(previous)
 barX(1,:)=xhat;
 for i=1:H,barX(i+1,:)=barX(i,:)+dt*motion(barX(i,:),barU(i,:));end
end
P=sparse(nv,nv);Aeq=sparse(nx,nv);rhs=zeros(nx,1);Aeq(1:7,1:7)=eye(7);rhs(1:7)=(xr(1,:)-xhat)';
Eseed=zeros(H+1,7);Eseed(1,:)=rhs(1:7)';
for i=1:H
 [J,B]=jacobian_motion(barX(i,:));A=eye(7)+dt*J;B=dt*B;
 affine=barX(i,:)'+dt*motion(barX(i,:),barU(i,:))'-A*barX(i,:)'-B*barU(i,:)';
 c=xr(i+1,:)'-A*xr(i,:)'-B*ur(i,:)'-affine;
 rows=7*i+(1:7);state=7*(i-1)+(1:7);input=nx+3*(i-1)+(1:3);
 Aeq(rows,state)=-A;Aeq(rows,rows)=eye(7);Aeq(rows,input)=B;rhs(rows)=c;
 [Jref,~]=jacobian_motion(xr(i+1,:));I=eye(7);C=[I(1:3,:)/5;Jref(1:3,:)/2];
 P(rows,rows)=2*(C'*C);P(input,input)=2*.05*diag(1./umax.^2);
 Eseed(i+1,:)=(A*Eseed(i,:)'-B*seed(i,:)'+c)';
end
xmin=[-inf,-inf,-inf,15,-.2,-.9,-.6];xmax=[inf,inf,inf,25,.2,.9,.6];
lo=[reshape((xr-xmax)',[],1);reshape((-umax-ur)',[],1)];
hi=[reshape((xr-xmin)',[],1);reshape((umax-ur)',[],1)];
opts=struct('print_time',false,'error_on_fail',false,'warm_start_primal',true,'warm_start_dual',false);
opts.osqp=struct('verbose',false,'eps_abs',1e-6,'eps_rel',1e-6,'max_iter',10000,'polish',true);
Q=conic('tracking_qp','osqp',struct('h',sparsity(DM(P)),'a',sparsity(DM(Aeq))),opts);
z0=[reshape(Eseed',[],1);reshape(seed',[],1)];
answ=Q('h',P,'g',zeros(nv,1),'a',Aeq,'lba',rhs,'uba',rhs,'lbx',lo,'ubx',hi,'x0',z0);
st=Q.stats();z=full(answ.x);
v=max([0;abs(Aeq*z-rhs);lo-z;z-hi]);
assert(st.success && isfinite(v) && v<1e-4,'QP failed or violates its constraints.');
E=reshape(z(1:nx),7,[])';dU=reshape(z(nx+1:end),3,[])';plan=ur+dU;prediction=xr-E;
rec=struct('seconds',toc,'violation',v);
end

function result=clearance(X)
obstacles=[200,-140,155;400,140,155];result=inf;
for j=1:size(obstacles,1)
 a=X(1:end-1,1:2);b=X(2:end,1:2);d=b-a;
 t=min(1,max(0,sum((obstacles(j,1:2)-a).*d,2)./max(sum(d.^2,2),1e-15)));
 result=min(result,min(sqrt(sum((a+t.*d-obstacles(j,1:2)).^2,2))-obstacles(j,3)));
end
end

function plot_results(out,xr,ur,runs,dt)
t=(0:size(xr,1)-1)'*dt;colors=[.66,.43,.21;.13,.49,.54];
f=figure('Visible','off','Color','w','Position',[100,100,1100,440]);
subplot(1,2,1);hold on;theta=linspace(0,2*pi,120);
for c=[200,-140,155;400,140,155]'
 fill(c(1)+c(3)*cos(theta),c(2)+c(3)*sin(theta),[.88,.89,.90],'EdgeColor',[.5,.5,.5],'HandleVisibility','off');
end
plot(xr(:,1),xr(:,2),'k--','LineWidth',1.4);
for i=1:2,plot(runs{i}.X(:,1),runs{i}.X(:,2),'Color',colors(i,:),'LineWidth',1.5);end
axis equal;xlim([-10,615]);ylim([-225,225]);xlabel('x / m');ylabel('y / m');grid on;
legend('Nominal','Open loop','MPC H=20','Location','northwest');
subplot(1,2,2);hold on;plot(t,xr(:,3),'k--','LineWidth',1.4);
for i=1:2,plot(t,runs{i}.X(:,3),'Color',colors(i,:),'LineWidth',1.5);end
xlabel('Time / s');ylabel('z / m');grid on;exportgraphics(f,fullfile(out,'flight_views.png'),'Resolution',180);close(f);
f=figure('Visible','off','Color','w','Position',[100,100,1050,380]);
subplot(1,2,1);plot(t,runs{1}.error,t,runs{2}.error,'LineWidth',1.4);legend('Open loop','MPC H=20');grid on;xlabel('Time / s');ylabel('Position error / m');
subplot(1,2,2);plot(t,runs{3}.error,t,runs{2}.error,t,runs{4}.error,'LineWidth',1.4);legend('H=5','H=20','H=40');grid on;xlabel('Time / s');ylabel('Position error / m');
exportgraphics(f,fullfile(out,'errors.png'),'Resolution',180);close(f);
f=figure('Visible','off','Color','w','Position',[100,100,1000,650]);limits=[2,.08,.4];labels={'a / (m/s^2)','omega gamma / (rad/s)','omega phi / (rad/s)'};
for j=1:3
 subplot(3,1,j);stairs(t(1:end-1),ur(:,j),'k--');hold on;stairs(t(1:end-1),runs{2}.U(:,j),'LineWidth',1.3);yline(limits(j),':');yline(-limits(j),':');ylabel(labels{j});grid on;
end
xlabel('Time / s');exportgraphics(f,fullfile(out,'inputs.png'),'Resolution',180);close(f);
end
