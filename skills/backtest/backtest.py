#!/usr/bin/env python3
"""Walk-forward replay of the detectors: does a method have an edge on this instrument, and with which settings?

usage: backtest.py BARS.json [--method bpb|qm|snd|btc|all] [--swing K] [--rr 2] [--spread 0.3] [--window 300] [--bias]
BARS.json is a long TradingView get_ohlcv result (3000+ bars). At every bar the detector sees only the
bars that had closed by then. Entries: bpb = the resume close; qm = limit at the QML; snd / btc = limit at
the proximal edge of a zone that was fresh the bar before. Stop from the detector, target at --rr times the risk.
--bias takes only trades in the direction of the same timeframe's last MSB.

What this is not: the full SOP. One timeframe only, so no D1 bias and no M15 confirmation; no news or
session filter; every signal is taken, overlapping or not. It measures the raw zones, which is the floor
the confirmation rules have to improve on. A bar that touches both stop and target counts as a loss.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("btc", "snd", "bpb", "qm"):
    sys.path.insert(0, os.path.join(HERE, "..", d))
import bpb  # noqa: E402
import btc  # noqa: E402
import qm  # noqa: E402
import snd  # noqa: E402


def outcome(bars, k, long, entry, sl, tp, limit):
    """R result of a trade opened on bar k, or None if still open at the end of the data."""
    risk = abs(entry - sl)
    for x in range(k if limit else k + 1, len(bars)):
        b = bars[x]
        if (b["l"] <= sl) if long else (b["h"] >= sl):
            return -1.0
        if x > k and ((b["h"] >= tp) if long else (b["l"] <= tp)):  # a limit fill and the target in the same bar cannot be ordered: not counted
            return abs(tp - entry) / risk
    return None


def signals(method, win, nxt, swing):
    """Orders the detector state `win` (closed bars) puts on the next bar `nxt`: (key, long, entry, sl, limit)."""
    out = []
    if method == "bpb":  # needs nxt inside the window: the trigger is its close
        for s in bpb.analyze(win + [nxt], swing=swing)["setups"]:
            if s["status"] == "resumed" and s["trigger_age"] == 0:
                out.append((("bpb", s["t"]), s["dir"] == "long", s["entry"], s["sl"], False))
    elif method == "qm":
        for s in qm.analyze(win, swing=swing)["setups"]:
            if s["status"] == "waiting" and ((nxt["h"] >= s["qml"]) if s["dir"] == "short" else (nxt["l"] <= s["qml"])):
                out.append((("qm", s["t"], s["qml"]), s["dir"] == "long", s["entry"], s["sl"], True))
    elif method == "snd":
        r = snd.analyze(win)
        for z in r["demand"] + r["supply"]:
            d = z["type"] == "demand"
            if z["status"] == "fresh" and ((nxt["l"] <= z["top"]) if d else (nxt["h"] >= z["bottom"])):
                out.append((("snd", z["t"], z["top"]), d, z["entry"], z["sl"], True))
    elif method == "btc":
        for p in btc.analyze(win, swing=swing)["pois"]:
            d = p["dir"] == "bull"
            if p["fresh"] and p["type"] != "FVG" and ((nxt["l"] <= p["top"]) if d else (nxt["h"] >= p["bottom"])):
                out.append((("btc", p["type"], p["t"]), d, p["entry"], p["sl"], True))
    return out


def run(bars, method, swing=btc.SWING, rr=2.0, spread=0.0, window=300, bias=False):
    seen, res = set(), []
    for k in range(window, len(bars)):
        win = bars[k - window:k]
        sig = signals(method, win, bars[k], swing)
        if not sig:
            continue
        b = btc.analyze(win, swing=swing)["bias"] if bias else None
        for key, long, entry, sl, limit in sig:
            if key in seen or (bias and b != ("up" if long else "down")):
                continue
            if limit and ((bars[k]["o"] < entry) if long else (bars[k]["o"] > entry)):
                continue  # the bar opened beyond the limit price: a gap, no clean fill at the level
            seen.add(key)
            risk = abs(entry - sl)
            if risk <= 0:
                continue
            r = outcome(bars, k, long, entry, sl, entry + rr * risk if long else entry - rr * risk, limit)
            if r is not None:
                res.append((r * risk - spread) / risk if r > 0 else -(risk + spread) / risk)
    return stats(res, rr)


def stats(res, rr):
    if not res:
        return dict(trades=0)
    eq = peak = dd = 0.0
    for r in res:
        eq += r
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    wins = sum(r > 0 for r in res)
    return dict(trades=len(res), win_rate=round(100 * wins / len(res), 1), breakeven_win_rate=round(100 / (1 + rr), 1),
                expectancy_r=round(sum(res) / len(res), 3), total_r=round(sum(res), 1), max_drawdown_r=round(dd, 1))


def selfcheck():
    mk = lambda rows: [dict(t=i, o=o, h=h, l=l, c=c) for i, (o, h, l, c) in enumerate(rows)]  # noqa: E731
    bars = mk([(10, 10.5, 9.5, 10), (10, 10.4, 9.8, 10.2), (10.2, 12.5, 10.1, 12.4), (12.4, 12.6, 8, 9)])
    assert outcome(bars, 0, True, 10, 9, 12, False) == 2.0       # market long from bar 0: target 12 hit on bar 2
    assert outcome(bars, 0, False, 10, 11, 8, False) == -1.0     # short: stop 11 hit on bar 2 before the target
    assert outcome(bars, 3, True, 12, 11, 14, True) == -1.0      # limit filled on bar 3, same bar takes the stop
    assert outcome(bars, 1, True, 10, 7, 30, True) is None       # never resolved
    assert outcome(mk([(10, 10, 10, 10), (10, 12.5, 8.5, 11)]), 0, True, 10, 9, 12, False) == -1.0  # both in one bar = loss
    s = stats([2, -1, -1, 2, -1], 2)
    assert s["trades"] == 5 and s["win_rate"] == 40 and s["expectancy_r"] == 0.2 and s["max_drawdown_r"] == 2 and s["breakeven_win_rate"] == 33.3, s
    # smoke: every method replays a random walk without error and never reports more wins than trades
    import random
    random.seed(7)
    px, rows = 100.0, []
    for _ in range(260):
        o = px
        c = o + random.uniform(-2, 2)
        rows.append((o, max(o, c) + random.random(), min(o, c) - random.random(), c))
        px = c
    for m in ("bpb", "qm", "snd", "btc"):
        r = run(mk(rows), m, swing=1, window=100, spread=0.05)
        assert r["trades"] == 0 or 0 <= r["win_rate"] <= 100, (m, r)
    print("selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selfcheck":
        selfcheck()
        sys.exit(0)
    a = sys.argv[2:]
    opt = lambda k, d, f=float: f(a[a.index(k) + 1]) if k in a else d  # noqa: E731
    bars = btc.load(sys.argv[1])
    m = opt("--method", "all", str)
    kw = dict(swing=opt("--swing", btc.SWING, int), rr=opt("--rr", 2.0), spread=opt("--spread", 0.0), window=opt("--window", 300, int), bias="--bias" in a)
    print(json.dumps(dict(bars=len(bars), settings=kw, results={x: run(bars, x, **kw) for x in (["bpb", "qm", "snd", "btc"] if m == "all" else [m])}), indent=1))
