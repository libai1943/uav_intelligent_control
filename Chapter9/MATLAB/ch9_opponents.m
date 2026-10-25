function [acts,s] = ch9_opponents(e,ids,pool,s)
acts=zeros(e.n,3);obs=ch9_obs(e,2);u=unique(ids);
for k=1:numel(u)
    id=u(k);ix=find(ids==id);
    if id>=0
        z=ch9_rule(e,id,2);acts(ix,:)=z(ix,:);
    else
        [z,~,~,s]=ch9_policy(pool{-id},obs(ix,:),s,false);acts(ix,:)=z;
    end
end
end
