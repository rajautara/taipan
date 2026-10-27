---
name: bpb
description: "Breakout-Pullback scan: finds recent body-close breakouts of structure on H4 and M15, the retest zone each one left (broken level to breakout open, or the breakout's FVG), the pullback status (waiting / in pullback / resumed / failed), and the continuation entry once the pullback resumes. Use for /bpb, \"breakout pullback\", \"break and retest\", \"BPB\", \"retest\", \"continuation entry\", \"dah break, nak tunggu pullback\"."
argument-hint: "[symbol] [--m15]"
---

# Breakout-Pullback scan

A breakout is a **body close** past a Structure High/Low — the same MSB `btc.py` finds, so a wick past the level is never a breakout. The trade is not the break; it is the pullback into what the break left behind and the close that says the pullback is over.

## 1. Get the bars

Symbol from TRADING.md (else ask once). TradingView `get_ohlcv`, `format: "columns"`, to the scratchpad: `d1.json` (1D, 120) for bias, `h4.json` (4h, 120), and `m15.json` (15m, 300) when price is within 1 H4-ATR of an H4 retest zone or `--m15` was passed.

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bpb/bpb.py" h4.json --label H4
```

Output: `bias`, and `setups` (newest first; failed breakouts removed) each with `dir`, `level`, `kind` (continuation / reversal), `zone_top`, `zone_bottom`, `zone_src` (`fvg` = the breakout left a gap, the tighter zone; `level-open` = broken level to breakout candle open), `status`, `pullback_extreme`, `entry`, `sl`, `age`, `price_vs_zone`.

## 2. Read it

1. **Direction.** D1 bias. Only breakouts in the bias direction are trades. A `reversal` breakout against the D1 bias is information (the picture may be shifting), not an entry, unless TRADING.md says otherwise.
2. **Which breakout.** Prefer `kind: continuation`, `zone_src: fvg` (a gap means the break had force), and `age` small. A breakout older than ~15 bars with no pullback yet is weakening; say so.
3. **Status decides the verdict.**
   - `waiting` → WAIT. Alert at `zone_top` (short) / `zone_bottom` (long). Nothing to do.
   - `in_pullback` → WAIT for the close. The trigger is a body close back out of the zone in the breakout direction. Drop to M15 for a tighter trigger: run `bpb.py` on m15.json and look for the same `resumed` on the M15 structure inside the H4 zone.
   - `resumed` → candidate. Entry at the trigger close (or the zone edge on a limit retest, if TRADING.md allows), SL beyond `pullback_extreme`, TP at the next liquidity in the breakout direction.
   - `failed` → gone; `bpb.py` has already removed it. If the trader asks about it: the level was reclaimed by a body close, the breakout was false.
4. **RR.** (TP − entry) / (entry − SL) ≥ 2 or SKIP. A deep pullback makes the SL wide; if the maths does not work, the setup does not exist.

## 3. Apply the Taipan checklist

TRADING.md account constraints last; they override everything. Lot size from risk % and SL distance, one line of arithmetic.

## Reply format

Plain markdown, never a code block: the trader reads this on a phone at the screen. Short bold labels, one idea per line, prices in **bold**. Headings only if the reply has more than one section.

**<SYMBOL> — Breakout-Pullback, <date time local>**

- **Bias:** bull / bear
- **Breakouts** (newest first, max 3): <dir> body close past <level> on <date>, continuation/reversal, zone <bottom–top> (fvg / level-open), <status>, age <n>
- **Trigger:** resumed at <close> on <date> / waiting for close back above/below <edge> / price not in zone yet, alert <edge>

End with the verdict table:

| | |
|---|---|
| **Bias** | <one line> |
| **Setup** | <SOP rule / method + zone, or "none"> |
| **Risk** | entry <..> · SL <..> · TP <..> · RR <..> · lots <..> |
| **Invalidation** | <body close beyond ..> |
| **Verdict** | **TAKE / WAIT / NO TRADE** — <one reason> |

## Limits

Classic rules, not the trader's own pullback qualification (a NINJA-style multi-pattern pullback state machine would go in TRADING.md and override step 3). Breakout candles with body > 2.5 ATR are skipped as climaxes. The retest check uses only the nearest unbroken swing, as the method defines MSB.
