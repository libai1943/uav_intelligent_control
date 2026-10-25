function agg=ch9_summarize(out,rows,seeds)
ch9_write_structs(fullfile(out,'metrics_by_seed.csv'),rows);
methods=unique({rows.method},'stable');agg=struct([]);
for k=1:numel(methods)
    method=methods{k};d=[];
    for s=seeds
        x=readmatrix(fullfile(out,sprintf('evaluation_%s_%d.csv',method,s)),'NumHeaderLines',1);
        d=[d;x]; %#ok<AGROW>
    end
    rr=rows(strcmp({rows.method},method));m=ch9_metrics(d);
    row.method=method;row.seeds=numel(seeds);n=fieldnames(m);
    for j=1:numel(n),row.(n{j})=m.(n{j});end
    row.win_sd_between_seeds=std([rr.win],0);row.score_sd_between_seeds=std([rr.score],0);
    agg=[agg,row]; %#ok<AGROW>
end
ch9_write_structs(fullfile(out,'summary.csv'),agg);
by=table();
for s=seeds
    t=readtable(fullfile(out,sprintf('by_opponent_%d.csv',s)));by=[by;t]; %#ok<AGROW>
end
writetable(by,fullfile(out,'metrics_by_opponent.csv'));
end
