// SessionStart: print the mindset so it is active for the whole session, plus the
// trader's own TRADING.md (SOP + account constraints), the clock and today's journal state.
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const skill = fs.readFileSync(path.join(__dirname, "..", "skills", "taipan", "SKILL.md"), "utf8");
const body = skill.replace(/^---[\s\S]*?---\s*/, ""); // drop frontmatter

let out = "TAIPAN MODE ACTIVE\n\n" + body;

function py(script, args) {
  for (const exe of ["python3", "python"]) {
    try {
      return execFileSync(exe, [path.join(__dirname, "..", "skills", "taipan", script), ...args],
        { encoding: "utf8", timeout: 5000, stdio: ["ignore", "pipe", "ignore"] }).trim();
    } catch (e) { /* try the next interpreter; the session must start without Python too */ }
  }
  return "";
}

const rules = path.join(process.cwd(), "TRADING.md");
const text = fs.existsSync(rules) ? fs.readFileSync(rules, "utf8") : "";
if (text) {
  out += "\n\n# Trader's own rules (TRADING.md) — these override anything above\n\n" + text;
} else {
  out += "\n\nNo TRADING.md in this project. Ask the trader for their SOP and account constraints before grading any setup, and offer to save them to TRADING.md.";
}

// The scripts read taipan.json (account numbers, limits, time zone) from the project root themselves.
const cwd = process.cwd();
const has = (f) => fs.existsSync(path.join(cwd, f));
if (!has("taipan.json")) {
  out += "\n\nNo taipan.json in this project: check.py cannot size or gate a trade. Ask the trader for balance, risk %, contract size, spread and daily limits, and offer to save them (copy taipan.example.json).";
}
const clock = py("now.py", []);
if (clock) out += "\n\n# Clock at session start (goes stale: check.py reads the time again at every verdict)\n\n" + clock;
if (has("journal.csv")) {
  const st = py("journal.py", ["status"]);
  if (st) out += "\n\n# Journal today (journal.csv)\n\n" + st;
}
if (has("plan.json")) {
  const pl = py("plan.py", ["show"]);
  if (pl && pl !== "[]") out += "\n\n# Trades that are on (plan.json) — the trader is in these; use /manage\n\n" + pl;
}
if (has("backtest.json")) out += "\n\nbacktest.json holds this instrument's replay record; check.py quotes it per rule.";

process.stdout.write(out);
