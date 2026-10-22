#!/usr/bin/env bash
# Run the cocotb + Verilator regression. Run inside WSL; arguments go to pytest.
#   scripts/run_tests.sh                   # everything
#   scripts/run_tests.sh -k controller     # one block
set -euo pipefail
cd "$(dirname "$0")/.."
source "${VENV:-$HOME/.venvs/systolic}/bin/activate"
exec python -m pytest tb/test_runner.py -v "$@"
