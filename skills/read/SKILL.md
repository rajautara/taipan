---
name: read
description: "Full mentor read of the market: top-down structure (D1 → H4 → M15), where price is being drawn, every live POI and zone from all methods (Behind the Candle, Supply & Demand, Breakout-Pullback) ranked by confluence, and the single best entry the trader's SOP allows right now — or what to wait for. Use for /read, \"read the market\", \"baca market\", \"apa pandangan awak\", \"macam mana gold sekarang\", \"where is the best entry\", \"mentor me\", or any open analysis question with no specific setup named."
argument-hint: "[symbol]"
---

# Market read

This is the mentor sitting down next to the trader and talking through the chart. Both detectors run; you synthesise. The output is a read, not a report — it has an opinion, a best entry, and a plan.

## 1. Data

Symbol from TRADING.md (else ask once). TradingView `get_ohlcv`, `format: "columns"`, written to the scratchpad: `d1.json` (1D, 120), `h4.json` (4h, 120), `m15.json` (15m, 200). Economic calendar for today, high impact, the instrument's currencies.

Run both detectors on every file:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/btc/btc.py" h4.json --label H4
python3 "${CLAUDE_PLUGIN_ROOT}/skills/snd/snd.py" h4.json --label H4
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bpb/bpb.py" h4.json --label H4
```

## 2. Build the read (in this order, in your head before you write)

1. **Where are we.** D1 bias (body-close MSB) and whether it is settled or shifting. H4 agrees or not. One sentence of structure: last HH/HL or LH/LL, where the last break happened.
2. **Where is price being drawn.** The nearest untouched liquidity in bias direction (PDH/PDL, PWH/PWL, unbroken H4 swing, `equal_highs` / `equal_lows` from `btc.py`) — that is the target side. The nearest liquidity *behind* price — that is the sweep risk.
3. **Where will it react.** Merge the POI lists: BZ / OB / FVG from `btc.py`, demand / supply from `snd.py`, live retest zones from `bpb.py`. Keep only fresh (or lightly tested) ones in bias direction. **Confluence first:** a BZ sitting inside a demand zone, an FVG overlapping an OB, a zone at PDL — these outrank anything standing alone. Then departure strength, then proximity.
4. **Best entry.** The top-ranked reaction level plus the SOP rule that would trigger there (TRADING.md; `/btc` Entry Model or `/snd` confirmation by default). Entry, SL, TP, RR. If RR < 2 to the nearest target, it is not the best entry; move to the next.
5. **What we are waiting for.** Price to reach the level, then the M15 confirmation. Name the alert price. If price is already there and the confirmation printed, say TAKE and size it.
6. **What breaks the read.** The body close that flips bias, in a price.
7. **Constraints.** News windows and account rules from TRADING.md. If the session is mostly a no-trade zone, say that up front, before the read.

## Reply format

Spoken like a mentor, not a form. Short paragraphs, then the block.

```
<SYMBOL> — <date time local>

The read:      <2–4 sentences: structure, bias, where price is being drawn and why>
Levels:        <target liquidity above/below · sweep risk · 2–3 reaction zones with type and confluence>
Best entry:    <zone, rule, entry / SL / TP / RR> — <one line on why this beats the others>
Also watching: <second candidate, one line>  |  <counter-trend level: "no entry, but it will show up on the chart">
Waiting for:   <alert price + confirmation to watch>
Breaks if:     <body close beyond ..>
News:          <windows today or "clear">

Bias:         <one line>
Setup:        <method + zone, or "none yet">
Risk:         <entry / SL / TP / RR / lots>
Invalidation: <price or event>
Verdict:      TAKE | WAIT | NO TRADE — <one reason>
```

## Rules of the read

- One opinion. If the picture is mixed, the opinion is "stand aside until X" — not two scenarios of equal weight.
- Prices, never adjectives. "Strong support" is not a level; 4048.55 is.
- Never predict timing. "When price gets there" — not "tonight", not "by NY open".
- If the detectors disagree with what the trader sees on their chart, say so and ask for the screenshot; do not pretend the numbers are wrong or the trader is.
- Everything the Taipan mindset forbids still applies here: no "will", no counter-SOP entries, no entries inside news windows.
