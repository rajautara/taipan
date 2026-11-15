#!/usr/bin/env python3
"""One command for the whole read: all four detectors on every timeframe, key levels, and confluence.

usage: read.py [--d1 d1.json] [--h4 h4.json] [--m15 m15.json] [--swing K]
Each file is a TradingView get_ohlcv result. Prints compact JSON: bias per timeframe, key levels
(PDH/PDL, PWH/PWL, Asia range, equal highs/lows), live setups from bpb / qm, and every live zone
near price ranked by how many other methods, timeframes and key levels agree with it.
"""
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("btc", "snd", "bpb", "qm"):
    sys.path.insert(0, os.path.join(HERE, "..", d))
import bpb  # noqa: E402
import btc  # noqa: E402
import qm  # noqa: E402
import snd  # noqa: E402

NEAR_ATR = 6     # zones further than this many H4 ATRs from price are not on today's map
TOUCH_ATR = 0.25  # two zones, or a zone and a level, this close count as the same place
ASIA_END_UTC = 7  # Asia range = 00:00-07:00 UTC of the latest day in the M15 file


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc)


def levels(d1, m15):
    out = {}
    if d1:
        out["PDH"], out["PDL"] = d1[-1]["h"], d1[-1]["l"]  # load() has already dropped the forming day
        # shortcut: daily bars open the evening before in UTC, so +6h puts each bar in its own trading week
        week = lambda b: utc(b["t"] + 6 * 3600).isocalendar()[:2]  # noqa: E731
        prev = [b for b in d1 if week(b) != week(d1[-1])]
        prev = [b for b in prev if week(b) == week(prev[-1])] if prev else []
        if prev:
            out["PWH"], out["PWL"] = max(b["h"] for b in prev), min(b["l"] for b in prev)
    if m15:
        day = utc(m15[-1]["t"]).date()
        asia = [b for b in m15 if utc(b["t"]).date() == day and utc(b["t"]).hour < ASIA_END_UTC]
        if asia:
            out["AsiaH"], out["AsiaL"] = max(b["h"] for b in asia), min(b["l"] for b in asia)
            out["asia_range_complete"] = utc(m15[-1]["t"]).hour >= ASIA_END_UTC
    return out


def rank(zones, lv, price, atr_ref):
    tol = TOUCH_ATR * atr_ref
    near = [z for z in zones if min(abs(price - z["top"]), abs(price - z["bottom"])) <= NEAR_ATR * atr_ref or z["bottom"] <= price <= z["top"]]
    for z in near:
        z["with"] = sorted({f'{o["tf"]} {o["type"]}' for o in near if o is not z and o["dir"] == z["dir"]
                            and (o["tf"], o["type"]) != (z["tf"], z["type"])
                            and o["bottom"] <= z["top"] + tol and o["top"] >= z["bottom"] - tol}
                           | {k for k, v in lv.items() if isinstance(v, float) and z["bottom"] - tol <= v <= z["top"] + tol})
        z["dist"] = round(0 if z["bottom"] <= price <= z["top"] else min(abs(price - z["top"]), abs(price - z["bottom"])), 3)
    return sorted(near, key=lambda z: (-len(z["with"]), z["dist"]))


def read(files, swing=btc.SWING):
    bars = {tf: btc.load(p) for tf, p in files.items()}
    st = {tf: btc.analyze(b, swing=swing) for tf, b in bars.items()}
    ref = st.get("H4") or st.get("D1") or st["M15"]
    price = (st.get("M15") or ref)["last_close"]
    lv = levels(bars.get("D1"), bars.get("M15"))
    lv.update({f"{tf} EQH {i + 1}": float(p["price"]) for tf in ("H4",) if tf in st for i, p in enumerate(st[tf]["equal_highs"])})
    lv.update({f"{tf} EQL {i + 1}": float(p["price"]) for tf in ("H4",) if tf in st for i, p in enumerate(st[tf]["equal_lows"])})
    lv = {k: (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in lv.items()}

    zones = []
    for tf in ("D1", "H4"):
        if tf not in bars:
            continue
        for p in st[tf]["pois"]:
            if p["fresh"]:
                zones.append(dict(tf=tf, method="btc", type=p["type"], dir=p["dir"], bottom=p["bottom"], top=p["top"], entry=p["entry"], sl=p["sl"], status="fresh", t=p["t"]))
        s = snd.analyze(bars[tf])
        for z in s["demand"] + s["supply"]:
            zones.append(dict(tf=tf, method="snd", type=z["pattern"], dir="bull" if z["type"] == "demand" else "bear", bottom=z["bottom"], top=z["top"],
                              entry=z["entry"], sl=z["sl"], status=z["status"], touches=z["touches"], departure_atr=z["departure_atr"], t=z["t"]))
    setups = {}
    for tf in ("H4", "M15"):
        if tf not in bars:
            continue
        b, q = bpb.analyze(bars[tf], swing=swing), qm.analyze(bars[tf], swing=swing)
        setups[tf] = dict(bpb=b["setups"], qm=q["setups"])
        for x in b["setups"]:
            zones.append(dict(tf=tf, method="bpb", type="retest", dir="bull" if x["dir"] == "long" else "bear", bottom=x["zone_bottom"], top=x["zone_top"],
                              entry=x["entry"], sl=x["sl"], status=x["status"], t=x["t"]))
        for x in q["setups"]:
            zones.append(dict(tf=tf, method="qm", type="QML", dir="bull" if x["dir"] == "long" else "bear", bottom=x["qml"], top=x["qml"],
                              entry=x["entry"], sl=x["sl"], status=x["status"], t=x["t"]))
    return dict(
        price=price, atr={tf: s["atr"] for tf, s in st.items()},
        last_closed_bar_utc={tf: utc(s["last_t"]).strftime("%Y-%m-%d %H:%M") for tf, s in st.items()},
        bias={tf: dict(dir=s["bias"], last_msb=s["last_msb"] and dict(dir=s["last_msb"]["dir"], kind=s["last_msb"]["kind"], level=s["last_msb"]["level"],
                                                                    utc=utc(s["last_msb"]["t"]).strftime("%Y-%m-%d %H:%M"), bars_ago=s["bars"] - 1 - s["last_msb"]["i"]))
              for tf, s in st.items()},
        levels=lv, zones=rank(zones, lv, price, ref["atr"])[:10], setups=setups,
        m15_entry_model=[p for p in st["M15"]["pois"] if p["type"] == "BZ" and p["fresh"]] if "M15" in st else None)


def selfcheck():
    day = 86400
    mon = 1794787200  # Monday 2026-11-16 00:00 UTC
    d1 = [dict(t=mon - 7 * day + i * day - 2 * 3600, o=1, h=10 + i, l=1 + i, c=5) for i in range(5)]  # last week: H up to 14, L from 1
    d1 += [dict(t=mon - 2 * 3600, o=1, h=20, l=15, c=18)]  # Monday of this week
    m15 = [dict(t=mon + day + i * 900, o=1, h=30 + (i == 3), l=25 - (i == 5), c=28) for i in range(40)]  # Tuesday 00:00-10:00
    lv = levels(d1, m15)
    assert (lv["PDH"], lv["PDL"], lv["PWH"], lv["PWL"]) == (20, 15, 14, 1), lv
    assert (lv["AsiaH"], lv["AsiaL"]) == (31, 24) and lv["asia_range_complete"], lv
    z = [dict(tf="H4", method="snd", type="DBR", dir="bull", bottom=100, top=104), dict(tf="H4", method="btc", type="FVG", dir="bull", bottom=103, top=106),
         dict(tf="H4", method="btc", type="FVG", dir="bear", bottom=101, top=103), dict(tf="D1", method="btc", type="OB", dir="bull", bottom=120, top=122),
         dict(tf="H4", method="btc", type="OB", dir="bull", bottom=400, top=410)]
    r = rank(z, dict(PDL=100.5, PWH=300.0), 110, 4)
    assert len(r) == 4 and r[0]["type"] == "DBR" and r[0]["with"] == ["H4 FVG", "PDL"], r  # overlap same direction + a level inside; far zone dropped
    assert r[-1]["with"] == [] and all(a["dist"] <= b["dist"] for a, b in zip(r[1:], r[2:]) if len(a["with"]) == len(b["with"])), r
    print("selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selfcheck":
        selfcheck()
        sys.exit(0)
    a = sys.argv[1:]
    files = {tf: a[a.index(f"--{tf.lower()}") + 1] for tf in ("D1", "H4", "M15") if f"--{tf.lower()}" in a}
    if not files:
        sys.exit(__doc__)
    print(json.dumps(read(files, int(a[a.index("--swing") + 1]) if "--swing" in a else btc.SWING), indent=1))
