function [x,fval,exitflag,output]=ch11_milp(f,intcon,A,b,Aeq,beq,lb,ub)
% Exact branch-and-bound over this chapter's small mixed-integer model.
% Continuous relaxations use ch11_lp; every node splits one fractional integer.
stack={struct('lb',lb,'ub',ub)};x=[];fval=inf;nodes=0;tol=1e-7;
while ~isempty(stack)
    node=stack{end};stack(end)=[];nodes=nodes+1;
    [z,value,status]=ch11_lp(f,A,b,Aeq,beq,node.lb,node.ub);
    if status==-2,continue;end
    assert(status==1,'Unexpected unbounded relaxation.');
    if value>=fval-tol,continue;end
    distance=abs(z(intcon)-round(z(intcon)));[gap,j]=max(distance);
    if gap<=tol
        x=z;fval=value;continue;
    end
    j=intcon(j);left=node;right=node;
    left.ub(j)=min(left.ub(j),floor(z(j)));
    right.lb(j)=max(right.lb(j),ceil(z(j)));
    stack{end+1}=right;stack{end+1}=left; %#ok<AGROW>
    assert(nodes<100000,'Branch-and-bound node limit reached.');
end
exitflag=1;if isempty(x),exitflag=-2;fval=[];end
output=struct('algorithm','branch-and-bound with two-phase simplex', ...
    'nodes',nodes,'relativegap',0,'absolutegap',0);
end
