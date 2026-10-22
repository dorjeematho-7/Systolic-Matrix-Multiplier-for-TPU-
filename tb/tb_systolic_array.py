"""cocotb tests for rtl/systolic_array.sv.

The test plays the role of the memories, muxes and skew registers: row i
gets A[i][k] at cycle k + i on the west edge, and column j gets B[k][j] at
cycle k + j on the north edge. Each PE(i,j) should end with C[i][j].
"""
import cocotb
from cocotb.triggers import FallingEdge, ReadOnly

from common import make_rng, param, start_and_reset
from model import const_matrix, matmul, rand_matrix, smax, smin, to_unsigned

N = param("N", 3)
DW = param("DW", 8)
AW = param("AW", 18)
K = param("K", 2)  # stream length; not an RTL parameter of the array


class ArrayDriver:
    def __init__(self, dut, rng):
        self.dut = dut
        self.rng = rng

    def idle(self, garbage=False):
        for i in range(N):
            self.dut.a_west[i].value = self.rng.getrandbits(DW) if garbage else 0
            self.dut.a_west_v[i].value = 0
            self.dut.b_north[i].value = self.rng.getrandbits(DW) if garbage else 0
            self.dut.b_north_v[i].value = 0

    async def clear(self):
        """One cycle of clear with idle inputs. Returns at a falling edge with clear low."""
        await FallingEdge(self.dut.clk)
        self.idle()
        self.dut.clear.value = 1
        await FallingEdge(self.dut.clk)
        self.dut.clear.value = 0

    async def stream(self, a, b, garbage=False):
        """Feed one skewed product. With garbage=True, invalid slots carry random
        data instead of zeros, so the valid gating in the PEs gets exercised."""
        for t in range(K + 2 * N - 2):
            await FallingEdge(self.dut.clk)
            self.idle(garbage)
            for lane in range(N):
                k = t - lane
                if 0 <= k < K:
                    self.dut.a_west[lane].value = to_unsigned(a[lane][k], DW)
                    self.dut.a_west_v[lane].value = 1
                    self.dut.b_north[lane].value = to_unsigned(b[k][lane], DW)
                    self.dut.b_north_v[lane].value = 1
        await FallingEdge(self.dut.clk)
        self.idle(garbage)

    async def check(self, expected, name):
        await ReadOnly()
        for i in range(N):
            for j in range(N):
                got = self.dut.acc[i][j].value.to_signed()
                assert got == expected[i][j], f"[{name}] acc[{i}][{j}]={got}, expected {expected[i][j]}"

    async def run(self, a, b, name, garbage=False):
        await self.clear()
        await self.stream(a, b, garbage)
        await self.check(matmul(a, b), name)


async def setup(dut):
    rng = make_rng(dut)
    drv = ArrayDriver(dut, rng)
    dut.clear.value = 0
    drv.idle()
    await start_and_reset(dut)
    return drv


@cocotb.test()
async def test_directed(dut):
    drv = await setup(dut)
    lo, hi = smin(DW), smax(DW)
    await drv.run(const_matrix(N, K, 0), const_matrix(K, N, 0), "zeros")
    await drv.run(const_matrix(N, K, lo), const_matrix(K, N, lo), "min*min")
    await drv.run(const_matrix(N, K, hi), const_matrix(K, N, lo), "max*min")
    distinct_a = [[10 * (i + 1) + k for k in range(K)] for i in range(N)]
    distinct_b = [[-(10 * (j + 1) + k) for j in range(N)] for k in range(K)]
    await drv.run(distinct_a, distinct_b, "distinct")


@cocotb.test()
async def test_random(dut):
    drv = await setup(dut)
    for t in range(200):
        await drv.run(rand_matrix(drv.rng, N, K, DW), rand_matrix(drv.rng, K, N, DW), f"rand_{t}")


@cocotb.test()
async def test_garbage_when_invalid(dut):
    """Nonzero data with valid low must not reach any accumulator."""
    drv = await setup(dut)
    for t in range(100):
        await drv.run(rand_matrix(drv.rng, N, K, DW), rand_matrix(drv.rng, K, N, DW), f"garbage_{t}",
                      garbage=True)


@cocotb.test()
async def test_clear(dut):
    """Without clear, a second product adds onto the first. clear zeroes every PE."""
    drv = await setup(dut)
    a1, b1 = rand_matrix(drv.rng, N, K, DW), rand_matrix(drv.rng, K, N, DW)
    a2, b2 = rand_matrix(drv.rng, N, K, DW), rand_matrix(drv.rng, K, N, DW)
    await drv.run(a1, b1, "first")
    await drv.stream(a2, b2)
    c1, c2 = matmul(a1, b1), matmul(a2, b2)
    await drv.check([[c1[i][j] + c2[i][j] for j in range(N)] for i in range(N)], "accumulate")
    await drv.clear()
    await drv.check(const_matrix(N, N, 0), "cleared")


@cocotb.test()
async def test_reset(dut):
    """Async reset zeroes every accumulator."""
    drv = await setup(dut)
    await drv.run(rand_matrix(drv.rng, N, K, DW), rand_matrix(drv.rng, K, N, DW), "before_reset")
    await FallingEdge(dut.clk)
    dut.rst_n.value = 0
    await drv.check(const_matrix(N, N, 0), "reset")
