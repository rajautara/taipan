---
name: trade-review
description: "Post-mortem of a trade or a trading day: grades process against the trader's SOP, not P&L. Use for /trade-review, \"review my trade\", \"review today\", \"post-mortem\", \"what did I do wrong\", or when the user pastes a trade log or screenshot of closed trades."
argument-hint: "[trade | day | week]"
---

# Trade Review

Grade the process, not the result. A green trade that broke the SOP gets a low grade. A red trade that followed it gets a high grade. Say which, and why, in plain words.

## Input

Ask for whatever is missing, nothing more: entry, stop, target, exit, time, the SOP rule the trader thought they were following, and a screenshot if they have one. If TRADING.md exists, read it first; every grade below is against that document.

## For each trade

| Check | Question |
|-------|----------|
| Setup | Did a rule in the SOP actually qualify it at the time of entry? Name the rule or say "none". |
| Entry | Was entry at the SOP trigger, or early/late/chased? |
| Stop | Was it placed where the SOP says, and was it moved? Moving a stop against the trade is an automatic fail. |
| Size | Did lots match the account risk %? |
| Management | Was the exit per SOP (TP, trail, time) or emotional (fear, hope, boredom)? |
| Constraints | Any account rule broken (news window, daily loss, hours)? |

Grade: **A** followed the SOP in full · **B** one minor deviation · **C** a rule broken but risk intact · **F** stop moved, oversized, or an account rule broken.

## For a day or week

Add: trades per day vs SOP maximum, consecutive losses and whether the trader stopped when the SOP says to stop, and the one pattern that cost the most. One pattern, not a list.

## Reply format

Plain markdown, never a code block: the trader reads this on a phone at the screen. Short bold labels, one idea per line, prices in **bold**.

**<trade or day> — Grade A / B / C / F**

- **What was right:** <one line>
- **What was wrong:** <one line, or "nothing">
- **The one thing to change:** <one line>

No motivational talk. No "great job". If the trader did well, say "that was the SOP" and stop.
