function [v,s] = ch9_random(s,n,m,gaussian)
%CH9_RANDOM Portable Park--Miller stream and row-major Box--Muller draws.
% All integer products stay below 2^53, so double integer arithmetic is exact.
if nargin<4, gaussian=false; end
s=mod(double(s),2147483647); if s==0, s=1; end
if gaussian
    count=n*m; pairs=ceil(count/2);
    [u,s]=ch9_random(s,pairs,2,false);
    r=sqrt(-2*log(max(u(:,1),1e-15))); a=2*pi*u(:,2);
    z=[r.*cos(a),r.*sin(a)]; z=reshape(z.',[],1);
    v=reshape(z(1:count),m,n).';
else
    z=zeros(n*m,1);
    for k=1:numel(z)
        s=mod(16807*s,2147483647); z(k)=s/2147483647;
    end
    v=reshape(z,m,n).';
end
end
