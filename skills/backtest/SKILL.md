---
name: backtest
description: "Walk-forward replay of the Taipan detectors on real history: trades, win rate, expectancy in R and drawdown per method, so thresholds are chosen from data and no win rate is ever quoted from memory. Use for /backtest, \"backtest\", \"does this work\", \"what's the win rate\", \"ada edge tak\", \"test the strategy\", \"which swing setting\"."
argument-hint: "[symbol] [sop | timeframe] [--method bpb|qm|snd|btc] [--swing K] [--rr N] [--bias]"
---

# Backtest

Two replays. `backtest.py` answers: on one timeframe, do the raw zones make money before any confirmation is added. `sop.py` answers the question that matters: does the full SOP (D1 bias → H4 zone → lower-timeframe confirmation) make money. Start with `sop.py` unless the trader asks about a single timeframe.

## 1. Data

One TradingView `get_ohlcv` call, `format: "columns"`, `count: 3000` or more, symbol exactly as in TRADING.md. A result this size is saved to a file by the harness; pass that path. Intraday history is limited by the feed, so M15 covers weeks, H4 covers years.

## 2. Run

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/backtest/backtest.py" <file> --spread <typical spread from TRADING.md> [--method all] [--swing 1] [--rr 2] [--bias] [--window 300]
```

Takes about a minute per method on 3000 bars. Per method: `trades`, `win_rate`, `breakeven_win_rate` (what `--rr` needs just to break even), `expectancy_r` (average result per trade in R, after spread), `total_r`, `max_drawdown_r`.

How it trades: at each bar the detector sees only candles that had closed by then. `bpb` enters at the resume close; `qm` at a limit on the QML; `snd` and `btc` at a limit on the proximal edge of a zone that was fresh the bar before (`btc` uses BZ and OB only). Stop is the detector's `sl`, target is `--rr` × risk. A bar that touches both stop and target is counted as a loss. `--bias` keeps only trades in the direction of the same timeframe's last MSB.

## Full SOP replay

Three fetches, `format: "columns"`, `count: 8000` each: 1D, 4h, and the entry timeframe (15m). Then:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/backtest/sop.py" --d1 <file> --h4 <file> --ltf <file> --spread <..> [--rr 2] [--no-confirm] [--sessions "London,New York"]
```

Per rule (`btc`, `snd`, `bpb`, `qm`) and `all`: the same statistics as above. What each rule does is in the script's header. Always run it twice, with and without `--no-confirm`: the second enters the same zones at the edge on first touch, so the difference between the two is what the lower-timeframe confirmation is worth.

Two limits decide how far the answer can be trusted:

- **The feed holds about 6900 intraday bars per interval.** On 15m that is roughly 3.5 months and a few dozen trades: not enough to conclude anything. Run `--ltf` on a 1h file as well (about 10 months) and say plainly that it is a stand-in for M15, not the SOP itself.
- **Rule 3 does not use the lower timeframe**, so it can be tested on years: pass the 4h file as `--ltf` with `--no-confirm` and read the `bpb` line. On that run the other three lines mean "D1 bias + H4 zone, entry at the edge, no confirmation".

Not modelled: news windows, daily limits, "TP at nearest liquidity" (a fixed RR is used), D1 zones for rule 2, the "D1 shifting" exception for rule 4. Rules are scored independently.

Check a positive result two more ways before calling it an edge: split it by year, and by direction. A method that only makes money long in a market that went up has shown that the market went up.

## 3. Read it like a trader, not a salesman

- **Under about 100 trades the number is noise.** Say so. A method showing +0.15R on 60 trades has shown nothing yet.
- **Expectancy, not win rate.** 35% winners at 1:2 is a small profit; 45% winners at 1:1 is a loss.
- **Drawdown in R × risk % = the pain.** 20R at 0.5% risk is a 10% account drawdown. Hold that against the daily and total loss limits in TRADING.md.
- **Comparing settings is curve fitting.** If `--swing 2` beats `--swing 1` on one history, that is a hypothesis. It becomes a rule only if it also holds on a second instrument or an earlier period (`date_to` on the fetch) the choice was not made on.
- **This is the floor, not the SOP.** One timeframe: no D1 bias, no M15 confirmation, no news or session filter, every signal taken. A rule in TRADING.md is supposed to beat this floor; if the floor is negative, the confirmation is carrying the whole edge and that is worth saying.

## Reply format

Plain markdown, never a code block.

**<SYMBOL> <TF> — <n> bars, <from>–<to>, RR <x>, spread <y>**

One line per method: trades · win % (needs <breakeven> %) · expectancy <±x.xx>R · max drawdown <n>R · verdict: **edge / flat / negative / too few trades**.

Then two lines: what this says about the trader's SOP rules, and the one setting worth testing next. Never "this strategy works".
