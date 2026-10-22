"""pytest entry point: builds each RTL block with Verilator and runs its cocotb tests.

    scripts/run_tests.sh                      # whole regression
    scripts/run_tests.sh -k systolic_top      # one block
    SEED=7 NRAND=5000 scripts/run_tests.sh    # other seed, more random products
    WAVES=1 scripts/run_tests.sh -k pe        # dump FST waveforms into sim_build/
"""
import os
import sys
from pathlib import Path

import pytest
from cocotb_tools.runner import get_runner

ROOT = Path(__file__).resolve().parent.parent
RTL = ROOT / "rtl"
TB = ROOT / "tb"
BUILD = ROOT / "sim_build"

sys.path.insert(0, str(TB))  # the runner passes sys.path on, so tests can import common/model

# Files each top-level needs, dependencies first.
SOURCES = {
    "pe": ["pe.sv"],
    "skew_reg": ["skew_reg.sv"],
    "operand_mem": ["operand_mem.sv"],
    "controller": ["controller.sv"],
    "systolic_array": ["pe.sv", "systolic_array.sv"],
    "systolic_top": ["pe.sv", "skew_reg.sv", "operand_mem.sv", "controller.sv",
                     "systolic_array.sv", "systolic_top.sv"],
}

# (top-level, HDL parameters, extra test-only settings)
CONFIGS = [
    ("pe", {"DW": 8, "AW": 20}, {}),
    *[("skew_reg", {"DW": 8, "DEPTH": d}, {}) for d in (0, 1, 2, 5)],
    *[("operand_mem", {"DW": 8, "K": k}, {}) for k in (1, 2, 3, 8)],
    *[("controller", {"N": n, "K": k}, {}) for n, k in ((3, 1), (3, 2), (3, 3), (3, 8), (1, 1), (4, 2))],
    *[("systolic_array", {"N": n, "DW": 8, "AW": 19}, {"K": k}) for n, k in ((3, 2), (3, 5), (4, 3))],
    *[("systolic_top", {"N": 3, "K": k, "DW": 8}, {}) for k in (1, 2, 3, 8)],
    ("systolic_top", {"N": 4, "K": 4, "DW": 8}, {}),
]

VERILATOR_ARGS = ["--x-assign", "unique", "--x-initial", "unique"]
WAVES = os.environ.get("WAVES") == "1"


def config_id(cfg):
    top, params, extra = cfg
    return top + "-" + "-".join(f"{k}{v}" for k, v in {**params, **extra}.items())


@pytest.mark.parametrize("cfg", CONFIGS, ids=[config_id(c) for c in CONFIGS])
def test_rtl(cfg):
    top, params, extra = cfg
    build_dir = BUILD / config_id(cfg)
    env = {k: str(v) for k, v in {**params, **extra}.items()}
    for knob in ("SEED", "NRAND"):
        if knob in os.environ:
            env[knob] = os.environ[knob]

    runner = get_runner("verilator")
    runner.build(
        sources=[RTL / f for f in SOURCES[top]],
        hdl_toplevel=top,
        parameters=params,
        build_dir=build_dir,
        build_args=VERILATOR_ARGS,
        waves=WAVES,
        always=True,
    )
    runner.test(
        hdl_toplevel=top,
        test_module=f"tb_{top}",
        test_dir=TB,
        build_dir=build_dir,
        extra_env=env,
        waves=WAVES,
    )
