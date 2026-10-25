function report=ch9_foundations(out)
q=zeros(3,2);vis=zeros(3,2);s=92;history=[];
for episode=1:5000
    [a,s]=choose(q,1,s);ns=a+1;r=3-a;
    vis(1,a)=vis(1,a)+1;eta=vis(1,a)^(-.65);
    q(1,a)=q(1,a)+eta*(r+.9*max(q(ns,:))-q(1,a));
    [a,s]=choose(q,ns,s);rr=[3 1;6 2];r=rr(ns-1,a);
    vis(ns,a)=vis(ns,a)+1;eta=vis(ns,a)^(-.65);q(ns,a)=q(ns,a)+eta*(r-q(ns,a));
    if mod(episode-1,25)==0 || episode==5000
        history(end+1,:)=[episode,reshape(q.',1,[])]; %#ok<AGROW>
    end
end
exact=[4.7 6.4;3 1;6 2];err=max(abs(q(:)-exact(:)));assert(err<1e-5);
report.Q=q;report.exact=exact;report.max_absolute_error=err;report.visits=vis;
report.one_step_Q_nonterminal=2+.2*(.5+.9*4-2);report.one_step_Q_terminal=2+.2*(.5-2);
report.PPO_terms=[2.4 1.2 -1.6 -3];
ch9_write_array(fullfile(out,'q_learning_history.csv'),history,{'episode','Q00','Q01','Q10','Q11','Q20','Q21'});
ch9_save_json(fullfile(out,'foundations.json'),report);
end
function [a,s]=choose(q,state,s)
[u,s]=ch9_random(s,1,2);
if u(1)<.2,a=1+(u(2)>=.5);else
    ids=find(q(state,:)==max(q(state,:)));a=ids(min(floor(u(2)*numel(ids))+1,numel(ids)));
end
end
