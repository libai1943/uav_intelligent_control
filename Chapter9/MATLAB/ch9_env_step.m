function [e,reward] = ch9_env_step(e,z)
%CH9_ENV_STEP Same-time joint actions, explicit Euler, chronological events.
% z is N-by-3-by-2. Pair-clearance threshold is NOT a measured impact model.
assert(isequal(size(z),[e.n,3,2]) && all(isfinite(z(:))),'Invalid action array.');
z=min(1,max(-1,z));phiOld=ch9_potential(e);wasDone=e.done;
e.prev(~e.done,:,:)=z(~e.done,:,:);
n=e.n;c=e.c;dt=c.dt;
for sub=1:c.substeps
    active=~e.done;if ~any(active), break;end
    acc=zeros(n,3,2);dp=dt*e.v;pn=e.p+dp;
    f=inf(n,2);good=false(n,2);bad=inf(n,2);finish=inf(n,2);
    for w=1:2
        j=min(e.g(:,w),4)+1;target=e.gates(j,1:3);
        target(:,2)=target(:,2)+c.offset_fraction*(e.gates(j,4)/2-c.gate_margin).*z(:,2,w);
        target(:,3)=target(:,3)+c.offset_fraction*(e.gates(j,5)/2-c.gate_margin).*z(:,3,w);
        vr=[c.speed_mid+c.speed_scale*z(:,1,w),...
           min(c.lateral_speed_max,max(-c.lateral_speed_max,c.lateral_gain*(target(:,2)-e.p(:,2,w)))),...
           min(c.vertical_speed_max,max(-c.vertical_speed_max,c.lateral_gain*(target(:,3)-e.p(:,3,w))))];
        aa=(vr-e.v(:,:,w))/c.velocity_tau;
        an=sqrt(sum(aa.^2,2));acc(:,:,w)=aa.*min(1,c.accel_max./max(an,1e-12));
        gx=e.gates(j,1);cross=e.p(:,1,w)<gx & pn(:,1,w)>=gx;
        f(cross,w)=(gx(cross)-e.p(cross,1,w))./max(dp(cross,1,w),1e-12);
        fs=f(:,w);fs(~cross)=0;gp=e.p(:,:,w)+fs.*dp(:,:,w);
        good(:,w)=cross & abs(gp(:,2)-e.gates(j,2))<=e.gates(j,4)/2-c.gate_margin+1e-12 & ...
            abs(gp(:,3)-e.gates(j,3))<=e.gates(j,5)/2-c.gate_margin+1e-12;
        ix=cross & ~good(:,w);bad(ix,w)=f(ix,w);
        lo=[-4 -5 .5];hi=[52 5 5];
        for d=1:3
            fl=inf(n,1);fh=fl;
            ix=pn(:,d,w)<lo(d) & dp(:,d,w)<0;
            fl(ix)=(lo(d)-e.p(ix,d,w))./dp(ix,d,w);
            ix=pn(:,d,w)>hi(d) & dp(:,d,w)>0;
            fh(ix)=(hi(d)-e.p(ix,d,w))./dp(ix,d,w);
            bad(:,w)=min(bad(:,w),min(fl,fh));
        end
        ix=good(:,w)&j==5;finish(ix,w)=f(ix,w);
    end
    r=e.p(:,:,1)-e.p(:,:,2);dr=dp(:,:,1)-dp(:,:,2);
    aa=sum(dr.^2,2);bb=2*sum(r.*dr,2);cc=sum(r.^2,2)-c.separation^2;
    disc=bb.^2-4*aa.*cc;rt=(-bb-sqrt(max(disc,0)))./(2*max(aa,1e-24));
    col=inf(n,1);ix=aa>1e-20 & disc>=0 & rt>=0 & rt<=1;col(ix)=rt(ix);col(cc<=0)=0;
    first=min([col,bad,finish],[],2);terminal=active & first<=1;
    frac=ones(n,1);frac(terminal)=first(terminal);frac(~active)=0;
    closest=min(frac,max(0,-sum(r.*dr,2)./max(aa,1e-24)));
    ds=sqrt(sum((r+closest.*dr).^2,2));e.min_sep(active)=min(e.min_sep(active),ds(active));
    peak=max([sqrt(sum(acc(:,:,1).^2,2)),sqrt(sum(acc(:,:,2).^2,2))],[],2);
    e.accel_peak(active)=max(e.accel_peak(active),peak(active));
    e.p=e.p+reshape(frac,n,1,1).*dp;
    e.v=e.v+reshape(frac,n,1,1).*dt.*acc;e.t=e.t+frac*dt;
    passed=good & f<=frac+1e-10 & active;e.g=e.g+double(passed);
    collision=terminal & col<=first+1e-10;
    ba=terminal & bad(:,1)<=first+1e-10 & ~collision;
    bc=terminal & bad(:,2)<=first+1e-10 & ~collision;
    fa=terminal & finish(:,1)<=first+1e-10 & ~collision & ~ba & ~bc;
    fb=terminal & finish(:,2)<=first+1e-10 & ~collision & ~ba & ~bc;
    e.reason(collision)=4;e.score(collision,:)=-1;
    e.reason(ba & ~bc)=5;e.score(ba & ~bc,1)=-1;
    e.reason(bc & ~ba)=6;e.score(bc & ~ba,2)=-1;
    e.reason(ba & bc)=7;e.score(ba & bc,:)=-1;
    e.reason(fa & ~fb)=1;e.score(fa & ~fb,1)=1;
    e.reason(fb & ~fa)=2;e.score(fb & ~fa,2)=1;
    e.reason(fa & fb)=3;e.score(fa & fb,:)=.5;
    e.done=e.done|terminal;
    timeout=~e.done & e.t>=c.time_limit-1e-10;e.reason(timeout)=8;e.done=e.done|timeout;
end
reward=c.beta*(ch9_potential(e)-phiOld);
new=e.done & ~wasDone;reward(new,:)=reward(new,:)+e.score(new,:);
reward(wasDone,:)=0;e.reward_sum=e.reward_sum+reward;
end
