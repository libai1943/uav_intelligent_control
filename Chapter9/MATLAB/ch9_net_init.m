function [net,s] = ch9_net_init(s,d,h,o,lastScale)
[u,s]=ch9_random(s,d,h); net.W1=(2*u-1)*sqrt(3/d);
net.b1=zeros(1,h);
[u,s]=ch9_random(s,h,o); net.W2=(2*u-1)*lastScale;
net.b2=zeros(1,o);
end
