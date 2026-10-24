function RunMe(caseName)
% Independent MATLAB implementation. No Python process is invoked.
% Install CasADi 3.7.2 for MATLAB, add it to the path, then run RunMe.
% Alternatively set the environment variable CASADI_MATLAB_PATH.
if nargin<1,caseName='all';end
root=fileparts(mfilename('fullpath'));addpath(fullfile(root,'matlab'));
dependency=getenv('CASADI_MATLAB_PATH');
if ~isempty(dependency),addpath(dependency);end
assert(exist('casadi.MX','class')==8 || exist('casadiMEX','file')==3, ...
 'Install CasADi for MATLAB and add its directory to the MATLAB path. See README.md.');
setenv('OMP_NUM_THREADS','1');setenv('OPENBLAS_NUM_THREADS','1');setenv('MKL_NUM_THREADS','1');
settings=jsondecode(fileread(fullfile(root,'config.json')));
jobs={'two_straight','two','straight',false,200; 'two_north','two','north',false,200; ...
 'two_south','two','south',false,200;'two_corridor','two','astar',true,200; ...
 'four_direct','four','astar',false,200;'four_corridor','four','astar',true,200; ...
 'five_corridor','five','astar',true,200;'four_grid100','four','astar',true,100; 'slalom_direct','slalom','astar',false,200; ...
 'crowd10_direct','crowd10','north',false,200; 'crowd20_direct','crowd20','north',false,200};
assert(strcmp(caseName,'all') || any(strcmp(caseName,jobs(:,1))),'Unknown experiment name.');
out=fullfile(root,'results_matlab');if ~exist(out,'dir'),mkdir(out);end
results=struct();records={};
for i=1:size(jobs,1)
 name=jobs{i,1};if ~strcmp(caseName,'all') && ~strcmp(caseName,name),continue;end
 fprintf('%s: constructing and solving\n',name);
 cfg=settings.config;sc=settings.scenes.(jobs{i,2});
 if isfield(sc,'overrides'),fields=fieldnames(sc.overrides);for j=1:numel(fields),cfg.(fields{j})=sc.overrides.(fields{j});end;end
 cfg.benchmark_repetitions=1;
 if any(strcmp(name,{'two_north','crowd10_direct','crowd20_direct'})),cfg.benchmark_repetitions=5;end
 r=solve_fixedwing(cfg,sc,jobs{i,2},jobs{i,3},jobs{i,4},jobs{i,5});
 folder=fullfile(out,name);if ~exist(folder,'dir'),mkdir(folder);end
 save(fullfile(folder,'data.mat'),'r');
 writecsv(fullfile(folder,'state.csv'),[r.time,r.X],{'t','x','y','z','V','gamma','chi','phi'});
 writecsv(fullfile(folder,'control.csv'),[r.time(1:end-1),r.U],{'t','a','omega_gamma','omega_phi'});
 writecsv(fullfile(folder,'initial_state.csv'),[r.time,r.initial_X],{'t','x','y','z','V','gamma','chi','phi'});
 writecsv(fullfile(folder,'initial_control.csv'),[r.time(1:end-1),r.initial_U],{'t','a','omega_gamma','omega_phi'});
 writecsv(fullfile(folder,'raw_path.csv'),r.raw,{'x','y','z'});
 writecsv(fullfile(folder,'boxes.csv'),r.boxes,{'xmin','ymin','zmin','xmax','ymax','zmax'});
 meta=rmfield(r,{'X','U','time','initial_X','initial_U','raw','spline','knots','boxes','owner','columns','history','rollout'});
 writejson(fullfile(folder,'result.json'),meta);records{end+1}=meta; %#ok<AGROW>
 results.(name)=r;
 fprintf('accepted=%d, J=%.8g, iterations=%d, solve=%.4f s, violation=%.3g\n', ...
   r.accepted,r.objective,r.iterations,r.seconds,r.checks.max_scaled_constraint_violation);
 assert(r.accepted,'Inspect result.json: solver or independent checks failed.');
end
environment=struct('matlab',version,'computer',computer,'casadi',casadi.CasadiMeta.version(), ...
 'solver','IPOPT bundled with CasADi','random_initialization',false,'deterministic',true);
[~,os]=system('ver');environment.os=strtrim(os);
writejson(fullfile(out,'summary.json'),struct('config',settings.config,'scenes',settings.scenes, ...
 'environment',environment,'results',{records}));
matlab_examples(out);plot_results(results,out);
fprintf('Finished: %s\n',out);
end

function writecsv(path,data,names)
writetable(array2table(data,'VariableNames',names),path);
end
function writejson(path,data)
fid=fopen(path,'w','n','UTF-8');assert(fid>=0);c=onCleanup(@()fclose(fid));
fprintf(fid,'%s',jsonencode(data,'PrettyPrint',true));
end
