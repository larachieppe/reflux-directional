#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "=== [1/2] electrode-count sweep ==="
.venv/bin/python -u run_directional.py
echo "=== [2/2] locked-design study ==="
.venv/bin/python -u run_design.py
echo "=== BOTH COMPLETE ==="
