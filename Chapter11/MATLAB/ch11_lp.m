function [x,fval,exitflag,output] = ch11_lp(f,A,b,Aeq,beq,lb,ub)
% Small educational LP solver: two-phase simplex with Bland pivoting.
% Handles this chapter's finite lower bounds, Ax<=b, Aeq*x=beq.
% Uses base MATLAB only. All arithmetic is local; no Python bridge.
n=numel(f); f=f(:); tol=1e-9; x=[]; fval=[]; exitflag=-2;
output=struct('algorithm','two-phase simplex','iterations',0);
if isempty(lb),lb=zeros(n,1);end
if isempty(ub),ub=inf(n,1);end
lb=lb(:);ub=ub(:);
assert(all(isfinite(lb)), 'This teaching solver requires finite lower bounds.');
if any(ub<lb-tol),return;end
if isempty(A),A=zeros(0,n);b=zeros(0,1);end
if isempty(Aeq),Aeq=zeros(0,n);beq=zeros(0,1);end
b=b(:)-A*lb;beq=beq(:)-Aeq*lb;
finite=find(isfinite(ub));I=eye(n);
A=[A;I(finite,:)];b=[b;ub(finite)-lb(finite)];
m1=size(A,1);m2=size(Aeq,1);m=m1+m2;
C=[A;Aeq];rhs=[b;beq];signs=ones(m,1);signs(rhs<0)=-1;
C=C.*signs;rhs=rhs.*signs;
C=[C,zeros(m,m1+m)];basis=zeros(m,1);art=[];next=n+m1;
for i=1:m
    if i<=m1,C(i,n+i)=signs(i);end
    if i<=m1 && signs(i)>0
        basis(i)=n+i;
    else
        next=next+1;C(i,next)=1;basis(i)=next;art(end+1)=next; %#ok<AGROW>
    end
end
C=C(:,1:next);cost=zeros(next,1);cost(art)=1;
[C,rhs,basis,flag,it]=simplex(C,rhs,basis,cost,tol);
output.iterations=it;
if flag~=1 || cost(basis)'*rhs>1e-7,return;end
% Pivot zero-valued artificial basics out; discard redundant equations.
for i=m:-1:1
    if ismember(basis(i),art)
        candidates=setdiff(find(abs(C(i,1:n+m1))>tol),basis);
        if isempty(candidates)
            C(i,:)=[];rhs(i)=[];basis(i)=[];
        else
            [C,rhs]=pivot(C,rhs,i,candidates(1));basis(i)=candidates(1);
        end
    end
end
C=C(:,1:n+m1);cost=[f;zeros(m1,1)];
[C,rhs,basis,flag,it]=simplex(C,rhs,basis,cost,tol);
output.iterations=output.iterations+it;exitflag=flag;
if flag~=1,return;end
z=zeros(n+m1,1);z(basis)=rhs;x=z(1:n)+lb;fval=f'*x;
end

function [C,rhs,basis,flag,it]=simplex(C,rhs,basis,cost,tol)
flag=0;
for it=1:20000
    rc=cost'-cost(basis)'*C;rc(basis)=0;
    entering=find(rc < -tol,1);
    if isempty(entering),flag=1;return;end
    candidates=find(C(:,entering)>tol);
    if isempty(candidates),flag=-3;return;end
    ratios=rhs(candidates)./C(candidates,entering);
    best=min(ratios);tied=candidates(ratios<=best+tol);
    [~,j]=min(basis(tied));leaving=tied(j);
    [C,rhs]=pivot(C,rhs,leaving,entering);basis(leaving)=entering;
end
error('Simplex iteration limit reached.');
end

function [C,rhs]=pivot(C,rhs,row,col)
p=C(row,col);C(row,:)=C(row,:)/p;rhs(row)=rhs(row)/p;
a=C(:,col);a(row)=0;C=C-a*C(row,:);rhs=rhs-a*rhs(row);
rhs(abs(rhs)<1e-12)=0;
end
