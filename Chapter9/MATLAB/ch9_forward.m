function [y,h] = ch9_forward(net,x)
h=tanh(x*net.W1+net.b1);
y=h*net.W2+net.b2;
end
