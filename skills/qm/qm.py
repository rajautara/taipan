#!/usr/bin/env python3
"""Quasimodo (QM) detector. Reuses btc.py structure points.

usage: qm.py BARS.json [--label H4] [--last N]
Bearish QM: Structure High LS -> Structure Low L1 -> higher high HEAD (sweeps LS) -> body close under L1.
QML = LS high (entry on return), SL above HEAD, TP = L1 / next liquidity. Bullish is the mirror.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "btc"))
from btc import analyze as structure, load  # noqa: E402

MAX_AGE = 60  # bars since the MSB; older QMs are stale


def pivots(s):
    """Alternating pivot list [(i, 'H'|'L', price)] from btc structure points; consecutive same-side pivots keep the extreme."""
    pts = sorted([(p["i"], "H", p["price"]) for p in s["_sh"]] + [(p["i"], "L", p["price"]) for p in s["_sl"]])
    out = []
    for p in pts:
        if out and out[-1][1] == p[1]:
            keep = (p[2] > out[-1][2]) if p[1] == "H" else (p[2] < out[-1][2])
            if keep:
                out[-1] = p
            continue
        out.append(p)
    return out


def analyze(bars):
    s = structure(bars, max_body_atr=99)
    n = len(bars)
    h = [b["h"] for b in bars]
    l = [b["l"] for b in bars]
    c = [b["c"] for b in bars]
    s["_sh"] = [dict(i=i, price=h[i]) for i in range(1, n - 1) if h[i] > h[i - 1] and h[i] > h[i + 1]]
    s["_sl"] = [dict(i=i, price=l[i]) for i in range(1, n - 1) if l[i] < l[i - 1] and l[i] < l[i + 1]]
    pv = pivots(s)
    setups = []
    for k in range(len(pv) - 2):
        (ia, ta, pa), (ib, tb, pb), (ic, tc, pc) = pv[k], pv[k + 1], pv[k + 2]
        bear = ta == "H" and pc > pa  # LS high, L1, HEAD higher high
        bull = ta == "L" and pc < pa  # LS low, H1, HEAD lower low
        if not (bear or bull):
            continue
        under = next((x for x in range(ic + 1, n) if (c[x] < pb if bear else c[x] > pb)), None)
        if under is None or n - under > MAX_AGE:
            continue
        qml, head = pa, pc
        status, trigger = "waiting", None
        for x in range(under + 1, n):
            if (c[x] > head) if bear else (c[x] < head):
                status = "failed"
                break
            if (h[x] >= qml) if bear else (l[x] <= qml):
                status, trigger = "at_qml", trigger or x
        last = c[-1]
        setups.append(dict(dir="short" if bear else "long", ls_i=ia, l1=pb, head_i=ic, head=head, under_i=under,
                           t=bars[under]["t"], qml=qml, status=status, touch_i=trigger,
                           entry=qml, sl=head, tp=pb, rr=round(abs(pb - qml) / max(abs(head - qml), 1e-9), 2),
                           age=n - 1 - under, dist=round(abs(last - qml), 3),
                           price_vs_qml=("below" if last < qml else "above") if bear else ("above" if last > qml else "below")))
    live = [x for x in setups if x["status"] != "failed"]
    return dict(bars=n, last_close=c[-1], atr=s["atr"], bias=s["bias"],
                setups=sorted(live, key=lambda x: x["age"]), failed=len(setups) - len(live))


def selfcheck():
    # Bearish QM: LS high 12 (bar 2), L1 low 10 (bar 4), HEAD high 13 (bar 6), body close 9 < L1 at bar 8 (under),
    # then price returns to QML 12 at bar 10 -> at_qml. Entry 12, SL 13, TP 10 -> RR 2.
    oh = [(10, 10.5, 9.5, 10.2), (10.2, 11.5, 10, 11.3), (11.3, 12, 11, 11.6), (11.6, 11.7, 10.4, 10.6),
          (10.6, 10.8, 10, 10.5), (10.5, 12.2, 10.3, 12), (12, 13, 11.8, 12.4), (12.4, 12.6, 10.8, 11),
          (11, 11.2, 8.8, 9), (9, 11, 8.9, 10.8), (10.8, 12.1, 10.7, 11.5), (11.5, 11.6, 11, 11.2)]
    bars = [dict(t=i, o=o, h=h, l=l, c=c) for i, (o, h, l, c) in enumerate(oh)]
    r = analyze(bars)
    qm = [x for x in r["setups"] if x["dir"] == "short" and x["qml"] == 12]
    assert qm and qm[0]["head"] == 13 and qm[0]["under_i"] == 8 and qm[0]["status"] == "at_qml" and qm[0]["touch_i"] == 10 and qm[0]["rr"] == 2.0, r
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
