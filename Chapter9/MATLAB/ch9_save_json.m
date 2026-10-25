function ch9_save_json(path,data)
folder=fileparts(path);if ~exist(folder,'dir'),mkdir(folder);end
f=fopen(path,'w','n','UTF-8');if f<0,error('CH9:File','Cannot write %s',path);end
cleaner=onCleanup(@()fclose(f)); %#ok<NASGU>
fprintf(f,'%s',jsonencode(data));
end
