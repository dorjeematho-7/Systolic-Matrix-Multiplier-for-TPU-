"""cocotb tests for rtl/pe.sv.

Every cycle is checked against a model: the accumulator, and the one-cycle
pass-through of A, B and their valid bits.
"""
import cocotb
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge

from common import make_rng, param, start_and_reset
from model import smax, smin, to_signed, to_unsigned

DW = param("DW", 8)
AW = param("AW", 20)


class PeChecker:
    def __init__(self, dut):
        self.dut = dut
        self.acc = 0
        self.n = 0

    async def cycle(self, clear=0, a=0, av=0, b=0, bv=0):
        """Drive one cycle of inputs, then check the PE right after the clock edge."""
        dut = self.dut
        await FallingEdge(dut.clk)
        dut.clear.value = clear
        dut.a_in.value = to_unsigned(a, DW)
        dut.a_vin.value = av
        dut.b_in.value = to_unsigned(b, DW)
        dut.b_vin.value = bv
        await RisingEdge(dut.clk)
        await ReadOnly()

        if clear:
            self.acc = 0
        elif av and bv:
            self.acc = to_signed(self.acc + to_signed(a, DW) * to_signed(b, DW), AW)
        self.n += 1

        where = f"cycle {self.n} (clear={clear} a={a}/v{av} b={b}/v{bv})"
        got = dut.acc.value.to_signed()
        assert got == self.acc, f"{where}: acc={got}, expected {self.acc}"
        assert dut.a_out.value.to_signed() == to_signed(a, DW), f"{where}: a_out wrong"
        assert dut.b_out.value.to_signed() == to_signed(b, DW), f"{where}: b_out wrong"
        assert int(dut.a_vout.value) == av, f"{where}: a_vout wrong"
        assert int(dut.b_vout.value) == bv, f"{where}: b_vout wrong"


async def setup(dut):
    for sig in (dut.clear, dut.a_in, dut.a_vin, dut.b_in, dut.b_vin):
        sig.value = 0
    await start_and_reset(dut)
    return PeChecker(dut)


@cocotb.test()
async def test_reset_state(dut):
    """Asserting rst_n zeroes the accumulator and every output register."""
    pe = await setup(dut)
    await pe.cycle(a=5, av=1, b=5, bv=1)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 0
    await ReadOnly()
    for name in ("acc", "a_out", "b_out", "a_vout", "b_vout"):
        assert int(getattr(dut, name).value) == 0, f"{name} not cleared by async reset"


@cocotb.test()
async def test_basic_mac(dut):
    pe = await setup(dut)
    await pe.cycle(clear=1)
    await pe.cycle(a=3, av=1, b=4, bv=1)
    await pe.cycle(a=-5, av=1, b=6, bv=1)
    await pe.cycle(a=7, av=1, b=-7, bv=1)
    assert pe.acc == 12 - 30 - 49


@cocotb.test()
async def test_valid_gating(dut):
    """No accumulation unless both operands are valid, even with nonzero data."""
    pe = await setup(dut)
    await pe.cycle(clear=1)
    await pe.cycle(a=100, av=1, b=100, bv=0)
    await pe.cycle(a=100, av=0, b=100, bv=1)
    await pe.cycle(a=100, av=0, b=100, bv=0)
    assert pe.acc == 0


@cocotb.test()
async def test_clear_priority(dut):
    """clear wins over a valid MAC on the same cycle."""
    pe = await setup(dut)
    await pe.cycle(a=9, av=1, b=9, bv=1)
    await pe.cycle(clear=1, a=50, av=1, b=50, bv=1)
    assert pe.acc == 0


@cocotb.test()
async def test_signed_extremes(dut):
    pe = await setup(dut)
    lo, hi = smin(DW), smax(DW)
    for a in (lo, hi, -1, 0, 1):
        for b in (lo, hi, -1, 0, 1):
            await pe.cycle(clear=1)
            await pe.cycle(a=a, av=1, b=b, bv=1)
            assert pe.acc == a * b


@cocotb.test()
async def test_random(dut):
    pe = await setup(dut)
    rng = make_rng(dut)
    for _ in range(3000):
        await pe.cycle(clear=int(rng.random() < 0.02),
                       a=rng.randint(smin(DW), smax(DW)), av=int(rng.random() < 0.75),
                       b=rng.randint(smin(DW), smax(DW)), bv=int(rng.random() < 0.75))
