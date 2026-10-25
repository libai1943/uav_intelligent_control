function [actor,initial,critic,pool,records] = ch9_train(c,seed,mode)
s=seed;[actor,s]=ch9_net_init(s,24,c.hidden,3,.02);
actor.logstd=log(c.initial_std)*ones(1,3);initial=actor;
[critic,s]=ch9_net_init(s,24,c.hidden,1,.05);ao=[];co=[];pool={};records=struct([]);
start=tic;nsteps=0;
for it=1:c.iterations
    [D,st,s]=ch9_collect(actor,critic,c,s,mode,pool);N=size(D.x,1);nsteps=nsteps+N;
    stop=false;aloss=0;vloss=0;kl=0;cf=0;
    for epoch=1:c.epochs
        [u,s]=ch9_random(s,N,1);[~,order]=sort(u);
        for first=1:c.minibatch:N
            ix=order(first:min(first+c.minibatch-1,N));
            [aloss,ag,kl,cf]=ch9_actor_loss(actor,D.x(ix,:),D.b(ix,:),D.oldlp(ix),D.adv(ix),c.ppo_clip);
            if kl>c.max_kl,stop=true;break;end
            [actor,ao]=ch9_adam(actor,ao,ag,c.actor_lr,c.grad_clip);
            actor.logstd=min(log(c.std_max),max(log(c.std_min),actor.logstd));
            [val,h]=ch9_forward(critic,D.x(ix,:));err=val-D.target(ix);vloss=mean(err.^2)/2;
            cg=ch9_backward(critic,D.x(ix,:),h,err/numel(ix));
            [critic,co]=ch9_adam(critic,co,cg,c.critic_lr,c.grad_clip);
        end
        if stop,break;end
    end
    vs=NaN;vv=NaN;vw=NaN;
    if mod(it,c.eval_every)==0 || it==1
        [vr,~,~]=ch9_evaluate(actor,c,600000+seed,40,[0 2]);vs=vr.score;vv=vr.violation;vw=vr.win;
    end
    if strcmp(mode,'league') && mod(it,c.snapshot_every)==0
        if ~isfinite(vv),[vr,~,~]=ch9_evaluate(actor,c,600000+seed,40,[0 2]);vv=vr.violation;end
        if vv<=.30
            pool{end+1}=actor;
            if numel(pool)>c.pool_capacity,pool=pool(end-c.pool_capacity+1:end);end
        end
    end
    row.iteration=it;row.steps=nsteps;row.train_score=st.train_score;row.train_win=st.train_win;
    row.train_violation=st.train_violation;row.samples=st.samples;row.audit=st.audit;
    row.actor_loss=aloss;row.critic_loss=vloss;row.kl=kl;row.clip_fraction=cf;
    row.validation_score=vs;row.validation_win=vw;row.validation_violation=vv;row.pool_size=numel(pool);row.seconds=toc(start);
    records=[records,row]; %#ok<AGROW>
    if it==1 || mod(it,10)==0
        fprintf('%s seed=%d iter=%3d steps=%d trainJ=%+.3f valJ=%+.3f pool=%d\n',mode,seed,it,nsteps,st.train_score,vs,numel(pool));
    end
end
end
