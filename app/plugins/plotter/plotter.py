from collections import deque
from typing import Callable
import time


class SignalPlotBuffer:
    def __init__(self, maxlen=10000):
        self.t = deque(maxlen=maxlen)
        self.v = deque(maxlen=maxlen)

    def append(self, value):
        self.t.append(time.time())
        self.v.append(value)


def make_plot_handler(plot_buffer: SignalPlotBuffer, signal_name: str) -> Callable:
    def handler(ctx):
        decoded = ctx.decoded or {}
        if signal_name in decoded:
            plot_buffer.append(decoded[signal_name])
    return handler
