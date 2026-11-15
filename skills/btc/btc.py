#!/usr/bin/env python3
"""Behind the Candle detector. Deterministic: code finds the structure, Taipan judges it.

usage: btc.py BARS.json [--label H4] [--last N] [--swing K]
BARS.json is the TradingView get_ohlcv result (format=columns or rows). Prints JSON:
structure points, MSBs, bias, and POIs (FVG / Order Block / Breaker Zone) with fresh flag.
Rules from "Behind the Candle" (SureShotFX): wick is never a break, body close is.
"""
import json
import sys
import time

SWING = 1             # bars each side of a Structure High/Low. 1 = the book's 3-candle pattern; test others with backtest.py --swing
SL_BUFFER_ATR = 0.1   # stop goes this far beyond the zone edge / extreme; spread is added by size.py


def load(path, now=None):
    d = json.load(open(path))
    b = d.get("bars", d) if isinstance(d, dict) else d
    if isinstance(b, dict):  # columns
        bars = [dict(t=t, o=o, h=h, l=l, c=c) for t, o, h, l, c in zip(b["t"], b["o"], b["h"], b["l"], b["c"])]
    else:
        bars = [dict(t=x["t"], o=x["o"], h=x["h"], l=x["l"], c=x["c"]) for x in b]
    # The feed's last bar is still forming while the market is open: it has no body close yet, so drop it.
    if len(bars) > 2:
        step = min(q["t"] - p["t"] for p, q in zip(bars, bars[1:]))
        if (now or time.time()) < bars[-1]["t"] + step:
            bars.pop()
    return bars


def swings(h, l, k=SWING):
    """Structure points: the wick is the extreme of k bars on each side. Confirmed at bar i+k."""
    n = len(h)
    sh = [i for i in range(k, n - k) if h[i] > max(h[i - k:i]) and h[i] > max(h[i + 1:i + k + 1])]
    sl = [i for i in range(k, n - k) if l[i] < min(l[i - k:i]) and l[i] < min(l[i + 1:i + k + 1])]
    return sh, sl


def stop(edge, long, atr_now):
    return round(edge - SL_BUFFER_ATR * atr_now if long else edge + SL_BUFFER_ATR * atr_now, 3)


def atr(bars, n=14):
    tr = [b["h"] - b["l"] for b in bars[:1]]
    for p, b in zip(bars, bars[1:]):
        tr.append(max(b["h"] - b["l"], abs(b["h"] - p["c"]), abs(b["l"] - p["c"])))
    return [sum(tr[max(0, i - n + 1):i + 1]) / len(tr[max(0, i - n + 1):i + 1]) for i in range(len(tr))]


def analyze(bars, max_body_atr=2.5, bz_lookback=5, ob_lookback=10, swing=SWING):
    n = len(bars)
    a = atr(bars)
    h = [b["h"] for b in bars]
    l = [b["l"] for b in bars]
    c = [b["c"] for b in bars]
    o = [b["o"] for b in bars]

    sh, sl = swings(h, l, swing)

    msbs, bias = [], None
    broken_sh, broken_sl = set(), set()
    raids, bzs = [], []

    def last_open(points, broken, j):  # most recent confirmed, unbroken point before bar j
        for i in reversed(points):
            if i <= j - swing - 1 and i not in broken:
                return i
        return None

    for j in range(n):
        ref_sh, ref_sl = last_open(sh, broken_sh, j), last_open(sl, broken_sl, j)
        big = (abs(c[j] - o[j]) > max_body_atr * a[j])
        if ref_sh is not None and c[j] > h[ref_sh]:
            msbs.append(dict(i=j, t=bars[j]["t"], dir="up", level=h[ref_sh], kind="reversal" if bias == "down" else "continuation", big_body=big))
            broken_sh.update(i for i in sh if i <= ref_sh)
            bias = "up"
        if ref_sl is not None and c[j] < l[ref_sl]:
            msbs.append(dict(i=j, t=bars[j]["t"], dir="down", level=l[ref_sl], kind="reversal" if bias == "up" else "continuation", big_body=big))
            broken_sl.update(i for i in sl if i <= ref_sl)
            bias = "down"

    # Liquidity raids: wick sweeps SH/SL (no body close) and the opposite MSB lands on the same or next bar.
    # shortcut: body-sweep-then-immediate-reversal exception from the book is not modelled, revisit if it costs setups
    msb_at = {}
    for m in msbs:
        msb_at.setdefault(m["i"], []).append(m)

    def raid(points, side):
        out = []
        for i in points:
            for r in range(i + swing + 1, n):  # first bar after confirmation that sweeps the point
                swept = h[r] > h[i] if side == "high" else l[r] < l[i]
                if not swept:
                    continue
                body_through = c[r] > h[i] if side == "high" else c[r] < l[i]
                if body_through:
                    break  # a real break, not a sweep
                want = "down" if side == "high" else "up"
                hit = [m for k in (r, r + 1) for m in msb_at.get(k, []) if m["dir"] == want]
                if hit and not hit[0]["big_body"]:
                    out.append(dict(point=i, raid=r, msb=hit[0]["i"], dir=want))
                break
        return out

    raids = raid(sh, "high") + raid(sl, "low")

    pois = []
    for rd in raids:  # Breaker Zone: last opposite-colour candle before the raid candle .. raid candle
        r, up = rd["raid"], rd["dir"] == "up"
        k = next((x for x in range(r - 1, max(-1, r - 1 - bz_lookback), -1) if ((c[x] > o[x]) if up else (c[x] < o[x]))), None)  # a doji has no colour
        if k is None:
            continue
        top, bot = max(h[k:r + 1]), min(l[k:r + 1])
        pois.append(dict(type="BZ", dir="bull" if up else "bear", top=top, bottom=bot, i=r, t=bars[r]["t"], msb_i=rd["msb"],
                         entry=top if up else bot, sl=stop(bot if up else top, up, a[-1])))

    fvgs = []
    for i in range(1, n - 1):  # FVG: wick of candle 1 and candle 3 do not overlap
        if l[i + 1] > h[i - 1]:
            fvgs.append(dict(type="FVG", dir="bull", top=l[i + 1], bottom=h[i - 1], i=i, t=bars[i]["t"], msb_i=None, entry=l[i + 1], sl=stop(h[i - 1], True, a[-1])))
        elif h[i + 1] < l[i - 1]:
            fvgs.append(dict(type="FVG", dir="bear", top=l[i - 1], bottom=h[i + 1], i=i, t=bars[i]["t"], msb_i=None, entry=h[i + 1], sl=stop(l[i - 1], False, a[-1])))

    for m in msbs:  # Order Block: last opposite candle before the MSB; it must take liquidity and the move away must leave an FVG
        j, up = m["i"], m["dir"] == "up"
        k = next((x for x in range(j - 1, max(0, j - 1 - ob_lookback), -1) if ((c[x] < o[x]) if up else (c[x] > o[x]))), None)
        if k is None or k == 0 or k + 1 >= n:
            continue
        took_liq = l[k] < l[k - 1] if up else h[k] > h[k - 1]
        gap = any(f["dir"] == ("bull" if up else "bear") and k < f["i"] <= j for f in fvgs)
        if took_liq and gap:
            pois.append(dict(type="OB", dir="bull" if up else "bear", top=h[k], bottom=l[k], i=k, t=bars[k]["t"], msb_i=j,
                             entry=h[k] if up else l[k], sl=stop(l[k] if up else h[k], up, a[-1])))
    pois += fvgs

    last = c[-1]
    for p in pois:  # fresh = no wick has entered the zone since it completed (after the MSB for BZ/OB, after candle 3 for FVG)
        start = (p["msb_i"] if p["msb_i"] is not None else p["i"] + 1) + 1
        p["fresh"] = all(h[x] < p["bottom"] or l[x] > p["top"] for x in range(start, n))
        p["price_vs_zone"] = "inside" if p["bottom"] <= last <= p["top"] else ("above" if last > p["top"] else "below")
        p["dist"] = round(0 if p["price_vs_zone"] == "inside" else min(abs(last - p["top"]), abs(last - p["bottom"])), 3)

    def equal(points, px, broken):  # 2+ unbroken points within 0.15 ATR of each other = a liquidity pool
        pools, used = [], set()
        for i in points:
            if i in broken or i in used:
                continue
            grp = [k for k in points if k not in broken and k not in used and abs(px[k] - px[i]) <= 0.15 * a[-1]]
            if len(grp) >= 2:
                used.update(grp)
                pools.append(dict(price=round(sum(px[k] for k in grp) / len(grp), 3), touches=len(grp), t=bars[grp[-1]]["t"]))
        return pools

    return dict(
        bars=n, last_close=last, last_t=bars[-1]["t"], atr=round(a[-1], 3), swing=swing, bias=bias,
        equal_highs=equal(sh, h, broken_sh), equal_lows=equal(sl, l, broken_sl),
        last_msb=msbs[-1] if msbs else None,
        structure_highs=[dict(i=i, t=bars[i]["t"], price=h[i], broken=i in broken_sh) for i in sh[-6:]],
        structure_lows=[dict(i=i, t=bars[i]["t"], price=l[i], broken=i in broken_sl) for i in sl[-6:]],
        msbs=msbs[-8:],
        raids=raids[-6:],
        pois=sorted(pois, key=lambda p: p["i"]),
    )


def selfcheck():
    # 10 bars: SH at bar 2 (high 12), SL at bar 4 (low 8). Bar 6 wicks above 12 but closes 11 (sweep),
    # bar 7 closes 7 below SL 8 -> MSB down on the next bar = valid Liquidity Raid, bearish BZ.
    oh = [(10, 11, 9, 10.5), (10.5, 11.5, 10, 11), (11, 12, 10.5, 11.5), (11.5, 11.8, 10, 10.2),
          (10.2, 10.5, 8, 9), (9, 10, 8.5, 9.8), (9.8, 12.5, 9.5, 11), (11, 11.2, 6.5, 7),
          (7, 7.5, 6, 6.5), (6.5, 7, 5.5, 6)]
    bars = [dict(t=i, o=o, h=h, l=l, c=c) for i, (o, h, l, c) in enumerate(oh)]
    r = analyze(bars, max_body_atr=99, swing=1)
    assert 2 in [s["i"] for s in r["structure_highs"]] and 4 in [s["i"] for s in r["structure_lows"]]
    assert r["bias"] == "down" and r["last_msb"]["i"] == 7
    assert r["raids"] and r["raids"][0]["raid"] == 6 and r["raids"][0]["msb"] == 7
    bz = [p for p in r["pois"] if p["type"] == "BZ"]
    assert bz and bz[0]["dir"] == "bear" and bz[0]["top"] == 12.5 and bz[0]["entry"] == bz[0]["bottom"]
    assert bz[0]["sl"] > 12.5  # stop sits beyond the edge, never on it
    # Order Block: down candle (bar 3) takes the low of bar 2, then a displacement leaves an FVG and breaks SH 11
    ob = [(10, 10.5, 9.6, 10.3), (10.3, 11, 10, 10.5), (10.5, 10.8, 9.8, 10), (10, 10.2, 9.3, 9.6),
          (9.6, 11.5, 9.5, 11.4), (11.4, 12.5, 11.2, 12.3), (12.3, 12.8, 12, 12.6)]
    ro = analyze([dict(t=i, o=o, h=h, l=l, c=c) for i, (o, h, l, c) in enumerate(ob)], max_body_atr=99, swing=1)
    assert [p for p in ro["pois"] if p["type"] == "OB" and p["dir"] == "bull" and p["i"] == 3], ro["pois"]
    # forming bar: a last bar whose period has not ended is dropped, a finished one is kept
    import os, tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump([dict(t=i * 60, o=1, h=2, l=0, c=1) for i in range(5)], f)
    assert len(load(f.name, now=4 * 60 + 30)) == 4 and len(load(f.name, now=5 * 60)) == 5
    os.unlink(f.name)
    # equal lows: two unbroken SLs at 8.0 and 8.02 -> one pool
    oh2 = [(10, 10.5, 9, 9.5), (9.5, 9.6, 8.0, 9.2), (9.2, 9.8, 9.0, 9.6), (9.6, 9.7, 8.02, 9.3), (9.3, 9.9, 9.1, 9.7), (9.7, 9.9, 9.2, 9.6)]
    r2 = analyze([dict(t=i, o=o, h=h, l=l, c=c) for i, (o, h, l, c) in enumerate(oh2)], swing=1)
    assert len(r2["equal_lows"]) == 1 and r2["equal_lows"][0]["touches"] == 2, r2["equal_lows"]
    print("selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selfcheck":
        selfcheck()
        sys.exit(0)
    args = sys.argv[2:]
    bars = load(sys.argv[1])
    if "--last" in args:
        bars = bars[-int(args[args.index("--last") + 1]):]
    out = analyze(bars, swing=int(args[args.index("--swing") + 1]) if "--swing" in args else SWING)
    out["label"] = args[args.index("--label") + 1] if "--label" in args else ""
    print(json.dumps(out, indent=1))
