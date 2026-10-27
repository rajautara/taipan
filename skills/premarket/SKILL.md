---
name: premarket
description: "Pre-session brief for the trader's instrument: HTF bias, key levels, today's news windows, and the plan for the session. Use for /premarket, \"premarket\", \"morning brief\", \"what's the plan today\", \"anything on the calendar\"."
argument-hint: "[symbol] [session]"
---

# Premarket

Build the session plan before the first candle, so the trader is not deciding under pressure later.

## Data

Default symbol and session come from TRADING.md; otherwise ask once.

If a TradingView connector is available, use it: OHLCV for D1/H4/H1 for the last ~60 bars, and the economic calendar for today in the trader's time zone, filtered to high-impact events for the instrument's currencies (for XAUUSD: USD). If no connector, ask the trader to paste the levels and today's red-folder events; do not invent either.

## Output

Keep it to one screen.

```
<SYMBOL> — <date>, <session>

Bias (D1/H4):   <direction + the structure that says so>
Key levels:     <3–5 prices: HTF S/R, yesterday H/L, weekly open>
News windows:   <time – time (local): event> ... or "none"
No-trade zones: <ranges where SOP says stand aside, incl. news windows + buffer from TRADING.md>
Plan A:         <if price does X at level Y → SOP rule Z, direction>
Plan B:         <the opposite scenario>
Stand aside if: <the condition that means no trade today>
```

Rules: levels are prices, not adjectives. Every plan line names an SOP rule. If the calendar makes most of the session a no-trade zone, say so up front — that is the brief.
