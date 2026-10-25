function ch9_write_structs(path,rows)
if isempty(rows),return;end
names=fieldnames(rows);folder=fileparts(path);if ~exist(folder,'dir'),mkdir(folder);end
f=fopen(path,'w','n','UTF-8');if f<0,error('CH9:File','Cannot write %s',path);end
cleanup=onCleanup(@()fclose(f)); %#ok<NASGU>
fprintf(f,'%s\n',strjoin(names.',','));
for i=1:numel(rows)
    parts=cell(1,numel(names));
    for j=1:numel(names)
        v=rows(i).(names{j});
        if isnumeric(v) || islogical(v),parts{j}=sprintf('%.16g',v);else,parts{j}=char(v);end
    end
    fprintf(f,'%s\n',strjoin(parts,','));
end
end
