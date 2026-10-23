function f=motion(x,u)
% Seven-state, rate-input, near-level fixed-wing planning model (z upward).
% Rows are time samples. Angles and angular rates use radians.
V=x(:,4);ga=x(:,5);ch=x(:,6);phi=x(:,7);
f=[V.*cos(ga).*cos(ch),V.*cos(ga).*sin(ch),V.*sin(ga), ...
   u(:,1),u(:,2),9.81*tan(phi)./V,u(:,3)];
end
