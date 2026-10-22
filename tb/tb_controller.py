"""cocotb tests for rtl/controller.sv.

Two independent checks:
  - every cycle against ControllerModel (tb/model.py)
  - spec-level properties of a recorded trace (busy length, feed window,
    done pulse, clear timing), written straight from the state table
"""
import cocotb
from cocotb.triggers import FallingEdge, ReadOnly

from common import make_rng, param, start_and_reset
from model import ControllerModel

N = param("N", 3)
K = param("K", 2)
LATENCY = K + 2 * N - 2  # COMPUTE cycles


class CtrlChecker:
    def __init__(self, dut):
        self.dut = dut
        self.model = ControllerModel(N, K)
        self.trace = []

    async def cycle(self, start):
        dut = self.dut
        await FallingEdge(dut.clk)
        dut.start.value = start
        await ReadOnly()
        exp = self.model.outputs(start)
        got = {name: int(getattr(dut, name).value) for name in exp}
        n = len(self.trace)
        assert got == exp, f"cycle {n} start={start} state={self.model.state}: got {got}, expected {exp}"
        self.trace.append({"start": start, **got})
        self.model.step(start)


async def setup(dut):
    dut.start.value = 0
    await start_and_reset(dut)
    await ReadOnly()
    for name in ("busy", "done", "clear", "feed_v"):
        assert int(getattr(dut, name).value) == 0, f"{name} high after reset"
    return CtrlChecker(dut)


def check_runs(trace):
    """Spec properties, checked on every run found in the trace."""
    t = 0
    runs = 0
    while t < len(trace):
        if not trace[t]["busy"]:
            t += 1
            continue
        first = t
        assert first > 0 and trace[first - 1]["clear"] == 1, f"cycle {first}: COMPUTE not preceded by clear"
        while t < len(trace) and trace[t]["busy"]:
            t += 1
        if t == len(trace):
            break  # run still in progress at end of trace
        busy = trace[first:t]
        assert len(busy) == LATENCY, f"run at {first}: busy for {len(busy)} cycles, expected {LATENCY}"
        feeds = [c["feed_v"] for c in busy]
        assert feeds == [1] * K + [0] * (LATENCY - K), f"run at {first}: feed_v pattern {feeds}"
        sels = [c["s0"] for c in busy[:K]]
        assert sels == list(range(K)), f"run at {first}: select sequence {sels}"
        assert trace[t]["done"] == 1, f"run at {first}: no done right after COMPUTE"
        runs += 1
    dones = [i for i, c in enumerate(trace) if c["done"]]
    for i in dones:
        assert i + 1 >= len(trace) or not trace[i + 1]["done"], f"cycle {i}: done longer than one cycle"
    return runs


@cocotb.test()
async def test_single_run(dut):
    ctl = await setup(dut)
    await ctl.cycle(1)
    for _ in range(LATENCY + 5):
        await ctl.cycle(0)
    assert check_runs(ctl.trace) == 1


@cocotb.test()
async def test_start_held(dut):
    """start held high: back-to-back runs, one every LATENCY + 2 cycles
    (1 LOAD + LATENCY COMPUTE + 1 OUTPUT)."""
    ctl = await setup(dut)
    for _ in range(4 * (LATENCY + 2) + 1):
        await ctl.cycle(1)
    assert check_runs(ctl.trace) == 4
    dones = [i for i, c in enumerate(ctl.trace) if c["done"]]
    gaps = {b - a for a, b in zip(dones, dones[1:])}
    assert gaps == {LATENCY + 2}, f"done spacing {gaps}"


@cocotb.test()
async def test_start_ignored_outside_load(dut):
    """start held through all of COMPUTE and the OUTPUT cycle, then dropped
    before LOAD, launches exactly one run."""
    ctl = await setup(dut)
    for _ in range(1 + LATENCY + 1):  # accept cycle, COMPUTE, OUTPUT
        await ctl.cycle(1)
    for _ in range(LATENCY + 3):
        await ctl.cycle(0)
    assert check_runs(ctl.trace) == 1, "a start outside LOAD launched an extra run"


@cocotb.test()
async def test_random_start(dut):
    ctl = await setup(dut)
    rng = make_rng(dut)
    for _ in range(3000):
        await ctl.cycle(int(rng.random() < 0.3))
    runs = check_runs(ctl.trace)
    dut._log.info("%d runs checked", runs)
    assert runs > 10
