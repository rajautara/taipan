// SessionStart: print the mindset so it is active for the whole session, plus the
// trader's own TRADING.md (SOP + account constraints) when the project has one.
const fs = require("fs");
const path = require("path");

const skill = fs.readFileSync(path.join(__dirname, "..", "skills", "taipan", "SKILL.md"), "utf8");
const body = skill.replace(/^---[\s\S]*?---\s*/, ""); // drop frontmatter

let out = "TAIPAN MODE ACTIVE\n\n" + body;

const rules = path.join(process.cwd(), "TRADING.md");
if (fs.existsSync(rules)) {
  out += "\n\n# Trader's own rules (TRADING.md) — these override anything above\n\n" + fs.readFileSync(rules, "utf8");
} else {
  out += "\n\nNo TRADING.md in this project. Ask the trader for their SOP and account constraints before grading any setup, and offer to save them to TRADING.md.";
}

process.stdout.write(out);
