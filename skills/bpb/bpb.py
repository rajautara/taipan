#!/usr/bin/env python3
"""Breakout-Pullback detector. Reuses btc.py: a breakout is a body-close MSB; this adds the pullback.

usage: bpb.py BARS.json [--label H4] [--last N] [--swing K]
For each recent MSB: the retest zone (broken level .. breakout candle open, or the FVG the breakout
left), the pullback status, and entry / SL once the pullback has resumed.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "btc"))
from btc import SWING, analyze as structure, load, stop  # noqa: E402

MAX_AGE = 30          # bars: a breakout older than this is stale
MAX_BREAK_ATR = 2.5   # breakout candle body larger than this is a climax, not a breakout to retest
MAX_TRIGGER_AGE = 3   # bars after the resume close; later than this the entry is a chase


def analyze(bars, swing=SWING):
    s = structure(bars, max_body_atr=MAX_BREAK_ATR, swing=swing)
    n = len(bars)
    o = [b["o"] for b in bars]
    h = [b["h"] for b in bars]
    l = [b["l"] for b in bars]
    c = [b["c"] for b in bars]
    fvg = {p["i"]: p for p in s["pois"] if p["type"] == "FVG"}
    setups = []
    for m in s["msbs"]:
        j, up, lvl = m["i"], m["dir"] == "up", m["level"]
        if n - j > MAX_AGE or m["big_body"]:
            continue
        # retest zone: broken level .. breakout candle open; the FVG left by the breakout (bar j is its
        # middle candle) is the tighter zone when it exists in the right direction
        g = fvg.get(j)
        if g and g["dir"] != ("bull" if up else "bear"):
            g = None
        if g:
            top, bot = g["top"], g["bottom"]
        else:
            top, bot = (lvl, o[j]) if up else (o[j], lvl)
            top, bot = max(top, bot), min(top, bot)
        status, touch, ext, trigger = "waiting", None, None, None
        for x in range(j + 1, n):
            failed = c[x] < lvl if up else c[x] > lvl
            if failed:
                status = "failed"
                break
            inside = l[x] < top if up else h[x] > bot  # strict: the candle that defines an FVG edge is not a retest
            if inside and touch is None:
                touch, ext, status = x, (l[x] if up else h[x]), "in_pullback"
            elif touch is not None and status == "in_pullback":
                ext = min(ext, l[x]) if up else max(ext, h[x])
                resumed = c[x] > top if up else c[x] < bot  # body close back out of the zone in breakout direction
                if resumed:
                    status, trigger = "resumed", x
        entry = c[trigger] if trigger is not None else (top if up else bot)
        sl = stop(ext, up, s["atr"]) if ext is not None else None
        if status == "resumed":  # the entry is the resume close: once price has run 1R, or 3 bars have passed, it is gone
            risk = abs(entry - sl)
            ran = any((h[x] - entry if up else entry - l[x]) >= risk for x in range(trigger + 1, n))
            if ran or n - 1 - trigger > MAX_TRIGGER_AGE:
                status = "expired"
        setups.append(dict(dir="long" if up else "short", level=lvl, break_i=j, t=bars[j]["t"], kind=m["kind"],
                           zone_top=top, zone_bottom=bot, zone_src="fvg" if g else "level-open",
                           status=status, touch_i=touch, trigger_i=trigger, pullback_extreme=ext,
                           entry=entry, sl=sl, age=n - 1 - j,
                           trigger_age=None if trigger is None else n - 1 - trigger))
    last = c[-1]
    for st in setups:
        st["price_vs_zone"] = "inside" if st["zone_bottom"] <= last <= st["zone_top"] else ("above" if last > st["zone_top"] else "below")
    live = [st for st in setups if st["status"] not in ("failed", "expired")]
    return dict(bars=n, last_close=last, last_t=bars[-1]["t"], atr=s["atr"], bias=s["bias"],
                setups=sorted(live, key=lambda st: st["age"]),
                failed=sum(st["status"] == "failed" for st in setups), expired=sum(st["status"] == "expired" for st in setups))


def selfcheck():
    # SH at bar 2 (high 12). Bar 5 body-closes above 12 (breakout up, level 12, open 11).
    # Bar 7 wicks back into 11..12 (pullback, low 11.3), bar 8 closes above 12 -> resumed, entry = bar 8 close, SL 11.3.
    oh = [(10, 11, 9, 10.5), (10.5, 11.5, 10, 11), (11, 12, 10.5, 11.5), (11.5, 11.8, 10, 10.2),
          (10.2, 10.8, 9.8, 10.6), (11, 13.2, 10.9, 13), (13, 13.5, 12.4, 12.6), (12.6, 12.8, 11.3, 12.1),
          (12.1, 13.0, 12.0, 12.9), (12.9, 13.6, 12.7, 13.4)]
    bars = [dict(t=i, o=o, h=h, l=l, c=c) for i, (o, h, l, c) in enumerate(oh)]
    r = analyze(bars[:9], swing=1)  # stop at the trigger bar: the setup is live
    st = [x for x in r["setups"] if x["level"] == 12]
    assert st and st[0]["dir"] == "long" and st[0]["status"] == "resumed", r
    assert st[0]["touch_i"] == 7 and st[0]["trigger_i"] == 8 and st[0]["pullback_extreme"] == 11.3 and st[0]["entry"] == 12.9, st[0]
    assert st[0]["sl"] < 11.3  # stop beyond the pullback extreme
    # five quiet bars later nobody should be offered the bar-8 close as an entry
    late = bars[:9] + [dict(t=9 + i, o=12.9, h=13.0, l=12.8, c=12.9) for i in range(5)]
    r = analyze(late, swing=1)
    assert not [x for x in r["setups"] if x["level"] == 12] and r["expired"] == 1, r
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
