#!/bin/zsh
# Run the remaining studies strictly one at a time.
#
# This machine has 8 GB and each worker holds a CEM factorization, so two studies
# running at once do not go twice as fast -- they livelock in swap. That is not a
# hypothesis: two precision runs overlapped and neither advanced for 30 minutes.
# Nothing here starts until the previous study has written its metrics file.
cd "$(dirname "$0")" || exit 1
PY=.venv/bin/python

wait_for_pid() {          # $1 = pid to wait on (may already be gone)
  while kill -0 "$1" 2>/dev/null; do sleep 20; done
}

# If a precision run is already in flight, wait it out rather than starting a second.
RUNNING=$(pgrep -f "run_precision.py" | head -1)
if [ -n "$RUNNING" ]; then
  echo "[queue] precision already running as $RUNNING, waiting" >&2
  wait_for_pid "$RUNNING"
fi

if [ ! -f metrics_precision.json ]; then
  echo "[queue] precision incomplete, resuming from checkpoint" >&2
  $PY run_precision.py >> /tmp/prec.log 2>&1
fi

if [ -f metrics_precision.json ]; then
  echo "[queue] precision done, starting motion2" >&2
  $PY run_motion2.py > /tmp/motion2.log 2>&1
else
  echo "[queue] precision still has no metrics file, not starting motion2" >&2
  exit 1
fi

echo "[queue] all queued studies finished" >&2
