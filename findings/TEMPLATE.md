# Findings Report Template

**Date:** YYYY-MM-DD
**Session ID:** (unique identifier for this testing session)
**Tested by:** (human or agent name)
**Category:** (Feature Enhancement, Bug Report, UX Improvement, Documentation, Integration, Testing, Performance, etc.)
**Spec-Kitty Version:** (git hash from `cd ../.. && git log -1 --format=%H`)
**Analysis Date:** (when you created this finding)
**Applies To:** (commit hash range, e.g., "ed3f461..HEAD" or specific version)

## Summary
Brief one-sentence or two-sentence summary of the finding.

## Observation
What did you observe? What was the behavior? What did you try to do and what happened?

## Impact
- **Severity:** (Critical, High, Medium, Low)
- **Scope:** (Who does this affect? Beginners, Advanced Users, LLM Agents, Integration Points, etc.)
- **Frequency:** (Happens always, sometimes, rare edge case)

## Root Cause Analysis
Why did this happen? What is the underlying reason? (What did we discover about the system?)

## User/Agent Journey
What steps did the user or agent take?
1. Step 1
2. Step 2
3. Step 3

## What Could Have Helped
- What information was missing?
- What could the tool have communicated better?
- What would a human or LLM agent need to know to avoid this friction?
- Were there unclear error messages, missing documentation, or hidden assumptions?

## Suggested Improvements
- Concrete suggestions for making spec-kitty better
- Could be UI changes, documentation additions, error message improvements, workflow adjustments, etc.

## Related Files
- File paths that are relevant to this finding
- Configuration, code, templates involved

## Example Output/Reproduction
If applicable, include the actual error message, output, or steps to reproduce.

---
**Notes:** Additional context or observations
