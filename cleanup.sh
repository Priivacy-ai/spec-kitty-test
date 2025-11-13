#!/bin/bash
# cleanup.sh - Remove all spec-kitty generated files

# Remove agent command directories
rm -rf .claude/
rm -rf .codex/
rm -rf .gemini/
rm -rf .github/
rm -rf .cursor/
rm -rf .qwen/
rm -rf .opencode/
rm -rf .windsurf/
rm -rf .kilocode/
rm -rf .augment/
rm -rf .roo/
rm -rf .amazonq/

# Remove kittify directory (main spec-kitty directory)
rm -rf .kittify/

# Remove git repository
rm -rf .git/

# Remove .gitignore if it was created
rm -f .gitignore

echo "Cleanup complete. All spec-kitty generated files have been removed."
