function [z,b,lp,s] = ch9_policy(actor,obs,s,deterministic)
if nargin<4, deterministic=false; end
[mu,~]=ch9_forward(actor,obs);
if deterministic
    b=mu;
else
    [eps,s]=ch9_random(s,size(mu,1),size(mu,2),true);
    b=mu+exp(actor.logstd).*eps;
end
z=tanh(b); lp=ch9_logprob(mu,actor.logstd,b);
end
