function [metrics,details,traces] = ch9_evaluate(actor,c,seed,n,kinds,deterministic,mirror,trace,rule,blind)
if nargin<5,kinds=0:4;end
if nargin<6,deterministic=false;end
if nargin<7,mirror=false;end
if nargin<8,trace=false;end
if nargin<9,rule=-1;end
if nargin<10,blind=false;end
[e,s]=ch9_env_init(c,n,seed,mirror);
ids=reshape(kinds(mod(floor((0:n-1)'/2),numel(kinds))+1),[],1);
traces={};
while ~all(e.done)
    o=ch9_obs(e,1);if blind,o(:,10:15)=0;end
    if rule>=0,za=ch9_rule(e,rule,1);else,[za,~,~,s]=ch9_policy(actor,o,s,deterministic);end
    [zb,s]=ch9_opponents(e,ids,{},s);
    if trace,traces{end+1}=trace_row(e,za,zb);end %#ok<AGROW>
    z=cat(3,za,zb);[e,~]=ch9_env_step(e,z);
end
if trace,traces{end+1}=trace_row(e,za,zb);end
% These columns exactly match Python's DETAIL_HEADER.
details=[(0:n-1)',ids,e.reason,e.score,e.t,e.g,e.min_sep,e.accel_peak,e.reward_sum,e.phi0];
metrics=ch9_metrics(details);err=abs(e.reward_sum-e.score+c.beta*e.phi0);
metrics.potential_audit=max(err(:));
end
function a=trace_row(e,za,zb)
a=[(0:e.n-1)',e.t,e.p(:,:,1),e.p(:,:,2),e.v(:,:,1),e.v(:,:,2),e.g,za,zb,double(e.done)];
end
