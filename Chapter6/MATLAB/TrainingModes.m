function report = TrainingModes(out)
% Independent BP calculation with two trainable weights and zero biases.
if nargin<1,out=fullfile(fileparts(mfilename('fullpath')),'results','training_modes');end
if ~exist(out,'dir'),mkdir(out);end
M=1000;steps=1500;rate=.3;initial=[1;1.2];
x=linspace(-1,1,M).';clean=1.6*tanh(2.4*x);
[noise,~]=uniformStream(20261101,M);target=clean+.2*(2*noise-1);
writetable(table(x,target,clean),fullfile(out,'training_samples.csv'));
names={'single','mini','full'};batches=[1,10,1000];
labels={'单样本','小批量（10条）','全批量'};
colors=[.733 .231 .208;.145 .518 .424;.192 .361 .643];markers={'s','+','o'};
report.samples=M;report.updates=steps;report.learning_rate=rate;
report.initial_weights=initial.';report.noise_bound=.2;
paths=cell(1,3);histories=cell(1,3);
for mode=1:3
    B=batches(mode);theta=initial;seed=456;offset=M;
    path=zeros(steps+1,2);path(1,:)=theta.';history=zeros(steps+1,3);
    history(1,3)=lossGradient(theta,x,target);
    for step=1:steps
        if offset==M,[values,seed]=uniformStream(seed,M);[~,order]=sort(values);offset=0;end
        ids=order(offset+1:offset+B);offset=offset+B;
        [~,gradient]=lossGradient(theta,x(ids),target(ids));theta=theta-rate*gradient;
        path(step+1,:)=theta.';history(step+1,:)=[step,step*B,lossGradient(theta,x,target)];
    end
    assert(all(isfinite(path(:))));paths{mode}=path;histories{mode}=history;
    writetable(array2table(path,'VariableNames',{'theta0','theta1'}),fullfile(out,[names{mode} '_parameters.csv']));
    writetable(array2table(history,'VariableNames',{'updates','samples_used','full_training_loss'}),fullfile(out,[names{mode} '_loss.csv']));
    s.batch_size=B;s.samples_used=steps*B;s.initial_loss=history(1,3);
    s.final_loss=history(end,3);s.final_weights=theta.';report.modes.(names{mode})=s;
end
fig=figure('Visible','off','Color','w','Position',[60 60 900 520]);hold on;handles=gobjects(1,3);
for k=1:3
    p=paths{k};handles(k)=plot(p(:,1),p(:,2),'Color',colors(k,:),'LineWidth',1.2,...
        'Marker',markers{k},'MarkerSize',4,'MarkerIndices',1:20:size(p,1));
end
plot(initial(1),initial(2),'*','Color',[.15 .2 .26],'MarkerSize',9);
text(1.03,1.2,'共同起点','VerticalAlignment','top','FontName','Microsoft YaHei');
xlabel('输入权重 \theta_0');ylabel('输出权重 \theta_1');xlim([.96 2.5]);ylim([1.16 1.98]);
legend(handles,labels,'Location','northwest','Box','off','FontName','Microsoft YaHei');
set(gca,'FontName','Microsoft YaHei','FontSize',12,'Box','off');
exportgraphics(fig,fullfile(out,'training_modes.pdf'),'ContentType','vector');
exportgraphics(fig,fullfile(out,'training_modes.png'),'Resolution',210);close(fig);
fig=figure('Visible','off','Color','w');hold on;
for k=1:3,h=histories{k};plot(h(:,1),h(:,3),'Color',colors(k,:),'LineWidth',1.1);end
set(gca,'YScale','log','FontName','Microsoft YaHei');xlabel('参数更新次数');ylabel('全训练集的平均损失');
legend(labels,'Box','off');grid on;
exportgraphics(fig,fullfile(out,'training_loss.pdf'),'ContentType','vector');close(fig);
fig=figure('Visible','off','Color','w');scatter(x,target,4,[.55 .59 .62],'filled');hold on;
plot(x,clean,'Color',[.15 .2 .26]);set(gca,'FontName','Microsoft YaHei');
xlabel('输入 x');ylabel('目标值 d');legend({'含噪声训练样本','生成函数'},'Box','off');
exportgraphics(fig,fullfile(out,'training_samples.png'),'Resolution',180);close(fig);
fid=fopen(fullfile(out,'summary.json'),'w');fprintf(fid,'%s',jsonencode(report));fclose(fid);
disp(report);
end

function [values,seed]=uniformStream(seed,n)
values=zeros(n,1);
for i=1:n,seed=mod(1664525*seed+1013904223,2^32);values(i)=seed/2^32;end
end

function [loss,gradient]=lossGradient(theta,x,target)
h=tanh(theta(1)*x);error=theta(2)*h-target;
loss=.5*mean(error.^2);
gradient=[mean(error.*theta(2).*(1-h.^2).*x);mean(error.*h)];
end
