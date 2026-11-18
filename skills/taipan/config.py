"""taipan.json: the account numbers and limits every script reads, so nobody retypes them into flags.

Also the pinned clock: TAIPAN_NOW=2026-11-18T13:20Z makes every script (and the detectors' closed-bar
check) run as if it were that moment, so a result can be reproduced.
"""
import json
import os
import sys
from datetime import datetime, timezone

DEFAULTS = dict(
    symbol=None, tz="UTC", balance=None, risk_pct=None,
    contract=100, lot_step=0.01, min_lot=0.01, max_lot=None, spread=0.0, commission=0.0,
    daily_loss_pct=None, max_trades_per_day=None, max_consec_losses=None, max_open_positions=1,
    min_rr=2.0, min_stop_spreads=5,      # a stop closer than this many spreads is noise
    sessions=None,                       # e.g. ["London", "New York"]; null = any session
    news_before_min=15, news_after_min=15, max_price_age_min=15,
)
NUMERIC = [k for k, v in DEFAULTS.items() if k not in ("symbol", "tz", "sessions")]


def load(path="taipan.json"):
    cfg = dict(DEFAULTS)
    if os.path.exists(path):
        try:
            user = json.load(open(path))
        except ValueError as e:
            sys.exit(f"{path} is not valid JSON: {e}")
        unknown = set(user) - set(DEFAULTS)
        if unknown:
            sys.exit(f"{path}: unknown key(s) {sorted(unknown)}")  # a typo in a limit must not silently switch it off
        cfg.update(user)
    for k in NUMERIC:
        if cfg[k] is not None and (isinstance(cfg[k], bool) or not isinstance(cfg[k], (int, float)) or cfg[k] < 0):
            sys.exit(f"{path}: {k} must be a number >= 0 or null, got {cfg[k]!r}")
    return cfg


def now():
    s = os.environ.get("TAIPAN_NOW")
    if not s:
        return datetime.now(timezone.utc)
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
