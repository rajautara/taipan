#!/usr/bin/env python3
"""The clock: current time, open sessions, market closed, and news windows. The model never guesses any of these.

usage: now.py [--events 2026-11-18T13:30Z,2026-11-18T19:00Z] [--tz Asia/Kuala_Lumpur] [--before 15] [--after 15]
--events  high-impact release times (UTC, ISO) from the calendar. Zone and window minutes come from taipan.json
unless a flag overrides them. TAIPAN_NOW=<ISO time> pins the clock.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

# Local cash-session hours; zoneinfo handles each city's daylight saving.
SESSIONS = [("Asia", "Asia/Tokyo", 9, 15), ("London", "Europe/London", 8, 16.5), ("New York", "America/New_York", 8, 17)]
NY = ZoneInfo("America/New_York")


def clock(now, tz="UTC", events=(), before=15, after=15):
    loc = now.astimezone(ZoneInfo(tz))
    ny = now.astimezone(NY)
    h = ny.hour + ny.minute / 60
    # spot FX / metals: closed Friday 17:00 New York to Sunday 18:00 New York
    closed = (ny.weekday() == 4 and h >= 17) or ny.weekday() == 5 or (ny.weekday() == 6 and h < 18)
    open_ = []
    for name, zone, a, b in SESSIONS:
        t = now.astimezone(ZoneInfo(zone))
        if t.weekday() < 5 and a <= t.hour + t.minute / 60 < b:
            open_.append(name)
    out = dict(utc=now.strftime("%Y-%m-%d %H:%M"), local=loc.strftime("%Y-%m-%d %H:%M %a"), tz=tz,
               market="closed" if closed else "open", sessions=[] if closed else open_)
    news = []
    for e in events:
        t = datetime.fromisoformat(e.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        start, end = t - timedelta(minutes=before), t + timedelta(minutes=after)
        if now > end:
            continue
        news.append(dict(release_local=t.astimezone(ZoneInfo(tz)).strftime("%H:%M %a"),
                         window_local=f"{start.astimezone(ZoneInfo(tz)):%H:%M}-{end.astimezone(ZoneInfo(tz)):%H:%M}",
                         in_window=start <= now <= end, minutes_to_window=max(0, round((start - now).total_seconds() / 60))))
    out["news"] = news
    out["restricted_now"] = any(n["in_window"] for n in news)
    return out


def selfcheck():
    u = timezone.utc
    r = clock(datetime(2026, 11, 18, 13, 20, tzinfo=u), "Asia/Kuala_Lumpur", ["2026-11-18T13:30Z"])  # Wednesday
    assert r["local"].startswith("2026-11-18 21:20") and r["sessions"] == ["London", "New York"] and r["market"] == "open", r
    assert r["restricted_now"] and r["news"][0]["window_local"] == "21:15-21:45", r
    r = clock(datetime(2026, 11, 18, 12, 0, tzinfo=u), "UTC", ["2026-11-18T13:30Z", "2026-11-18T10:00Z"])
    assert not r["restricted_now"] and len(r["news"]) == 1 and r["news"][0]["minutes_to_window"] == 75, r
    assert clock(datetime(2026, 11, 15, 12, 0, tzinfo=u))["market"] == "closed"  # Sunday midday
    assert clock(datetime(2026, 11, 20, 22, 30, tzinfo=u))["market"] == "closed"  # Friday 17:30 New York (EST)
    assert clock(datetime(2026, 7, 15, 7, 30, tzinfo=u))["sessions"] == ["London"]  # 08:30 London in summer time
    assert clock(datetime(2026, 11, 18, 1, 0, tzinfo=u))["sessions"] == ["Asia"]
    print("selfcheck ok")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        selfcheck()
        sys.exit(0)
    ap = argparse.ArgumentParser()
    cfg = config.load()
    ap.add_argument("--tz", default=cfg["tz"])
    ap.add_argument("--events", default="")
    ap.add_argument("--before", type=float, default=cfg["news_before_min"])
    ap.add_argument("--after", type=float, default=cfg["news_after_min"])
    a = ap.parse_args()
    print(json.dumps(clock(config.now(), a.tz, [e for e in a.events.split(",") if e], a.before, a.after), indent=1))
