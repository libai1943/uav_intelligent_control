function rows=ch9_run_seed(c,seed,out)
H={'episode','opponent','reason','score_A','score_B','stop_time','gates_A','gates_B','minimum_separation','maximum_acceleration','shaped_return_A','shaped_return_B','initial_potential_A','initial_potential_B'};
rows=struct([]);by=struct([]);modes={'fixed','league'};
for k=1:2
    mode=modes{k};[a,initial,critic,pool,records]=ch9_train(c,seed,mode);
    ch9_save_json(fullfile(out,'models',sprintf('%s_%d.json',mode,seed)),a);
    ch9_save_json(fullfile(out,'models',sprintf('%s_%d_critic.json',mode,seed)),critic);
    ch9_save_json(fullfile(out,'models',sprintf('initial_%d.json',seed)),initial);
    for j=1:numel(pool),ch9_save_json(fullfile(out,'models',sprintf('%s_%d_history%d.json',mode,seed,j-1)),pool{j});end
    ch9_write_structs(fullfile(out,sprintf('training_%s_%d.csv',mode,seed)),records);
    executions={'sampled','mean'};
    for kx=1:2
        execution=executions{kx};name=[mode '_' execution];
        [m,d,~]=ch9_evaluate(a,c,1800000+seed,c.eval_episodes,0:4,strcmp(execution,'mean'));
        m=rmfield(m,'potential_audit');row=add_info(m,seed,name);rows=[rows,row]; %#ok<AGROW>
        ch9_write_array(fullfile(out,sprintf('evaluation_%s_%d.csv',name,seed)),d,H);
        for kind=0:4
            mm=ch9_metrics(d(d(:,2)==kind,:));rr=add_info(mm,seed,name);rr.opponent=kind;by=[by,rr]; %#ok<AGROW>
        end
    end
    [m,d,~]=ch9_evaluate(a,c,1900000+seed,c.eval_episodes,[1 3 4],false,false);
    m=rmfield(m,'potential_audit');rows=[rows,add_info(m,seed,[mode '_holdout'])]; %#ok<AGROW>
    ch9_write_array(fullfile(out,sprintf('evaluation_%s_holdout_%d.csv',mode,seed)),d,H);
    [m,d,~]=ch9_evaluate(a,c,1900000+seed,c.eval_episodes,[1 3 4],false,true);
    m=rmfield(m,'potential_audit');rows=[rows,add_info(m,seed,[mode '_mirror'])]; %#ok<AGROW>
    ch9_write_array(fullfile(out,sprintf('evaluation_%s_mirror_%d.csv',mode,seed)),d,H);
    if strcmp(mode,'league')
        [m,d,~]=ch9_evaluate(a,c,1800000+seed,c.eval_episodes,0:4,false,false,false,-1,true);
        m=rmfield(m,'potential_audit');rows=[rows,add_info(m,seed,'league_blind')]; %#ok<AGROW>
        ch9_write_array(fullfile(out,sprintf('evaluation_league_blind_%d.csv',seed)),d,H);
    end
end
names={'initial','rule_center','rule_reactive','rule_fast','rule_max'};rules=[-1 0 2 3 5];
for k=1:numel(names)
    [m,d,~]=ch9_evaluate(initial,c,1800000+seed,c.eval_episodes,0:4,false,false,false,rules(k));
    m=rmfield(m,'potential_audit');rows=[rows,add_info(m,seed,names{k})]; %#ok<AGROW>
    ch9_write_array(fullfile(out,sprintf('evaluation_%s_%d.csv',names{k},seed)),d,H);
end
ch9_write_structs(fullfile(out,sprintf('metrics_%d.csv',seed)),rows);
ch9_write_structs(fullfile(out,sprintf('by_opponent_%d.csv',seed)),by);
end
function row=add_info(m,seed,name)
row.seed=seed;row.method=name;
n=fieldnames(m);for i=1:numel(n),row.(n{i})=m.(n{i});end
end
