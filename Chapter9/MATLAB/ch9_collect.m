function [data,stats,s] = ch9_collect(actor,critic,c,s,mode,pool)
[e,s]=ch9_env_init(c,c.batch_episodes,s,false);
if strcmp(mode,'fixed')
    ids=zeros(e.n,1);
else
    [q,s]=ch9_random(s,e.n,1);ids=2*ones(e.n,1);ids(q<.25)=0;
    if ~isempty(pool)
        [q2,s]=ch9_random(s,e.n,1);ix=q>=.5;
        ids(ix)=-1-min(floor(q2(ix)*numel(pool)),numel(pool)-1);
    end
end
O={};B={};LP={};V={};R={};A={};
while ~all(e.done)
    o=ch9_obs(e,1);[za,b,lp,s]=ch9_policy(actor,o,s,false);[zb,s]=ch9_opponents(e,ids,pool,s);
    A{end+1}=~e.done;O{end+1}=o;B{end+1}=b;LP{end+1}=lp; %#ok<AGROW>
    [val,~]=ch9_forward(critic,o);V{end+1}=val; %#ok<AGROW>
    [e,reward]=ch9_env_step(e,cat(3,za,zb));R{end+1}=reward(:,1); %#ok<AGROW>
end
T=numel(R);rewards=cat(2,R{:}).';G=zeros(T,e.n);fut=zeros(1,e.n);
for t=T:-1:1,fut=rewards(t,:)+c.gamma*fut;G(t,:)=fut;end
mask=vertcat(A{:});x=vertcat(O{:});b=vertcat(B{:});oldlp=vertcat(LP{:});oldv=vertcat(V{:});
target=reshape(G.',[],1);
data.x=x(mask,:);data.b=b(mask,:);data.oldlp=oldlp(mask);data.target=target(mask);
adv=target(mask)-oldv(mask);data.adv=(adv-mean(adv))/(std(adv,1)+1e-8);
stats.train_score=mean(e.score(:,1));stats.train_win=mean(e.reason==1);
stats.train_violation=mean(ismember(e.reason,[4 5 7]));stats.samples=sum(mask);
err=abs(e.reward_sum-e.score+c.beta*e.phi0);stats.audit=max(err(:));
end
