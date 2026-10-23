function RunMe
% 第一章独立 MATLAB 实现；不调用 Python，不需要工具箱。
root=fileparts(mfilename('fullpath'));out=fullfile(root,'results_matlab');if ~exist(out,'dir'),mkdir(out);end
airNorth=10;windsEast=[0 3 5];T=10;t=linspace(0,T,101)';
set(groot,'defaultFigureVisible','off','defaultAxesFontName','Microsoft YaHei','defaultTextFontName','Microsoft YaHei');
f=figure('Visible','off','Color','w');ax=subplot(1,2,1);hold(ax,'on');rows=zeros(numel(windsEast),3);
for k=1:numel(windsEast)
 w=windsEast(k);pos=t*[w airNorth];
 writetable(array2table([t pos],'VariableNames',{'time_s','east_m','north_m'}),fullfile(out,sprintf('wind_%g.csv',w)));
 plot(ax,pos(:,1),pos(:,2),'DisplayName',sprintf('向东风速 %g m/s',w));rows(k,:)=[w norm([w airNorth]) atan2d(w,airNorth)];
end
axis(ax,'equal');grid(ax,'on');xlabel(ax,'向东位置 / m');ylabel(ax,'向北位置 / m');legend(ax,'Location','best');title(ax,'机头始终朝北');
ax=subplot(1,2,2);hold(ax,'on');quiver(ax,0,0,0,10,0);quiver(ax,0,10,3,0,0);quiver(ax,0,0,3,10,0);axis(ax,'equal');grid(ax,'on');xlabel(ax,'向东速度 / (m/s)');ylabel(ax,'向北速度 / (m/s)');legend(ax,{'空速','风速','地速'},'Location','best');saveplots(f,out,'wind_groundtrack');
q=t/T;A=curve(q);B=curve(2*q-q.^2);
writetable(array2table([t A B],'VariableNames',{'time_s','x_A','y_A','x_B','y_B'}),fullfile(out,'time_schedules.csv'));
f=figure('Visible','off','Color','w');
for k=1:2
 ax=subplot(2,1,k);hold(ax,'on');plot(ax,A(:,1),A(:,2),'Color',[.7 .7 .7]);data=A;if k==2,data=B;end
 ix=1:20:101;scatter(ax,data(ix,1),data(ix,2),15,'filled');
 for j=1:numel(ix),text(ax,data(ix(j),1),data(ix(j),2)+.15,sprintf('%ds',(j-1)*2));end
 axis(ax,'equal');grid(ax,'on');xlabel(ax,'东向位置（相对尺度）');ylabel(ax,'北向位置（相对尺度）');
end
saveplots(f,out,'path_time_schedules');
writetable(array2table(rows,'VariableNames',{'wind_east_m_s','groundspeed_m_s','course_east_of_north_deg'}),fullfile(out,'checks.csv'));
assert(all(abs(rows(:,2)-hypot(rows(:,1),airNorth))<1e-12));fprintf('第一章MATLAB实验完成：%s\n',out);
end
function p=curve(a)
p=[3*(1-a).^2.*a+9*(1-a).*a.^2+5.7*a.^3,5.4*(1-a).^2.*a-2.1*(1-a).*a.^2+1.4*a.^3];
end
function saveplots(f,out,name)
exportgraphics(f,fullfile(out,[name '.pdf']),'ContentType','vector');exportgraphics(f,fullfile(out,[name '.png']),'Resolution',220);close(f);
end
