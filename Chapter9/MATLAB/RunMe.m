% Independent one-click book profile; no Python process or learning toolbox.
here=fileparts(mfilename('fullpath'));addpath(here);
try
    ch9_run('book');
catch ME
    if strcmp('book','book'),out=fullfile(here,'outputs');else,out=fullfile(here,'outputs_quick');end
    ch9_save_json(fullfile(out,'run_status.json'),struct('status','failed','error',ME.message));
    rethrow(ME);
end
