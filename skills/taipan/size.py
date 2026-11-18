#!/usr/bin/env python3
"""Position size from account risk. Money arithmetic is done here, never in the model's head.

usage: size.py --entry 3979.6 --sl 3993.4 [--tp 3950]
Account numbers come from taipan.json in the project root; any of them can be overridden with a flag:
               [--balance 10000] [--risk-pct 0.5] [--contract 100] [--lot-step 0.01] [--min-lot 0.01]
               [--max-lot N] [--spread 0.30] [--commission 7] [--min-stop-spreads 5]
--contract    units per 1.00 lot (XAUUSD 100 oz, FX 100000)
--spread      in price units, added to the stop distance and taken off the target distance
--commission  per 1.00 lot round turn, in account currency
shortcut: assumes the account currency is the quote currency (USD account, XAUUSD / EURUSD); add a conversion rate when a cross or a non-USD account is traded.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402


def size(balance, risk_pct, entry, sl, tp=None, contract=100, lot_step=0.01, min_lot=0.01, max_lot=None, spread=0.0, commission=0.0, min_stop_spreads=0):
    dist = abs(entry - sl)
    if dist <= 0:
        return dict(verdict="NO TRADE", reason="stop is at the entry: no stop, no trade")
    if spread and dist < min_stop_spreads * spread:
        return dict(verdict="NO TRADE", reason=f"stop too tight: {round(dist, 5)} is under {min_stop_spreads} spreads ({round(min_stop_spreads * spread, 5)}); normal noise would take it out")
    budget = balance * risk_pct / 100
    loss_per_lot = (dist + spread) * contract + commission
    lots = math.floor(budget / loss_per_lot / lot_step + 1e-9) * lot_step
    if max_lot is not None:
        lots = min(lots, max_lot)
    lots = round(lots, 8)
    out = dict(risk_budget=round(budget, 2), stop_distance=round(dist, 5), loss_per_lot=round(loss_per_lot, 2), lots=lots)
    if lots < min_lot:
        return dict(out, verdict="NO TRADE", reason=f"stop too wide: the minimum lot {min_lot} would risk {round(min_lot * loss_per_lot, 2)}, over the {round(budget, 2)} budget")
    out["risk_money"] = round(lots * loss_per_lot, 2)
    out["risk_pct_actual"] = round(100 * lots * loss_per_lot / balance, 3)
    if tp is not None:
        if (tp - entry) * (entry - sl) <= 0:
            return dict(out, verdict="NO TRADE", reason="target is on the stop's side of the entry")
        win_per_lot = (abs(tp - entry) - spread) * contract - commission
        out["reward_money"] = round(lots * win_per_lot, 2)
        out["rr_raw"] = round(abs(tp - entry) / dist, 2)
        out["rr_net"] = round(win_per_lot / loss_per_lot, 2)  # after spread and commission: this is the one to hold against the SOP minimum
    return out


ACCOUNT = ("balance", "risk_pct", "contract", "lot_step", "min_lot", "max_lot", "spread", "commission", "min_stop_spreads")


def selfcheck():
    r = size(10000, 0.5, 4000, 3990, tp=4020)
    assert r["lots"] == 0.05 and r["risk_money"] == 50 and r["rr_net"] == 2.0, r
    r = size(10000, 0.5, 4000, 3990, tp=4020, spread=0.5, commission=7)  # costs shrink the lot and the RR
    assert r["lots"] == 0.04 and r["risk_money"] <= 50 and r["rr_net"] < r["rr_raw"] == 2.0, r
    assert size(10000, 0.5, 4000, 4010, tp=3980)["rr_net"] == 2.0  # short
    assert size(500, 0.5, 4000, 3900)["verdict"] == "NO TRADE"  # 100 stop needs 0.00025 lot
    assert size(10000, 0.5, 4000, 4000)["verdict"] == "NO TRADE"
    assert size(10000, 0.5, 4000, 3990, tp=3980)["verdict"] == "NO TRADE"
    assert size(1e6, 1, 4000, 3990, max_lot=2)["lots"] == 2
    assert size(10000, 0.5, 4000, 3999, spread=0.3, min_stop_spreads=5)["verdict"] == "NO TRADE"  # 1.0 stop < 5 x 0.3
    assert "lots" in size(10000, 0.5, 4000, 3998, spread=0.3, min_stop_spreads=5)
    print("selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selfcheck":
        selfcheck()
        sys.exit(0)
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", type=float, required=True)
    ap.add_argument("--sl", type=float, required=True)
    ap.add_argument("--tp", type=float)
    for k in ACCOUNT:
        ap.add_argument("--" + k.replace("_", "-"), type=float)
    a, cfg = vars(ap.parse_args()), config.load()
    kw = {k: a[k] if a[k] is not None else cfg[k] for k in ACCOUNT}
    if kw["balance"] is None or kw["risk_pct"] is None:
        sys.exit("balance and risk_pct are not set: put them in taipan.json (copy taipan.example.json) or pass --balance and --risk-pct")
    print(json.dumps(size(entry=a["entry"], sl=a["sl"], tp=a["tp"], **kw), indent=1))
