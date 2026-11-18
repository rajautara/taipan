---
name: read
description: "Full mentor read of the market: top-down structure (D1 → H4 → M15), where price is being drawn, every live POI and zone from all methods (Behind the Candle, Supply & Demand, Breakout-Pullback, Quasimodo) ranked by confluence, and the single best entry the trader's SOP allows right now — or what to wait for. Use for /read, \"read the market\", \"baca market\", \"apa pandangan awak\", \"macam mana gold sekarang\", \"where is the best entry\", \"mentor me\", or any open analysis question with no specific setup named."
argument-hint: "[symbol]"
---

# Market read

This is the mentor sitting down next to the trader and talking through the chart. One script runs every detector and does the bookkeeping; you synthesise. The output is a read, not a report — it has an opinion, a best entry, and a plan.

## 1. Data

Symbol is `symbol` in `taipan.json`, in `EXCHANGE:TICKER` form so the feed matches the trader's broker (else ask once). Three TradingView `get_ohlcv` calls, `format: "columns"`: 1D (120 bars), 4h (120), 15m (300). When the harness saves a tool result to a file, pass that path straight to the script; only write the JSON to the scratchpad yourself when it came back inline. Then:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/read/read.py" --d1 <file> --h4 <file> --m15 <file>
python3 "${CLAUDE_PLUGIN_ROOT}/skills/taipan/now.py" --events <today's high-impact release times, ISO UTC>
```

`read.py` prints one compact JSON:

- `price`, `atr`, `last_closed_bar_utc` — the still-forming candle is already dropped on every timeframe.
- `bias` per timeframe: direction of the last body-close MSB, its level, time and `bars_ago`.
- `levels`: `PDH` / `PDL`, `PWH` / `PWL`, `AsiaH` / `AsiaL` (00:00–07:00 UTC; `asia_range_complete: false` means the range is still forming), and H4 equal highs / lows. Use these numbers; do not read levels off the bars yourself.
- `zones`: every live zone within 6 H4-ATR of price from all four methods (BZ / OB / FVG, demand / supply, breakout retest zones, QMLs), each with `entry`, `sl`, `status`, `dist`, and `with` — the other zones and key levels that sit in the same place. Sorted by confluence, then distance.
- `setups`: the raw `bpb` and `qm` setups on H4 and M15. `m15_entry_model`: fresh M15 Breaker Zones.

Run a single detector by hand only when you need a field `read.py` leaves out.

## 2. Build the read (in this order, in your head before you write)

1. **Where are we.** D1 bias (body-close MSB) and whether it is settled or shifting. H4 agrees or not. One sentence of structure: last HH/HL or LH/LL, where the last break happened.
2. **Where is price being drawn.** The nearest untouched liquidity in bias direction (PDH/PDL, PWH/PWL, unbroken H4 swing, `equal_highs` / `equal_lows` from `btc.py`) — that is the target side. The nearest liquidity *behind* price — that is the sweep risk.
3. **Where will it react.** Take `zones` in the order given. QMLs are reversal candidates: list them even against bias, entry only with an HTF reason. Keep only fresh (or lightly tested) zones in bias direction. **Confluence first** (the `with` list): a BZ sitting inside a demand zone, an FVG overlapping an OB, a zone at PDL — these outrank anything standing alone. Then departure strength, then proximity.
4. **Best entry.** The top-ranked reaction level plus the SOP rule that would trigger there (TRADING.md; `/btc` Entry Model or `/snd` confirmation by default). Entry, SL (the zone's `sl`), TP, then `check.py` for lots, `rr_net` and the gate. If it blocks on reward-to-risk to the nearest target, it is not the best entry; move to the next.
5. **What we are waiting for.** Price to reach the level, then the M15 confirmation. Name the alert price. If price is already there and the confirmation printed, say TAKE and size it.
6. **What breaks the read.** The body close that flips bias, in a price.
7. **Constraints.** `now.py` for the news windows; `check.py` has already applied the limits in `taipan.json`; anything else from TRADING.md. If the session is mostly a no-trade zone, say that up front, before the read.

## Reply format

Plain markdown, never a code block: the trader reads this on a phone at the screen. Short bold labels, one idea per line, prices in **bold**. Headings only if the reply has more than one section.

Spoken like a mentor, in short paragraphs — not a form, not a table of everything.

**<SYMBOL> — <date time local>**

**The read.** Two to four sentences: structure, bias, where price is being drawn and why.

**Levels.** Target liquidity above/below · sweep risk · then the reaction zones as a short numbered list, each one line: price range, type, and the confluence that puts it there.

**Best entry.** Zone, rule, entry / SL / TP / RR in **bold** — and one line on why it beats the others.

**Also watching.** Second candidate in one line. Counter-trend level in one line: "no entry, but it will show up on the chart."

**Waiting for.** Alert price + the confirmation to watch. **Breaks if:** the body close that flips the read. **News:** windows today, or "clear".

End with the verdict table:

| | |
|---|---|
| **Bias** | <one line> |
| **Setup** | <SOP rule / method + zone, or "none"> |
| **Risk** | entry <..> · SL <..> · TP <..> · RR <..> · lots <..> |
| **Invalidation** | <body close beyond ..> |
| **Verdict** | **TAKE / WAIT / NO TRADE** — <one reason> |

## Rules of the read

- One opinion. If the picture is mixed, the opinion is "stand aside until X" — not two scenarios of equal weight.
- Prices, never adjectives. "Strong support" is not a level; 4048.55 is.
- Never predict timing. "When price gets there" — not "tonight", not "by NY open".
- If the detectors disagree with what the trader sees on their chart, say so and ask for the screenshot; do not pretend the numbers are wrong or the trader is.
- Everything the Taipan mindset forbids still applies here: no "will", no counter-SOP entries, no entries inside news windows.
