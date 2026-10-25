function lp = ch9_logprob(mu,ls,b)
z=(b-mu).*exp(-ls);
lp=-.5*sum(z.^2+2*ls+log(2*pi),2);
end
