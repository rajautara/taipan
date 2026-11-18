# Taipan

Makes your AI agent think like the senior trader in the room.

*Taipan* (Malay, from Cantonese 大班): the most senior figure in the house — the one who has seen every cycle and still has an account.

Not a bot, not a calculator, not a strategy. A mentor that is on for the whole session: it reads the market with you top-down, points at the best entry your own method allows, teaches the read in passing — and still says "no trade" when that is the answer. Capital first, process over outcome, no call without an invalidation.

## Install

Claude Code:

```
/plugin marketplace add rajautara/taipan
/plugin install taipan@taipan
```

Local, before publishing:

```
claude --plugin-dir ./taipan
```

Cowork: zip the folder and drop it into the plugin install dialog.

## Setup

Two files in your project root:

- `taipan.json` (copy `taipan.example.json`): the numbers. Balance, risk %, contract size, spread, daily loss limit, max trades, sessions, news window. The scripts read it directly.
- `TRADING.md` (copy `TRADING.example.md`): the words. Your SOP rules and trade management.

The plugin reads both at session start. Without them, the agent asks for your rules before grading or sizing anything.

Needs Python 3.9+ on the path. Market data and the economic calendar come from a TradingView connector; without one, Taipan asks you for levels and events instead of inventing them.

Nothing here is financial advice or a promise of profit. Run `/backtest` on your own instrument before you trust any setup type with money.

## What you get

| Skill | Use |
|-------|-----|
| `/taipan` | Always-on mentor mindset. Every trade question is worked through Context → Setup → Risk → Invalidation → Constraints and ends with a TAKE / WAIT / NO TRADE verdict. Levels: `coach` (default, one line of why per step), `desk` (verdict only), `strict` (refuses anything outside your SOP). |
| `/read` | The full mentor read: structure D1 → H4 → M15, where price is being drawn, every live zone from all methods ranked by confluence, the single best entry with entry / SL / TP / RR, what to wait for, what breaks it. |
| `/premarket` | Session plan: bias, levels, news windows, Plan A / Plan B, stand-aside condition. Uses a TradingView connector when one is available. |
| `/btc` | Behind the Candle (SMC) scan. `btc.py` finds D1 bias, H4 POIs (FVG / OB / Breaker Zone) and the M15 Entry Model from live OHLCV — body close only, wicks are never breaks — then every candidate goes through the Taipan checklist. |
| `/snd` | Supply & Demand scan. `snd.py` finds fresh RBR / DBR demand and RBD / DBD supply zones on D1 and H4, ranks them by departure and freshness, confirms on M15 with a body-close MSB, then the Taipan checklist. |
| `/bpb` | Breakout-Pullback scan. `bpb.py` takes the body-close breakouts `btc.py` finds, maps the retest zone each one left (its FVG or level-to-open), tracks the pullback (waiting / in pullback / resumed / failed) and gives the continuation entry with SL beyond the pullback extreme. |
| `/qm` | Quasimodo scan. `qm.py` finds left shoulder → head that sweeps it → body close under/over the neckline, gives the QML entry level with SL beyond the head and TP at L1, and tracks waiting / at QML / failed. |
| `/manage` | You are already in the trade. Where it stands in R, whether the idea is still valid, and what your own management rules say to do now: hold, breakeven, partial, close before news. Never widens a stop. |
| `/trade-review` | Post-mortem graded against your SOP, not P&L. A–F, one thing to change. Every reviewed trade is logged to `journal.csv`. |
| `/backtest` | Walk-forward replay on real history: the full SOP (D1 bias → H4 zone → lower-timeframe confirmation) per rule, with and without the confirmation step, and the raw zones on a single timeframe. Trades, win rate, expectancy in R, drawdown. |

## The parts that are code, not judgment

| Script | What it settles |
|--------|-----------------|
| `skills/taipan/check.py` | The gate. One run sizes the entry and checks it against every limit in `taipan.json`: stop present and not too tight, reward-to-risk after costs, news window, session, trades today, losing streak, open positions, and the daily loss limit counting the risk of trades still on. PASS or BLOCK with reasons, plus the rule's backtest record. |
| `skills/taipan/plan.py` | `plan.json`: the trades that are on. Keeps the original stop, refuses to widen it, and logs R and P&L to the journal on close. |
| `skills/taipan/now.py` | Local time, open sessions, market closed, and whether you are inside a news window. |
| `skills/taipan/size.py` | Lot size from balance, risk %, stop distance, spread and commission; reward-to-risk after costs. |
| `skills/taipan/journal.py` | `journal.csv`: trades today, P&L today, losing streak, last-20 expectancy. |
| `skills/read/read.py` | All four detectors on D1 / H4 / M15 in one run, PDH/PDL, PWH/PWL, Asia range, and zones ranked by confluence. |
| `skills/backtest/backtest.py`, `sop.py` | The replays behind `/backtest`: one timeframe, and the full multi-timeframe SOP. |

Every detector works on closed candles only and puts the stop 0.1 ATR beyond the zone. An exit is never gated. `TAIPAN_NOW=<ISO time>` in front of any script reproduces a past run. `python3 tests/test_all.py` runs every self-check plus mirror-symmetry and stop-sanity tests.

## What it will never do

Recommend widening a stop, averaging a loser, revenge trading, oversizing, or entering inside a restricted news window. It will tell you when you are about to.
