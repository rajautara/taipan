#!/usr/bin/env python3
"""Trade journal: the memory behind the daily loss limit, max trades and consecutive-loss rules.

usage: journal.py add --symbol XAUUSD --rule "Rule 3" --dir long --entry 4000 --sl 3990 --exit 4020 --lots 0.05
                      --r 2.0 --pnl 100 [--grade A] [--note "..."] [--time 2026-11-18T13:40Z] [--file journal.csv]
       journal.py status [--tz Asia/Kuala_Lumpur] [--balance 10000] [--daily-loss-pct 2] [--max-trades 3] [--max-consec 2]
status prints today's count, R and P&L, the losing streak, the last-20 expectancy, and BLOCKED reasons
when a limit from TRADING.md is passed and has been reached. A day is a calendar day in --tz.
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

FIELDS = ["time", "symbol", "rule", "dir", "entry", "sl", "exit", "lots", "r", "pnl", "grade", "note"]


def add(path, row):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})


def status(path, now, tz="UTC", balance=None, daily_loss_pct=None, max_trades=None, max_consec=None):
    rows = list(csv.DictReader(open(path))) if os.path.exists(path) else []
    z = ZoneInfo(tz)
    day = lambda t: datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(z).date()  # noqa: E731
    today = [r for r in rows if day(r["time"]) == now.astimezone(z).date()]
    num = lambda r, k: float(r[k] or 0)  # noqa: E731
    streak = 0
    for r in reversed(today):  # consecutive losses today, most recent first
        if num(r, "r") >= 0:
            break
        streak += 1
    last = rows[-20:]
    out = dict(date_local=str(now.astimezone(z).date()), trades_today=len(today),
               r_today=round(sum(num(r, "r") for r in today), 2), pnl_today=round(sum(num(r, "pnl") for r in today), 2),
               losing_streak_today=streak, trades_total=len(rows),
               last20=dict(n=len(last), win_rate=round(100 * sum(num(r, "r") > 0 for r in last) / len(last), 1),
                           expectancy_r=round(sum(num(r, "r") for r in last) / len(last), 2)) if last else None)
    blocked = []
    if max_trades is not None and len(today) >= max_trades:
        blocked.append(f"max trades per day reached ({len(today)}/{int(max_trades)})")
    if max_consec is not None and streak >= max_consec:
        blocked.append(f"{streak} consecutive losses today (limit {int(max_consec)})")
    if balance and daily_loss_pct is not None and -out["pnl_today"] >= balance * daily_loss_pct / 100:
        blocked.append(f"daily loss limit hit ({out['pnl_today']} vs -{round(balance * daily_loss_pct / 100, 2)})")
    out["blocked"] = blocked
    return out


def selfcheck():
    import tempfile
    p = os.path.join(tempfile.mkdtemp(), "j.csv")
    now = datetime(2026, 11, 18, 14, 0, tzinfo=timezone.utc)
    assert status(p, now)["trades_today"] == 0 and status(p, now)["blocked"] == []
    add(p, dict(time="2026-11-17T20:00Z", symbol="XAUUSD", r=2, pnl=100))    # 04:00 on the 18th in Kuala Lumpur
    add(p, dict(time="2026-11-18T08:00Z", symbol="XAUUSD", r=-1, pnl=-50))
    add(p, dict(time="2026-11-18T12:00Z", symbol="XAUUSD", r=-1, pnl=-50, note="a, b"))
    s = status(p, now, "UTC", balance=10000, daily_loss_pct=1, max_trades=3, max_consec=2)
    assert s["trades_today"] == 2 and s["r_today"] == -2 and s["losing_streak_today"] == 2 and len(s["blocked"]) == 2, s
    s = status(p, now, "Asia/Kuala_Lumpur", max_trades=3)  # the day boundary follows the trader's zone
    assert s["trades_today"] == 3 and s["pnl_today"] == 0 and s["blocked"] and s["last20"]["expectancy_r"] == 0, s
    print("selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selfcheck":
        selfcheck()
        sys.exit(0)
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "status"])
    ap.add_argument("--file", default="journal.csv")
    ap.add_argument("--tz", default="UTC")
    ap.add_argument("--time")
    for k in FIELDS[1:]:
        ap.add_argument("--" + k)
    for k in ("balance", "daily-loss-pct", "max-trades", "max-consec"):
        ap.add_argument("--" + k, type=float)
    a = ap.parse_args()
    now = datetime.now(timezone.utc)
    if a.cmd == "add":
        if a.r is None or not a.symbol:
            sys.exit("add needs at least --symbol and --r")
        add(a.file, dict(vars(a), time=a.time or now.strftime("%Y-%m-%dT%H:%MZ")))
        print("logged")
    print(json.dumps(status(a.file, now, a.tz, a.balance, a.daily_loss_pct, a.max_trades, a.max_consec), indent=1))
