#!/usr/bin/env python3
"""plan.json: the trades that are on (pending or filled), written by check.py, read by /manage.

usage: plan.py show
       plan.py stop ID --to PRICE      move the stop; refused if it would sit further from the entry
       plan.py close ID --exit PRICE [--grade A] [--note "..."]    logs R and P&L to journal.csv, removes the plan
       plan.py cancel ID               an order that never filled: removed, nothing logged
The original stop is kept forever: R is always measured against it, however far the stop has been trailed.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import journal  # noqa: E402

FILE = "plan.json"


def load(path=FILE):
    return json.load(open(path)) if os.path.exists(path) else []


def save(plans, path=FILE):
    json.dump(plans, open(path, "w"), indent=1)


def add(plan, path=FILE):
    plans = load(path)
    plan = dict(plan, id=max([p["id"] for p in plans], default=0) + 1, sl_now=plan["sl"])
    save(plans + [plan], path)
    return plan


def find(plans, pid):
    hit = [p for p in plans if p["id"] == pid]
    if not hit:
        sys.exit(f"no plan with id {pid}; open plans: {[p['id'] for p in plans] or 'none'}")
    return hit[0]


def move_stop(pid, to, path=FILE):
    plans = load(path)
    p = find(plans, pid)
    long = p["dir"] == "long"
    if (to < p["sl_now"]) if long else (to > p["sl_now"]):
        sys.exit(f"REFUSED: {to} is further from the entry than the current stop {p['sl_now']}. A stop is never widened.")
    p["sl_now"] = to
    save(plans, path)
    return p


def close(pid, exit_price, grade="", note="", path=FILE, journal_path="journal.csv", contract=100, commission=0.0):
    plans = load(path)
    p = find(plans, pid)
    sign = 1 if p["dir"] == "long" else -1
    r = sign * (exit_price - p["entry"]) / abs(p["entry"] - p["sl"])  # against the ORIGINAL stop
    pnl = sign * (exit_price - p["entry"]) * p["lots"] * contract - commission * p["lots"]
    row = dict(time=config.now().strftime("%Y-%m-%dT%H:%MZ"), symbol=p.get("symbol", ""), rule=p.get("rule", ""), dir=p["dir"],
               entry=p["entry"], sl=p["sl"], exit=exit_price, lots=p["lots"], r=round(r, 2), pnl=round(pnl, 2), grade=grade, note=note)
    journal.add(journal_path, row)  # journal first: a crash must not lose the trade
    save([q for q in plans if q["id"] != pid], path)
    return row


def selfcheck():
    import subprocess
    import tempfile
    d = tempfile.mkdtemp()
    pf, jf = os.path.join(d, "plan.json"), os.path.join(d, "j.csv")
    a = add(dict(symbol="XAUUSD", rule="bpb", dir="long", entry=4000, sl=3990, tp=4020, lots=0.05, risk_money=50), pf)
    b = add(dict(symbol="XAUUSD", rule="qm", dir="short", entry=4100, sl=4110, tp=4080, lots=0.05, risk_money=50), pf)
    assert (a["id"], b["id"], a["sl_now"]) == (1, 2, 3990)
    assert move_stop(1, 4000, pf)["sl_now"] == 4000 and load(pf)[0]["sl"] == 3990  # trailed to breakeven, original kept
    me = os.path.abspath(__file__)
    for pid, to in (("1", "3995"), ("2", "4115")):  # widening is refused for a long and for a short
        out = subprocess.run([sys.executable, me, "stop", pid, "--to", to], cwd=d, capture_output=True, text=True)
        assert out.returncode != 0 and "REFUSED" in out.stderr, out
    row = close(1, 4020, "A", "tp", pf, jf)
    assert row["r"] == 2.0 and row["pnl"] == 100.0, row  # R against the original 3990 stop, not the trailed one
    row = close(2, 4110, path=pf, journal_path=jf, commission=7)
    assert row["r"] == -1.0 and row["pnl"] == -50.35 and load(pf) == [], row
    assert journal.status(jf, config.now())["trades_total"] == 2
    print("selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selfcheck":
        selfcheck()
        sys.exit(0)
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["show", "stop", "close", "cancel"])
    ap.add_argument("id", type=int, nargs="?")
    ap.add_argument("--to", type=float)
    ap.add_argument("--exit", type=float)
    ap.add_argument("--grade", default="")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    cfg = config.load()
    if a.cmd != "show" and a.id is None:
        sys.exit(f"{a.cmd} needs the plan id (see: plan.py show)")
    if a.cmd == "stop":
        if a.to is None:
            sys.exit("stop needs --to PRICE")
        move_stop(a.id, a.to)
    elif a.cmd == "close":
        if a.exit is None:
            sys.exit("close needs --exit PRICE")
        print("logged:", json.dumps(close(a.id, a.exit, a.grade, a.note, contract=cfg["contract"], commission=cfg["commission"])))
    elif a.cmd == "cancel":
        plans = load()
        find(plans, a.id)
        save([p for p in plans if p["id"] != a.id])
    print(json.dumps(load(), indent=1))
