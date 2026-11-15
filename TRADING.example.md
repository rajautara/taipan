# TRADING.md — the trader's own rules

Copy this file to the root of your project as `TRADING.md` and fill it in.
Taipan reads it at session start; every grade, size and verdict is measured against it.

## Instrument & schedule
- Symbol: OANDA:XAUUSD (EXCHANGE:TICKER — pick the TradingView feed closest to your broker's price)
- Time zone: Asia/Kuala_Lumpur
- Sessions traded: London open, New York open
- Timeframes: bias D1, zones H4, entry M15

## Account (size.py reads these; keep the balance current)
- Balance: 10000 USD
- Risk per trade: 0.5% of balance
- Contract size: 100 (units per 1.00 lot; XAUUSD = 100 oz)
- Lot step / minimum lot: 0.01 / 0.01
- Maximum lot: none
- Typical spread: 0.30 (in price)
- Commission: 0 per lot round turn

## Account constraints (hard rules — a setup that breaks one is NO TRADE)
- Daily loss limit: 2% — stop trading for the day when hit
- Max open positions: 1
- Max trades per day: 3
- Max consecutive losses per day: 2
- News: no entries from 15 min before to 15 min after high-impact USD releases; no closing trades within 15 min after a release (prop-firm rule)
- Stop loss: mandatory on every order, never widened after entry
- Minimum reward-to-risk: 1:2 after spread and commission

## Trade management (what /manage applies; leave a line out and it does not exist)
- Breakeven: move the stop to entry when price reaches +1R
- Partial: none
- Trail: none — the trade ends at the stop or the target
- Before news: stop to breakeven if the trade is past +0.5R, otherwise close 5 min before the window
- Weekend: no positions held through the Friday close

## SOP (the only setups that exist)
Name each rule. The plugin will refer to them by name.

- **Rule 1 — Behind the Candle**: D1 bias by body-close MSB → fresh H4 POI (BZ > OB > FVG) in bias direction → price enters POI → M15 Liquidity Raid + immediate MSB → M15 Breaker Zone in bias direction. Entry at BZ boundary, SL at the far edge of the BZ, TP at nearest liquidity, minimum 1:2. Handled by `/btc`.
- **Rule 2 — Supply & Demand**: D1/H4 RBR/DBR demand or RBD/DBD supply zone in bias direction, fresh preferred; price enters the zone; M15 body-close MSB in zone direction confirms. Entry at proximal edge, SL beyond distal edge, TP at nearest opposing zone, minimum 1:2. Handled by `/snd`.
- **Rule 3 — Breakout-Pullback**: H4 body close past a structure high/low in bias direction; wait for price to pull back into the zone the break left (its FVG, else level-to-open); entry on the body close back out of the zone in breakout direction, SL beyond the pullback extreme, TP at next liquidity, minimum 1:2. A body close back past the broken level = failed, no trade. Handled by `/bpb`.
- **Rule 4 — Quasimodo**: H4 left shoulder → head sweeps it → body close under/over the neckline (L1). Entry on return to the QML (left-shoulder level) with M15 body-close confirmation, SL beyond the head, TP at L1 or next liquidity, minimum 1:2. Only with an HTF reason for the reversal (D1 shifting, or at a D1 POI). Handled by `/qm`.
- **Rule 5 — ...**

## Stand-aside conditions
- D1 and H4 bias disagree
- Any restricted news window
