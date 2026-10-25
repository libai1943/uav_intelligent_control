function c = ch9_config(profile)
%CH9_CONFIG Same model and PPO settings as the independent NumPy version.
if nargin < 1, profile = 'book'; end
c.dt=.05; c.substeps=4; c.time_limit=24;
c.speed_mid=4.5; c.speed_scale=2; c.accel_max=6;
c.velocity_tau=.35; c.lateral_gain=2.2;
c.lateral_speed_max=2.2; c.vertical_speed_max=1.6;
c.gate_margin=.30; c.separation=.80; c.offset_fraction=.80;
c.beta=1; c.gamma=1; c.hidden=24;
c.actor_lr=5e-4; c.critic_lr=1.5e-3; c.ppo_clip=.2;
c.epochs=4; c.minibatch=256; c.grad_clip=.70;
c.initial_std=.45; c.std_min=.07; c.std_max=.65;
c.batch_episodes=64; c.iterations=500; c.snapshot_every=10;
c.pool_capacity=6; c.eval_every=10; c.eval_episodes=400; c.max_kl=.03;
% Evaluation uses 400 episodes per seed (same as the Python Config default).
if strcmp(profile,'quick')
    c.iterations=20; c.batch_episodes=32; c.eval_episodes=80;
elseif ~strcmp(profile,'book')
    error('CH9:Profile','Profile must be book or quick.');
end
end
