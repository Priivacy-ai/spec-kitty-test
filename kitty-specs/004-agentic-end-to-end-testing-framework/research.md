# Research Decision Log

Document the outcomes of Phase 0 discovery work for the Agentic End-to-End Testing Framework.

## Summary

- **Feature**: 004-agentic-end-to-end-testing-framework
- **Date**: 2026-01-19
- **Researchers**: Claude Opus 4.5 + Human
- **Open Questions**: Container registry hosting, CI/CD budget allocation, agent API cost tracking

## Decisions & Rationale

| Decision | Rationale | Evidence | Status |
|----------|-----------|----------|--------|
| Use Docker for container isolation | Industry standard, testcontainers-python integration, native resource limits support | E001, E002 | final |
| Use testcontainers-python 4.14.0 | Native pytest integration, yield fixtures, lifecycle management | E002 | final |
| Create internal Docker network | Blocks outbound internet by default, prevents data exfiltration | E001, E003 | final |
| Use Docker Secrets for credentials | More secure than env vars, same file path across environments | E003 | final |
| Use pytest-timeout for process control | Signal-based interruption, configurable per-test | E004 | final |
| Use pytest-subprocess for fake processes | Wait parameter for delays, signal_callback for kill handling | E004 | final |
| Use Toxiproxy for network failures | Industry standard TCP proxy, Docker integration, multiple "toxics" | E005 | final |
| Use Pumba for container chaos | Kill/stop/pause containers, network emulation via tc/iptables | E005 | final |
| Adopt 3-path architecture (1/2/3 agent) | Modular design, agents pluggable at runtime, tests available agents | User requirement | final |
| Focus on implement→review workflow | Core agent value, includes rejection cycles | User requirement | final |
| Manual test trigger only | Expensive real-agent tests, API costs, rate limits | User requirement | final |
| Install spec-kitty from PyPI in containers | Distribution testing principle - test what ships | E006 | final |

## Evidence Highlights

### E001: Container Isolation Patterns

**Key insight**: Docker provides sufficient isolation for AI agent testing when combined with:
- Internal networks (no internet access)
- Resource limits (CPU, memory, disk)
- Secrets mounted to `/run/secrets/`
- Enhanced Container Isolation (ECI) available in Docker Desktop

**Sandboxing hierarchy** (increasing security): Docker < gVisor < Firecracker

For our adversarial testing, Docker with internal networks is sufficient - we're testing the orchestrator's handling of agent behavior, not defending against malicious agents.

**Source**: CodeAnt AI sandboxing guide, Docker security blog

### E002: testcontainers-python Integration

**Key insight**: testcontainers-python 4.14.0 provides excellent pytest integration:

```python
@pytest.fixture(scope="session")
def agent_container():
    with GenericContainer("spec-kitty-agent:latest") as container:
        yield container
```

- Session-scoped fixtures for expensive containers
- Function-scoped for test isolation
- Automatic cleanup on test completion
- Works with custom Dockerfiles

**Source**: testcontainers.com, PyPI package docs

### E003: Credential Management

**Key insight**: Docker Compose secrets are the recommended approach for test credentials:

```yaml
services:
  agent-test:
    secrets:
      - claude_api_key
      - github_token

secrets:
  claude_api_key:
    file: ./secrets/claude_api_key.txt
```

- Never hardcode in Dockerfile
- Avoid env vars (leak in logs/inspection)
- Mount to `/run/secrets/<name>`
- Same path works across environments

**Source**: Docker secrets documentation, GitGuardian best practices

### E004: Fault Injection Tools

**Key insight**: pytest has excellent fault injection support:

| Tool | Purpose | Installation |
|------|---------|--------------|
| pytest-timeout | Test timeouts, SIGALRM/SIGKILL | `pip install pytest-timeout` |
| pytest-subprocess | Fake subprocess calls | `pip install pytest-subprocess` |
| pyfakefs | In-memory fake filesystem | `pip install pyfakefs` |
| monkeypatch | Env vars, file errors | Built into pytest |

**Process killing pattern**:
```python
proc.terminate()  # SIGTERM
try:
    proc.wait(timeout=5)
except subprocess.TimeoutExpired:
    proc.kill()  # SIGKILL
```

**Source**: pytest-timeout docs, pytest-subprocess docs

### E005: Network Chaos Engineering

**Key insight**: Two complementary tools for network failures:

**Toxiproxy** (TCP-level):
- latency, bandwidth, timeout, reset_peer, slicer toxics
- Python client: `toxiproxy-python`
- Docker image: `ghcr.io/shopify/toxiproxy:latest`

**Pumba** (Container-level):
- Kill, stop, pause containers
- Network emulation via Linux tc
- `pumba netem --duration 20s delay --time 3000 container_name`

**Source**: Shopify Toxiproxy, Pumba GitHub

### E006: Distribution Testing Principle

**Key insight**: The 0.10.8 catastrophe taught us that testing development code creates blind spots:

- 323 tests passed using `SPEC_KITTY_TEMPLATE_ROOT` bypass
- 100% of PyPI users failed with packaging bug
- Tests must install from PyPI, not local source

**Container Dockerfile pattern**:
```dockerfile
# Install from PyPI, NOT local source
RUN pip install spec-kitty==0.11.0
# DO NOT set SPEC_KITTY_TEMPLATE_ROOT
```

**Source**: findings/0.10.8/, CLAUDE.md

### E007: Agent Invocation Patterns (from Feature 020)

**Key insight**: 9 CLI-capable agents have documented invocation patterns:

| Agent | Command | Task Input | Headless | JSON Output |
|-------|---------|------------|----------|-------------|
| Claude Code | `claude` | stdin | `-p` | `--output-format json` |
| GitHub Codex | `codex exec` | stdin/arg | `-` | `--json` |
| GitHub Copilot | `copilot` | arg | `-p` | `--silent` |
| Google Gemini | `gemini` | stdin | `-p` | `--output-format json` |
| Qwen Code | `qwen` | stdin | `-p` | `--output-format json` |
| OpenCode | `opencode run` | stdin/`-f` | (default) | `--format json` |
| Kilocode | `kilocode` | arg | `-a` | `-j` |
| Augment Code | `auggie` | arg | `--acp` | (exit code only) |
| Cursor | `cursor agent` | arg | `-p` | `--output-format json` |

**Cursor special handling**: Requires `timeout 300` wrapper due to hanging issue.

**Source**: spec-kitty Feature 020 plan.md, data-model.md

### Risks / Concerns

1. **Container build time**: Building 9 agent-specific containers may be slow. Mitigation: Use multi-stage builds, cache layers.

2. **API costs**: Real agent tests incur LLM API costs. Mitigation: Manual trigger, budget tracking (out of scope but recommended).

3. **Rate limits**: Agents have different rate limits. Mitigation: Per-agent concurrency limits in configuration.

4. **Agent CLI changes**: Agent CLIs may change between versions. Mitigation: Version detection, graceful degradation.

5. **Credential rotation**: API keys expire. Mitigation: Document credential refresh process.

6. **Test flakiness**: Real agents produce non-deterministic output. Mitigation: Focus on workflow completion, not exact output matching.

## Next Actions

1. Design container Dockerfile(s) for agent testing
2. Create testcontainers-python fixture library
3. Implement fault injector component
4. Create 1-agent, 2-agent, 3-agent test path templates
5. Document credential setup process
6. Integrate with GitHub Actions for manual triggers

> Keep this document living. As more evidence arrives, update decisions and rationale so downstream implementers can trust the history.
