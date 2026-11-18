---
name: qm
description: "Quasimodo (QM) scan: finds QM reversal setups on H4 and M15 — left shoulder, head that sweeps it, body close under/over the neckline — and the QML entry level with SL beyond the head. Use for /qm, \"quasimodo\", \"QM\", \"QML\", \"over and under\", \"ada QM tak\", \"QM level\"."
argument-hint: "[symbol] [--m15]"
---

# Quasimodo scan

QM is head-and-shoulders with rules instead of a shape. Bearish: a Structure High (LS), a Structure Low (L1), a **higher** high (HEAD — the sweep of LS), then a **body close below L1** (the "under"). The QML is the LS high; the trade is the return to it. Bullish is the mirror. A wick below L1 is not an "under"; `qm.py` only accepts a body close.

## 1. Get the bars

Symbol is `symbol` in `taipan.json`, in `EXCHANGE:TICKER` form so the feed matches the trader's broker (else ask once). TradingView `get_ohlcv`, `format: "columns"`. When the harness saves a tool result to a file, pass that file's path straight to the script; only write the JSON to the scratchpad yourself when it came back inline. The scripts drop the still-forming last candle on their own, so every "close" in the output is a real close.

Files: `d1.json` (1D, 120) for bias, `h4.json` (4h, 120), `m15.json` (15m, 300) when price is within 1 H4-ATR of a QML or `--m15` was passed.

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/qm/qm.py" h4.json --label H4
```

Output: `bias`, `setups` (newest first; failed and expired ones removed) with `dir`, `qml`, `head`, `l1`, `under_i`, `t` (time of the under), `status` (`waiting` = price has not returned to the QML, `at_qml` = it has), `entry` (= QML), `sl` (0.1 ATR beyond the HEAD), `tp` (= L1), `rr`, `age`, `price_vs_qml`, `dist`.

## 2. Read it

1. **Direction.** QM is a *reversal* pattern, so a QM against the D1 bias is normal — that is what it is for. But it must agree with the HTF *context*: a bearish QM is a trade when D1 is bearish or shifting (D1 `last_msb` reversal), or when the H4 QM forms at a D1 supply / POI. A bearish QM in a clean D1 uptrend with no HTF reason is counter-trend: list it, no entry, unless TRADING.md allows it.
2. **Which QM.** Prefer `age` small, `rr` ≥ 2 to L1, and a head that swept a real liquidity pool (an `equal_highs` / `equal_lows` price from `btc.py`, or PDH / PWH) — a head that swept nothing is a weak QM.
3. **Status decides the verdict.**
   - `waiting` → WAIT. Alert at the QML. Do not chase the move away from it.
   - `at_qml` → confirmation needed before entry: on M15, a body-close MSB in the QM direction after the touch (run `btc.py` on m15.json), or the LTF confirmation TRADING.md names. Limit orders at the QML without confirmation only if TRADING.md allows it.
   - `failed` → removed. A body close beyond the head cancels the QM.
   - `expired` → removed. Price returned to the QML and has since run 1R from it, or 10 bars have passed: the entry window is closed.

   A QM whose QML-to-head distance is under 0.3 ATR or over 3 ATR is never listed: the first is noise, the second is not a stop anyone should trade.
4. **RR.** TP at L1 is the conservative target; the next liquidity beyond it is the extended one. (TP − entry) / (SL − entry) ≥ 2 or SKIP. `rr` in the output is the L1 version.

## 3. Apply the Taipan checklist

TRADING.md account constraints last; they override everything. Every candidate then goes through `check.py` (lots, net RR, news, session, daily limits, open risk): a BLOCK is NO TRADE.

## Reply format

Plain markdown, never a code block: the trader reads this on a phone at the screen. Short bold labels, one idea per line, prices in **bold**. Headings only if the reply has more than one section.

**<SYMBOL> — Quasimodo, <date time local>**

- **Bias:** bull / bear / shifting
- **QMs** (newest first, max 3): <dir> QML <..> · head <..> · L1 <..> · under <date> · waiting/at_qml · RR <..> · age <n>
- **Context:** <HTF reason this reversal is allowed, or "counter-trend, no entry">
- **Trigger:** at QML, waiting M15 close / price <dist> away, alert <qml>

End with the verdict table:

| | |
|---|---|
| **Bias** | <one line> |
| **Setup** | <SOP rule / method + zone, or "none"> |
| **Risk** | entry <..> · SL <..> · TP <..> · RR <..> · lots <..> |
| **Invalidation** | <body close beyond ..> |
| **Verdict** | **TAKE / WAIT / NO TRADE** — <one reason> |

## Limits

Pivots come from 3-candle structure points collapsed to alternate H/L; large QMs built on bigger swings may be fragmented into smaller ones — compare with the chart when in doubt. The head must be a structure point, not merely a wick. No "maximum pain level" (MPL) entry variant; TRADING.md can define one.
