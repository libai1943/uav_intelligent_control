function [boxes,owner,nodeLo,nodeHi]=build_corridors(seed,obs,cfg)
% Each shared endpoint must lie in both neighboring shrunken boxes.
N=cfg.intervals;group=cfg.fragment_steps;assert(mod(N,group)==0);
loGlobal=cfg.state_lower(1:3)';hiGlobal=cfg.state_upper(1:3)';
nodeLo=repmat(loGlobal,N+1,1);nodeHi=repmat(hiGlobal,N+1,1);
boxes=zeros(N/group,6);owner=repelem((1:N/group)',group);
padding=[2 2 8];cap=[34 40 18];margin=cfg.safety_margin_m;
for i=1:N/group
 ids=(i-1)*group+1:i*group+1;
 lo=max(min(seed(ids,:),[],1)-padding,loGlobal);
 hi=min(max(seed(ids,:),[],1)+padding,hiGlobal);
 assert(box_clearance(lo,hi,obs)>margin,'Unsafe seed box: refine grouping or change initial route.');
 baseLo=lo;baseHi=hi;
 for round=1:26
  for face=1:6
   d=ceil(face/2);cl=lo;ch=hi;
   if mod(face,2)==1,cl(d)=cl(d)-2;else,ch(d)=ch(d)+2;end
   if cl(d)<baseLo(d)-cap(d)||ch(d)>baseHi(d)+cap(d),continue;end
   cl=max(cl,loGlobal);ch=min(ch,hiGlobal);
   if box_clearance(cl,ch,obs)>margin+.05,lo=cl;hi=ch;end
  end
 end
 boxes(i,:)=[lo hi];buffer=cfg.corridor_node_buffer_m;
 nodeLo(ids,:)=max(nodeLo(ids,:),lo+buffer);nodeHi(ids,:)=min(nodeHi(ids,:),hi-buffer);
end
assert(all(nodeLo<=nodeHi,'all'),'Empty corridor intersection after inward buffer.');
end
