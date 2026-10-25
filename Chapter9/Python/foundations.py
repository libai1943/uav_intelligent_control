"""Small, fully enumerable Q-learning exercise using chapter hand-example values."""
from pathlib import Path
import json
import numpy as np
from ch9_core import PortableRNG

def run(out,episodes=5000):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    q=np.zeros((3,2));visits=np.zeros((3,2),int);rng=PortableRNG(92);history=[]
    def action(s):
        u=rng.uniform((2,))
        if u[0]<.2:return int(u[1]>=.5)
        idx=np.flatnonzero(q[s]==q[s].max());return int(idx[min(int(u[1]*len(idx)),len(idx)-1)])
    for ep in range(episodes):
        s=0;a=action(s);ns=1 if a==0 else 2;r=2. if a==0 else 1.
        visits[s,a]+=1;eta=visits[s,a]**(-.65)
        q[s,a]+=eta*(r+.9*q[ns].max()-q[s,a])
        s=ns;a=action(s);r=[[3.,1.],[6.,2.]][s-1][a]
        visits[s,a]+=1;eta=visits[s,a]**(-.65);q[s,a]+=eta*(r-q[s,a])
        if ep%25==0 or ep==episodes-1:history.append([ep+1,*q.ravel()])
    exact=np.array([[4.7,6.4],[3.,1.],[6.,2.]])
    err=float(np.max(np.abs(q-exact)))
    assert err<1e-5
    np.savetxt(out/'q_learning_history.csv',np.array(history),delimiter=',',header='episode,Q00,Q01,Q10,Q11,Q20,Q21',comments='')
    report={'Q':q.tolist(),'exact':exact.tolist(),'max_absolute_error':err,'visits':visits.tolist(),
     'one_step_Q_nonterminal':2+.2*(.5+.9*4-2),'one_step_Q_terminal':2+.2*(.5-2),
     'PPO_terms':[2.4,1.2,-1.6,-3.0]}
    (out/'foundations.json').write_text(json.dumps(report,indent=2))
    return report
if __name__=='__main__':print(run(Path(__file__).resolve().parent/'outputs'))
