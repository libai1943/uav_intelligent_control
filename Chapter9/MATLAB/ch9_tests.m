function checks=ch9_tests(root)
%CH9_TESTS Run before training. Numerical fixtures originate in NumPy and
% are independently recomputed here. Passing is a local runtime result.
c=ch9_config('book');
[u,~]=ch9_random(1,1,3);expected=[16807 282475249 1622650073]/2147483647;
assert(max(abs(u-expected))<1e-15);checks.portable_rng=true;
p=fullfile(root,'validation','cross_language_fixture.json');
if ~exist(p,'file'),error('CH9:Fixture','Missing supplied validation fixture.');end
f=jsondecode(fileread(p));a=f.actor;a.b1=a.b1(:).';a.b2=a.b2(:).';a.logstd=a.logstd(:).';
[loss,g,~,~]=ch9_actor_loss(a,f.x,f.b,f.oldlp(:),f.adv(:),c.ppo_clip);
checks.cross_language_loss_error=abs(loss-f.loss);
assert(checks.cross_language_loss_error<1e-9,'PPO loss differs from fixture.');
names=fieldnames(g);mx=0;
for k=1:numel(names)
    name=names{k};expected=f.gradient.(name);observed=g.(name);
    if isvector(observed),expected=reshape(expected,size(observed));end
    d=abs(observed-expected);mx=max(mx,max(d(:)));
end
checks.cross_language_gradient_error=mx;
assert(mx<1e-8,'PPO gradient differs from fixture.');
% Finite difference, independent of the stored expected derivative.
val=a.W1(3,2);eps=1e-6;a.W1(3,2)=val+eps;
[l1,~,~,~]=ch9_actor_loss(a,f.x,f.b,f.oldlp(:),f.adv(:),c.ppo_clip);
a.W1(3,2)=val-eps;
[l0,~,~,~]=ch9_actor_loss(a,f.x,f.b,f.oldlp(:),f.adv(:),c.ppo_clip);a.W1(3,2)=val;
checks.finite_difference_error=abs((l1-l0)/(2*eps)-g.W1(3,2));
assert(checks.finite_difference_error<2e-7);
[~,d,~]=ch9_evaluate(a,c,f.evaluation_seed,f.evaluation_n);
err=abs(d-f.evaluation_details);checks.cross_language_rollout_error=max(err(:));
assert(checks.cross_language_rollout_error<1e-7,'Frozen-policy rollout differs from Python fixture.');
[e,~]=ch9_env_init(c,1,1);e.p(:,:,1)=[0 -1 2.5];e.p(:,:,2)=[0 1 2.5];
e.v(:,:,1)=[0 60 0];e.v(:,:,2)=[0 -60 0];[e,~]=ch9_env_step(e,zeros(1,3,2));
assert(e.reason==4 && abs(e.t-.01)<1e-10);checks.swept_clearance=true;
[e,~]=ch9_env_init(c,1,1);e.g(:)=4;e.p(:,:,1)=[49.9 -.45 2.5];e.p(:,:,2)=[49.8 .45 2.5];
e.v(:,:,1)=[5 0 0];e.v(:,:,2)=[5 0 0];[e,~]=ch9_env_step(e,zeros(1,3,2));
assert(e.reason==1 && abs(e.t-.02)<1e-10);checks.substep_finish_order=true;
checks.runtime=version;checks.status='PASSED in the runtime recorded above';
ch9_save_json(fullfile(root,'MATLAB','outputs','matlab_tests.json'),checks);
fprintf('All MATLAB-local numerical tests passed.\n');
end
