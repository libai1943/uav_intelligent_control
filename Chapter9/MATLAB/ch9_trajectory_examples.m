function ch9_trajectory_examples(c,out,seed)
a=ch9_load_net(fullfile(out,'models',sprintf('league_%d.json',seed)));
[~,d,logs]=ch9_evaluate(a,c,1810101,100,3,false,false,true);
all=vertcat(logs{:});initial=logs{1};ids=find(d(:,3)==1 & initial(:,3)<initial(:,6));
if isempty(ids),ids=find(d(:,3)==1);end
if isempty(ids),eid=0;else,eid=ids(1)-1;end
H={'episode','time','x_A','y_A','z_A','x_B','y_B','z_B','vx_A','vy_A','vz_A','vx_B','vy_B','vz_B','gate_A','gate_B','action_speed_A','action_y_A','action_z_A','action_speed_B','action_y_B','action_z_B','done'};
ch9_write_array(fullfile(out,'trajectory_all_episodes.csv'),all,H);
ep=all(all(:,1)==eid,:);ep=ep([true;diff(ep(:,2))>1e-10],:);
ch9_write_array(fullfile(out,'trajectory_example.csv'),ep,H);
bad=find(ismember(d(:,3),[4 5 7]));
if ~isempty(bad)
    ep=all(all(:,1)==bad(1)-1,:);ep=ep([true;diff(ep(:,2))>1e-10],:);
    ch9_write_array(fullfile(out,'trajectory_failure.csv'),ep,H);
end
r.seed=1810101;r.episode=eid;r.rule='First initially trailing winner vs fast rule; otherwise first winner; otherwise episode 0.';
ch9_save_json(fullfile(out,'trajectory_selection.json'),r);
end
