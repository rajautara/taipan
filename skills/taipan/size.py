#!/usr/bin/env python3
"""Position size from account risk. Money arithmetic is done here, never in the model's head.

usage: size.py --balance 10000 --risk-pct 0.5 --entry 3979.6 --sl 3993.4 [--tp 3950]
               [--contract 100] [--lot-step 0.01] [--min-lot 0.01] [--max-lot N]
               [--spread 0.30] [--commission 7]
--contract    units per 1.00 lot (XAUUSD 100 oz, FX 100000)
--spread      in price units, added to the stop distance and taken off the target distance
--commission  per 1.00 lot round turn, in account currency
shortcut: assumes the account currency is the quote currency (USD account, XAUUSD / EURUSD); add a conversion rate when a cross or a non-USD account is traded.
"""
import argparse
import json
import math
import sys


def size(balance, risk_pct, entry, sl, tp=None, contract=100, lot_step=0.01, min_lot=0.01, max_lot=None, spread=0.0, commission=0.0):
    dist = abs(entry - sl)
    if dist <= 0:
        return dict(verdict="NO TRADE", reason="stop is at the entry: no stop, no trade")
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
    print("selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selfcheck":
        selfcheck()
        sys.exit(0)
    ap = argparse.ArgumentParser()
    for k in ("balance", "risk-pct", "entry", "sl"):
        ap.add_argument("--" + k, type=float, required=True)
    ap.add_argument("--tp", type=float)
    ap.add_argument("--contract", type=float, default=100)
    ap.add_argument("--lot-step", type=float, default=0.01)
    ap.add_argument("--min-lot", type=float, default=0.01)
    ap.add_argument("--max-lot", type=float)
    ap.add_argument("--spread", type=float, default=0.0)
    ap.add_argument("--commission", type=float, default=0.0)
    print(json.dumps(size(**vars(ap.parse_args())), indent=1))
