# Minimal gauge value propagation; GUI gauges implemented in Qt elsewhere
class InstrumentBinding:
    def __init__(self, widget, signal_name: str):
        self.widget = widget
        self.signal = signal_name

    def handler(self, ctx):
        val = (ctx.decoded or {}).get(self.signal)
        if val is not None:
            self.widget.set_value(val)
