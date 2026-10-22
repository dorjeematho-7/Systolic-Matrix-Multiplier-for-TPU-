"""cocotb tests for rtl/systolic_top.sv, the full design.

A background monitor checks the protocol on every cycle:
  - busy and done never high together; done is a one-cycle pulse
  - each busy window is exactly LATENCY cycles and is followed by done
  - at the array edge, A and B lanes are valid on the same cycles, and
    carry zeros when not valid ("fed zeros")
The tests check C against a Python matmul, the exact start->done latency,
back-to-back runs, holding C after done, and dropped writes while busy.
"""
import cocotb
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge

from common import make_rng, param, start_and_reset
from model import clog2, const_matrix, matmul, rand_matrix, smax, smin, to_signed, to_unsigned

N = param("N", 3)
K = param("K", 2)
DW = param("DW", 8)
NRAND = param("NRAND", 1000)
AW = 2 * DW + clog2(K)
LATENCY = K + 2 * N - 2  # clock edges from start accepted to done


class Top:
    def __init__(self, dut):
        self.dut = dut
        self.rng = make_rng(dut)
        self.a = const_matrix(N, K, 0)
        self.b = const_matrix(K, N, 0)
        self.runs = 0

    async def init(self):
        dut = self.dut
        for sig in (dut.a_we, dut.a_bank, dut.a_addr, dut.a_wdata,
                    dut.b_we, dut.b_bank, dut.b_addr, dut.b_wdata, dut.start):
            sig.value = 0
        await start_and_reset(dut)
        await ReadOnly()
        assert int(dut.busy.value) == 0 and int(dut.done.value) == 0, "busy/done high after reset"
        cocotb.start_soon(self.monitor())

    async def monitor(self):
        dut = self.dut
        prev_done = 0
        busy_len = 0
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            busy, done = int(dut.busy.value), int(dut.done.value)
            assert not (busy and done), "busy and done high together"
            assert not (prev_done and done), "done high for more than one cycle"
            if busy:
                busy_len += 1
            elif busy_len:
                assert busy_len == LATENCY, f"busy for {busy_len} cycles, expected {LATENCY}"
                assert done, "COMPUTE ended without done"
                busy_len = 0
            for lane in range(N):
                av, bv = int(dut.a_west_v[lane].value), int(dut.b_north_v[lane].value)
                assert av == bv, f"lane {lane}: A valid {av} != B valid {bv} at the array edge"
                if not av:
                    assert int(dut.a_west[lane].value) == 0, f"lane {lane}: A not zero while invalid"
                    assert int(dut.b_north[lane].value) == 0, f"lane {lane}: B not zero while invalid"
            prev_done = done

    def set(self, a, b):
        self.a, self.b = a, b

    def fill(self, av, bv):
        self.set(const_matrix(N, K, av), const_matrix(K, N, bv))

    def fill_rand(self):
        self.set(rand_matrix(self.rng, N, K, DW), rand_matrix(self.rng, K, N, DW))

    async def load(self):
        """Write A row i into A bank i and B column j into B bank j, entry k."""
        dut = self.dut
        for lane in range(N):
            for k in range(K):
                await FallingEdge(dut.clk)
                dut.a_we.value = 1
                dut.a_bank.value = lane
                dut.a_addr.value = k
                dut.a_wdata.value = to_unsigned(self.a[lane][k], DW)
                dut.b_we.value = 1
                dut.b_bank.value = lane
                dut.b_addr.value = k
                dut.b_wdata.value = to_unsigned(self.b[k][lane], DW)
        await FallingEdge(dut.clk)
        dut.a_we.value = 0
        dut.b_we.value = 0

    async def start_op(self):
        """Hold start until the controller accepts it (busy rises after the edge).
        Returns in the ReadOnly phase just after the accepting edge."""
        dut = self.dut
        await FallingEdge(dut.clk)
        dut.start.value = 1
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            if int(dut.busy.value):
                break
        await FallingEdge(dut.clk)
        dut.start.value = 0
        await ReadOnly()

    def read_c(self):
        flat = self.dut.c_flat.value.to_unsigned()
        return [[to_signed(flat >> ((i * N + j) * AW), AW) for j in range(N)] for i in range(N)]

    def check(self, name):
        expected = matmul(self.a, self.b)
        got = self.read_c()
        bad = [(i, j) for i in range(N) for j in range(N) if got[i][j] != expected[i][j]]
        assert not bad, (f"[{name}] {len(bad)} wrong entries, first C[{bad[0][0]}][{bad[0][1]}]="
                         f"{got[bad[0][0]][bad[0][1]]} expected {expected[bad[0][0]][bad[0][1]]}\n"
                         f"A={self.a}\nB={self.b}")
        self.runs += 1

    async def wait_done(self, limit):
        cycles = 0
        while not int(self.dut.done.value):
            await RisingEdge(self.dut.clk)
            await ReadOnly()
            cycles += 1
            assert cycles <= limit, f"no done within {limit} cycles"
        return cycles

    async def run(self, name):
        """Start, wait for done, check the exact latency and the result."""
        await self.start_op()
        # Counts edges after the accepting one, so done lands on edge LATENCY.
        cycles = await self.wait_done(LATENCY + 10)
        assert cycles == LATENCY, f"[{name}] latency {cycles} cycles, expected {LATENCY}"
        self.check(name)


async def setup(dut):
    top = Top(dut)
    await top.init()
    return top


@cocotb.test()
async def test_directed(dut):
    top = await setup(dut)
    lo, hi = smin(DW), smax(DW)
    cases = [("zeros", 0, 0), ("max*max", hi, hi), ("min*min", lo, lo),
             ("max*min", hi, lo), ("neg_ones", -1, -1)]
    for name, av, bv in cases:
        top.fill(av, bv)
        await top.load()
        await top.run(name)

    top.set([[int(i == k) for k in range(K)] for i in range(N)],
            [[int(k == j) for j in range(N)] for k in range(K)])
    await top.load()
    await top.run("identity")

    top.set([[lo if (i + k) % 2 else hi for k in range(K)] for i in range(N)],
            [[hi if (k + j) % 2 else lo for j in range(N)] for k in range(K)])
    await top.load()
    await top.run("checker")

    # Distinct values: a swapped lane or wrong k shows up as a wrong entry
    top.set([[10 * (i + 1) + k for k in range(K)] for i in range(N)],
            [[-(10 * (j + 1) + k) for j in range(N)] for k in range(K)])
    await top.load()
    await top.run("distinct")


@cocotb.test()
async def test_onehot(dut):
    """A single 1 in A (B random), then a single 1 in B (A random), at every
    position. Catches transposed or misrouted lanes and select errors."""
    top = await setup(dut)
    for i in range(N):
        for k in range(K):
            top.fill_rand()
            top.a = const_matrix(N, K, 0)
            top.a[i][k] = 1
            await top.load()
            await top.run(f"onehotA_{i}_{k}")

            top.fill_rand()
            top.b = const_matrix(K, N, 0)
            top.b[k][i] = 1
            await top.load()
            await top.run(f"onehotB_{k}_{i}")


@cocotb.test()
async def test_random(dut):
    top = await setup(dut)
    for t in range(NRAND):
        top.fill_rand()
        await top.load()
        await top.run(f"rand_{t}")
    dut._log.info("%d random products checked", NRAND)


@cocotb.test()
async def test_back_to_back_and_hold(dut):
    """Rerun without reloading: the result must repeat, so clear works and
    nothing leaks between runs. C must also hold in LOAD after done."""
    top = await setup(dut)
    top.fill_rand()
    await top.load()
    for r in range(5):
        await top.run(f"b2b_{r}")
    for _ in range(10):
        await RisingEdge(dut.clk)
    await ReadOnly()
    top.check("hold_after_done")


@cocotb.test()
async def test_start_held(dut):
    """start held high: LOAD -> COMPUTE -> OUTPUT -> LOAD -> ... one run every
    LATENCY + 2 cycles, each producing the same C."""
    top = await setup(dut)
    top.fill_rand()
    await top.load()
    dut.start.value = 1
    done_at = []
    cycle = 0
    while len(done_at) < 3:
        await RisingEdge(dut.clk)
        await ReadOnly()
        cycle += 1
        if int(dut.done.value):
            done_at.append(cycle)
            top.check(f"held_{len(done_at)}")
        assert cycle < 5 * (LATENCY + 2), "start held but runs stopped"
    gaps = {b - a for a, b in zip(done_at, done_at[1:])}
    assert gaps == {LATENCY + 2}, f"done spacing {gaps}, expected {LATENCY + 2}"
    await FallingEdge(dut.clk)
    dut.start.value = 0
    for _ in range(LATENCY + 3):
        await RisingEdge(dut.clk)


@cocotb.test()
async def test_start_ignored_outside_load(dut):
    """A start pulse during COMPUTE or OUTPUT is ignored: no second run."""
    top = await setup(dut)
    top.fill_rand()
    await top.load()
    await top.start_op()
    # Pulse start once mid-COMPUTE, then once in the OUTPUT cycle
    await FallingEdge(dut.clk)
    dut.start.value = 1
    await FallingEdge(dut.clk)
    dut.start.value = 0
    await top.wait_done(LATENCY + 10)
    top.check("pulse_in_compute")
    await FallingEdge(dut.clk)
    dut.start.value = 1
    await FallingEdge(dut.clk)
    dut.start.value = 0
    for _ in range(2 * LATENCY):
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert not int(dut.busy.value), "start outside LOAD launched a run"


@cocotb.test()
async def test_busy_writes_dropped(dut):
    """Overwrite every buffer entry with garbage during COMPUTE. Both this run
    and a rerun must still use the original A and B."""
    top = await setup(dut)
    top.fill_rand()
    await top.load()
    await top.start_op()
    mask = (1 << DW) - 1
    for n in range(N * K):
        await FallingEdge(dut.clk)
        dut.a_we.value = 0
        dut.b_we.value = 0
        if not int(dut.busy.value):
            break
        lane, k = divmod(n, K)
        dut.a_we.value = 1
        dut.a_bank.value = lane
        dut.a_addr.value = k
        dut.a_wdata.value = ~top.a[lane][k] & mask
        dut.b_we.value = 1
        dut.b_bank.value = lane
        dut.b_addr.value = k
        dut.b_wdata.value = ~top.b[k][lane] & mask
    await FallingEdge(dut.clk)
    dut.a_we.value = 0
    dut.b_we.value = 0
    # The loop may end in COMPUTE or in OUTPUT; either way, wait out COMPUTE.
    # The monitor checks that done followed, and C holds afterwards.
    await ReadOnly()
    while int(dut.busy.value):
        await RisingEdge(dut.clk)
        await ReadOnly()
    top.check("busy_writes")
    await top.run("busy_writes_rerun")
