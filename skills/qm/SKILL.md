---
name: qm
description: "Quasimodo (QM) scan: finds QM reversal setups on H4 and M15 — left shoulder, head that sweeps it, body close under/over the neckline — and the QML entry level with SL beyond the head. Use for /qm, \"quasimodo\", \"QM\", \"QML\", \"over and under\", \"ada QM tak\", \"QM level\"."
argument-hint: "[symbol] [--m15]"
---

# Quasimodo scan

QM is head-and-shoulders with rules instead of a shape. Bearish: a Structure High (LS), a Structure Low (L1), a **higher** high (HEAD — the sweep of LS), then a **body close below L1** (the "under"). The QML is the LS high; the trade is the return to it. Bullish is the mirror. A wick below L1 is not an "under"; `qm.py` only accepts a body close.

## 1. Get the bars

Symbol from TRADING.md (else ask once). TradingView `get_ohlcv`, `format: "columns"`, to the scratchpad: `d1.json` (1D, 120) for bias, `h4.json` (4h, 120), `m15.json` (15m, 300) when price is within 1 H4-ATR of a QML or `--m15` was passed.

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/qm/qm.py" h4.json --label H4
```

Output: `bias`, `setups` (newest first; failed ones removed) with `dir`, `qml`, `head`, `l1`, `under_i`, `t` (time of the under), `status` (`waiting` = price has not returned to the QML, `at_qml` = it has), `entry` (= QML), `sl` (= HEAD), `tp` (= L1), `rr`, `age`, `price_vs_qml`, `dist`.

## 2. Read it

1. **Direction.** QM is a *reversal* pattern, so a QM against the D1 bias is normal — that is what it is for. But it must agree with the HTF *context*: a bearish QM is a trade when D1 is bearish or shifting (D1 `last_msb` reversal), or when the H4 QM forms at a D1 supply / POI. A bearish QM in a clean D1 uptrend with no HTF reason is counter-trend: list it, no entry, unless TRADING.md allows it.
2. **Which QM.** Prefer `age` small, `rr` ≥ 2 to L1, and a head that swept a real liquidity pool (an `equal_highs` / `equal_lows` price from `btc.py`, or PDH / PWH) — a head that swept nothing is a weak QM.
3. **Status decides the verdict.**
   - `waiting` → WAIT. Alert at the QML. Do not chase the move away from it.
   - `at_qml` → confirmation needed before entry: on M15, a body-close MSB in the QM direction after the touch (run `btc.py` on m15.json), or the LTF confirmation TRADING.md names. Limit orders at the QML without confirmation only if TRADING.md allows it.
   - `failed` → removed. A body close beyond the head cancels the QM.
4. **RR.** TP at L1 is the conservative target; the next liquidity beyond it is the extended one. (TP − entry) / (SL − entry) ≥ 2 or SKIP. `rr` in the output is the L1 version.

## 3. Apply the Taipan checklist

TRADING.md account constraints last; they override everything. Lot size from risk % and SL distance (QML to head), one line of arithmetic.

## Reply format

```
<SYMBOL> — Quasimodo, <date time local>

Bias:      <bull|bear|shifting>
QMs:       <dir> QML <..> · head <..> · L1 <..> · under on <date> · <waiting|at_qml> · RR <..> · age <n>
           ...  (max 3, newest first)
Context:   <HTF reason this reversal is allowed, or "counter-trend, no entry">
Trigger:   <at QML, waiting M15 close | price <dist> away, alert <qml>>

Bias:         <one line>
Setup:        QM — <H4|M15> <dir> QML <..>
Risk:         entry <..> / SL <..> / TP <..> / RR <..> / lots <..>
Invalidation: <body close beyond head <..>>
Verdict:      TAKE | WAIT | NO TRADE — <reason>
```

## Limits

Pivots come from 3-candle structure points collapsed to alternate H/L; large QMs built on bigger swings may be fragmented into smaller ones — compare with the chart when in doubt. The head must be a structure point, not merely a wick. No "maximum pain level" (MPL) entry variant; TRADING.md can define one.
