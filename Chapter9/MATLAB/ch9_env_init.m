function [e,s] = ch9_env_init(c,n,s,mirror)
if nargin<4, mirror=false; end
assert(c.gamma==1,'Finite-race reward requires gamma=1.');
assert(c.dt>0 && c.substeps>=1 && c.velocity_tau>0,'Invalid timing parameters.');
e.c=c; e.n=n;
e.gates=[10 0 2.5 3.6 2.2;20 1.5 3 3.2 2;30 -1 2.4 1.2 1;40 1 3 3.2 2;50 0 2.5 2.6 1.8];
if mirror, e.gates(:,2)=-e.gates(:,2); end
[u,s]=ch9_random(s,n,6);
e.p=zeros(n,3,2); e.v=zeros(n,3,2);
gap=4*(u(:,1)-.5); side=ones(n,1); side(u(:,2)<.5)=-1;
e.p(:,1,1)=-.5*gap; e.p(:,1,2)=.5*gap;
e.p(:,2,1)=side.*(.80+.1*(u(:,3)-.5));
e.p(:,2,2)=-side.*(.80+.1*(u(:,4)-.5));
e.p(:,3,1)=2.5+.08*(u(:,5)-.5);e.p(:,3,2)=2.5+.08*(u(:,6)-.5);
e.v(:,1,:)=3.5;
if mod(n,2)==0
    e.p(2:2:n,:,1)=e.p(1:2:n,:,2);e.p(2:2:n,:,2)=e.p(1:2:n,:,1);
end
e.g=zeros(n,2); e.t=zeros(n,1); e.prev=zeros(n,3,2);
e.done=false(n,1);e.reason=zeros(n,1);e.score=zeros(n,2);
e.min_sep=sqrt(sum((e.p(:,:,1)-e.p(:,:,2)).^2,2));
e.accel_peak=zeros(n,1);e.phi0=ch9_potential(e);e.reward_sum=zeros(n,2);e.initial_p=e.p;
end
