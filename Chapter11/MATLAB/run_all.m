function results = run_all()
%RUN_ALL Chapter 11: cargo LP and two-aircraft four-task scheduling.
% Uses Optimization Toolbox when present; otherwise local simplex and
% branch-and-bound solvers reproduce the same small models.
% Run: change to this code directory and type run_all.
% The textbook's scheduling time unit is minute.
% Outputs are written to ../results/matlab/.

here = fileparts(mfilename('fullpath'));
outdir = fullfile(here, '..', 'results', 'matlab');
if ~exist(outdir, 'dir'), mkdir(outdir); end
tol = 1e-5;
results.environment.matlab_version = version;
results.environment.computer = computer;
results.environment.optimization_toolbox = ver('optim');
results.environment.validation_tolerance = tol;
results.single_aircraft_lp = cargo_lp(tol);
results.two_aircraft_transport_lp = transport_lp(tol);

names = {'baseline', 'deadline_3_is_7', 'aircraft_2_unavailable'};
for q = 1:numel(names)
    data = base_data();
    if q == 2, data.d(3) = 7; end
    if q == 3, data.available(2) = 0; end
    solved = solve_schedule(data, [], tol);
    enumeration = enumerate_schedules(data, tol);
    if isfinite(enumeration.optimal_objective)
        assert(solved.exitflag == 1, 'MILP did not certify optimality.');
        assert(abs(solved.objective - enumeration.optimal_objective) <= tol);
    else
        assert(solved.exitflag == -2, 'Expected infeasible MILP.');
    end
    case_result.data = data;
    case_result.milp = solved;
    case_result.enumeration = enumeration;
    case_result.decoder_check = check_decoder(data, enumeration, tol);
    case_result.split_decoder_check = check_split_decoder(data, enumeration, tol);
    results.scheduling.(names{q}) = case_result;
    if isfinite(enumeration.optimal_objective)
        selected = enumeration.optimal_earliest_schedules(1);
        task = (1:numel(data.r))';
        aircraft = selected.assignment(:);
        start_min = selected.starts(:);
        complete_min = selected.completions(:);
        writetable(table(task, aircraft, start_min, complete_min), ...
            fullfile(outdir, [names{q}, '_schedule.csv']));
        fprintf('%s: MILP=%.9g, enumeration=%.9g\n', names{q}, ...
            solved.objective, enumeration.optimal_objective);
    else
        fprintf('%s: infeasible in MILP and independent enumeration.\n', names{q});
    end
end
results.wrong_constant_M_8 = solve_schedule(base_data(), 8, tol);
assert(results.wrong_constant_M_8.exitflag == -2);
results.lp_relaxation_baseline = solve_relaxation(base_data(), []);
results.lp_relaxation_M_1000 = solve_relaxation(base_data(), 1000);
baseline_data = base_data();
results.physical_workload_lower_bound_baseline = ...
    sum(min(baseline_data.p, [], 1)) / 2;
save(fullfile(outdir, 'results.mat'), 'results');
text = jsonencode(results);
fid = fopen(fullfile(outdir, 'results.json'), 'w', 'n', 'UTF-8');
assert(fid >= 0, 'Cannot open results.json for writing.');
cleanup = onCleanup(@() fclose(fid));
fwrite(fid, text, 'char');
fprintf('Cargo: q_A=4 kg, q_B=6 kg, net return=40 yuan, fuel=1.4 L.\n');
fprintf('Transportation: [q11,q12,q21,q22]=[6,0,0,4] kg; minimum cost=16.\n');
fprintf('All independent checks passed; results are in %s\n', outdir);
end

function result = cargo_lp(tol)
% F = 0.4 + 0.1*(q_A+q_B) L, fuel price 10 yuan/L.
% Cargo gross margins before fuel are 6 and 5 yuan/kg.
% Net return = 5*q_A+4*q_B-4; the constant -4 does not change the optimizer.
A = [1 1; 2 1]; b = [10; 14]; c = [5; 4];

[x,fval,exitflag] = solve_lp(-c, A, b, [], [], [0;0], []);
assert(exitflag == 1);
assert(norm(x-[4;6], inf) <= tol);
Aall = [A; -eye(2)]; ball = [b;0;0];
pairs = nchoosek(1:4,2);
vertices = [];
for k=1:size(pairs,1)
    G = Aall(pairs(k,:),:);
    if abs(det(G)) <= tol, continue; end
    point = G \ ball(pairs(k,:));
    if all(Aall*point <= ball+tol)
        vertices(end+1,:) = point'; %#ok<AGROW>
    end
end
vertices = unique(vertices, 'rows');
assert(abs(max(vertices*c-4)-(-fval-4)) <= tol);
result.variables_kg = x';
result.net_return_yuan = -fval-4;
result.fuel_L = .4+.1*sum(x);
result.resource_use = (A*x)';
result.resource_slack = (b-A*x)';
result.vertices_qA_qB_return = [vertices, vertices*c-4];
result.upper_bound_certificate = ...
    '5*q_A+4*q_B-4=3*(q_A+q_B)+(2*q_A+q_B)-4<=40';
changed = {[10;15], [11;14]};
labels = {'warehouse_15', 'payload_11'};
for k=1:2
    [xx, ff, ef] = solve_lp(-c,A,changed{k},[],[],[0;0],[]);
    assert(ef == 1);
    result.sensitivities.(labels{k}).variables_kg = xx';
    result.sensitivities.(labels{k}).net_return_yuan = -ff-4;
    result.sensitivities.(labels{k}).fuel_L = .4+.1*sum(xx);
end
end

function result = transport_lp(tol)
% Order of the four continuous variables: q11,q12,q21,q22.
% Each aircraft has capacity 6; receiver demands are respectively 6 and 4.
costs=[2;5;4;1];
A=[1 1 0 0;0 0 1 1]; b=[6;6];
Aeq=[1 0 1 0;0 1 0 1]; beq=[6;4];

[x,fval,exitflag]=solve_lp(costs,A,b,Aeq,beq,zeros(4,1),[]);
assert(exitflag==1);
assert(norm(x-[6;0;0;4],inf)<=tol);
violation=max([0;A*x-b;abs(Aeq*x-beq);-x]);
assert(violation<=tol);
% Substituting receiver demands gives cost=16+2*q21+4*q12 >=16.
certificate_dual=[2;1]; reduced_cost=costs-Aeq'*certificate_dual;
assert(all(reduced_cost>=0));
lower_bound=beq'*certificate_dual;
assert(abs(fval-lower_bound)<=tol);
result.variable_order={'q11','q12','q21','q22'};
result.variables_kg=x'; result.unit_cost=costs';
result.minimum_cost=fval;
result.aircraft_load_kg=(A*x)';
result.receiver_deliveries_kg=(Aeq*x)';
result.maximum_linear_constraint_violation=violation;
result.lower_bound_certificate='cost=16+2*q21+4*q12>=16';
result.exact_lower_bound=lower_bound;
result.certificate_reduced_costs=reduced_cost';
result.checked_absolute_gap=fval-lower_bound;
result.validation_tolerance=tol;
end

function data = base_data()
data.p = [4 6 5 7; 7 4 6 5];
data.r = [0 0 2 1];
data.d = [12 12 14 13];
data.available = [1 1];
end

function model = make_model(data, constant_M)
% Exactly the chapter's big-M conditional disjunctive model.
[m,n] = size(data.p);
pairs = nchoosek(1:n,2);
nx = m*n; ny = size(pairs,1);
ix = reshape(1:nx,n,m)';
iy = (nx+1):(nx+ny);
is = (nx+ny+1):(nx+ny+n);
ic = (nx+ny+n+1):(nx+ny+2*n);
iC = nx+ny+2*n+1; nv = iC;
obj = zeros(nv,1); obj(iC)=1;
lb = zeros(nv,1); ub = inf(nv,1);
ub(1:nx+ny)=1;
for i=1:m, ub(ix(i,:))=data.available(i); end
lb(is)=data.r; ub(is)=data.d; ub(ic)=data.d; ub(iC)=max(data.d);
Aeq=zeros(2*n,nv); beq=zeros(2*n,1);
A=zeros(n+2*m*ny,nv); b=zeros(n+2*m*ny,1);
for j=1:n
    Aeq(j,ix(:,j))=1; beq(j)=1;
    Aeq(n+j,ic(j))=1; Aeq(n+j,is(j))=-1;
    Aeq(n+j,ix(:,j))=-data.p(:,j)';
    A(j,ic(j))=1; A(j,iC)=-1;
end
M=max(0,data.d(:)-data.r(:)');
if ~isempty(constant_M), M(:)=constant_M; end
row=n;
for q=1:ny
    j=pairs(q,1); k=pairs(q,2);
    for i=1:m
        % c_j-s_k+M_jk*y+M_jk*x_ij+M_jk*x_ik <= 3*M_jk.
        row=row+1;
        A(row,ic(j))=1; A(row,is(k))=-1;
        A(row,iy(q))=M(j,k);
        A(row,ix(i,j))=M(j,k); A(row,ix(i,k))=M(j,k);
        b(row)=3*M(j,k);
        % c_k-s_j-M_kj*y+M_kj*x_ij+M_kj*x_ik <= 2*M_kj.
        row=row+1;
        A(row,ic(k))=1; A(row,is(j))=-1;
        A(row,iy(q))=-M(k,j);
        A(row,ix(i,j))=M(k,j); A(row,ix(i,k))=M(k,j);
        b(row)=2*M(k,j);
    end
end
model.obj=obj; model.intcon=1:(nx+ny);
model.A=A; model.b=b; model.Aeq=Aeq; model.beq=beq;
model.lb=lb; model.ub=ub; model.ix=ix; model.iy=iy;
model.is=is; model.ic=ic; model.iC=iC; model.M=M;
end

function result = solve_schedule(data, constant_M, tol)
model=make_model(data,constant_M);

[z,fval,exitflag,output]=solve_milp(model.obj,model.intcon, ...
    model.A,model.b,model.Aeq,model.beq,model.lb,model.ub);
result.exitflag=exitflag; result.solver_output=output;
if exitflag==-2
    result.status_text='Infeasible model under the specified constraints.';
elseif exitflag==1
    result.status_text='Optimal solution returned within solver tolerances.';
else
    result.status_text='Inspect solver_output and independent checks.';
end
% Store MATLAB's raw output fields; relativegap definitions vary by version.
if isempty(z), return; end
xx=z(model.ix); [~,assignment]=max(xx,[],1);
assert(max(abs(xx(:)-round(xx(:)))) <= tol);
starts=z(model.is)'; completions=z(model.ic)';
validate_schedule(data,assignment,starts,completions,tol);
violation=max([0; model.A*z-model.b; abs(model.Aeq*z-model.beq); ...
    model.lb-z; z-model.ub]);
assert(violation<=tol);
result.objective=fval;
result.schedule_makespan=max(completions);
result.x=xx;
result.assignment_aircraft_1_based=assignment;
result.starts=starts; result.completions=completions;
result.directional_M=model.M;
result.maximum_linear_constraint_violation=violation;
result.validation_tolerance=tol;
end

function result = solve_relaxation(data, constant_M)
model=make_model(data,constant_M);

[z,fval,exitflag]=solve_lp(model.obj,model.A,model.b, ...
    model.Aeq,model.beq,model.lb,model.ub);
result.exitflag=exitflag;
if exitflag==1
    result.objective=fval; result.x=z(model.ix);
    result.starts=z(model.is)'; result.completions=z(model.ic)';
end
end

function validate_schedule(data,assignment,starts,completions,tol)
n=numel(data.r);
assert(all(starts>=data.r-tol));
assert(all(completions<=data.d+tol));
for j=1:n
    i=assignment(j);
    assert(data.available(i)==1);
    assert(abs(completions(j)-starts(j)-data.p(i,j))<=tol);
end
for j=1:n-1
    for k=j+1:n
        if assignment(j)==assignment(k)
            assert(completions(j)<=starts(k)+tol || ...
                completions(k)<=starts(j)+tol);
        end
    end
end
end

function orders = list_orders(group)
if isempty(group), orders={[]}; return; end
all=sortrows(perms(group));
orders=cell(size(all,1),1);
for k=1:size(all,1), orders{k}=all(k,:); end
end

function schedule = decode_orders(data,assignment,orders)
n=numel(data.r); starts=zeros(1,n); completions=zeros(1,n);
for i=1:numel(orders)
    clock=0;
    for j=orders{i}
        starts(j)=max(clock,data.r(j));
        completions(j)=starts(j)+data.p(i,j);
        clock=completions(j);
    end
end
schedule.assignment=assignment;
schedule.orders=orders;
schedule.starts=starts; schedule.completions=completions;
schedule.makespan=max(completions);
end

function result = enumerate_schedules(data,tol)
% For this two-aircraft instance, inspect all assignments and local orders.
n=numel(data.r); best=inf; tested=0; feasible=0;
optimizers=struct('assignment',{},'orders',{},'starts',{},'completions',{},'makespan',{}); feasible_schedules=optimizers;
for mask=0:2^n-1
    assignment=1+bitget(mask,1:n);
    if any(data.available(assignment)==0), continue; end
    a=list_orders(find(assignment==1)); b=list_orders(find(assignment==2));
    for p=1:numel(a)
        for q=1:numel(b)
            tested=tested+1;
            schedule=decode_orders(data,assignment,{a{p},b{q}});
            if any(schedule.completions>data.d+tol), continue; end
            feasible=feasible+1;
            feasible_schedules(end+1)=schedule; %#ok<AGROW>
            validate_schedule(data,assignment,schedule.starts,schedule.completions,tol);
            if schedule.makespan<best-tol
                best=schedule.makespan; optimizers=struct('assignment',{},'orders',{},'starts',{},'completions',{},'makespan',{});
            end
            if abs(schedule.makespan-best)<=tol
                optimizers(end+1)=schedule; %#ok<AGROW>
            end
        end
    end
end
result.enumerated_assignment_order_combinations=tested;
result.feasible_assignment_order_combinations=feasible;
result.optimal_objective=best;
result.has_feasible_schedule=isfinite(best);
result.optimal_earliest_schedules=optimizers;
result.all_feasible_earliest_schedules=feasible_schedules;
end

function result = check_decoder(data,enumeration,tol)
% Encoding is a task permutation plus a per-task aircraft assignment.
% Repeated global interleavings may decode to the same pair of local orders.
n=numel(data.r); permutations=perms(1:n);
best=inf; total=0; feasible=0;
for mask=0:2^n-1
    assignment=1+bitget(mask,1:n);
    if any(data.available(assignment)==0), continue; end
    for q=1:size(permutations,1)
        total=total+1;
        permutation=permutations(q,:);
        orders={permutation(assignment(permutation)==1), ...
            permutation(assignment(permutation)==2)};
        schedule=decode_orders(data,assignment,orders);
        if any(schedule.completions>data.d+tol), continue; end
        feasible=feasible+1; best=min(best,schedule.makespan);
    end
end
if isfinite(best)
    assert(abs(best-enumeration.optimal_objective)<=tol);
else
    assert(isinf(enumeration.optimal_objective));
end
result.enumerated_encodings=total;
result.feasible_encodings=feasible;
result.best_objective=best;
result.matches_exact_schedule_enumeration=true;
result.automatic_constraints={'unique assignment','release time','same-aircraft nonoverlap'};
result.checked_not_automatic={'deadline','aircraft availability'};
end

function result = check_split_decoder(data,enumeration,tol)
% Permutation plus a cut gives exactly one pair of local ordered lists.
n=numel(data.r); permutations=perms(1:n);
best=inf; total=0; feasible=0;
for q=1:size(permutations,1)
    permutation=permutations(q,:);
    for cut=0:n
        total=total+1;
        orders={permutation(1:cut),permutation(cut+1:end)};
        assignment=2*ones(1,n); assignment(orders{1})=1;
        schedule=decode_orders(data,assignment,orders);
        if any(data.available(assignment)==0) || ...
                any(schedule.completions>data.d+tol), continue; end
        feasible=feasible+1; best=min(best,schedule.makespan);
    end
end
if isfinite(best)
    assert(abs(best-enumeration.optimal_objective)<=tol);
else
    assert(isinf(enumeration.optimal_objective));
end
assert(feasible==enumeration.feasible_assignment_order_combinations);
result.enumerated_encodings=total;
result.feasible_encodings=feasible;
result.best_objective=best;
result.one_to_one_with_pairs_of_local_ordered_lists=true;
result.matches_exact_schedule_enumeration=true;
end

function [x,fval,flag,output]=solve_lp(f,A,b,Aeq,beq,lb,ub)
if exist('linprog','file')==2
    options=optimoptions('linprog','Display','none');
    [x,fval,flag,output]=linprog(f,A,b,Aeq,beq,lb,ub,options);
else
    [x,fval,flag,output]=ch11_lp(f,A,b,Aeq,beq,lb,ub);
end
end

function [x,fval,flag,output]=solve_milp(f,intcon,A,b,Aeq,beq,lb,ub)
if exist('intlinprog','file')==2
    options=optimoptions('intlinprog','Display','off','RelativeGapTolerance',0,'AbsoluteGapTolerance',0);
    [x,fval,flag,output]=intlinprog(f,intcon,A,b,Aeq,beq,lb,ub,options);
else
    [x,fval,flag,output]=ch11_milp(f,intcon,A,b,Aeq,beq,lb,ub);
end
end
