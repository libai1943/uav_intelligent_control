function z=ch9_rule(e,kind,w)
if nargin<3,w=2;end
n=e.n;q=3-w;z=zeros(n,3);d=e.p(:,:,q)-e.p(:,:,w);
ahead=d(:,1)>0 & d(:,1)<3 & sqrt(sum(d(:,2:3).^2,2))<1;
sgn=ones(n,1);sgn(e.p(:,2,w)<e.p(:,2,q))=-1;
switch kind
case 0
    speed=4.6*ones(n,1);z(:,2)=-.20;
case 1
    speed=4.4*ones(n,1);speed(ahead)=3.1;z(:,2)=.25*sgn;
case 2
    speed=5.1*ones(n,1);speed(ahead)=4.0;z(:,2)=.65*sgn;
    near=e.g(:,w)==2 & 30-e.p(:,1,w)<5 & ahead;speed(near)=2.8;
case 3
    speed=5.6*ones(n,1);z(:,2)=.15;
case 4
    speed=5.1*ones(n,1);z(:,2)=.65*sin(.8*e.t+.7*e.g(:,w));z(:,3)=.2*cos(.5*e.t);
case 5
    speed=6.5*ones(n,1);z(:,2)=0;
otherwise
    error('CH9:Rule','Unknown rule ID.');
end
z(:,1)=(speed-e.c.speed_mid)/e.c.speed_scale;z=min(.98,max(-.98,z));
if kind==5,z(:,1)=1;end % A rule may attain the closed speed limit.
end
