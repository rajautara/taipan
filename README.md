# Taipan

Makes your AI agent think like the senior trader in the room.

*Taipan* (Malay, from Cantonese 大班): the most senior figure in the house — the one who has seen every cycle and still has an account.

Not a bot, not a calculator, not a strategy. A way of thinking that is on for the whole session: capital first, process over outcome, no call without an invalidation, and "no trade" as a valid answer. The same idea as ponytail for coding — applied to the chart.

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
| `/taipan` | Always-on mindset. Every trade question is worked through Context → Setup → Risk → Invalidation → Constraints and ends with a TAKE / WAIT / NO TRADE verdict. Levels: `desk` (default), `coach` (explains why), `strict` (refuses anything outside your SOP). |
| `/premarket` | Session plan: bias, levels, news windows, Plan A / Plan B, stand-aside condition. Uses a TradingView connector when one is available. |
| `/trade-review` | Post-mortem graded against your SOP, not P&L. A–F, one thing to change. |

## What it will never do

Recommend widening a stop, averaging a loser, revenge trading, oversizing, or entering inside a restricted news window. It will tell you when you are about to.
