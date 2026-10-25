function [loss,g,kl,clipFraction] = ch9_actor_loss(actor,x,b,oldlp,adv,clip)
[mu,h]=ch9_forward(actor,x); lp=ch9_logprob(mu,actor.logstd,b);
lr=min(40,max(-40,lp-oldlp)); ratio=exp(lr);
cr=min(1+clip,max(1-clip,ratio));
loss=-mean(min(ratio.*adv,cr.*adv));
live=(adv>=0 & ratio<=1+clip) | (adv<0 & ratio>=1-clip);
dlp=-(double(live).*adv.*ratio)/size(x,1);
invvar=exp(-2*actor.logstd); diff=b-mu;
g=ch9_backward(actor,x,h,dlp.*diff.*invvar);
g.logstd=sum(dlp.*(diff.^2.*invvar-1),1);
kl=mean(exp(lr)-1-lr); clipFraction=mean(abs(ratio-1)>clip);
end
