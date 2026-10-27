#!/usr/bin/env python3
"""Supply & Demand zone detector (RBR / DBR = demand, RBD / DBD = supply). Deterministic.

usage: snd.py BARS.json [--label H4] [--last N]
BARS.json is the TradingView get_ohlcv result (columns or rows). Prints JSON: zones with
pattern, proximal/distal, status (fresh / tested / broken), departure strength and a score.

A zone is a base (1..MAX_BASE candles, each <= 50% of the leg-out range) left by an impulse candle.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "btc"))
from btc import atr, load  # noqa: E402

BASE_VS_LEGOUT = 0.5   # base candle range <= 50% of the leg-out candle's range
MAX_BASE = 5
IMPULSE_ATR = 1.5      # leg-out range >= 1.5 ATR
IMPULSE_BODY_FRAC = 0.6


def analyze(bars):
    n = len(bars)
    a = atr(bars)
    o = [b["o"] for b in bars]
    h = [b["h"] for b in bars]
    l = [b["l"] for b in bars]
    c = [b["c"] for b in bars]
    rng = [max(h[i] - l[i], 1e-9) for i in range(n)]
    body = [abs(c[i] - o[i]) for i in range(n)]
    is_imp = [rng[i] >= IMPULSE_ATR * a[i] and body[i] >= IMPULSE_BODY_FRAC * rng[i] for i in range(n)]
    up = [c[i] > o[i] for i in range(n)]

    zones = []
    for out in range(2, n):  # for each impulse, walk back over the base it left
        if not is_imp[out]:
            continue
        i = out - 1
        while i > 0 and out - i < MAX_BASE and rng[i] <= BASE_VS_LEGOUT * rng[out] and not is_imp[i]:
            i -= 1
        i += 1
        if i > out - 1 or i == 0:
            continue
        j, leg_in = out - 1, i - 1
        pat = ("R" if up[leg_in] else "D") + "B" + ("R" if up[out] else "D")
        demand = up[out]
        top, bot = max(h[i:j + 1]), min(l[i:j + 1])
        zones.append(dict(type="demand" if demand else "supply", pattern=pat, proximal=top if demand else bot,
                          distal=bot if demand else top, top=top, bottom=bot, base_len=j - i + 1,
                          i=i, t=bars[i]["t"], legout_i=out, departure_atr=round(rng[out] / a[out], 2),
                          entry=top if demand else bot, sl=bot if demand else top))

    last = c[-1]
    for z in zones:  # status from the bars after the leg-out
        after = range(z["legout_i"] + 1, n)
        d = z["type"] == "demand"
        broken = any((c[x] < z["bottom"]) if d else (c[x] > z["top"]) for x in after)
        touched = any((l[x] <= z["top"]) if d else (h[x] >= z["bottom"]) for x in after)
        z["status"] = "broken" if broken else ("tested" if touched else "fresh")
        z["price_vs_zone"] = "inside" if z["bottom"] <= last <= z["top"] else ("above" if last > z["top"] else "below")
        z["dist"] = round(0 if z["price_vs_zone"] == "inside" else min(abs(last - z["top"]), abs(last - z["bottom"])), 3)
        # score: strong departure, short base, untouched. 0..10, for ranking only.
        z["score"] = round(min(z["departure_atr"], 4) * 1.5 + (MAX_BASE - z["base_len"]) * 0.4 + {"fresh": 2, "tested": 0.5, "broken": -10}[z["status"]], 1)

    live = [z for z in zones if z["status"] != "broken"]
    return dict(bars=n, last_close=last, atr=round(a[-1], 3),
                demand=sorted([z for z in live if z["type"] == "demand"], key=lambda z: -z["score"]),
                supply=sorted([z for z in live if z["type"] == "supply"], key=lambda z: -z["score"]),
                broken=len(zones) - len(live))


def selfcheck():
    # a wide down candle, 2 base candles (each < 50% of the leg-out range), then an impulse up: DBR demand 9.8..10.4
    oh = [(10, 10.6, 9.6, 10.2), (10.2, 10.8, 9.7, 10.1), (10.1, 10.6, 9.5, 10.0), (10.0, 10.7, 9.6, 10.3),
          (10.3, 10.5, 8.9, 9.1), (9.8, 10.3, 9.8, 10.0), (10.0, 10.4, 9.9, 10.1),
          (10.0, 12.5, 9.9, 12.4), (12.4, 12.9, 12.0, 12.6), (12.6, 13.0, 12.2, 12.8)]
    bars = [dict(t=i, o=o, h=h, l=l, c=c) for i, (o, h, l, c) in enumerate(oh)]
    r = analyze(bars)
    assert len(r["demand"]) == 1 and not r["supply"], r
    z = r["demand"][0]
    assert z["pattern"] == "DBR" and z["base_len"] == 2 and z["top"] == 10.4 and z["bottom"] == 9.8 and z["status"] == "fresh", z
    print("selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selfcheck":
        selfcheck()
        sys.exit(0)
    args = sys.argv[2:]
    bars = load(sys.argv[1])
    if "--last" in args:
        bars = bars[-int(args[args.index("--last") + 1]):]
    out = analyze(bars)
    out["label"] = args[args.index("--label") + 1] if "--label" in args else ""
    print(json.dumps(out, indent=1))
