"""Section 6.3: real BP trajectories in a two-parameter plane.

Network: hidden=tanh(theta0*x), prediction=theta1*hidden. Both biases are zero.
Both trainable weights are updated by analytic backpropagation. Only batch size
changes across runs; data, initial weights, rate and shuffled data stream match.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SAMPLES, UPDATES, RATE = 1000, 1500, 0.3
INITIAL = np.array([1., 1.2])
MODES = [('single', 1, '单样本'), ('mini', 10, '小批量（10条）'), ('full', 1000, '全批量')]
COLORS = ['#bb3b35', '#25846c', '#315ca4']

def uniform_stream(seed, count):
    """Identical integer generator in Python and MATLAB."""
    values = np.empty(count)
    for i in range(count):
        seed = (1664525*seed+1013904223) % 2**32
        values[i] = seed/2**32
    return values, seed

def make_problem():
    x = np.linspace(-1., 1., SAMPLES)
    clean = 1.6*np.tanh(2.4*x)
    noise, _ = uniform_stream(20261101, SAMPLES)
    return x, clean, clean+0.2*(2*noise-1)

def predict(theta, x):
    return theta[1]*np.tanh(theta[0]*x)

def loss_and_gradient(theta, x, target):
    hidden = np.tanh(theta[0]*x)
    error = theta[1]*hidden-target
    # Output derivative is 1; hidden derivative is 1-hidden**2.
    gradient = np.array([np.mean(error*theta[1]*(1-hidden**2)*x), np.mean(error*hidden)])
    return float(.5*np.mean(error**2)), gradient

def check_gradient(x, target):
    errors=[]
    for count in (1, 10, 1000):
        _, analytic=loss_and_gradient(INITIAL, x[:count], target[:count])
        numeric=np.zeros(2)
        for i in range(2):
            left,right=INITIAL.copy(),INITIAL.copy()
            left[i]-=1e-6;right[i]+=1e-6
            numeric[i]=(loss_and_gradient(right,x[:count],target[:count])[0]
                        -loss_and_gradient(left,x[:count],target[:count])[0])/2e-6
        errors.append(float(np.max(np.abs(analytic-numeric))))
    assert max(errors)<1e-8,errors
    return errors

def train(x, target, batch):
    theta=INITIAL.copy();seed=456;offset=SAMPLES
    path=np.empty((UPDATES+1,2));path[0]=theta
    history=np.empty((UPDATES+1,3));history[0]=[0,0,loss_and_gradient(theta,x,target)[0]]
    for step in range(1,UPDATES+1):
        if offset==SAMPLES:
            values,seed=uniform_stream(seed,SAMPLES)
            order=np.argsort(values);offset=0
        ids=order[offset:offset+batch];offset+=batch
        _,gradient=loss_and_gradient(theta,x[ids],target[ids])
        theta-=RATE*gradient
        path[step]=theta
        history[step]=[step,step*batch,loss_and_gradient(theta,x,target)[0]]
    assert np.isfinite(path).all()
    return path,history

def plot_results(out,x,clean,target,traces):
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'],
                         'axes.unicode_minus':False,'font.size':12,
                         'pdf.fonttype':42,'path.simplify':False})
    fig,ax=plt.subplots(figsize=(7.4,4.3))
    for (name,_,label),color,marker in zip(MODES,COLORS,['s','+','o']):
        path,_=traces[name]
        # Consecutive true updates, no smoothing. Markers spaced for legibility.
        ax.plot(path[:,0],path[:,1],color=color,lw=1.05 if name!='full' else 1.8,
                marker=marker,markersize=4 if name!='full' else 3.8,
                markevery=20,label=label,zorder=2 if name!='full' else 3)
    ax.plot(*INITIAL,marker='*',ms=10,color='#273642',zorder=5)
    ax.annotate('共同起点',INITIAL,xytext=(12,-5),textcoords='offset points',fontsize=10)
    ax.set(xlabel=r'输入权重 $\theta_0$',ylabel=r'输出权重 $\theta_1$',xlim=(.96,2.5),ylim=(1.16,1.98))
    ax.legend(loc='upper left',frameon=False,handlelength=2.4,fontsize=11)
    ax.spines[['top','right']].set_visible(False);ax.tick_params(direction='in');fig.tight_layout(pad=1.1)
    fig.savefig(out/'training_modes.pdf');fig.savefig(out/'training_modes.png',dpi=210);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.4,3.6))
    for (name,_,label),color in zip(MODES,COLORS):
        _,hist=traces[name];ax.semilogy(hist[:,0],hist[:,2],color=color,lw=1.1,label=label)
    ax.set(xlabel='参数更新次数',ylabel='全训练集的平均损失',xlim=(0,UPDATES))
    ax.legend(frameon=False);ax.grid(alpha=.15);fig.tight_layout()
    fig.savefig(out/'training_loss.pdf');fig.savefig(out/'training_loss.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.4,3.6))
    ax.scatter(x,target,s=4,color='#8d969d',alpha=.5,label='含噪声训练样本')
    ax.plot(x,clean,color='#273642',lw=1.4,label='生成函数')
    ax.set(xlabel='输入 x',ylabel='目标值 d');ax.legend(frameon=False);fig.tight_layout()
    fig.savefig(out/'training_samples.png',dpi=180);plt.close(fig)

def main(out=None):
    out=Path(out) if out else Path(__file__).resolve().parent/'results/training_modes'
    out.mkdir(parents=True,exist_ok=True)
    x,clean,target=make_problem();traces={}
    report={'samples':SAMPLES,'updates':UPDATES,'learning_rate':RATE,'initial_weights':INITIAL.tolist(),
            'noise_bound':.2,'gradient_max_abs_errors':check_gradient(x,target),'modes':{}}
    np.savetxt(out/'training_samples.csv',np.c_[x,target,clean],delimiter=',',header='x,target,clean',comments='',fmt='%.17g')
    for name,batch,_ in MODES:
        path,hist=train(x,target,batch);traces[name]=(path,hist)
        np.savetxt(out/f'{name}_parameters.csv',path,delimiter=',',header='theta0,theta1',comments='',fmt='%.17g')
        np.savetxt(out/f'{name}_loss.csv',hist,delimiter=',',header='updates,samples_used,full_training_loss',comments='',fmt='%.17g')
        report['modes'][name]={'batch_size':batch,'samples_used':UPDATES*batch,
                              'initial_loss':float(hist[0,2]),'final_loss':float(hist[-1,2]),'final_weights':path[-1].tolist()}
    plot_results(out,x,clean,target,traces)
    (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));return report

if __name__=='__main__': main()
