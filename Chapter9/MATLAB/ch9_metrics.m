function r=ch9_metrics(d)
reason=d(:,3);valid=ismember(reason,[1 3]);bad=ismember(reason,[4 5 7]);
r.n=size(d,1);r.win=mean(reason==1);r.tie=mean(reason==3);
r.violation=mean(bad);r.separation_violation=mean(reason==4);r.valid_finish=mean(valid);
r.timeout=mean(reason==8);r.score=mean(d(:,4));
if any(valid),r.finish_time=mean(d(valid,6));else,r.finish_time=NaN;end
r.mean_gates=mean(d(:,7));
end
