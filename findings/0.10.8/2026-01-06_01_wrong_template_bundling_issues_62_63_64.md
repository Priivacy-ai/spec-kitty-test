# Issues #62, #63, #64: Wrong Template Directory Bundled in pyproject.toml

**Date:** 2026-01-06
**Session ID:** template-bundling-analysis-2026-01-06
**Tested by:** Claude Code Agent
**Category:** Critical Bug - Package Configuration
**Spec-Kitty Version:** v0.10.8
**Analysis Date:** 2026-01-06
**Applies To:** v0.10.8 (and potentially earlier versions)

## Summary

The pyproject.toml file bundles the wrong template directory, causing all new installations and projects to receive outdated templates with bash/PowerShell script references instead of Python CLI commands. This affects all three critical user scenarios: upgrades without migration, new project initialization, and fresh installations.

## Observation

Three distinct but related issues were reported:

1. **Issue #62** - Users who upgraded their spec-kitty installation but didn't run `spec-kitty upgrade` in their project encounter errors like:
   ```
   check-prerequisites.sh: No such file or directory
   ```

2. **Issue #63** - Users who run `spec-kitty init` with v0.10.8 get projects with broken references:
   ```
   .github/prompts/spec-kitty.specify.prompt.md references create-new-feature.ps1
   ```

3. **Issue #64** - Users who install spec-kitty via `uv tool install` find that ALL slash commands reference non-existent bash/PowerShell scripts instead of using the Python CLI.

## Impact

- **Severity:** **CRITICAL**
- **Scope:**
  - ALL new users installing spec-kitty v0.10.8
  - ALL existing users who upgrade spec-kitty but don't migrate their projects
  - ALL new projects created with `spec-kitty init`
- **Frequency:** Happens always in v0.10.8

This is a blocking issue that makes spec-kitty unusable for:
- New users trying the tool for the first time
- Existing users who upgrade without running migrations
- Any project created with the v0.10.8 package

## Root Cause Analysis

### The Core Problem

Line 72 of `pyproject.toml` contains:
```toml
"templates" = "specify_cli/templates"
```

This bundles the `/templates/` directory (outdated, contains bash/PowerShell script references) instead of the correct `/.kittify/templates/` directory (contains Python CLI commands).

### Why This Happened

The spec-kitty project has THREE divergent template sources:

| Location | Status | Used By | Content |
|----------|--------|---------|---------|
| `/templates/command-templates/` | ❌ Outdated | **Bundled package (BUG!)** | Bash/PS1 script references |
| `/.kittify/templates/command-templates/` | ✅ Correct | Local dev only | Python CLI commands |
| `/.kittify/missions/*/command-templates/` | ✅ Correct | Migrations only | Python CLI commands |

When spec-kitty was migrated from bash/PowerShell scripts to Python CLI (v0.10.0), the templates in `/.kittify/templates/` were updated correctly, but:
1. The old `/templates/` directory was not removed or updated
2. `pyproject.toml` continued to point to the old directory
3. The package build process bundled the outdated templates

### How Each Issue Manifests

**Issue #62 - Worktree script failure:**
- User scenario: Upgraded spec-kitty binary but didn't run `spec-kitty upgrade` on project
- What happens: Project still has old templates that reference `check-prerequisites.sh`
- Why it fails: The script doesn't exist in the Python CLI version
- Workaround: Run `spec-kitty upgrade` to apply v0.10.0 migration

**Issue #63 - New project has broken references:**
- User scenario: Fresh `spec-kitty init` with v0.10.8
- What happens: New project gets templates that reference `create-new-feature.ps1`
- Why it fails: The bundled templates are outdated
- No workaround: Even `spec-kitty upgrade` won't help because the project is already at v0.10.8

**Issue #64 - New installation breakdown:**
- User scenario: `uv tool install spec-kitty-cli`
- What happens: ALL command templates reference bash/PowerShell scripts
- Why it fails: Package bundles the wrong template directory
- No workaround: Requires package fix and republish

### Version Comparison Issue

Issue #64 also mentions "Migration doesn't work for new projects (version comparison issue)":
- New projects created with v0.10.8 are marked as version 0.10.8
- Migrations for v0.10.0 → v0.10.8 check if current version < target version
- Since new projects are already at 0.10.8, migrations don't run
- But the bundled templates are pre-v0.10.0 (bash/PS1 scripts)!
- Result: New projects have outdated templates with no way to fix them

## User/Agent Journey

### Journey 1: Existing User Upgrades (Issue #62)

1. User has working spec-kitty v0.9.x project
2. User runs `pip install --upgrade spec-kitty-cli` → gets v0.10.8
3. User continues working in existing project
4. User tries to create worktree: `spec-kitty agent feature create-feature my-feature`
5. **Error:** `check-prerequisites.sh: No such file or directory`
6. User is confused - the command worked before the upgrade
7. User must discover they need to run `spec-kitty upgrade` in their project

### Journey 2: New Project (Issue #63)

1. New user installs spec-kitty: `pip install spec-kitty-cli` → gets v0.10.8
2. User creates project: `spec-kitty init my-project --ai=claude`
3. Project is created successfully
4. User opens `.github/prompts/spec-kitty.specify.prompt.md`
5. **Finds:** References to `create-new-feature.ps1` and other `.ps1` scripts
6. User tries to follow instructions, scripts don't exist
7. User is blocked - no workaround possible

### Journey 3: Fresh Installation (Issue #64)

1. Developer installs spec-kitty: `uv tool install spec-kitty-cli` → gets v0.10.8
2. Developer creates project: `spec-kitty init test-project --ai=claude`
3. Developer examines ALL command templates in `.github/prompts/`
4. **Discovers:** Every single command references bash or PowerShell scripts:
   - `check-prerequisites.sh`
   - `create-new-feature.ps1`
   - `approve-task.sh`
   - etc.
5. None of these scripts exist anywhere
6. Developer concludes spec-kitty is broken/unusable
7. Developer abandons tool

## What Could Have Helped

### Prevention
1. **Automated testing of packaged distribution:**
   - Test that installs spec-kitty from built package (not local editable install)
   - Verifies command templates contain Python CLI commands
   - Would have caught this before v0.10.8 release

2. **Template directory consolidation:**
   - Remove old `/templates/` directory entirely
   - Single source of truth: `/.kittify/templates/`
   - Update `pyproject.toml` to point to correct location

3. **Build-time validation:**
   - Script to verify template content before package build
   - Fail build if templates contain `.sh` or `.ps1` references
   - Ensure package includes correct templates

### Detection
1. **Clear error messages:**
   - When command references missing script, suggest `spec-kitty upgrade`
   - Detect if user has old templates, offer to fix
   - Guide users to solution

2. **Version metadata:**
   - Track template version separately from CLI version
   - Detect template/CLI version mismatch
   - Auto-suggest fixes

3. **Documentation:**
   - Prominent upgrade guide after installing new version
   - Explain when and why to run `spec-kitty upgrade`
   - List breaking changes and migration paths

## Suggested Improvements

### Immediate Fix (Required for v0.10.9)

1. **Fix pyproject.toml line 72:**
   ```toml
   # Before (WRONG):
   "templates" = "specify_cli/templates"

   # After (CORRECT):
   ".kittify/templates" = "specify_cli/templates"
   ```

2. **Sync or remove old templates directory:**

   **Option A (Recommended):** Remove old directory entirely
   ```bash
   git rm -r templates/
   ```

   **Option B:** Sync from correct source
   ```bash
   rsync -av .kittify/templates/command-templates/ templates/command-templates/
   ```

3. **Add build-time validation:**
   ```python
   # In pyproject.toml or build script
   # Verify no .sh or .ps1 references in bundled templates
   ```

### Enhanced Migration System

4. **Template version tracking:**
   ```json
   // .kittify/meta.json
   {
     "version": "0.10.8",
     "template_version": "0.10.0",  // NEW: Track separately
     "cli_version": "0.10.8"
   }
   ```

5. **Smart upgrade detection:**
   ```python
   # In upgrade command
   if project.template_version < CLI_TEMPLATE_VERSION:
       print("Templates need updating. Running template migration...")
       migrate_templates(project)
   elif project.version == CLI_VERSION:
       print("Project is up to date!")
   ```

6. **Force template refresh command:**
   ```bash
   spec-kitty upgrade --force-templates
   # Always updates templates, even if versions match
   ```

### Better User Communication

7. **Post-install message:**
   ```bash
   $ pip install spec-kitty-cli
   ...
   Successfully installed spec-kitty-cli-0.10.9

   📦 IMPORTANT: If upgrading from earlier version:
      Run 'spec-kitty upgrade' in existing projects
      to apply template updates.
   ```

8. **Helpful error messages:**
   ```bash
   $ spec-kitty agent feature create-feature my-feature
   Error: check-prerequisites.sh not found

   💡 This error suggests your project has outdated templates.
      Try running: spec-kitty upgrade
   ```

9. **Upgrade command improvements:**
   ```bash
   $ spec-kitty upgrade
   Checking project version...
   ✓ Project version: 0.10.8
   ✓ CLI version: 0.10.9

   Checking template version...
   ⚠ Templates are outdated (0.9.0 → 0.10.9)

   Applying migrations:
   • 0.10.0: Migrate from bash/PS1 scripts to Python CLI
   • 0.10.5: Update workflow commands
   ...

   ✓ Upgrade complete!
   ```

### Testing Improvements

10. **Add package distribution tests:**
    ```python
    # tests/functional/test_package_distribution.py
    def test_packaged_templates_are_correct():
        """Verify templates in built package have Python CLI commands"""

    def test_no_script_references_in_package():
        """Ensure package doesn't include bash/PS1 references"""
    ```

11. **Add new project validation tests:**
    ```python
    # tests/functional/test_fresh_init.py
    def test_new_project_has_current_templates():
        """New projects should have latest template version"""

    def test_new_project_uses_python_cli():
        """All commands should use Python CLI, not scripts"""
    ```

## Related Files

**Configuration:**
- `/pyproject.toml` (line 72) - **ROOT CAUSE**

**Template Sources (divergent):**
- `/templates/command-templates/*.md` - Outdated (bash/PS1 refs)
- `/.kittify/templates/command-templates/*.md` - Correct (Python CLI)
- `/.kittify/missions/*/command-templates/*.md` - Correct (Python CLI)

**Affected User Files:**
- `.github/prompts/spec-kitty.*.prompt.md` (Claude)
- `.github/copilot/spec-kitty.*.md` (Copilot)
- `.cursor/prompts/spec-kitty.*.prompt.md` (Cursor)
- etc. (all agent command templates)

**Code Files:**
- `src/specify_cli/template/manager.py` - Reads from .kittify/memory/
- `src/specify_cli/worktree.py` - Creates worktrees, copies templates
- `src/specify_cli/commands/init.py` - Initializes new projects

## Example Output/Reproduction

### Issue #62 - Worktree Script Failure

```bash
$ # User has v0.9.0 project, upgrades CLI to v0.10.8
$ pip install --upgrade spec-kitty-cli
$ cd my-existing-project
$ spec-kitty agent feature create-feature new-feature "Add new feature"

Error: check-prerequisites.sh: No such file or directory
Command: .kittify/commands/check-prerequisites.sh

This script was removed in v0.10.0 (replaced with Python CLI).
Please run: spec-kitty upgrade
```

### Issue #63 - New Project Broken References

```bash
$ pip install spec-kitty-cli  # Gets v0.10.8
$ spec-kitty init my-project --ai=claude
$ cat my-project/.github/prompts/spec-kitty.specify.prompt.md

# Inside the file:
To create a new feature, run:
./create-new-feature.ps1 feature-name "Feature description"

# But this file doesn't exist!
$ ls my-project/*.ps1
ls: *.ps1: No such file or directory
```

### Issue #64 - All Commands Broken

```bash
$ uv tool install spec-kitty-cli  # Gets v0.10.8
$ spec-kitty init test --ai=claude
$ find test -name "*.prompt.md" -exec grep -l "\.sh\|\.ps1" {} \;

test/.github/prompts/spec-kitty.specify.prompt.md
test/.github/prompts/spec-kitty.create-feature.prompt.md
test/.github/prompts/spec-kitty.approve-task.prompt.md
test/.github/prompts/spec-kitty.worktree.prompt.md
... (ALL 12+ command templates reference scripts)
```

## Test Coverage

Comprehensive test suite created in:
`tests/functional/test_issue_62_63_64_template_bundling.py`

**Test Classes:**
1. `TestPackageTemplateValidation` (5 tests)
   - Detect bash script references in templates/
   - Detect PowerShell script references in templates/
   - Verify .kittify/templates/ uses Python CLI
   - Verify .kittify/templates/ has no script refs
   - Check pyproject.toml points to correct directory ⭐ **ROOT CAUSE TEST**

2. `TestNewProjectInitValidation` (6 tests)
   - New projects don't have bash references
   - New projects don't have PowerShell references ⭐ **Issue #63**
   - New projects use Python CLI commands
   - All command templates are correct ⭐ **Issue #64**
   - Worktree commands use CLI not scripts ⭐ **Issue #62**
   - Project structure is complete

3. `TestTemplateDirectoryStructure` (4 tests)
   - Both template directories exist
   - Mission templates exist
   - Analyze three divergent template sources ⭐ **Issue #64 analysis**
   - Comprehensive divergence report

4. `TestUpgradePathValidation` (3 tests)
   - Upgrade command exists and works ⭐ **Issue #62 workaround**
   - Upgrade message quality
   - Version comparison for new projects ⭐ **Issue #64 migration bug**

**Total:** 18 comprehensive tests

These tests will:
- ✅ **Fail** on current v0.10.8 (confirming the bugs)
- ✅ **Pass** after pyproject.toml fix
- ✅ **Prevent regression** in future releases

## Priority

**🚨 CRITICAL - BLOCKING RELEASE**

This issue makes spec-kitty v0.10.8 essentially unusable for:
- New users (first impression is "broken tool")
- Existing users who upgrade (commands suddenly fail)
- Fresh installations (no workaround available)

**Recommended Action:**
1. Fix immediately in v0.10.9 emergency patch
2. Test package distribution (not just local dev install)
3. Deprecate/remove v0.10.8 from PyPI if possible
4. Add automated tests for package distribution
5. Document migration path prominently

---

**Notes:**

This finding documents three related GitHub issues that share the same root cause. The fix is simple (change one line in pyproject.toml), but the impact is severe (makes tool unusable for new users and upgrades). The test suite provides comprehensive coverage to prevent this type of issue in the future.

The three divergent template sources need to be consolidated or clearly documented. The migration system needs enhancement to handle template version mismatches independently of CLI version.
