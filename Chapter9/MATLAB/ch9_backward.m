function g = ch9_backward(net,x,h,dy)
dh=(dy*net.W2.').*(1-h.^2);
g.W1=x.'*dh; g.b1=sum(dh,1);
g.W2=h.'*dy; g.b2=sum(dy,1);
end
