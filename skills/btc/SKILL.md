---
name: btc
description: "Behind the Candle (SMC) scan: finds the D1 bias, H4 POIs (FVG / Order Block / Breaker Zone) and the M15 Entry Model from live OHLCV, then runs the Taipan checklist on each candidate. Use for /btc, \"behind the candle\", \"scan for entries\", \"cari setup\", \"ada setup tak\", \"check BTC\", or any SMC setup question."
argument-hint: "[symbol] [--m15]"
---

# Behind the Candle scan

Code finds the structure. You judge it. Never eyeball candles from numbers — run `btc.py` and read its output.

Rule #1 of the method: **no body close past the level = no break. A wick is never a break.** `btc.py` enforces this; you enforce it in every sentence you write.

## 1. Get the bars

Symbol is `symbol` in `taipan.json`, in `EXCHANGE:TICKER` form so the feed matches the trader's broker (else ask once). TradingView `get_ohlcv`, `format: "columns"`. When the harness saves a tool result to a file, pass that file's path straight to the script; only write the JSON to the scratchpad yourself when it came back inline. The scripts drop the still-forming last candle on their own, so every "close" in the output is a real close.

Files:

| File | interval | count |
|------|----------|-------|
| `d1.json` | 1D | 120 |
| `h4.json` | 4h | 90 |
| `m15.json` | 15m | 200 — only when price is inside or within 1 H4-ATR of a fresh H4 POI, or the user passed `--m15` |

Then, for each file:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/btc/btc.py" d1.json --label D1
```

`--swing K` widens a Structure High/Low to K candles each side (default 1, the book's 3-candle pattern). Use it only when TRADING.md says so or `/backtest` has shown it is better on this instrument.

Output per timeframe: `bias` (direction of the last body-close MSB), `last_msb`, `raids`, `equal_highs` / `equal_lows` (unbroken structure points within 0.15 ATR of each other — liquidity pools, the book's EQH / EQL), and `pois` — each with `type` (FVG / OB / BZ), `dir`, `top`, `bottom`, `entry`, `sl`, `fresh`, `price_vs_zone`, `dist`. `sl` is already 0.1 ATR beyond the zone edge. An Order Block is the last opposite candle before the MSB that took the prior candle's liquidity and whose move away left an FVG. Timestamps are unix UTC; `read.py` prints them readable.

## 2. Read it in the book's order

1. **D1 — direction.** `bias` from d1.json. Bull → only look for buys. Bear → only sells. If `last_msb.kind` is `reversal` and happened in the last 3 bars, say the picture is *shifting*, not settled.
2. **H4 — POI.** Keep only POIs where `dir` matches D1 bias and `fresh` is true. Rank: BZ first (the method's premium POI), then OB, then FVG. Also list the liquidity targets: PDH/PDL and PWH/PWL from d1.json's last completed bars, and any unbroken `structure_highs`/`structure_lows` on H4 the price has not yet reached.
3. **M15 — Entry Model.** Only if price is inside a kept H4 POI. From m15.json: is there a `raid` whose `dir` matches the bias, with a BZ POI built on it, formed *after* price entered the H4 POI? That BZ is the Entry Model. Entry at `entry`, SL at `sl`.
4. **RR.** Target = nearest liquidity in bias direction. (target − entry) / (entry − sl) must be ≥ 2, or the setup is SKIP.

A candidate that fails any step is not "almost there". It is SKIP. Say which step.

## 3. Apply the Taipan checklist

Account constraints from TRADING.md (news windows, daily loss, max lots) are checked last and override everything. Every candidate then goes through `check.py` (lots, net RR, news, session, daily limits, open risk): a BLOCK is NO TRADE.

## Reply format

Plain markdown, never a code block: the trader reads this on a phone at the screen. Short bold labels, one idea per line, prices in **bold**. Headings only if the reply has more than one section.

**<SYMBOL> — Behind the Candle, <date time local>**

- **D1 bias:** bull / bear / shifting — last MSB <dir>, body close <level>, <date>
- **H4 POIs** (ranked, max 3): <type dir bottom–top>, fresh, price above/below/inside, <dist> away
- **Liquidity:** PDH/PDL <..>, PWH/PWL <..>, next unbroken H4 swing <..>
- **M15:** Entry Model found — BZ <dir> <bottom–top> / none — price not in POI / none — no valid raid yet

WAIT always names the alert price (POI boundary) and the confirmation to watch. Never predict when it forms.

End with the verdict table:

| | |
|---|---|
| **Bias** | <one line> |
| **Setup** | <SOP rule / method + zone, or "none"> |
| **Risk** | entry <..> · SL <..> · TP <..> · RR <..> · lots <..> |
| **Invalidation** | <body close beyond ..> |
| **Verdict** | **TAKE / WAIT / NO TRADE** — <one reason> |

## Limits

`btc.py` does not model the book's body-sweep exception for Liquidity Raids, and uses body > 2.5×ATR as the "very big body" skip. The OB's "leaves an FVG" test is this plugin's reading of the book's imbalance rule. Asia range comes from `read.py`, not from this script. Say so if a setup hinges on one of these.
