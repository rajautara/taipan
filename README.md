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

Copy `TRADING.example.md` to your project root as `TRADING.md` and write in your own SOP and account rules. The plugin reads it at session start. Without it, the agent will ask for your rules before grading anything.

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
| `/trade-review` | Post-mortem graded against your SOP, not P&L. A–F, one thing to change. |

## What it will never do

Recommend widening a stop, averaging a loser, revenge trading, oversizing, or entering inside a restricted news window. It will tell you when you are about to.
