% Chapter 6: run both controllers, export all data and draw one comparison.
% Independent MATLAB implementation; no additional toolbox or Python needed.
clear; close all;
root = fileparts(mfilename('fullpath'));
out = fullfile(root,'results'); if ~exist(out,'dir'), mkdir(out); end
feedback = simulate(false); learning = simulate(true);
names = {'time','height','velocity','error','neural','feedback','thrust', ...
         'W1','W2','b1','b2','v1','v2','c'};
writetable(array2table(feedback,'VariableNames',names),fullfile(out,'feedback.csv'));
writetable(array2table(learning,'VariableNames',names),fullfile(out,'learning.csv'));
summary.feedback = summarize(feedback); summary.learning = summarize(learning);
assert(abs(summary.feedback.final_error - .98/6)<1e-4);
assert(abs(summary.learning.final_error)<1e-4);
assert(abs(summary.learning.final_neural-.98)<1e-4);
assert(min([feedback(:,7);learning(:,7)])>0 && max([feedback(:,7);learning(:,7)])<24);
summary.checks_passed = true;
fid=fopen(fullfile(out,'summary.json'),'w'); fprintf(fid,'%s',jsonencode(summary)); fclose(fid);
c=[.333 .365 .404;.129 .490 .541;.659 .431 .212;.424 .341 .592];
fig=figure('Visible','off','Color','w','Position',[50 50 850 780]);
tiledlayout(3,1,'TileSpacing','compact','Padding','compact');
ax1=nexttile; a=plot(feedback(:,1),feedback(:,4),'--','Color',c(1,:),'LineWidth',1.5); hold on;
b=plot(learning(:,1),learning(:,4),'Color',c(2,:),'LineWidth',1.5); ylabel('Height error / m'); grid on;
ax2=nexttile; cc=plot(learning(:,1),learning(:,5),'Color',c(3,:),'LineWidth',1.5); hold on;
d=plot(learning(:,1),learning(:,6),'Color',c(4,:),'LineWidth',1.5); ylabel('Learning corrections / N'); grid on;
ax3=nexttile; plot(feedback(:,1),feedback(:,7),'--','Color',c(1,:),'LineWidth',1.5); hold on;
plot(learning(:,1),learning(:,7),'Color',c(2,:),'LineWidth',1.5); ylabel('Total thrust / N'); xlabel('Time / s'); grid on;
linkaxes([ax1 ax2 ax3],'x'); xlim([0 10]);
lg=legend([a b cc d],{'Feedback only','Neural learning control','Neural feedforward','Feedback correction'},'NumColumns',2);
lg.Layout.Tile='north'; lg.Box='off';
exportgraphics(fig,fullfile(out,'learning_control.pdf'),'ContentType','vector');
exportgraphics(fig,fullfile(out,'learning_control.png'),'Resolution',180); close(fig);
disp(summary); fprintf('Results: %s\n',out);
addpath(root); TrainingModes(fullfile(out,'training_modes')); 

function [value, gradient] = network(theta, feature)
hidden=tanh(theta(1:2)*feature+theta(3:4));
value=theta(5:6).'*hidden+theta(7);
delta=theta(5:6).*(1-hidden.^2);
gradient=[delta*feature;delta;hidden;1];
end

function [neural,fb,thrust,nextTheta] = controller(height,velocity,theta,learning)
% Only nominal mass is available to the controller; actual mass is in plant.
fb=6*(3-height)-5*velocity;
[value,gradient]=network(theta,3/3);
neural=0; if learning, neural=value; end
command=1.5*9.8+neural+fb; thrust=min(24,max(0,command));
nextTheta=theta;
if learning && command>0 && command<24
    nextTheta=theta+.006*fb*gradient;
end
end

function data = simulate(learning)
dt=.01; n=round(10/dt); h=3; v=0; theta=[.3;-.3;.2;-.2;0;0;0];
data=zeros(n+1,14);
for k=0:n
    [neural,fb,thrust,nextTheta]=controller(h,v,theta,learning);
    data(k+1,:)=[k*dt,h,v,3-h,neural,fb,thrust,theta.'];
    nextH=h+dt*v; nextV=v+dt*(thrust-1.6*9.8-1.6*v)/1.6;
    h=nextH; v=nextV; theta=nextTheta;
end
end

function s = summarize(data)
s.final_error=data(end,4); s.final_neural=data(end,5); s.final_feedback=data(end,6);
s.peak_abs_error=max(abs(data(:,4))); s.min_thrust=min(data(:,7)); s.max_thrust=max(data(:,7));
end
