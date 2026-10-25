function net=ch9_load_net(path)
net=jsondecode(fileread(path));
net.b1=reshape(net.b1,1,[]);net.b2=reshape(net.b2,1,[]);
if isfield(net,'logstd'),net.logstd=reshape(net.logstd,1,[]);end
end
