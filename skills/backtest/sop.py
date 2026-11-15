#!/usr/bin/env python3
"""Walk-forward replay of the full SOP in TRADING.example.md: D1 bias -> H4 zone -> lower-timeframe confirmation.

usage: sop.py --d1 D1.json --h4 H4.json --ltf M15.json [--rr 2] [--spread 0.3] [--swing K]
              [--no-confirm] [--sessions "London,New York"]
Each file is a long TradingView get_ohlcv result. The replay steps through the lower-timeframe bars;
at each one it knows only the D1 / H4 / LTF candles that had closed by then.

Rule 1 btc  fresh H4 POI in D1 bias -> price enters -> LTF liquidity raid + MSB -> limit at the LTF Breaker Zone, stop beyond it
Rule 2 snd  fresh H4 demand / supply in D1 bias -> price enters -> LTF body-close MSB -> enter at that close, stop beyond the zone
Rule 3 bpb  H4 breakout-pullback resumed in D1 bias -> enter at the open after the H4 resume close, stop beyond the pullback extreme
Rule 4 qm   H4 QM in D1 bias -> price returns to the QML -> LTF body-close MSB -> enter at that close, stop beyond the head
Target is --rr times the risk. --no-confirm enters rules 1, 2, 4 at the zone edge on first touch (the same
zones without the LTF step), which is the comparison that shows what the confirmation is worth.

Not modelled: news windows, daily limits, "TP at nearest liquidity" (a fixed RR is used), D1 zones for rule 2,
the "D1 shifting" exception for rule 4. Each zone gets one visit. Rules are scored independently, so the
same move can be counted under two rules.
"""
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("btc", "snd", "bpb", "qm", "taipan", "backtest"):
    sys.path.insert(0, os.path.join(HERE, "..", d))
import bpb  # noqa: E402
import btc  # noqa: E402
import qm  # noqa: E402
import snd  # noqa: E402
from backtest import outcome, stats  # noqa: E402
from now import clock  # noqa: E402

D1_WIN, H4_WIN, LTF_WIN = 120, 200, 150
ARM_BARS = 16    # LTF bars after price last touched the zone during which a confirmation still counts
ORDER_BARS = 32  # LTF bars a rule-1 limit order stays live


def htf_state(h4, bias, swing):
    """Zones and breakout entries the closed H4 bars offer in the D1 bias direction."""
    want, side = ("bull", "long") if bias == "up" else ("bear", "short")
    long = bias == "up"
    zones = [dict(rule="btc", key=("btc", p["type"], p["t"]), long=long, top=p["top"], bottom=p["bottom"], sl=p["sl"])
             for p in btc.analyze(h4, swing=swing)["pois"] if p["fresh"] and p["dir"] == want]
    s = snd.analyze(h4)
    zones += [dict(rule="snd", key=("snd", z["t"], z["top"]), long=long, top=z["top"], bottom=z["bottom"], sl=z["sl"])
              for z in (s["demand"] if long else s["supply"]) if z["status"] == "fresh"]
    zones += [dict(rule="qm", key=("qm", x["t"], x["qml"]), long=long, top=x["qml"], bottom=x["qml"], sl=x["sl"])
              for x in qm.analyze(h4, swing=swing)["setups"] if x["status"] == "waiting" and x["dir"] == side]
    breaks = [dict(key=("bpb", x["t"]), long=long, entry=x["entry"], sl=x["sl"])
              for x in bpb.analyze(h4, swing=swing)["setups"] if x["status"] == "resumed" and x["trigger_age"] == 0 and x["dir"] == side]
    return zones, breaks


def sop(d1, h4, ltf, rr=2.0, spread=0.0, swing=btc.SWING, confirm=True, sessions=None):
    step = min(q["t"] - p["t"] for p, q in zip(ltf, ltf[1:]))
    log, trades = [], []   # log = every decision (for the no-lookahead test); trades = resolved results
    seen, armed, zones, bias, di, hi = set(), {}, [], None, 0, 0

    def take(rule, k, long, entry, sl, limit, t_decided, gap_check=True):
        log.append((t_decided, rule, round(entry, 3), round(sl, 3)))
        risk = (entry - sl) if long else (sl - entry)
        if risk <= 0:
            return
        if limit and gap_check and ((ltf[k]["o"] < entry) if long else (ltf[k]["o"] > entry)):
            return  # opened beyond the limit price: no clean fill at the level
        if sessions and not set(sessions) & set(clock(datetime.fromtimestamp(ltf[k]["t"] + step, timezone.utc))["sessions"]):
            return
        r = outcome(ltf, k, long, entry, sl, entry + rr * risk if long else entry - rr * risk, limit)
        if r is not None:
            trades.append((rule, (r * risk - spread) / risk if r > 0 else -(risk + spread) / risk))

    for k in range(LTF_WIN, len(ltf)):
        b, now = ltf[k], ltf[k]["t"] + step
        nd, nh = di, hi
        # Higher-timeframe bars that had closed when this LTF bar OPENED: orders resting inside the bar may only use those.
        while nd < len(d1) and d1[nd]["t"] + 86400 <= b["t"]:
            nd += 1
        while nh < len(h4) and h4[nh]["t"] + 14400 <= b["t"]:
            nh += 1
        if nd != di and nd >= 20:
            bias = btc.analyze(d1[max(0, nd - D1_WIN):nd], swing=swing)["bias"]
        if (nd != di or nh != hi) and bias and nh >= 50:
            zones, breaks = htf_state(h4[max(0, nh - H4_WIN):nh], bias, swing)
            for x in breaks if nh != hi else []:  # rule 3 fires once, on the H4 close that resumed
                if x["key"] not in seen:
                    seen.add(x["key"])
                    take("bpb", k, x["long"], b["o"], x["sl"], True, b["t"], gap_check=False)  # market order at the first open after the H4 close
        di, hi = nd, nh

        for z in zones:  # first touch arms the zone; each zone gets one visit
            if z["key"] in seen or not ((b["l"] <= z["top"]) if z["long"] else (b["h"] >= z["bottom"])):
                continue
            seen.add(z["key"])
            if not confirm:
                take(z["rule"], k, z["long"], z["top"] if z["long"] else z["bottom"], z["sl"], True, now)
            elif (b["c"] >= z["bottom"]) if z["long"] else (b["c"] <= z["top"]):
                armed[z["key"]] = dict(z, arm_t=b["t"], last=k)
        if not armed:
            continue

        m = btc.analyze(ltf[k - LTF_WIN + 1:k + 1], swing=swing)
        for key, z in list(armed.items()):
            long = z["long"]
            if (b["l"] <= z["top"]) if long else (b["h"] >= z["bottom"]):
                z["last"] = k
            if ((b["c"] < z["bottom"]) if long else (b["c"] > z["top"])) or k - z["last"] > ARM_BARS:
                del armed[key]  # closed through the zone, or wandered off without confirming
                continue
            want = "bull" if long else "bear"
            if z["rule"] == "btc":  # Entry Model: a fresh LTF Breaker Zone built after price entered the H4 POI
                bz = [p for p in m["pois"] if p["type"] == "BZ" and p["dir"] == want and p["fresh"] and p["t"] >= z["arm_t"]]
                if bz:
                    p = bz[-1]
                    fill = next((f for f in range(k + 1, min(k + 1 + ORDER_BARS, len(ltf)))
                                 if ((ltf[f]["l"] <= p["entry"]) if long else (ltf[f]["h"] >= p["entry"]))), None)
                    del armed[key]
                    if fill is not None:
                        take("btc", fill, long, p["entry"], p["sl"], True, now)
                    else:
                        log.append((now, "btc-unfilled", round(p["entry"], 3), round(p["sl"], 3)))
            else:
                lm = m["last_msb"]
                if lm and lm["i"] == LTF_WIN - 1 and lm["dir"] == ("up" if long else "down"):
                    del armed[key]
                    take(z["rule"], k, long, b["c"], z["sl"], False, now)

    out = {r: stats([x for rule, x in trades if rule == r], rr) for r in ("btc", "snd", "bpb", "qm")}
    out["all"] = stats([x for _, x in trades], rr)
    return out, log


def selfcheck():
    import random
    random.seed(3)
    px, m15 = 2000.0, []
    for i in range(96 * 150):  # 150 days of 15-minute bars, with occasional impulses
        o = px
        c = o + random.gauss(0, 1.2) * (5 if random.random() < 0.03 else 1)
        m15.append(dict(t=i * 900, o=o, h=max(o, c) + abs(random.gauss(0, 0.5)), l=min(o, c) - abs(random.gauss(0, 0.5)), c=c))
        px = c

    def agg(n):
        return [dict(t=g[0]["t"], o=g[0]["o"], h=max(x["h"] for x in g), l=min(x["l"] for x in g), c=g[-1]["c"])
                for g in (m15[i:i + n] for i in range(0, len(m15), n))]

    d1, h4 = agg(96), agg(16)
    res, log = sop(d1, h4, m15)
    assert res["all"]["trades"] > 0 and {"btc", "snd", "bpb", "qm"} <= set(res), res
    # no lookahead: cutting the future off must not change any decision already made (rule-1 fills excepted: they look ORDER_BARS ahead by design)
    cut = len(m15) * 2 // 3
    t_cut = m15[cut]["t"] - ORDER_BARS * 900
    _, early = sop([b for b in d1 if b["t"] < m15[cut]["t"]], [b for b in h4 if b["t"] < m15[cut]["t"]], m15[:cut])
    strip = lambda lg: [(t, r.replace("-unfilled", ""), e, s) for t, r, e, s in lg if t <= t_cut]  # noqa: E731
    assert strip(early) == strip(log) and strip(log), (len(strip(early)), len(strip(log)))
    # every decision has its stop on the losing side of the entry or is discarded by take()
    res2, _ = sop(d1, h4, m15, confirm=False, sessions=["London", "New York"])
    assert res2["all"]["trades"] > 0
    print("selfcheck ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "--selfcheck":
        selfcheck()
        sys.exit(0)
    opt = lambda k, d, f=float: f(a[a.index(k) + 1]) if k in a else d  # noqa: E731
    d1, h4, ltf = (btc.load(opt(k, None, str)) for k in ("--d1", "--h4", "--ltf"))
    kw = dict(rr=opt("--rr", 2.0), spread=opt("--spread", 0.0), swing=opt("--swing", btc.SWING, int), confirm="--no-confirm" not in a,
              sessions=[s.strip() for s in opt("--sessions", "", str).split(",") if s.strip()] or None)
    res, _ = sop(d1, h4, ltf, **kw)
    day = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")  # noqa: E731
    print(json.dumps(dict(period=f'{day(ltf[LTF_WIN]["t"])} to {day(ltf[-1]["t"])}', ltf_bars=len(ltf), settings=kw, results=res), indent=1))
