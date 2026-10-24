function r=solve_fixedwing(cfg,scene,sceneName,seedKind,corridor,N)
% Direct transcription: 7(N+1)+3N variables and 7N single-step Euler equalities.
% Configurations, equations and checks match the Python implementation.
import casadi.*
cfg.intervals=N;cfg.fragment_steps=N/20;M=N+1;dt=cfg.duration_s/N;
obs=scene.columns;start=cfg.start_state(:)';goal=scene.goal(:)';
sx=[600 150 150 20 .3 .6 .6];su=[2 .08 .4];
scale=[repmat(sx',M,1);repmat(su',N,1)];
[raw,expanded]=astar3d(start(1:3),goal(1:3),obs,cfg);
fprintf('  search finished: %d expanded nodes\n',expanded);
if any(strcmp(seedKind,{'north','south'}))
 y=160;if strcmp(seedKind,'south'),y=-160;end
 point=[300 y 120];[a,ea]=astar3d(start(1:3),point,obs,cfg);[b,eb]=astar3d(point,goal(1:3),obs,cfg);
 raw=[a;b(2:end,:)];expanded=ea+eb;
end
[p,dense,knots,clearance]=spline_seed(raw,obs,cfg);
fprintf('  spline finished\n');
seedSpeed=sum(vecnorm(diff(dense),2,2))/cfg.duration_s;
if strcmp(seedKind,'straight'),p=start(1:3)+linspace(0,1,M)'*(goal(1:3)-start(1:3));dense=p;end
[X0,U0]=inverse_seed(p,dt);X0(1,:)=start;X0(end,:)=goal;
lx=repmat(cfg.state_lower(:)',M,1);hx=repmat(cfg.state_upper(:)',M,1);
lx(:,4:7)=lx(:,4:7)+[.15 .02 .02 .02];hx(:,4:7)=hx(:,4:7)-[.15 .02 .02 .02];
boxes=zeros(0,6);owner=zeros(0,1);
if corridor,[boxes,owner,lx(:,1:3),hx(:,1:3)]=build_corridors(p,obs,cfg);end
assert(all(start>=lx(1,:) & start<=hx(1,:)) && all(goal>=lx(end,:) & goal<=hx(end,:)));
lx(1,:)=start;hx(1,:)=start;lx(end,:)=goal;hx(end,:)=goal;
lb=[reshape(lx',[],1);repmat(cfg.input_lower(:),N,1)]./scale;
ub=[reshape(hx',[],1);repmat(cfg.input_upper(:),N,1)]./scale;
z0=min(max([reshape(X0',[],1);reshape(U0',[],1)]./scale,lb),ub);
fprintf('  initialization finished\n');
X0=reshape(z0(1:7*M).*scale(1:7*M),7,M)';U0=reshape(z0(7*M+1:end).*scale(7*M+1:end),3,N)';
z=MX.sym('z',numel(scale));q=z.*DM(scale);X=reshape(q(1:7*M),7,M);U=reshape(q(7*M+1:end),3,N);
V=X(4,1:N);ga=X(5,1:N);ch=X(6,1:N);phi=X(7,1:N);
F=[V.*cos(ga).*cos(ch);V.*cos(ga).*sin(ch);V.*sin(ga);U(1,:);U(2,:);9.81*tan(phi)./V;U(3,:)];
eq=reshape((X(:,2:end)-X(:,1:N)-dt*F)./repmat(DM(sx'),1,N),7*N,1);
J=dt*(.3*sumsqr(U(1,:)/2)+sumsqr(U(2,:)/.08)+sumsqr(U(3,:)/.4));
g=eq;lbg=zeros(7*N,1);ubg=lbg;
if ~corridor
 for j=1:size(obs,1)
  radius=obs(j,3)+cfg.safety_margin_m+cfg.corridor_node_buffer_m;
  dist=((X(1,:)-obs(j,1)).^2+(X(2,:)-obs(j,2)).^2)/radius^2-1;
  g=[g;dist'];lbg=[lbg;zeros(M,1)];ubg=[ubg;inf(M,1)]; %#ok<AGROW>
 end
end
gf=Function('g',{z},{g});of=Function('J',{z},{J});jf=Function('constraintJacobian',{z},{jacobian(g,z)});df=Function('grad',{z},{gradient(J,z)});
fprintf('  symbolic model finished\n');
jac=full(jf(z0));grad=full(df(z0));err=0;
for col=unique(floor(linspace(7,numel(scale)-4,18)))+1
 d=zeros(size(z0));d(col)=1e-6;
 err=max([err;abs((full(gf(z0+d))-full(gf(z0-d)))/2e-6-jac(:,col)); ...
  abs((full(of(z0+d))-full(of(z0-d)))/2e-6-grad(col))]);
end
assert(err<3e-5,'Automatic derivatives disagree with finite differences.');
fprintf('  derivatives checked: %.3g\n',err);
opts=struct('print_time',false);opts.ipopt=struct('print_level',0,'sb','yes','tol',1e-8, ...
 'constr_viol_tol',1e-8,'max_iter',700,'bound_relax_factor',0,'fixed_variable_treatment','make_parameter');
solver=nlpsol('plan','ipopt',struct('x',z,'f',J,'g',g),opts);
fprintf('  solver initialized\n');
repetitions=1;if isfield(cfg,'benchmark_repetitions'),repetitions=cfg.benchmark_repetitions;end
if repetitions>1,solver('x0',z0,'lbx',lb,'ubx',ub,'lbg',lbg,'ubg',ubg);end
solveTimes=zeros(1,repetitions);
for repeat=1:repetitions
 tic;res=solver('x0',z0,'lbx',lb,'ubx',ub,'lbg',lbg,'ubg',ubg);solveTimes(repeat)=toc;
end
seconds=median(solveTimes);stats=solver.stats();
zz=full(res.x);physical=zz.*scale;XX=reshape(physical(1:7*M),7,M)';UU=reshape(physical(7*M+1:end),3,N)';
gv=full(gf(zz));violation=max([0;abs(gv(1:7*N));-gv(7*N+1:end);lb-zz;zz-ub]);
rollout=zeros(M,7);rollout(1,:)=XX(1,:);
for k=1:N,rollout(k+1,:)=rollout(k,:)+dt*motion(rollout(k,:),UU(k,:));end
clear=inf;for k=1:N,clear=min(clear,segment_clearance(rollout(k,1:3),rollout(k+1,1:3),obs));end
terminal=rollout(end,:)-goal;nodeError=max(vecnorm(rollout(:,1:3)-XX(:,1:3),2,2));
sv=max([0;reshape(cfg.state_lower(:)'-rollout,[],1);reshape(rollout-cfg.state_upper(:)',[],1)]);bv=0;
if corridor
 for k=1:N
  box=boxes(owner(k),:);d=rollout(k:k+1,1:3);
  bv=max([bv;reshape(box(1:3)-d,[],1);reshape(d-box(4:6),[],1)]);
 end
end
checks=struct('max_scaled_constraint_violation',violation,'min_discrete_segment_clearance_m',clear, ...
 'remaining_geometric_margin_m',clear-cfg.safety_margin_m,'terminal_position_error_m',norm(terminal(1:3)), ...
 'terminal_speed_error_m_s',abs(terminal(4)),'terminal_direction_error_deg',max(abs(terminal(5:6)))*180/pi, ...
 'terminal_bank_error_deg',abs(terminal(7))*180/pi,'max_node_reconstruction_error_m',nodeError, ...
 'max_discrete_corridor_violation_m',bv,'discrete_state_bound_violation',sv);
if corridor
 boxClear=inf;for k=1:size(boxes,1),boxClear=min(boxClear,box_clearance(boxes(k,1:3),boxes(k,4:6),obs));end
 checks.whole_box_clearance_m=boxClear;
end
passed=violation<1e-6 && clear>=cfg.safety_margin_m && nodeError<1e-3 && norm(terminal(1:3))<1e-3 ...
 && max(abs(terminal(4:end)))<1e-5 && bv<1e-4 && sv<1e-4;
initialG=full(gf(z0));
r=struct('scene',sceneName,'seed_kind',seedKind,'corridor',corridor,'intervals',N, ...
 'solver_success',logical(stats.success),'accepted',logical(stats.success && passed), ...
 'message',stats.return_status,'objective',full(res.f),'iterations',stats.iter_count,'seconds',seconds,'solve_times_s',solveTimes, ...
 'checks',checks,'derivative_check_max_error',err,'initial_max_scaled_defect',max(abs(initialG(1:7*N))), ...
 'nonlinear_obstacle_constraints',double(~corridor)*size(obs,1)*M,'position_box_bounds',double(corridor)*6*M, ...
 'seed_average_speed_m_s',seedSpeed,'spline_clearance_m',clearance, ...
 'X',XX,'U',UU,'time',(0:N)'*dt,'initial_X',X0,'initial_U',U0, ...
 'raw',raw,'spline',dense,'knots',knots,'boxes',boxes,'owner',owner,'columns',obs, ...
 'astar_expanded',expanded,'rollout',rollout,'history',[stats.iterations.obj(:),stats.iterations.inf_pr(:)]);
end

function [X,U]=inverse_seed(p,dt)
v=diff2(p,dt);V=vecnorm(v,2,2);ga=atan2(v(:,3),vecnorm(v(:,1:2),2,2));ch=unwrap(atan2(v(:,2),v(:,1)));
phi=atan(V.*diff2(ch,dt)/9.81);a=diff2(V,dt);og=diff2(ga,dt);op=diff2(phi,dt);
X=[p V ga ch phi];U=[a og op];U=U(1:end-1,:);
end
function d=diff2(x,h)
d=zeros(size(x));d(2:end-1,:)=(x(3:end,:)-x(1:end-2,:))/(2*h);
d(1,:)=(-3*x(1,:)+4*x(2,:)-x(3,:))/(2*h);
d(end,:)=(3*x(end,:)-4*x(end-1,:)+x(end-2,:))/(2*h);
end
