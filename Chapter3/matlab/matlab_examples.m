function matlab_examples(out)
% The forward-Euler and local-gradient illustrations, computed in MATLAB.
dt=.01;t=(0:200)'*dt;U=[.4*t .015*t .02*t];X=zeros(201,7);X(1,:)=[0 0 100 20 0 0 0];
for k=1:200,X(k+1,:)=X(k,:)+dt*motion(X(k,:),U(k,:));end
assert(max(abs(X(:,7)-.01*(t.^2-dt*t)))<1e-12);
writetable(array2table([t U X],'VariableNames',{'t','a','omega_gamma','omega_phi','x','y','z','V','gamma','chi','phi'}),fullfile(out,'forward_example.csv'));
f=figure('Visible','off','Color','white','Position',[100 100 1100 550]);tiledlayout(2,3,'TileSpacing','compact');
values=[U(:,1),U(:,2:3)*180/pi,X(:,4),X(:,5)*180/pi,X(:,7)*180/pi];
labels={'a / (m/s^2)','omega gamma / (deg/s)','omega phi / (deg/s)','V / (m/s)','gamma / deg','phi / deg'};
for j=1:6,nexttile;plot(t,values(:,j),'LineWidth',1.5);ylabel(labels{j});xlabel('t / s');grid on;end
savefigure(f,out,'forward_example');
starts=[-1.6 -.2 .2 1.6];records=repmat(struct('initial',0,'solution',0,'cost',0,'iterations',0),1,4);traces=cell(4,1);
for j=1:4
 x=starts(j);trace=x;count=0;
 while abs(4*x*(x*x-1))>=1e-4 && count<500,x=x-.1*4*x*(x*x-1);trace(end+1)=x;count=count+1;end %#ok<AGROW>
 assert(abs(4*x*(x*x-1))<1e-4);
 records(j)=struct('initial',starts(j),'solution',x,'cost',(x*x-1)^2,'iterations',count);traces{j}=trace;
end
fid=fopen(fullfile(out,'gradient_example.json'),'w');fprintf(fid,'%s',jsonencode(records,'PrettyPrint',true));fclose(fid);
f=figure('Visible','off','Color','white','Position',[100 100 1000 380]);tiledlayout(1,2);
nexttile;xx=linspace(-1.7,1.7,1000);plot(xx,(xx.^2-1).^2,'k');xlabel('xi');ylabel('f(xi)');grid on;
nexttile;hold on;for j=1:4,plot(0:numel(traces{j})-1,traces{j},'DisplayName',num2str(starts(j)));end
xlabel('Iteration');ylabel('xi');legend('Location','best');grid on;savefigure(f,out,'gradient_example');
end
function savefigure(f,out,name)
exportgraphics(f,fullfile(out,[name '.pdf']),'ContentType','vector');exportgraphics(f,fullfile(out,[name '.png']),'Resolution',160);close(f);
end
