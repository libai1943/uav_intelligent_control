function plot_results(results,out)
% Independent MATLAB rendering of all experiment curves and geometry.
set(groot,'defaultAxesFontName','Microsoft YaHei','defaultTextFontName','Microsoft YaHei');
names=fieldnames(results);blue=[.13 .49 .54];warm=[.66 .43 .21];
for i=1:numel(names)
 name=names{i};r=results.(name);f=figure('Visible','off','Color','white','Position',[100 100 1000 420]);
 tiledlayout(1,2,'TileSpacing','compact');nexttile;hold on;
 columns(r.columns);plot(r.initial_X(:,1),r.initial_X(:,2),'--','Color',warm);plot(r.X(:,1),r.X(:,2),'Color',blue,'LineWidth',1.8);
 axis equal;grid on;xlabel('位置 x / m');ylabel('位置 y / m');
 nexttile;plot(r.time,r.X(:,3),'Color',blue,'LineWidth',1.8);xlabel('时间 / s');ylabel('高度 z / m');grid on;
 savefigure(f,out,[name '_views']);
end
if isfield(results,'four_corridor')
 r=results.four_corridor;f=figure('Visible','off','Color','white','Position',[100 100 1000 560]);tiledlayout(2,2,'TileSpacing','compact');
 labels={'V / (m/s)','gamma / deg','chi / deg','phi / deg'};bounds=[15 25;-.2 .2;-.9 .9;-.6 .6];
 for j=1:4
  nexttile;factor=1;if j>1,factor=180/pi;end
  plot(r.time,r.X(:,j+3)*factor,'Color',blue,'LineWidth',1.5);hold on;
  yline(bounds(j,1)*factor,':');yline(bounds(j,2)*factor,':');ylabel(labels{j});xlabel('时间 / s');grid on;
 end
 savefigure(f,out,'states');
 f=figure('Visible','off','Color','white','Position',[100 100 1100 350]);tiledlayout(1,3);
 labels={'a / (m/s^2)','omega gamma / (deg/s)','omega phi / (deg/s)'};bounds=[2 .08 .4];
 for j=1:3
  nexttile;factor=1;if j>1,factor=180/pi;end
  stairs(r.time,[r.U(:,j);r.U(end,j)]*factor,'Color',blue,'LineWidth',1.5);hold on;
  yline(bounds(j)*factor,':');yline(-bounds(j)*factor,':');ylabel(labels{j});xlabel('时间 / s');grid on;
 end
 savefigure(f,out,'inputs');
 f=figure('Visible','off','Color','white','Position',[100 100 1000 450]);hold on;
 for i=1:size(r.boxes,1),box3(r.boxes(i,:),blue);end
 for j=1:size(r.columns,1)
  [x,y,z]=cylinder(r.columns(j,3),40);surf(x+r.columns(j,1),y+r.columns(j,2),60+125*z,'FaceColor',[.6 .6 .6],'FaceAlpha',.18,'EdgeColor','none');
 end
 plot3(r.X(:,1),r.X(:,2),r.X(:,3),'Color',blue,'LineWidth',2);axis equal;view(-62,32);grid on;
 xlabel('x / m');ylabel('y / m');zlabel('z / m');savefigure(f,out,'four_corridor_3d');
end
if all(isfield(results,{'two_straight','two_north','two_south'}))
 f=figure('Visible','off','Color','white','Position',[100 100 1050 400]);tiledlayout(1,2);ax1=nexttile;hold on;ax2=nexttile;hold on;
 list={'two_straight','two_north','two_south'};
 for j=1:3
  r=results.(list{j});plot(ax1,0:size(r.history,1)-1,r.history(:,1),'DisplayName',list{j});
  semilogy(ax2,0:size(r.history,1)-1,max(r.history(:,2),1e-12),'DisplayName',list{j});
 end
 xlabel(ax1,'Iteration');ylabel(ax1,'J');grid(ax1,'on');legend(ax1,'Interpreter','none');
 set(ax2,'YScale','log');xlabel(ax2,'Iteration');ylabel(ax2,'IPOPT primal infeasibility');grid(ax2,'on');
 savefigure(f,out,'convergence_compare');
end
if all(isfield(results,{'four_grid100','four_corridor'}))
 a=results.four_grid100;b=results.four_corridor;d=vecnorm(interp1(a.time,a.X(:,1:3),b.time)-b.X(:,1:3),2,2);
 writetable(array2table([b.time d],'VariableNames',{'t','position_difference_m'}),fullfile(out,'grid_position_difference.csv'));
end
end
function columns(obs)
th=linspace(0,2*pi,120);for j=1:size(obs,1),fill(obs(j,1)+obs(j,3)*cos(th),obs(j,2)+obs(j,3)*sin(th),[.85 .85 .85],'EdgeColor',[.5 .5 .5]);end
end
function box3(b,c)
v=[b(1) b(2) b(3);b(4) b(2) b(3);b(4) b(5) b(3);b(1) b(5) b(3);b(1) b(2) b(6);b(4) b(2) b(6);b(4) b(5) b(6);b(1) b(5) b(6)];
patch('Vertices',v,'Faces',[1 2 3 4;5 6 7 8;1 2 6 5;2 3 7 6;3 4 8 7;4 1 5 8],'FaceColor',c,'FaceAlpha',.02,'EdgeColor',c,'EdgeAlpha',.3);
end
function savefigure(f,out,name)
exportgraphics(f,fullfile(out,[name '.pdf']),'ContentType','vector');exportgraphics(f,fullfile(out,[name '.png']),'Resolution',160);close(f);
end
