---
name: snd
description: "Supply & Demand scan: finds fresh RBR / DBR demand and RBD / DBD supply zones on D1 and H4 from live OHLCV, ranks them by departure strength and freshness, checks the LTF confirmation, then runs the Taipan checklist. Use for /snd, \"supply and demand\", \"S&D\", \"snd\", \"demand zone\", \"supply zone\", \"ada zone tak\", \"scan zone\"."
argument-hint: "[symbol] [--m15]"
---

# Supply & Demand scan

Code finds the zones. You judge them. Never mark zones by eye from numbers — run `snd.py` and read its output.

A zone is a **base** (1–5 candles, each no wider than half the leg-out candle) left by an **impulse** (range ≥ 1.5 ATR, body ≥ 60% of range). Pattern letters: leg-in + B + leg-out. **RBR / DBR = demand. RBD / DBD = supply.** Proximal = the edge nearest price (entry); distal = the far edge (stop).

## 1. Get the bars

Symbol defaults to the one in TRADING.md (else ask once). TradingView `get_ohlcv`, `format: "columns"`, written to files in the scratchpad:

| File | interval | count |
|------|----------|-------|
| `d1.json` | 1D | 120 |
| `h4.json` | 4h | 120 |
| `m15.json` | 15m | 200 — only when price is inside or within 1 H4-ATR of a kept zone, or the user passed `--m15` |

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/snd/snd.py" h4.json --label H4
```

Output: `demand` and `supply` lists (broken zones already removed), each with `pattern`, `bottom`, `top`, `proximal`, `distal`, `entry`, `sl`, `base_len`, `departure_atr`, `status` (fresh / tested), `price_vs_zone`, `dist`, `score`. Lists are sorted by score; score is for ranking only, never quote it as a probability.

## 2. Read it

1. **Direction.** D1 bias from `btc.py` on d1.json (body-close MSB), or from TRADING.md's own bias rule if it names one. Bull → demand zones only. Bear → supply zones only. Zones against the bias are listed as *counter-trend, no entry*.
2. **Zones.** Keep the top 3 in bias direction. Prefer: fresh over tested, D1 over H4 when they overlap, strong departure (≥ 2 ATR) over weak, short base over long. A tested zone is weaker; say so. A zone price has already traded through with a body close is gone — `snd.py` has removed it.
3. **Confirmation.** Only if price is inside a kept zone. Run `btc.py` on m15.json: a body-close MSB in the zone's direction, formed after price entered the zone, is the confirmation. If TRADING.md names its own confirmation (an H1 engulfing close, an M5 BOS), use that instead and say which rule you applied. No confirmation → WAIT.
4. **RR.** Entry at the proximal edge, SL beyond the distal edge, target = nearest opposing zone or liquidity. (target − entry) / (entry − sl) ≥ 2 or SKIP.

## 3. Apply the Taipan checklist

TRADING.md account constraints last; they override everything. Lot size from risk % and SL distance, one line of arithmetic.

## Reply format

```
<SYMBOL> — Supply & Demand, <date time local>

Bias:        <bull|bear> — <how it was decided>
Zones (in bias):
  1. <D1|H4> <pattern> <bottom>–<top>  <fresh|tested>  departure <x> ATR  price <above|below|inside> (<dist>)
  2. ...
Counter-trend: <one line or "none">
Confirmation: <M15 MSB <dir> at <level> | none — price not in zone | none — no close yet>

Bias:         <one line>
Setup:        S&D — <D1|H4> <pattern> <demand|supply>
Risk:         entry <..> / SL <..> / TP <..> / RR <..> / lots <..>
Invalidation: <body close beyond distal ..>
Verdict:      TAKE | WAIT | NO TRADE — <reason>
```

WAIT means: set an alert at the proximal edge and stop. Do not predict whether the zone will hold.

## Limits

Thresholds (base ≤ 50% of leg-out, impulse ≥ 1.5 ATR) are the classic defaults, not calibrated to the trader's own zone indicator. If the trader's chart shows a zone `snd.py` does not, compare the numbers before trusting either. No "gap / fresh-move-away" scoring beyond departure size.
