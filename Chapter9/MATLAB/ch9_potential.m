function phi = ch9_potential(e)
phi=zeros(e.n,2);
for w=1:2
    j=min(e.g(:,w),4); fx=e.gates(j+1,1);
    sx=e.gates(max(j,1),1);sx(j==0)=-2;
    f=min(1,max(0,(e.p(:,1,w)-sx)./(fx-sx)));
    phi(:,w)=(j+f)/5;
end
phi(e.done,:)=0;
end
