"""Chapter 6: conventional feedback and neural feedforward learning.

Run this file once to simulate both controllers, save all samples, draw the
comparison and check the results. Only NumPy and Matplotlib are required.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

OUT = Path(__file__).resolve().parent / 'results'
DT, END = 0.01, 10.0
REFERENCE, HEIGHT_SCALE, FORCE_SCALE = 3.0, 3.0, 1.0
MASS, NOMINAL_MASS, GRAVITY, DAMPING = 1.6, 1.5, 9.8, 1.6
KP, KD, RATE, LIMIT = 6.0, 5.0, 0.006, 24.0
THETA0 = np.array([0.3, -0.3, 0.2, -0.2, 0., 0., 0.])
FIELDS = 'time,height,velocity,error,neural,feedback,thrust,W1,W2,b1,b2,v1,v2,c'


def forward_and_gradient(theta, feature):
    """One input, two tanh hidden units, one linear output; analytic BP."""
    hidden = np.tanh(theta[:2] * feature + theta[2:4])
    output = theta[4:6] @ hidden + theta[6]
    hidden_delta = theta[4:6] * (1.0 - hidden**2)
    gradient = np.r_[hidden_delta * feature, hidden_delta, hidden, 1.0]
    return float(output), gradient


def controller(height, velocity, theta, learning):
    """Uses measured motion and nominal mass, never the actual mass."""
    feedback = KP * (REFERENCE - height) - KD * velocity
    output, gradient = forward_and_gradient(theta, REFERENCE / HEIGHT_SCALE)
    neural = FORCE_SCALE * output if learning else 0.0
    command = NOMINAL_MASS * GRAVITY + neural + feedback
    thrust = float(np.clip(command, 0.0, LIMIT))
    # All derivatives use the same pre-update parameters. New parameters are
    # used next cycle. Do not train on a correction the actuator cannot apply.
    next_theta = theta.copy()
    if learning and 0.0 < command < LIMIT:
        next_theta += RATE * (feedback / FORCE_SCALE) * gradient
    return neural, feedback, thrust, next_theta


def simulate(learning):
    height, velocity, theta = REFERENCE, 0.0, THETA0.copy()
    rows = []
    for k in range(round(END / DT) + 1):
        neural, feedback, thrust, next_theta = controller(height, velocity, theta, learning)
        rows.append([k*DT, height, velocity, REFERENCE-height,
                     neural, feedback, thrust, *theta])
        # Synchronous Euler: both new states use the previous state.
        height, velocity = (height + DT*velocity,
                            velocity + DT*(thrust-MASS*GRAVITY-DAMPING*velocity)/MASS)
        theta = next_theta
    return np.asarray(rows)


def summarize(data):
    return dict(final_error=float(data[-1,3]), final_neural=float(data[-1,4]),
                final_feedback=float(data[-1,5]), peak_abs_error=float(abs(data[:,3]).max()),
                min_thrust=float(data[:,6].min()), max_thrust=float(data[:,6].max()))


def plot_results(feedback, learning):
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],
                         'axes.unicode_minus':False,'font.size':10,'pdf.fonttype':42})
    c = ['#555D67','#217D8A','#A86E36','#6C5797']
    fig, axes = plt.subplots(3,1,figsize=(7.0,6.5),sharex=True)
    t = learning[:,0]
    for data, color, style in [(feedback,c[0],'--'),(learning,c[1],'-')]:
        axes[0].plot(t,data[:,3],style,color=color,lw=1.6)
        axes[2].plot(t,data[:,6],style,color=color,lw=1.6)
    axes[1].plot(t,learning[:,4],color=c[2],lw=1.7)
    axes[1].plot(t,learning[:,5],color=c[3],lw=1.6)
    for ax, name in zip(axes,['高度误差 / m','学习方案的修正 / N','总推力 / N']):
        ax.set_ylabel(name);ax.grid(alpha=.2);ax.set_xlim(0,END)
        ax.spines[['top','right']].set_visible(False)
    axes[-1].set_xlabel('时间 / s')
    handles=[Line2D([0],[0],color=c[0],ls='--',lw=1.6),
             Line2D([0],[0],color=c[1],lw=1.6),
             Line2D([0],[0],color=c[2],lw=1.7),Line2D([0],[0],color=c[3],lw=1.6)]
    fig.legend(handles,['仅常规反馈','加入神经网络学习控制','网络前馈','常规反馈修正'],
               loc='upper center',ncol=2,frameon=False,bbox_to_anchor=(.53,.995))
    fig.subplots_adjust(left=.14,right=.98,bottom=.09,top=.89,hspace=.23)
    fig.savefig(OUT/'learning_control.pdf');fig.savefig(OUT/'learning_control.png',dpi=180)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    results = {name:simulate(flag) for name,flag in [('feedback',False),('learning',True)]}
    for name,data in results.items():
        np.savetxt(OUT/f'{name}.csv',data,delimiter=',',header=FIELDS,comments='',fmt='%.16g')
    summary={name:summarize(data) for name,data in results.items()}
    assert abs(summary['feedback']['final_error']-(MASS-NOMINAL_MASS)*GRAVITY/KP)<1e-4
    assert abs(summary['learning']['final_error'])<1e-4
    assert abs(summary['learning']['final_neural']-(MASS-NOMINAL_MASS)*GRAVITY)<1e-4
    assert all(0<s['min_thrust']<=s['max_thrust']<LIMIT for s in summary.values())
    summary['checks_passed']=True
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),'utf-8')
    plot_results(results['feedback'],results['learning'])
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print(f'Results: {OUT}')
    from TrainingModes import main as training_modes
    training_modes(OUT/'training_modes')


if __name__ == '__main__':
    main()
