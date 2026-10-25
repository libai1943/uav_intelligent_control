function ch9_write_array(path,x,headers)
folder=fileparts(path);if ~exist(folder,'dir'),mkdir(folder);end
f=fopen(path,'w','n','UTF-8');if f<0,error('CH9:File','Cannot write %s',path);end
cleanup=onCleanup(@()fclose(f)); %#ok<NASGU>
fprintf(f,'%s\n',strjoin(headers,','));
format=[repmat('%.16g,',1,size(x,2)-1) '%.16g\n'];
fprintf(f,format,x.');
end
