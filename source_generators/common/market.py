"""Deterministic daily price series per instrument (random walk). Used by trades, positions and valuation
so every source agrees on price. FX conversion uses the real REST API, not this module."""
import math
import random
from .calendar import bdays

VOL = {"EQUITY": 0.016, "BOND": 0.0025, "FX": 0.005, "COMMODITY": 0.015, "DERIVATIVE": 0.04}


class PriceBook:
    def __init__(self, cfg, instruments, last_date):
        self.days = bdays(cfg["history_start"], last_date)
        self.idx = {d: n for n, d in enumerate(self.days)}
        self.series = {}
        for ins in instruments:
            r = random.Random("%s-%s" % (cfg["seed"], ins["sec_code"]))
            px, s = ins["base_price"], []
            for _ in self.days:
                px = max(px * math.exp(r.gauss(0, VOL[ins["sec_type"]])), 0.01)
                s.append(round(px, 4))
            self.series[ins["sec_code"]] = s

    def price(self, sec_code, d):
        s = self.series[sec_code]
        if d in self.idx:
            return s[self.idx[d]]
        return s[0] if d < self.days[0] else s[-1]
