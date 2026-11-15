---
name: manage
description: "In-trade management: the trader is already in a position and asks what to do — hold, move to breakeven, take a partial, trail, or close before news. Use for /manage, \"I'm in a trade\", \"dah masuk\", \"should I close\", \"move SL to BE\", \"nak hold ke\", \"take partial\", \"trail stop\"."
argument-hint: "[entry] [sl] [tp] [current price]"
---

# Manage an open trade

The decision to enter is over. This skill only answers: what does the SOP say to do with the position now. It never produces a new entry and never re-argues the old one.

## Input

Ask only for what is missing: direction, entry, current stop, target, lots, and the SOP rule the trade was taken on. Current price from TradingView `get_symbol_data` when a connector is available, else from the trader.

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/taipan/now.py" --tz <zone> --events <today's high-impact release times, ISO UTC> --before <min> --after <min>
```

## Work out, in this order

1. **Where the trade stands in R.** (price − entry) / (entry − original stop) for a long, mirrored for a short. One number.
2. **Is the idea still valid.** The invalidation named at entry: has a candle *closed* beyond it? If yes, the SOP exit is now, wherever the stop sits. A wick is not a close.
3. **What the Trade management section of TRADING.md says at this R.** Breakeven trigger, partial, trail, time stop. Apply exactly that. If TRADING.md has no management section, say so, apply nothing by invention, and tell the trader the only two SOP outcomes are stop or target; offer to add a management rule to TRADING.md *after* this trade, not during it.
4. **News.** `now.py`: if a restricted window starts before the trade can reasonably reach target, apply the SOP's pre-news rule (close, reduce, or hold with stop at breakeven). `minutes_to_window` is the number to quote.
5. **Session and weekend.** `market` and `sessions` from `now.py`: a position running into the Friday close gets the SOP's weekend rule.

## Never

- Move the stop further from entry. Not for news, not for "room", not once.
- Add to a losing position, or re-enter the same idea after the stop.
- Take the target away because the move "looks strong". Trailing is only what TRADING.md defines.
- Close a trade that is inside its plan because of the last candle's colour. Say that it is noise and what price would actually change the plan.

## Reply format

Plain markdown, never a code block. One screen.

**<SYMBOL> <long/short> — at <x.x>R**

- **Idea:** valid / invalidated by the close at **<price>**
- **SOP says:** <the management rule that applies now, quoted by name, or "nothing yet">
- **Do:** HOLD / MOVE STOP TO **<price>** / CLOSE **<fraction>** / CLOSE ALL — <one reason>
- **Next decision at:** **<price>** (<what happens there>) · **News:** <window, minutes away, or "clear">

When the trade is closed, log it with `journal.py add` and offer `/trade-review`.
