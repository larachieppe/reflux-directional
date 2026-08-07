#!/bin/zsh
# Run the remaining studies strictly one at a time.
#
# This machine has 8 GB and each worker holds a CEM factorization, so two studies
# running at once do not go twice as fast -- they livelock in swap. That is not a
# hypothesis: two precision runs overlapped and neither advanced for 30 minutes.
# Nothing here starts until the previous study has written its metrics file.
#
# ORDER. Forward-model verification runs before the remaining science, even
# though it is not itself a study: it checks reciprocity and mesh convergence,
# and if the forward solve is not converged then every result already published
# is suspect. It is also short (minutes), so it costs almost nothing to front-load.
cd "$(dirname "$0")" || exit 1
PY=.venv/bin/python

wait_for_pid() {          # $1 = pid to wait on (may already be gone)
  while kill -0 "$1" 2>/dev/null; do sleep 20; done
}

run_step() {              # $1 = script, $2 = metrics file, $3 = log
  if [ -f "$2" ]; then
    echo "[queue] $2 already present, skipping $1" >&2
    return 0
  fi
  echo "[queue] starting $1 -> $2" >&2
  $PY "$1" >> "$3" 2>&1
  if [ -f "$2" ]; then
    echo "[queue] $1 finished" >&2
  else
    echo "[queue] $1 exited WITHOUT writing $2" >&2
    return 1
  fi
}

# If a precision run is already in flight, wait it out rather than starting a second.
RUNNING=$(pgrep -f "run_precision.py" | head -1)
if [ -n "$RUNNING" ]; then
  echo "[queue] precision already running as $RUNNING, waiting" >&2
  wait_for_pid "$RUNNING"
fi

# precision resumes from its JSONL checkpoint if it was interrupted
run_step run_precision.py  metrics_precision.json /tmp/prec.log

# short, foundational: reciprocity + mesh convergence + contact-impedance immunity
run_step verify_forward.py metrics_verify.json    /tmp/verify.log

# the existential one: non-rigid respiratory motion
run_step run_motion2.py    metrics_motion2.json   /tmp/motion2.log

echo "[queue] all queued work finished" >&2
