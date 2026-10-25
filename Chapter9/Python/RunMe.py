#!/usr/bin/env python3
"""One entry point: all numerical checks, fresh PPO training, evaluation, plots."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ.setdefault(key,'1')
from pathlib import Path
import argparse
from run_experiments import run_all

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',choices=['book','quick'],default='book')
    p.add_argument('--parallel',action='store_true',help='Parallelize independent training seeds.')
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    out=a.out or Path(__file__).resolve().parent/('outputs' if a.profile=='book' else 'outputs_quick')
    try:
        run_all(a.profile,out=out,parallel=a.parallel)
    except Exception as exc:
        import json
        out.mkdir(parents=True,exist_ok=True)
        (out/'run_status.json').write_text(json.dumps({'status':'failed','error':str(exc)}),encoding='utf-8')
        raise

if __name__=='__main__':main()
