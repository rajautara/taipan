---
name: premarket
description: "Pre-session brief for the trader's instrument: HTF bias, key levels, today's news windows, and the plan for the session. Use for /premarket, \"premarket\", \"morning brief\", \"what's the plan today\", \"anything on the calendar\"."
argument-hint: "[symbol] [session]"
---

# Premarket

Build the session plan before the first candle, so the trader is not deciding under pressure later.

## Data

Default symbol and session come from TRADING.md; otherwise ask once.

If a TradingView connector is available, use it: the same three `get_ohlcv` files `/read` uses (1D, 4h, 15m), and the economic calendar for today, filtered to high-impact events for the instrument's currencies (for XAUUSD: USD). Then:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/read/read.py" --d1 <file> --h4 <file> --m15 <file>
python3 "${CLAUDE_PLUGIN_ROOT}/skills/taipan/now.py" --tz <zone> --events <release times, ISO UTC> --before <min> --after <min>
python3 "${CLAUDE_PLUGIN_ROOT}/skills/taipan/journal.py" status --tz <zone> --balance <..> --daily-loss-pct <..> --max-trades <..> --max-consec <..>
```

Bias and key levels come from `read.py` (`bias`, `levels`), the news windows in local time from `now.py`, and what is left of today's limits from the journal. If there is no connector, ask the trader to paste the levels and today's red-folder events; do not invent either.

## Output

Plain markdown, never a code block: the trader reads this on a phone at the screen. Short bold labels, one idea per line, prices in **bold**.

Keep it to one screen.

**<SYMBOL> — <date>, <session>**

- **Bias (D1/H4):** <direction + the structure that says so>
- **Key levels:** 3–5 prices — HTF S/R, yesterday H/L, weekly open
- **News windows:** <time – time local: event>, or "none"
- **No-trade zones:** <ranges where SOP says stand aside, incl. news windows + buffer from TRADING.md>
- **Plan A:** if price does X at level Y → SOP rule Z, direction
- **Plan B:** the opposite scenario
- **Stand aside if:** <the condition that means no trade today>
- **Left today:** <trades and loss room remaining from the journal, or "journal empty">

Rules: levels are prices, not adjectives. Every plan line names an SOP rule. If the calendar makes most of the session a no-trade zone, say so first — that is the brief.
