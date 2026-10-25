function ch9_run(profile)
%CH9_RUN Independent, base-MATLAB training and experiment entry point.
% MATLAB R2022b or newer; no Reinforcement Learning/Deep Learning Toolbox.
if nargin<1,profile='book';end
here=fileparts(mfilename('fullpath'));root=fileparts(here);addpath(here);
if strcmp(profile,'book'),out=fullfile(here,'outputs');else,out=fullfile(here,'outputs_quick');end
if ~exist(out,'dir'),mkdir(out);end
ch9_save_json(fullfile(out,'run_status.json'),struct('status','running','profile',profile));
fprintf('Chapter 9: %s profile. Fresh PPO training will run.\n',profile);
checks=ch9_tests(root); %#ok<NASGU>
ch9_foundations(out);c=ch9_config(profile);
if strcmp(profile,'book'),seeds=[101 202 303];else,seeds=101;end
meta.profile=profile;meta.training_seeds=seeds;meta.config=c;
meta.runtime=['MATLAB ' version];meta.matlab_runtime_verified=true;
meta.gates=[10 0 2.5 3.6 2.2;20 1.5 3 3.2 2;30 -1 2.4 1.2 1;40 1 3 3.2 2;50 0 2.5 2.6 1.8];
meta.explanation='Fresh MATLAB training. No Python process or supplied trained weights are used by this entry point.';
ch9_save_json(fullfile(out,'configuration.json'),meta);start=tic;rows=struct([]);
for seed=seeds
    rr=ch9_run_seed(c,seed,out);rows=[rows rr]; %#ok<AGROW>
end
ch9_summarize(out,rows,seeds);ch9_trajectory_examples(c,out,seeds(1));ch9_plot_results(out,seeds);
meta.elapsed_seconds=toc(start);ch9_save_json(fullfile(out,'configuration.json'),meta);
fprintf('\nResults, CSV records, weights, PDF/PNG/FIG plots: %s\n',out);
fprintf('Book figures are based on the supplied Python reference run. Inspect your local results before replacing manuscript assets.\n');
end
