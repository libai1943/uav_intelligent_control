#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
if ! .venv/bin/python -c 'import numpy, matplotlib' >/dev/null 2>&1; then
  .venv/bin/python -m pip install -r requirements.txt
fi
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
.venv/bin/python RunMe.py --profile book --parallel
