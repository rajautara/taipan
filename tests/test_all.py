#!/usr/bin/env python3
"""Run every selfcheck, then property tests the single-case selfchecks cannot give:
mirror symmetry (a bearish chart is a bullish chart upside down) and stop sanity on a long random walk.

usage: python3 tests/test_all.py
"""
import os
import random
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills")
for d in ("btc", "snd", "bpb", "qm"):
    sys.path.insert(0, os.path.join(ROOT, d))
import bpb  # noqa: E402
import btc  # noqa: E402
import qm  # noqa: E402
import snd  # noqa: E402

for s in ("btc/btc.py", "snd/snd.py", "bpb/bpb.py", "qm/qm.py", "taipan/size.py", "taipan/now.py", "taipan/journal.py", "read/read.py", "backtest/backtest.py"):
    subprocess.run([sys.executable, os.path.join(ROOT, s), "--selfcheck"], check=True, stdout=subprocess.DEVNULL)

random.seed(11)
K, px, bars = 20000, 10000, []
for i in range(600):  # integer ticks, so the mirrored chart compares exactly
    o = px
    c = o + random.randint(-40, 40) * (4 if random.random() < 0.08 else 1)
    bars.append(dict(t=i, o=o, h=max(o, c) + random.randint(0, 15), l=min(o, c) - random.randint(0, 15), c=c))
    px = c
mirror = [dict(t=b["t"], o=K - b["o"], h=K - b["l"], l=K - b["h"], c=K - b["c"]) for b in bars]
flip = {"up": "down", "down": "up", "bull": "bear", "bear": "bull", "long": "short", "short": "long", None: None}

for k in (1, 2):
    a, m = btc.analyze(bars, swing=k), btc.analyze(mirror, swing=k)
    assert a["bias"] == flip[m["bias"]] and len(a["msbs"]) == len(m["msbs"])
    assert sorted((p["type"], p["dir"], p["i"], p["fresh"]) for p in a["pois"]) == sorted((p["type"], flip[p["dir"]], p["i"], p["fresh"]) for p in m["pois"])
    assert {"FVG", "OB"} <= {p["type"] for p in a["pois"]}, "detector stopped finding a POI type"
    for p in a["pois"]:
        assert (p["sl"] < p["bottom"]) if p["dir"] == "bull" else (p["sl"] > p["top"]), p
    for mod in (bpb, qm):
        x, y = mod.analyze(bars, swing=k), mod.analyze(mirror, swing=k)
        assert [(s["dir"], s["status"], s["age"]) for s in x["setups"]] == [(flip[s["dir"]], s["status"], s["age"]) for s in y["setups"]], mod.__name__
        assert (x["failed"], x["expired"]) == (y["failed"], y["expired"])
        for s in x["setups"]:
            assert s["status"] not in ("failed", "expired")
            if s["sl"] is not None:
                assert (s["sl"] < s["entry"]) if s["dir"] == "long" else (s["sl"] > s["entry"]), s
    for s in qm.analyze(bars, swing=k)["setups"]:
        assert qm.MIN_STOP_ATR * a["atr"] <= abs(s["sl"] - s["entry"]) <= (qm.MAX_STOP_ATR + btc.SL_BUFFER_ATR) * a["atr"] + 1e-6, s

z, zm = snd.analyze(bars), snd.analyze(mirror)
assert [(q["pattern"], q["i"], q["status"], q["touches"]) for q in z["demand"]] == [(q["pattern"].translate(str.maketrans("RD", "DR")), q["i"], q["status"], q["touches"]) for q in zm["supply"]]
assert len(z["supply"]) == len(zm["demand"]) and z["demand"] and z["supply"]
for q in z["demand"]:
    assert q["sl"] < q["bottom"] < q["top"] == q["entry"]
print("all tests ok")
