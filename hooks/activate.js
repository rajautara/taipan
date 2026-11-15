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

// The "Time zone:" line of TRADING.md, else the machine's.
const tz = (text.match(/time ?zone:\s*([A-Za-z_]+\/[A-Za-z_\/]+)/i) || [])[1] || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
const clock = py("now.py", ["--tz", tz]);
if (clock) out += "\n\n# Clock at session start (goes stale: run now.py again before any verdict)\n\n" + clock;

const journal = path.join(process.cwd(), "journal.csv");
if (fs.existsSync(journal)) {
  const st = py("journal.py", ["status", "--file", journal, "--tz", tz]);
  if (st) out += "\n\n# Journal today (journal.csv)\n\n" + st;
}

process.stdout.write(out);
