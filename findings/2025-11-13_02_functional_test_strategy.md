# Functional Test Strategy for Spec-Kitty

**Date:** 2025-11-13
**Session ID:** spec-kitty-testing-strategy-001
**Prepared by:** Claude Code (research agent)
**Category:** Testing Strategy, Architecture, Integration
**Spec-Kitty Version:** ed3f4618b84ab40e4c5bd19ba4cd8423cea23ac6
**Analysis Date:** 2025-11-13
**Applies To:** spec-kitty architecture at commit ed3f461 (and likely stable across versions given the stable core design)

## Executive Summary

This document proposes a comprehensive strategy for creating functional tests that evaluate spec-kitty's end-to-end workflow with real agent interaction. The strategy accounts for both human users and LLM agents (Claude, Codex, Gemini, etc.) and tests the critical paths where humans and machines collaborate.

---

## Part 1: Testing Philosophy

### Core Principles

1. **Test Both User Paths**: Tests must cover:
   - **Human path**: User runs spec-kitty init, reads generated prompts, manually interacts with agents
   - **Agent path**: Agents discover commands in `.claude/commands/`, `.codex/prompts/`, etc., process them, and return results
   - **Integration path**: How results from agents get fed back into the workflow

2. **Avoid Over-Mocking**: While unit tests mock heavily, functional tests should:
   - Use real file I/O for generated files
   - Actually render templates with real variables
   - Test real path rewriting and format conversions
   - Only mock external services (network calls to GitHub, API calls to agents themselves)

3. **Test Agent Orchestration**: The key insight is that spec-kitty orchestrates interactions with agents:
   - It generates prompts customized for each agent
   - Different agents expect different formats (Markdown, TOML, shell variables)
   - Agents need to find their commands in the right location
   - The workflow depends on agents completing steps in order

4. **Real-World Scenarios**: Tests should reflect how humans and agents actually use the system:
   - User wants to initialize a project with multiple agents
   - Agent (Claude/Codex) needs to find its commands
   - Agent generates specification, plan, tasks
   - Human reviews dashboard to see progress
   - Agent implements code based on tasks
   - Both human and agent validate work

---

## Part 2: Test Categories & Scenarios

### Category 1: Initialization Workflows

#### Test 1.1: Complete Multi-Agent Init
**Objective**: Verify that `spec-kitty init` with multiple agents creates all necessary files in correct format

**Scenario**:
```
1. User runs: spec-kitty init my-project --ai=claude,codex
2. System creates .claude/commands/ with Markdown files
3. System creates .codex/prompts/ with Markdown files
4. Both agents can discover their commands
5. .kittify/ structure is complete and valid
6. Dashboard can start and detect project state
```

**What to Test**:
- ✓ All 13 command files created per agent
- ✓ Command files are in agent-specific locations
- ✓ File formats match agent expectations (Claude: .md, Gemini: .toml, etc.)
- ✓ Variable substitutions happened (AGENT_SCRIPT, SCRIPT, ARGS properly replaced)
- ✓ Path rewriting for .kittify/ references is correct
- ✓ .gitignore properly protects agent directories
- ✓ Git repo initialized and initial commit made
- ✓ Mission symlink created and resolves correctly
- ✓ AGENTS.md documents all 12 agents
- ✓ Dashboard can parse project state

**Agent Simulation**:
```python
def test_init_creates_agent_discoverable_commands(tmp_path):
    # Run init
    result = init_command(tmp_path, agents=['claude', 'codex'])

    # Simulate Claude discovering its commands
    claude_dir = tmp_path / '.claude' / 'commands'
    assert claude_dir.exists()
    spec_command = claude_dir / 'spec-kitty.specify.md'
    assert spec_command.exists()

    # Parse the command file - Claude would do this
    content = spec_command.read_text()
    assert '$ARGUMENTS' in content  # Claude variable format
    assert 'claude-code' in content.lower()

    # Verify variables are substituted
    assert '{AGENT_SCRIPT}' not in content  # Should be replaced
    assert content.startswith('# ') or content.startswith('---')  # Valid Markdown

    # Simulate Codex discovering its commands
    codex_dir = tmp_path / '.codex' / 'prompts'
    assert codex_dir.exists()
    task_command = codex_dir / 'spec-kitty.tasks.md'
    assert task_command.exists()

    # Both agents have same 13 commands
    claude_commands = set(f.name for f in claude_dir.glob('*.md'))
    codex_commands = set(f.name for f in codex_dir.glob('*.md'))
    assert claude_commands == codex_commands
```

---

#### Test 1.2: Init with Different Missions
**Objective**: Verify that different missions (software-dev vs research) create appropriate templates

**Scenario**:
```
1. User runs init with --mission=software-dev
   → Creates software development workflow commands
2. User runs init with --mission=research
   → Creates research/analysis workflow commands
3. Mission symlink points to correct mission directory
4. Commands are mission-specific
```

**Agent Simulation**:
- Agent reads mission.yaml to understand available workflows
- Agent looks in active mission's commands/ for mission-specific overrides
- Fallback to root templates/ if mission-specific version doesn't exist

---

### Category 2: Agent Workflow Execution

#### Test 2.1: Agent Command Processing Pipeline
**Objective**: Verify agents can execute the complete workflow in order

**Scenario**:
```
1. Agent reads /spec-kitty.constitution.md
   → Understands project principles
2. Agent reads /spec-kitty.specify.md
   → Creates detailed specification
   → Writes to /specs/specification.md
3. Agent reads /spec-kitty.plan.md
   → Creates implementation plan
   → Writes to /plans/plan.md
4. Agent reads /spec-kitty.tasks.md
   → Generates tasks from plan
   → Creates files in /tasks/planned/
5. Dashboard detects new work packages
6. Agent reads next commands (implement, review, etc.)
```

**What to Test**:
- ✓ Commands are in correct sequence
- ✓ Each command's $ARGUMENTS variable gets proper values
- ✓ Commands reference correct output directories
- ✓ Work package file format is compatible with dashboard
- ✓ Each command contains mission-appropriate guidance
- ✓ Error handling commands are included (review, accept, merge)

**Agent Simulation**:
```python
def test_agent_workflow_execution_order(tmp_path):
    # Initialize project
    init_command(tmp_path, agents=['claude'])

    # Simulate agent workflow
    commands_dir = tmp_path / '.claude' / 'commands'

    # Step 1: Read constitution
    constitution = (commands_dir / 'spec-kitty.constitution.md').read_text()
    assert 'principles' in constitution.lower() or 'values' in constitution.lower()

    # Step 2: Read specify command
    specify = (commands_dir / 'spec-kitty.specify.md').read_text()
    assert 'specification' in specify.lower()
    assert '---' in specify  # YAML frontmatter

    # Step 3: Read plan command
    plan = (commands_dir / 'spec-kitty.plan.md').read_text()
    assert 'plan' in plan.lower()

    # Step 4: Read tasks command
    tasks = (commands_dir / 'spec-kitty.tasks.md').read_text()
    assert 'task' in tasks.lower()
    assert 'lane' in tasks.lower()  # Kanban lane concept

    # Verify correct order (constitution → specify → plan → tasks)
    command_files = sorted(commands_dir.glob('spec-kitty.*.md'))
    expected_order = ['constitution', 'clarify', 'specify', 'plan', 'research', 'tasks', 'implement', 'review', 'accept', 'merge', 'dashboard', 'analyze', 'checklist']

    # Find indices of key commands
    const_idx = next(i for i, f in enumerate(command_files) if 'constitution' in f.name)
    spec_idx = next(i for i, f in enumerate(command_files) if 'specify' in f.name)
    plan_idx = next(i for i, f in enumerate(command_files) if 'plan' in f.name)
    task_idx = next(i for i, f in enumerate(command_files) if 'tasks' in f.name)

    assert const_idx < spec_idx < plan_idx < task_idx
```

---

#### Test 2.2: Multi-Agent Parallel Execution
**Objective**: Verify multiple agents can execute in parallel without conflicts

**Scenario**:
```
1. Init creates project with claude, codex
2. Claude starts /spec-kitty.specify.md
3. Codex reads same /spec-kitty.specify.md (different format location)
4. Both agents generate specifications (Claude: .md, Codex: .md but different dir)
5. Dashboard aggregates both outputs
6. No file conflicts, no overwriting
```

**What to Test**:
- ✓ Agents write to different directories
- ✓ Each agent has isolated command files
- ✓ No race conditions in shared .kittify/ directory
- ✓ Dashboard can track multiple agents' progress
- ✓ Work package state reflects all agent contributions

---

### Category 3: Template Rendering & Variable Substitution

#### Test 3.1: Agent-Specific Variable Substitution
**Objective**: Verify templates render correctly for each agent with proper variable format

**Scenario**:
```
Agent: Claude
Template: spec-kitty.specify.md with $ARGUMENTS variable
Expected: $ARGUMENTS replaced with actual arguments
Format: Markdown with Claude-specific syntax

Agent: Gemini
Template: spec-kitty.specify.toml with {{args}} variable
Expected: {{args}} replaced with actual arguments
Format: TOML (not Markdown)

Agent: Codex
Template: spec-kitty.specify.md with $ARGUMENTS variable
Expected: Similar to Claude but in different directory
```

**What to Test**:
- ✓ Template variable substitution works per agent
- ✓ Path references point to correct .kittify/ paths
- ✓ Agent names are properly included
- ✓ Mission context is included in templates
- ✓ Format conversions (MD→TOML) happen for appropriate agents
- ✓ No template variables remain unreplaced

**Test Code**:
```python
def test_template_substitution_per_agent(tmp_path):
    init_command(tmp_path, agents=['claude', 'gemini', 'codex'])

    # Claude: should be Markdown with $ARGUMENTS
    claude_specify = (tmp_path / '.claude' / 'commands' / 'spec-kitty.specify.md').read_text()
    assert '$ARGUMENTS' in claude_specify
    assert '{{args}}' not in claude_specify  # Not Gemini format
    assert claude_specify.startswith('---') or claude_specify.startswith('#')  # Markdown

    # Gemini: should be TOML with {{args}}
    gemini_specify = (tmp_path / '.gemini' / 'commands' / 'spec-kitty.specify.toml').read_text()
    assert '{{args}}' in gemini_specify
    assert '$ARGUMENTS' not in gemini_specify  # Not Claude format
    assert gemini_specify.startswith('[') or 'prompt' in gemini_specify  # TOML format

    # Codex: should be Markdown with $ARGUMENTS
    codex_specify = (tmp_path / '.codex' / 'prompts' / 'spec-kitty.specify.md').read_text()
    assert '$ARGUMENTS' in codex_specify

    # All should have no unsubstituted template variables
    for f in tmp_path.glob('**/*.md') | tmp_path.glob('**/*.toml'):
        content = f.read_text()
        assert '{AGENT_SCRIPT}' not in content
        assert '__AGENT__' not in content
        assert '{SCRIPT}' not in content or 'bash' in content  # May appear in script files
```

---

#### Test 3.2: Path Rewriting Correctness
**Objective**: Verify that template paths are correctly rewritten to .kittify/ references

**Scenario**:
```
Template contains: ../templates/spec-template.md
After rendering: ./.kittify/templates/spec-template.md

Template contains: ./scripts/bash/implement.sh
After rendering: ./.kittify/scripts/bash/implement.sh
```

**What to Test**:
- ✓ Relative paths are rewritten to .kittify/ namespace
- ✓ Agent names are embedded in paths where appropriate
- ✓ All paths resolve correctly from agent command location
- ✓ Path rewriting doesn't break on edge cases

---

### Category 4: Dashboard & State Management

#### Test 4.1: Dashboard State Detection After Init
**Objective**: Verify dashboard correctly detects and displays project state

**Scenario**:
```
1. Run spec-kitty init
2. Start dashboard (or let it auto-start)
3. Dashboard scans .kittify/missions/
4. Dashboard finds available work packages
5. Dashboard displays initial kanban state
6. No work started yet (all in "planned" lane)
```

**What to Test**:
- ✓ Dashboard can parse .kittify/missions/active/ mission
- ✓ Dashboard finds work package files
- ✓ Dashboard creates correct lane structure (planned, doing, review, done)
- ✓ Initial state shows no work in progress
- ✓ Dashboard API returns correct JSON structure

---

#### Test 4.2: Work Package State Transitions
**Objective**: Verify dashboard correctly tracks work package state through workflow

**Scenario**:
```
1. Agent creates task in /tasks/planned/ lane
2. Dashboard detects new work package
3. Agent moves task to /tasks/doing/ lane
4. Dashboard updates in real-time
5. Human reviews work, moves to /tasks/review/
6. Agent implements changes, moves to /tasks/done/
7. Dashboard reflects all transitions
```

**What to Test**:
- ✓ Dashboard detects file creation and movement
- ✓ Lane transitions trigger state updates
- ✓ API returns current state correctly
- ✓ Websocket broadcasts real-time updates

---

### Category 5: Human & Agent Interaction Points

#### Test 5.1: Human Reads Generated Prompts
**Objective**: Verify that generated command files are readable and usable by humans

**Scenario**:
```
1. Human opens ~/.claude/commands/spec-kitty.specify.md
2. File is well-formatted Markdown
3. Clear instructions on what to do
4. $ARGUMENTS placeholder is obvious
5. References to output files are clear
6. Links to templates are accessible
```

**What to Test**:
- ✓ Command files are valid Markdown
- ✓ YAML frontmatter (if present) is valid
- ✓ Instructions are clear and actionable
- ✓ All file paths exist or will be created
- ✓ Language is appropriate for both humans and LLMs
- ✓ No broken links to templates

---

#### Test 5.2: Agent Parses and Executes Command
**Objective**: Verify that agents can correctly parse and execute generated commands

**Scenario**:
```
1. Agent (Claude) reads ~/.claude/commands/spec-kitty.specify.md
2. Agent extracts:
   - Task description
   - Instructions
   - Context and requirements
   - Expected output format
3. Agent executes the specified task
4. Agent writes output to correct location
5. Work package state updates
```

**What to Test**:
- ✓ Command files are parseable by LLM agents
- ✓ Instructions are unambiguous
- ✓ Context and constraints are clear
- ✓ Expected output format is specified
- ✓ File paths are actionable from agent perspective
- ✓ No ambiguity in what needs to be done

---

### Category 6: Error Handling & Edge Cases

#### Test 6.1: Init Fails Gracefully When Templates Missing
**Objective**: Verify clear error messages when template discovery fails

**Scenario**:
```
1. SPEC_KITTY_TEMPLATE_ROOT not set
2. Package templates not available
3. Network unavailable (can't fetch remote)
4. Init fails with helpful error message
5. Suggests remediation steps
```

**What to Test**:
- ✓ Error message is descriptive (not current cryptic version)
- ✓ Error suggests solutions (set env var, install package, etc.)
- ✓ Paths checked are listed for debugging
- ✓ Documentation link is provided

---

#### Test 6.2: Init Handles Existing Project
**Objective**: Verify init can merge with existing project structure

**Scenario**:
```
1. Project already has some files (README, .gitignore, etc.)
2. Run spec-kitty init
3. Init merges, doesn't destroy existing content
4. Provides confirmation before overwriting
```

**What to Test**:
- ✓ Warning about existing content
- ✓ User confirmation required
- ✓ Existing files preserved
- ✓ .gitignore merged (not replaced)

---

## Part 3: Testing Infrastructure

### Test Organization

```
tests/
├── functional/
│   ├── conftest.py                    # Shared fixtures
│   ├── test_init_workflows.py          # Category 1
│   ├── test_agent_execution.py         # Category 2
│   ├── test_template_rendering.py      # Category 3
│   ├── test_dashboard_state.py         # Category 4
│   ├── test_human_agent_interaction.py # Category 5
│   ├── test_error_handling.py          # Category 6
│   └── fixtures/
│       ├── sample_commands.py
│       ├── mock_agents.py
│       └── state_validators.py
└── unit/
    └── (existing unit tests)
```

### Key Fixtures

```python
@pytest.fixture
def temp_project(tmp_path):
    """Temporary project directory"""
    return tmp_path

@pytest.fixture
def initialized_project(temp_project):
    """Project after spec-kitty init"""
    init_command(temp_project, agents=['claude', 'codex'])
    return temp_project

@pytest.fixture
def mock_agent_claude(initialized_project):
    """Simulated Claude agent that can discover and read commands"""
    return AgentSimulator(
        agent_name='claude',
        project_path=initialized_project,
        command_dir='.claude/commands'
    )

@pytest.fixture
def mock_dashboard(initialized_project):
    """Simulated dashboard state scanner"""
    return DashboardSimulator(initialized_project)
```

### Agent Simulator Class

```python
class AgentSimulator:
    """Simulates how an agent discovers and processes commands"""

    def __init__(self, agent_name, project_path, command_dir):
        self.agent_name = agent_name
        self.project_path = project_path
        self.command_dir = project_path / command_dir

    def discover_commands(self):
        """Agent discovers available commands"""
        return sorted(self.command_dir.glob('spec-kitty.*.md'))

    def read_command(self, command_name):
        """Agent reads a specific command"""
        path = self.command_dir / f'spec-kitty.{command_name}.md'
        return path.read_text()

    def parse_task(self, command_content):
        """Agent parses command into components"""
        # Extract title, instructions, expected output, etc.
        pass

    def validate_command(self, command_content):
        """Check if command is valid and executable"""
        # Check for ambiguity, missing paths, invalid variables
        pass

    def execute_command(self, command_name):
        """Simulate agent executing a command"""
        content = self.read_command(command_name)
        task = self.parse_task(content)
        return self.validate_command(content)
```

---

## Part 4: Success Criteria

### For Each Test Category

| Category | Pass Criteria | Coverage |
|----------|---------------|----------|
| 1. Init Workflows | All agents initialized, files created correctly, formats validated | 15 test cases |
| 2. Agent Execution | Commands executable in order, state transitions correct, no conflicts | 12 test cases |
| 3. Template Rendering | Variables substituted correctly per agent, paths rewritten, formats converted | 10 test cases |
| 4. Dashboard State | State correctly detected, transitions tracked, API responds correctly | 8 test cases |
| 5. Human/Agent Interaction | Commands readable by both, unambiguous, paths actionable | 10 test cases |
| 6. Error Handling | Graceful failures, helpful messages, recovery paths clear | 8 test cases |

**Total Target**: 63 functional test cases

### Coverage Goals

- **90%+** coverage of init command flow
- **80%+** coverage of template rendering
- **70%+** coverage of dashboard operations
- **100%** coverage of agent command directories

---

## Part 5: Metrics & Feedback

### What to Measure

1. **Human Usability**:
   - Can new users understand error messages?
   - Do generated commands make sense?
   - Is the workflow clear?

2. **Agent Compatibility**:
   - Can agents reliably find their commands?
   - Are instructions unambiguous?
   - Do output formats match expectations?

3. **Reliability**:
   - Percentage of init commands that succeed
   - Percentage of agents that can execute workflow
   - Percentage of work packages tracked correctly by dashboard

4. **Performance**:
   - Init command execution time
   - Dashboard state detection latency
   - Template rendering speed

---

## Part 6: Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Create test fixtures and utilities
- [ ] Implement AgentSimulator class
- [ ] Implement DashboardSimulator class
- [ ] Run existing tests to establish baseline

### Phase 2: Init Tests (Week 2)
- [ ] Test single-agent init
- [ ] Test multi-agent init
- [ ] Test mission selection
- [ ] Test error cases

### Phase 3: Agent Tests (Week 3)
- [ ] Test command discovery
- [ ] Test command parsing
- [ ] Test workflow execution order
- [ ] Test parallel execution

### Phase 4: Template Tests (Week 4)
- [ ] Test variable substitution
- [ ] Test path rewriting
- [ ] Test format conversion
- [ ] Test per-agent customization

### Phase 5: Integration Tests (Week 5)
- [ ] End-to-end init → execution → dashboard
- [ ] Human-readable output validation
- [ ] Agent compatibility validation
- [ ] Error recovery and user guidance

---

## Part 7: Key Insights for Spec-Kitty Maintainers

### What This Testing Strategy Reveals

1. **The Human-LLM Bridge**: Spec-kitty's real value is in how it generates prompts that work for both humans and machines. Tests should validate this duality.

2. **The Orchestration Layer**: Spec-kitty orchestrates agent interactions. Tests should verify this orchestration works reliably.

3. **The Format Diversity**: Supporting 12 different agents means handling 3+ different formats. Tests must verify each format works correctly.

4. **The State Management**: The `.kittify/` directory and mission system are central to spec-kitty's approach. Tests should validate state integrity.

5. **The Discovery Problem**: Agents need to find their commands reliably. Tests should verify discovery works across different scenarios.

---

## Part 8: Recommended Next Steps

1. **Implement Phase 1** fixtures and simulators
2. **Create** first 15 tests from Category 1 (Init Workflows)
3. **Run tests** against current code to identify gaps
4. **Document findings** using the findings report system
5. **Iterate** through phases, adding more complex scenarios

---

**Document Status**: Draft Strategy
**Next Review**: After Phase 1 implementation
**Audience**: Spec-kitty development team, test engineers, LLM researchers
