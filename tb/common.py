"""Clock, reset and parameter helpers shared by the cocotb tests."""
import os
import random

from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge


def param(name, default):
    """HDL parameters and test knobs arrive as environment variables from test_runner.py."""
    return int(os.environ.get(name, default))


def make_rng(dut):
    seed = param("SEED", 1)
    dut._log.info("Python RNG seed: SEED=%d", seed)
    return random.Random(seed)


async def start_and_reset(dut, cycles=3):
    """Start a 10 ns clock and hold rst_n low for a few cycles.

    Returns just after a falling edge with reset released. Drive every input
    to a known value before calling this.
    """
    Clock(dut.clk, 10, unit="ns").start()
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, cycles)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
