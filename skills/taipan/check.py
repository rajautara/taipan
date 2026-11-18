#!/usr/bin/env python3
"""The gate. One run answers: is this entry allowed by the account's own limits. PASS or BLOCK, with every reason.

usage: check.py --entry 3979.6 --sl 3993.4 --tp 3950 --rule bpb --events 2026-11-18T13:30Z,...
                [--price 3975.2 --price-age 2] [--invalidation "H4 close above 3993"] [--write]
--rule        the SOP rule's detector (btc | snd | bpb | qm): its backtest record is quoted with the verdict
--events      today's high-impact release times (ISO UTC) from the calendar; pass "none" when the calendar is clear
--price       the current price, when entering at market: risk is measured from the worse of the plan's
              entry and this price, so a plan made earlier cannot understate the risk after price has run
--price-age   minutes since that price was read; older than max_price_age_min it is not used
--write       on PASS, record the trade in plan.json (it then counts as open risk until plan.py closes it)
Limits, account numbers and the time zone come from taipan.json. Exit code 0 = PASS, 1 = BLOCK.

This checks entries only. Getting out of a trade is never checked against a limit and never blocked.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import journal  # noqa: E402
import now as clock_mod  # noqa: E402
import plan as plan_mod  # noqa: E402
from size import ACCOUNT, size  # noqa: E402


def check(cfg, now, entry, sl, tp, rule=None, events=None, price=None, price_age=0.0, plans=(), journal_path="journal.csv", record=None):
    block, warn = [], []
    if cfg["balance"] is None or cfg["risk_pct"] is None:
        return dict(verdict="BLOCK", reasons=["balance and risk_pct are not set in taipan.json: the trade cannot be sized"], warnings=[])
    long = sl < entry
    used = entry
    if price is not None:
        if price_age > cfg["max_price_age_min"]:
            warn.append(f"price is {price_age:g} min old (limit {cfg['max_price_age_min']:g}): not used, risk measured from the plan's entry")
        else:
            used = max(entry, price) if long else min(entry, price)
            if used != entry:
                warn.append(f"price has run past the plan's entry: risk measured from {used}, not {entry}")
    s = size(entry=used, sl=sl, tp=tp, **{k: cfg[k] for k in ACCOUNT})
    if s.get("verdict") == "NO TRADE":
        block.append(s["reason"])
    elif s["rr_net"] < cfg["min_rr"]:
        block.append(f"reward-to-risk {s['rr_net']} after costs is under the minimum {cfg['min_rr']:g}")

    c = clock_mod.clock(now, cfg["tz"], events or [], cfg["news_before_min"], cfg["news_after_min"])
    if c["market"] == "closed":
        block.append("market is closed")
    elif cfg["sessions"] and not set(cfg["sessions"]) & set(c["sessions"]):
        block.append(f"outside the sessions traded ({', '.join(cfg['sessions'])}); open now: {', '.join(c['sessions']) or 'none'}")
    if c["restricted_now"]:
        block.append(f"inside a news window ({[n['window_local'] for n in c['news'] if n['in_window']][0]} local)")
    if events is None:
        warn.append("news not checked: pass --events with today's release times, or --events none")

    j = journal.status(journal_path, now, cfg["tz"])
    today = j["date_local"]
    opened_today = [p for p in plans if p.get("opened_local") == today]
    n_today = j["trades_today"] + len(opened_today)
    if cfg["max_trades_per_day"] is not None and n_today >= cfg["max_trades_per_day"]:
        block.append(f"max trades per day reached ({n_today}/{cfg['max_trades_per_day']:g})")
    if cfg["max_consec_losses"] is not None and j["losing_streak_today"] >= cfg["max_consec_losses"]:
        block.append(f"{j['losing_streak_today']} consecutive losses today (limit {cfg['max_consec_losses']:g})")
    if cfg["max_open_positions"] is not None and len(plans) >= cfg["max_open_positions"]:
        block.append(f"{len(plans)} position(s) already on (limit {cfg['max_open_positions']:g}): plan id {[p['id'] for p in plans]}")
    lost = max(0.0, -j["pnl_today"])  # a winning morning does not buy a bigger losing afternoon
    open_risk = round(sum(p["risk_money"] for p in plans), 2)
    this = s.get("risk_money", 0.0)
    daily = None if cfg["daily_loss_pct"] is None else round(cfg["balance"] * cfg["daily_loss_pct"] / 100, 2)
    if daily is not None and lost + open_risk + this > daily + 1e-9:
        block.append(f"daily loss limit: {lost:g} lost today + {open_risk:g} at risk in open trades + {this:g} this trade = {round(lost + open_risk + this, 2):g}, over {daily:g}")

    rec = (record or {}).get("results", {}).get(rule) if rule else None
    if rec is None:
        warn.append(f"no backtest record for rule {rule!r}: run sop.py --write. This setup type is unproven on this instrument." if rule
                    else "no --rule given: the trade is not tied to an SOP rule")
    out = dict(verdict="BLOCK" if block else "PASS", reasons=block, warnings=warn,
               trade=dict(dir="long" if long else "short", entry=used, sl=sl, tp=tp, **{k: s[k] for k in ("lots", "risk_money", "risk_pct_actual", "reward_money", "rr_net") if k in s}),
               today=dict(date_local=today, trades=n_today, max_trades=cfg["max_trades_per_day"], lost=lost, open_risk=open_risk, daily_limit=daily,
                          losing_streak=j["losing_streak_today"]),
               clock=dict(local=c["local"], sessions=c["sessions"], news=c["news"]))
    if rec is not None:
        out["record"] = dict(period=record.get("period"), trades=rec["trades"], expectancy_r=rec.get("expectancy_r"), verdict=rec["verdict"],
                             this_direction={k: rec[side][k] for k in ("trades", "expectancy_r", "verdict") if k in rec[side]}
                             if (side := "long" if long else "short") in rec else None)
    return out


def selfcheck():
    import tempfile
    from datetime import datetime, timezone
    d = tempfile.mkdtemp()
    jf = os.path.join(d, "j.csv")
    cfg = dict(config.DEFAULTS, balance=10000, risk_pct=0.5, spread=0.3, daily_loss_pct=1, max_trades_per_day=3, max_consec_losses=2,
               sessions=["London", "New York"], tz="Asia/Kuala_Lumpur")
    wed = datetime(2026, 11, 18, 14, 0, tzinfo=timezone.utc)  # Wednesday, London + New York open
    ok = dict(cfg=cfg, now=wed, entry=4000, sl=3990, tp=4025, rule="bpb", events=[], journal_path=jf)
    r = check(**ok)
    assert r["verdict"] == "PASS" and r["trade"]["lots"] == 0.04 and r["trade"]["dir"] == "long", r
    assert any("no backtest record" in w for w in r["warnings"])
    rec = dict(period="x", results=dict(bpb=dict(trades=187, expectancy_r=0.2, verdict="v", long=dict(trades=122, expectancy_r=0.3, verdict="vl"))))
    assert check(**ok, record=rec)["record"]["this_direction"]["trades"] == 122
    assert "news not checked" in " ".join(check(**dict(ok, events=None))["warnings"])
    b = lambda **kw: " | ".join(check(**dict(ok, **kw))["reasons"])  # noqa: E731
    assert "under the minimum" in b(tp=4015)                                    # RR 1.5 < 2
    assert "stop too tight" in b(sl=3999)                                       # 1.0 < 5 spreads
    assert "news window" in b(events=["2026-11-18T14:10Z"])
    assert "market is closed" in b(now=datetime(2026, 11, 21, 14, 0, tzinfo=timezone.utc))
    assert "outside the sessions" in b(now=datetime(2026, 11, 18, 2, 0, tzinfo=timezone.utc))
    # price ran 4 past the plan's entry: risk grows, RR falls below the minimum; a stale price is ignored with a warning
    assert "under the minimum" in b(price=4004, price_age=1) and check(**dict(ok, price=4004, price_age=1))["trade"]["entry"] == 4004
    r = check(**dict(ok, price=4004, price_age=60))
    assert r["verdict"] == "PASS" and "not used" in " ".join(r["warnings"])
    # open risk counts toward the day: 60 already at risk + 41.2 this trade > 100 daily limit; and the position cap
    on = [dict(id=1, risk_money=60, opened_local="2026-11-18")]
    assert "daily loss limit" in b(plans=on) and "already on" in b(plans=on)
    assert "daily loss limit" not in b(plans=[dict(id=1, risk_money=50, opened_local="2026-11-17")])
    journal.add(jf, dict(time="2026-11-18T09:00Z", symbol="X", r=-1, pnl=-50))
    journal.add(jf, dict(time="2026-11-18T10:00Z", symbol="X", r=-1, pnl=-50))
    assert "consecutive losses" in b() and "daily loss limit" in b()
    journal.add(jf, dict(time="2026-11-18T11:00Z", symbol="X", r=2, pnl=100))
    assert "max trades per day" in b() and "daily loss limit" not in b()        # 3 trades done; net flat, nothing lost
    assert check(**dict(ok, cfg=dict(cfg, balance=None)))["verdict"] == "BLOCK"
    print("selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selfcheck":
        selfcheck()
        sys.exit(0)
    ap = argparse.ArgumentParser()
    for k in ("entry", "sl", "tp"):
        ap.add_argument("--" + k, type=float, required=True)
    ap.add_argument("--rule")
    ap.add_argument("--events")
    ap.add_argument("--price", type=float)
    ap.add_argument("--price-age", type=float, default=0.0)
    ap.add_argument("--invalidation", default="")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    cfg, now = config.load(), config.now()
    events = None if a.events is None else [e for e in a.events.split(",") if e and e.lower() != "none"]
    record = json.load(open("backtest.json")) if os.path.exists("backtest.json") else None
    out = check(cfg, now, a.entry, a.sl, a.tp, a.rule, events, a.price, a.price_age, plan_mod.load(), record=record)
    if a.write and out["verdict"] == "PASS":
        t = out["trade"]
        out["plan"] = plan_mod.add(dict(symbol=cfg["symbol"], rule=a.rule or "", dir=t["dir"], entry=t["entry"], sl=t["sl"], tp=t["tp"], lots=t["lots"],
                                        risk_money=t["risk_money"], invalidation=a.invalidation, opened_utc=now.strftime("%Y-%m-%dT%H:%MZ"),
                                        opened_local=out["today"]["date_local"]))
    print(json.dumps(out, indent=1))
    sys.exit(0 if out["verdict"] == "PASS" else 1)
