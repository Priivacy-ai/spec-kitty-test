# Additional Init Bugs Found - v0.10.4

**Date:** 2025-12-18
**Category:** Bug Report, Init Command
**Severity:** HIGH
**Status:** 🐛 OPEN

---

## Bugs Found During All-Agent Testing

### Bug #7: Copilot Init Crashes

**Error:** `Initialization failed: name 'commands_dir' is not defined`

**Reproduction:**
```bash
spec-kitty init test --ai=copilot
# Error: name 'commands_dir' is not defined
```

**Impact:** Copilot users cannot initialize projects

---

### Bug #8: Gemini Gets No Commands

**Issue:** Gemini directory created but spec-kitty commands not copied

**Reproduction:**
```bash
spec-kitty init test --ai=gemini
ls test/.gemini/commands/spec-kitty.*.md
# Result: No files found
```

**Impact:** Gemini users have no slash commands

---

## Summary

While 11/12 agents work, 2 still have bugs:
- ✅ 9 agents fully working (claude, codex, opencode, cursor, qwen, windsurf, kilocode, roo, q)
- ⚠️ 1 agent crashes (copilot)
- ⚠️ 1 agent missing commands (gemini)
- 🔄 1 agent untested (auggie)
