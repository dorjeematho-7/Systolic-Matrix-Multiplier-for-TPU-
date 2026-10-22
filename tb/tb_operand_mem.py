"""cocotb tests for rtl/operand_mem.sv: synchronous write port, combinational K:1 read mux."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge

from common import make_rng, param

DW = param("DW", 8)
K = param("K", 2)


async def setup(dut):
    dut.we.value = 0
    dut.waddr.value = 0
    dut.wdata.value = 0
    dut.sel.value = 0
    # operand_mem has no reset port, so only start the clock.
    Clock(dut.clk, 10, unit="ns").start()
    await FallingEdge(dut.clk)


async def write(dut, addr, data):
    await FallingEdge(dut.clk)
    dut.we.value = 1
    dut.waddr.value = addr
    dut.wdata.value = data
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.we.value = 0


async def read(dut, sel):
    dut.sel.value = sel
    await ReadOnly()
    return int(dut.rdata.value)


@cocotb.test()
async def test_write_then_read(dut):
    rng = make_rng(dut)
    await setup(dut)
    mem = [rng.getrandbits(DW) for _ in range(K)]
    for addr, data in enumerate(mem):
        await write(dut, addr, data)
    for sel in range(K):
        await FallingEdge(dut.clk)
        got = await read(dut, sel)
        assert got == mem[sel], f"entry {sel}: read {got:#x}, expected {mem[sel]:#x}"


@cocotb.test()
async def test_no_write_without_we(dut):
    rng = make_rng(dut)
    await setup(dut)
    mem = [rng.getrandbits(DW) for _ in range(K)]
    for addr, data in enumerate(mem):
        await write(dut, addr, data)
    for addr in range(K):
        await FallingEdge(dut.clk)
        dut.we.value = 0
        dut.waddr.value = addr
        dut.wdata.value = ~mem[addr] & ((1 << DW) - 1)
    for sel in range(K):
        await FallingEdge(dut.clk)
        got = await read(dut, sel)
        assert got == mem[sel], f"entry {sel} changed with we=0"


@cocotb.test()
async def test_random_rw(dut):
    """Random writes and reads every cycle. The read is combinational, so a
    write on this cycle only shows up on the next one."""
    rng = make_rng(dut)
    await setup(dut)
    mem = [rng.getrandbits(DW) for _ in range(K)]
    for addr, data in enumerate(mem):
        await write(dut, addr, data)
    for n in range(2000):
        await FallingEdge(dut.clk)
        we = rng.getrandbits(1)
        addr = rng.randrange(K)
        data = rng.getrandbits(DW)
        dut.we.value = we
        dut.waddr.value = addr
        dut.wdata.value = data
        sel = rng.randrange(K)
        got = await read(dut, sel)
        assert got == mem[sel], f"cycle {n}: sel={sel} read {got:#x}, expected {mem[sel]:#x}"
        if we:
            mem[addr] = data
