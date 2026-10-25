function [net,opt] = ch9_adam(net,opt,g,lr,maxnorm)
%CH9_ADAM Adam with explicit first/second moments and global norm clipping.
names=fieldnames(net);
if isempty(opt)
    opt.t=0;
    for k=1:numel(names)
        name=names{k}; opt.m.(name)=zeros(size(net.(name))); opt.v.(name)=zeros(size(net.(name)));
    end
end
ss=0;
for k=1:numel(names)
    gg=g.(names{k}); ss=ss+sum(gg(:).^2);
end
scale=min(1,maxnorm/(sqrt(ss)+1e-12)); opt.t=opt.t+1;
for k=1:numel(names)
    name=names{k}; gg=g.(name)*scale;
    opt.m.(name)=.9*opt.m.(name)+.1*gg;
    opt.v.(name)=.999*opt.v.(name)+.001*gg.^2;
    mh=opt.m.(name)/(1-.9^opt.t); vh=opt.v.(name)/(1-.999^opt.t);
    net.(name)=net.(name)-lr*mh./(sqrt(vh)+1e-8);
end
end
