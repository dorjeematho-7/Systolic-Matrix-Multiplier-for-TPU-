"""Reference models for the cocotb tests.

Plain Python written from the spec, sharing nothing with the RTL, so a
mistake in the hardware can't be copied into the expected values.
"""


def clog2(n):
    return (n - 1).bit_length() if n > 1 else 0


def to_unsigned(v, bits):
    return v & ((1 << bits) - 1)


def to_signed(v, bits):
    v = to_unsigned(v, bits)
    return v - (1 << bits) if v >> (bits - 1) else v


def smin(dw):
    return -(1 << (dw - 1))


def smax(dw):
    return (1 << (dw - 1)) - 1


def rand_matrix(rng, rows, cols, dw):
    return [[rng.randint(smin(dw), smax(dw)) for _ in range(cols)] for _ in range(rows)]


def const_matrix(rows, cols, v):
    return [[v] * cols for _ in range(rows)]


def matmul(a, b):
    inner = len(b)
    return [[sum(a[i][x] * b[x][j] for x in range(inner)) for j in range(len(b[0]))]
            for i in range(len(a))]


class ControllerModel:
    """Cycle model of the LOAD -> COMPUTE -> OUTPUT -> LOAD sequencer.

    outputs() gives the values during the current cycle (clear depends on the
    start input combinationally). step() applies the rising clock edge.
    """

    LOAD, COMPUTE, OUTPUT = "LOAD", "COMPUTE", "OUTPUT"

    def __init__(self, n, k):
        self.k = k
        self.last = k + 2 * (n - 1) - 1
        self.state = self.LOAD
        self.count = 0

    def outputs(self, start):
        busy = self.state == self.COMPUTE
        feed_v = busy and self.count < self.k
        sel = self.count if feed_v else 0
        return {
            "clear": int(self.state == self.LOAD and bool(start)),
            "busy": int(busy),
            "done": int(self.state == self.OUTPUT),
            "feed_v": int(feed_v),
            "s0": sel,
            "s1": sel,
        }

    def step(self, start):
        if self.state == self.LOAD:
            if start:
                self.state = self.COMPUTE
                self.count = 0
        elif self.state == self.COMPUTE:
            if self.count == self.last:
                self.state = self.OUTPUT
            else:
                self.count += 1
        else:
            self.state = self.LOAD
