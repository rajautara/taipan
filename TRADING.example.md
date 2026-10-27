# TRADING.md — the trader's own rules

Copy this file to the root of your project as `TRADING.md` and fill it in.
Taipan reads it at session start; every grade, size and verdict is measured against it.

## Instrument & schedule
- Symbol: XAUUSD
- Sessions traded: London open, New York open (local time: Asia/Kuala_Lumpur)
- Timeframes: bias D1/H4, setup H1, entry M5

## Account constraints (hard rules — a setup that breaks one is NO TRADE)
- Risk per trade: 0.5% of balance
- Daily loss limit: 2% — stop trading for the day when hit
- Max open positions: 1
- Max trades per day: 3
- News: no entries from 15 min before to 15 min after high-impact USD releases; no closing trades within 15 min after a release (prop-firm rule)
- Stop loss: mandatory on every order, never widened after entry

## SOP (the only setups that exist)
Name each rule. The plugin will refer to them by name.

- **Rule 1 — HTF zone + M5 confirmation**: price taps a marked H4 supply/demand zone in the direction of D1 bias; enter on M5 BOS back in bias direction; SL beyond the zone; TP at next H4 level, minimum 1:2.
- **Rule 2 — ...**

## Stand-aside conditions
- D1 and H4 bias disagree
- Consecutive losses today: 2
- Any restricted news window
