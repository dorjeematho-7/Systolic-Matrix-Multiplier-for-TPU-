"""cocotb tests for rtl/skew_reg.sv: output equals input delayed by exactly DEPTH cycles."""
from collections import deque

import cocotb
from cocotb.triggers import FallingEdge, ReadOnly

from common import make_rng, param, start_and_reset

DW = param("DW", 8)
DEPTH = param("DEPTH", 1)


async def stream(dut, rng, cycles):
    """Drive random data/valid and check every output against a delay-line model."""
    pipe = deque([(0, 0)] * DEPTH)  # register contents after reset
    for n in range(cycles):
        await FallingEdge(dut.clk)
        d, v = rng.getrandbits(DW), rng.getrandbits(1)
        dut.d_in.value = d
        dut.v_in.value = v
        pipe.append((d, v))
        exp_d, exp_v = pipe.popleft()
        await ReadOnly()
        got = (int(dut.d_out.value), int(dut.v_out.value))
        assert got == (exp_d, exp_v), f"DEPTH={DEPTH} cycle {n}: out={got}, expected {(exp_d, exp_v)}"


@cocotb.test()
async def test_delay(dut):
    dut.d_in.value = 0
    dut.v_in.value = 0
    await start_and_reset(dut)
    await stream(dut, make_rng(dut), 2000)


@cocotb.test()
async def test_reset_mid_stream(dut):
    """Async reset empties the delay line; nothing from before reset comes out after."""
    dut.d_in.value = 0
    dut.v_in.value = 0
    await start_and_reset(dut)
    rng = make_rng(dut)
    await stream(dut, rng, 50)

    await FallingEdge(dut.clk)
    dut.d_in.value = 0
    dut.v_in.value = 0
    dut.rst_n.value = 0
    await ReadOnly()
    if DEPTH > 0:
        assert int(dut.v_out.value) == 0 and int(dut.d_out.value) == 0, "outputs not cleared by reset"
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await stream(dut, rng, 50)
