# Spec Kitty Init Workflow - Detailed Flowchart

**Spec-Kitty Version Analyzed:** ed3f4618b84ab40e4c5bd19ba4cd8423cea23ac6 (commit ed3f461)
**Analysis Date:** 2025-11-13
**Applies To:** The init command as implemented at the specified commit

## Main Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ spec-kitty init <project_name> [options]                        │
│ Options: --ai, --script, --mission, --here, --no-git, etc.     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │ 1. VALIDATE INPUTS              │
        ├────────────────────────────────┤
        │ • Project name OR --here flag   │
        │ • Check directory conflicts     │
        │ • Verify CWD accessible        │
        └────────────┬───────────────────┘
                     │ (exits on error)
                     ▼
        ┌────────────────────────────────┐
        │ 2. CHECK GIT AVAILABILITY      │
        ├────────────────────────────────┤
        │ • Unless --no-git flag         │
        │ • Determines should_init_git   │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │ 3. SELECT AI ASSISTANTS             │
        ├────────────────────────────────────┤
        │ • Multi-select from 12 options      │
        │ • CLI: --ai claude,gemini          │
        │ • Interactive: Show picker          │
        │ • Result: selected_agents: list     │
        └────────────┬────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │ 4. CHECK AGENT TOOL REQUIREMENTS    │
        ├────────────────────────────────────┤
        │ • For each selected agent          │
        │ • Check if tool installed (claude) │
        │ • Skip with --ignore-agent-tools   │
        │ • Exit with helpful URLs if missing│
        └────────────┬────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │ 5. SELECT SCRIPT TYPE              │
        ├────────────────────────────────────┤
        │ • Options: sh (Unix) or ps (Win)   │
        │ • CLI: --script sh|ps              │
        │ • Auto-detect: os.name == 'nt'     │
        │ • Result: selected_script          │
        └────────────┬────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │ 6. SELECT MISSION                  │
        ├────────────────────────────────────┤
        │ • Options: software-dev, research  │
        │ • CLI: --mission software-dev      │
        │ • Default: software-dev            │
        │ • Result: selected_mission         │
        └────────────┬────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │ 7. DETECT TEMPLATE MODE            │
        ├────────────────────────────────────┤
        │ Priority:                          │
        │ 1. Local: get_local_repo_root()    │
        │ 2. Remote: SPECIFY_TEMPLATE_REPO   │
        │ 3. Package: bundled in site-pkg    │
        │ Result: template_mode, repo_owner, │
        │         repo_name (if remote)      │
        └────────────┬────────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────────────┐
        │ 8. INITIALIZE PROGRESS TRACKER          │
        ├─────────────────────────────────────────┤
        │ tracker = StepTracker()                 │
        │ Add steps: precheck, ai-select,        │
        │   script-select, mission-select,       │
        │   mission-activate, chmod, git, final  │
        │ For each agent: {agent}-fetch,         │
        │   {agent}-download, {agent}-extract... │
        └────────────┬────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────┐
        │ 9. ACQUIRE TEMPLATES & GENERATE AGENT ASSETS     │
        │                                                  │
        │ ┌─ FOR EACH SELECTED AGENT ─────────────────┐  │
        │ │                                            │  │
        │ │ A. TEMPLATE ACQUISITION:                   │  │
        │ │                                            │  │
        │ │ IF template_mode == "local" or "package": │  │
        │ │  └─ (Only once, not per agent)            │  │
        │ │     commands_dir = copy_specify_base()    │  │
        │ │                                            │  │
        │ │ IF template_mode == "remote":             │  │
        │ │  └─ download_and_extract_template()       │  │
        │ │     └─ Fetch from GitHub                  │  │
        │ │     └─ Extract zip to project             │  │
        │ │                                            │  │
        │ │ B. ASSET GENERATION:                       │  │
        │ │  └─ generate_agent_assets(                │  │
        │ │       commands_dir,                       │  │
        │ │       project_path,                       │  │
        │ │       agent_key,      # "claude"          │  │
        │ │       selected_script # "sh"              │  │
        │ │     )                                     │  │
        │ │                                            │  │
        │ │ C. FOR EACH TEMPLATE IN commands_dir:     │  │
        │ │  ├─ render_template(template_path)        │  │
        │ │  │  ├─ parse_frontmatter()                │  │
        │ │  │  ├─ resolve_variables()                │  │
        │ │  │  │  ├─ {SCRIPT} → actual command      │  │
        │ │  │  │  ├─ {ARGS} → agent-format args     │  │
        │ │  │  │  ├─ __AGENT__ → agent key          │  │
        │ │  │  ├─ rewrite_paths()                    │  │
        │ │  │  │  ├─ scripts/ → .kittify/scripts/   │  │
        │ │  │  │  ├─ templates/ → .kittify/templ... │  │
        │ │  │  └─ Return: (metadata, body, raw_fm)  │  │
        │ │  │                                        │  │
        │ │  └─ Write to agent output dir:           │  │
        │ │     Path: {agent_output_dir}/spec-kitty. │  │
        │ │            {command_name}.{ext}          │  │
        │ │     Example: .claude/commands/           │  │
        │ │              spec-kitty.specify.md       │  │
        │ │                                            │  │
        │ │ D. FORMAT CONVERSION (if needed):          │  │
        │ │  IF ext == "toml" (gemini):              │  │
        │ │   └─ Convert: description + body toml    │  │
        │ │  IF agent == "codex":                     │  │
        │ │   └─ Replace dashes with underscores     │  │
        │ │                                            │  │
        │ │ E. TRACKER UPDATE:                         │  │
        │ │  └─ tracker.complete("{agent}-extract") │  │
        │ │  └─ tracker.complete("{agent}-cleanup") │  │
        │ │                                            │  │
        │ └────────────────────────────────────────────┘  │
        └──────────────────┬───────────────────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │ 10. ACTIVATE MISSION                │
        ├─────────────────────────────────────┤
        │ _activate_mission(                  │
        │   project_path,                     │
        │   selected_mission,  # "software-dev"
        │   mission_display,   # "Software Dev"
        │   _console                          │
        │ )                                   │
        │                                     │
        │ Actions:                            │
        │ • Create symlink:                   │
        │   .kittify/active-mission →         │
        │   .kittify/missions/software-dev    │
        │ • Load mission.yaml                 │
        │ • Initialize mission resources      │
        │ • Result: mission_status string     │
        └─────────────┬───────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────────────┐
        │ 11. ENSURE SCRIPTS EXECUTABLE       │
        ├─────────────────────────────────────┤
        │ _ensure_executable_scripts(         │
        │   project_path,                     │
        │   tracker=tracker                   │
        │ )                                   │
        │                                     │
        │ Actions (Unix/Linux/macOS):         │
        │ • chmod +x .kittify/scripts/bash/*  │
        │ • chmod +x .kittify/scripts/tasks/* │
        │ • Tracker: complete("chmod")        │
        └─────────────┬───────────────────────┘
                      │
                      ▼
        ┌──────────────────────────────────────┐
        │ 12. INITIALIZE GIT REPOSITORY        │
        ├──────────────────────────────────────┤
        │ IF not no_git AND should_init_git:   │
        │   IF is_git_repo(project_path):      │
        │     └─ tracker.complete("git",       │
        │        "existing repo detected")     │
        │   ELSE:                              │
        │     └─ init_git_repo(project_path)   │
        │     └─ tracker.complete("git",       │
        │        "initialized")                │
        │ ELSE:                                │
        │   └─ tracker.skip("git", reason)     │
        │                                      │
        │ Actions:                             │
        │ • git init                           │
        │ • Create .gitignore with agent dirs  │
        │ • Initial commit                     │
        └──────────────┬───────────────────────┘
                       │
                       ▼
        ┌────────────────────────────────────────┐
        │ 13. START DASHBOARD                    │
        ├────────────────────────────────────────┤
        │ dashboard_url, port, started =         │
        │   ensure_dashboard_running(project)    │
        │                                        │
        │ Actions:                               │
        │ • Check if already running (port)      │
        │ • If running: reconnect               │
        │ • If not: start as detached process   │
        │ • Determine available port (3000+)     │
        │ • Return (url, port, started_flag)     │
        └────────────┬─────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │ 14. DISPLAY SUMMARY & NEXT STEPS       │
        ├────────────────────────────────────────┤
        │ • Project ready panel                 │
        │ • Agent folder security notice        │
        │ • Gitignore recommendations           │
        │ • Next steps panel (13 commands)       │
        │ • Enhancement commands panel          │
        │ • Dashboard connection info           │
        └────────────┬─────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │ 15. SUCCESS COMPLETE                   │
        ├────────────────────────────────────────┤
        │ Exit code: 0                           │
        │ Message: "Project ready."              │
        │ Dashboard: Running in background       │
        └────────────────────────────────────────┘
```

## Template Rendering Sub-Flow

For each template file (specify.md, plan.md, etc.):

```
Template File
(templates/commands/specify.md)
│
├─ Frontmatter:
│  ├─ description: "Create specification"
│  └─ scripts:
│     ├─ sh: ".kittify/scripts/bash/... {ARGS}"
│     └─ ps: ".kittify/scripts/powershell/... {ARGS}"
│
├─ Body: (Markdown content)
│  └─ Contains {SCRIPT}, {ARGS}, __AGENT__, references to templates/, etc.
│
▼
render_template(template_path, variables)
│
├─ parse_frontmatter()
│  └─ Extract metadata dict, body, raw_frontmatter_text
│
├─ _resolve_variables(metadata, variables_resolver)
│  └─ IF callable: variables_resolver(metadata) → dict
│     ELSE: return variables dict directly
│
│  Returns mapping:
│  ├─ {SCRIPT} → ".kittify/scripts/bash/create-new-feature.sh --json "$ARGUMENTS""
│  ├─ {ARGS} → "$ARGUMENTS" (Claude) or "{{args}}" (Gemini)
│  ├─ {AGENT_SCRIPT} → optional agent-specific setup
│  └─ __AGENT__ → "claude" or "gemini" or etc.
│
├─ _apply_variables(body, replacements)
│  └─ Substitute all {PLACEHOLDER} and __PLACEHOLDER__ in body
│
├─ rewrite_paths(rendered_body, patterns)
│  └─ Apply regex replacements:
│     ├─ scripts/ → .kittify/scripts/
│     ├─ templates/ → .kittify/templates/
│     └─ memory/ → .kittify/memory/
│
▼
Output:
├─ metadata: dict (description, scripts, etc.)
├─ rendered: str (fully processed body)
└─ raw_frontmatter: str (raw YAML text)

▼
render_command_template() wrapping
│
├─ Format conversion (if needed):
│  ├─ IF agent == "gemini": Convert to TOML
│  ├─ IF agent == "codex": Replace dashes with underscores
│  └─ Else: Keep Markdown
│
├─ Frontmatter handling:
│  ├─ Keep for Markdown outputs (Claude, Cursor, etc.)
│  └─ Convert to description field for TOML (Gemini)
│
▼
Write File:
├─ Directory: project_path / agent_config["dir"]
│  └─ Example: .claude/commands
│
├─ Filename: spec-kitty.{template_stem}.{ext}
│  └─ Example: spec-kitty.specify.md
│
└─ Content: Rendered output (markdown/toml/etc.)
```

## Agent Asset Generation Sub-Flow

```
generate_agent_assets(commands_dir, project_path, agent_key, script_type)
│
├─ 1. LOOKUP AGENT CONFIG
│  └─ config = AGENT_COMMAND_CONFIG[agent_key]
│     ├─ dir: ".claude/commands"
│     ├─ ext: "md"
│     └─ arg_format: "$ARGUMENTS"
│
├─ 2. CREATE OUTPUT DIRECTORY
│  └─ output_dir = project_path / config["dir"]
│  └─ If exists: Remove and recreate
│  └─ mkdir -p output_dir
│
├─ 3. VERIFY SOURCE TEMPLATES EXIST
│  └─ IF NOT commands_dir.exists():
│     └─ Raise FileNotFoundError
│
├─ 4. FOR EACH TEMPLATE IN commands_dir/*.md:
│  │
│  ├─ render_command_template(
│  │   template_path="specify.md",
│  │   script_type="sh",
│  │   agent_key="claude",
│  │   arg_format="$ARGUMENTS",
│  │   extension="md"
│  │ )
│  │  │
│  │  ├─ build_variables(metadata):
│  │  │  ├─ scripts = metadata["scripts"] or {}
│  │  │  ├─ agent_scripts = metadata["agent_scripts"] or {}
│  │  │  ├─ script_command = scripts["sh"] = ".kittify/scripts/bash/..."
│  │  │  ├─ agent_script_command = agent_scripts.get("sh")
│  │  │  │
│  │  │  └─ RETURN {
│  │  │       "{SCRIPT}": script_command,
│  │  │       "{AGENT_SCRIPT}": agent_script_command or "",
│  │  │       "{ARGS}": "$ARGUMENTS",
│  │  │       "__AGENT__": "claude"
│  │  │     }
│  │  │
│  │  ├─ render_template(template_path, build_variables)
│  │  │  └─ (See Template Rendering Sub-Flow)
│  │  │
│  │  ├─ POST-PROCESS FRONTMATTER
│  │  │  ├─ Extract description
│  │  │  ├─ Filter frontmatter if needed
│  │  │  └─ Format for output type
│  │  │
│  │  └─ RETURN rendered_output (str)
│  │
│  └─ WRITE FILE
│     ├─ stem = template_path.stem  # "specify"
│     ├─ IF agent_key == "codex": Replace "-" with "_"
│     ├─ filename = f"spec-kitty.{stem}.{ext}"
│     │  └─ Example: "spec-kitty.specify.md"
│     │
│     └─ (output_dir / filename).write_text(rendered_output)
│
├─ 5. SPECIAL: COPILOT VS CODE SETTINGS
│  └─ IF agent_key == "copilot":
│     └─ Copy vscode-settings.json to .vscode/settings.json
│
└─ COMPLETE
```

## State After Init Completes

### Directory Structure Created

```
project-name/
├── .claude/
│   └── commands/                    # 13+ Claude commands
│       ├── spec-kitty.specify.md
│       ├── spec-kitty.plan.md
│       ├── spec-kitty.tasks.md
│       └── ... (other commands)
├── .gemini/
│   └── commands/                    # 13+ Gemini commands (TOML)
│       ├── spec-kitty.specify.toml
│       └── ... (other commands)
├── .codex/
│   └── prompts/                     # 13+ Codex commands
│       ├── spec_kitty.specify.md    # Note: underscores
│       └── ... (other commands)
├── .kittify/
│   ├── active-mission → missions/software-dev/
│   ├── missions/
│   │   ├── software-dev/
│   │   │   ├── mission.yaml
│   │   │   ├── commands/            # Mission-specific commands
│   │   │   ├── constitution/        # Project rules
│   │   │   └── templates/           # Mission templates
│   │   └── research/
│   ├── scripts/
│   │   ├── bash/                    # Implementation scripts
│   │   ├── powershell/              # (if needed)
│   │   └── tasks/                   # Task CLI
│   ├── memory/                      # Persistent memory
│   └── AGENTS.md
├── .git/                            # (if git initialized)
│   └── ...
├── .gitignore                       # Protects .claude/, .gemini/, etc.
└── (Any other project files)
```

### Files Created by Agent

**Claude** (`.claude/commands/`):
- `spec-kitty.specify.md` - Define specification
- `spec-kitty.plan.md` - Create plan
- `spec-kitty.tasks.md` - Generate tasks
- `spec-kitty.implement.md` - Implement feature
- `spec-kitty.review.md` - Code review
- `spec-kitty.accept.md` - Acceptance check
- `spec-kitty.research.md` - Research phase
- `spec-kitty.clarify.md` - Ask clarifying questions
- `spec-kitty.analyze.md` - Analyze artifacts
- `spec-kitty.checklist.md` - Generate checklists
- `spec-kitty.constitution.md` - Project principles
- `spec-kitty.dashboard.md` - Open dashboard
- `spec-kitty.merge.md` - Merge to main

**Gemini** (`.gemini/commands/`):
- Same 13 commands but in TOML format
- Uses `{{args}}` instead of `$ARGUMENTS`
- Fields: description, [command] with prompt

**Codex** (`.codex/prompts/`):
- Same 13 commands with underscores (spec_kitty.*)
- Markdown format
- Uses `$ARGUMENTS` placeholder

## Key Variables and States

### After Init Validation
```
- project_path: Path                     # Where project will be
- project_name: str                      # Project directory name
- current_dir: Path                      # Where command ran from
- here: bool                             # Using --here flag
```

### After Agent Selection
```
- selected_agents: list[str]             # ["claude", "gemini"]
- AI_CHOICES: dict                       # Display names for each
```

### After Configuration Selection
```
- selected_script: str                   # "sh" or "ps"
- selected_mission: str                  # "software-dev" or "research"
- mission_display: str                   # "Software Dev Kitty"
```

### After Template Mode Detection
```
- template_mode: str                     # "local", "package", or "remote"
- local_repo: Path | None                # Path to spec-kitty source (if local)
- repo_owner: str | None                 # GitHub owner (if remote)
- repo_name: str | None                  # GitHub repo name (if remote)
```

### After Asset Generation
```
- commands_dir: Path                     # Where templates were copied
- base_prepared: bool                    # True after first agent
- created_assets: list[Path]             # All generated command files
```

### After Mission Activation
```
- mission_status: str                    # Status message from activation
```

### Final State
```
- dashboard_url: str                     # "http://localhost"
- dashboard_port: int                    # 3000-5000
- dashboard_started: bool                # True if newly started
```

## Error Handling and Exit Points

```
Early Exits (typer.Exit(1)):
├─ Project name XOR --here flag
├─ Directory already exists (non --here)
├─ Current directory inaccessible
├─ User declines merge confirmation
├─ No AI assistants selected
├─ Invalid AI assistant names
├─ Agent tools missing (non --ignore-agent-tools)
├─ Invalid script type
├─ Invalid mission name
├─ Template processing error
├─ Mission activation error
└─ Any uncaught exception

Success Exit (0):
├─ All stages complete
└─ Dashboard confirmed running (or auto-starting)
```

## Execution Timeline

```
1. Input Validation         ~0.1s
2. Tool Checks              ~0.5s (checks for git, etc.)
3. Interactive Selection    ~0-30s (user input)
4. Template Acquisition     ~1-5s (local) or ~30s (remote)
5. Asset Generation         ~2-10s (depends on # agents)
6. Mission Activation       ~0.5s
7. Script chmod             ~0.1s
8. Git Initialization       ~1s (or skip)
9. Dashboard Start          ~2-5s (background process)

Total:                       ~5-50s (depending on template mode and user input)
```

---

End of Flowchart
