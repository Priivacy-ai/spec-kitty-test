# Container Infrastructure for Agentic E2E Testing

## Overview

This directory contains Docker configuration for running spec-kitty's
agentic tests in isolated containers. The container architecture ensures:

- **Distribution testing**: spec-kitty is installed from PyPI, not local source
- **Network isolation**: Internal network blocks all internet access
- **Resource limits**: CPU, memory, and disk constraints prevent runaway processes
- **Filesystem isolation**: Read-only root with explicit writable paths
- **Credential security**: API keys mounted via Docker secrets

## Quick Start

```bash
# Build the base image (always use --no-cache for clean builds)
docker compose build --no-cache agent-runner

# Run a test command
docker compose run --rm agent-runner "spec-kitty --version"

# Build with specific spec-kitty version
SPEC_KITTY_VERSION=0.11.0 docker compose build --no-cache agent-runner
```

## Prerequisites

### 1. Docker Engine

Docker must be installed and running:
```bash
docker --version  # Should show Docker version
docker compose version  # Should show Compose v2
```

### 2. Agent CLIs (Host System)

Agent CLIs must be installed on the host system and will be accessed
via volume mounts or by invoking them from within the container.

### 3. API Credentials

Create credential files in `tests/agentic/config/secrets/`:

```bash
# Create placeholder files (replace with real credentials for actual testing)
echo "your-claude-api-key" > ../config/secrets/claude_api_key.txt
echo "your-github-token" > ../config/secrets/github_token.txt
echo "your-cursor-api-key" > ../config/secrets/cursor_api_key.txt
echo "your-gemini-api-key" > ../config/secrets/gemini_api_key.txt
echo "your-opencode-api-key" > ../config/secrets/opencode_api_key.txt
echo "your-qwen-api-key" > ../config/secrets/qwen_api_key.txt
echo "your-kilocode-api-key" > ../config/secrets/kilocode_api_key.txt
echo "your-augment-api-key" > ../config/secrets/augment_api_key.txt
```

**IMPORTANT**: These files are git-ignored. Never commit real credentials.

## Network Isolation

The `agent-test-internal` network has `internal: true`, which means:

| Access Type | Allowed? | Reason |
|-------------|----------|--------|
| Internet access | **NO** | Prevents data exfiltration |
| Container-to-container | Yes | Required for Toxiproxy |
| Mounted volumes | Yes | Required for worktree access |
| Docker host | Limited | Only via explicit mounts |

This prevents:
- Agents from making unauthorized network requests
- Data exfiltration to external services
- Rate limit issues from uncontrolled API calls
- Accidental exposure of credentials

## Resource Limits

| Resource | Limit | Rationale |
|----------|-------|-----------|
| CPU | 2 cores | Prevents runaway processes from consuming all CPU |
| Memory | 4 GB | Sufficient for LLM responses, prevents OOM on host |
| Disk | 10 GB | Via volume constraints (not enforced in compose) |
| tmpfs | 1 GB | Ephemeral storage for /tmp operations |

These limits are configured in `docker-compose.yaml` under `deploy.resources`.

## Filesystem Isolation

| Path | Access | Purpose |
|------|--------|---------|
| `/` (root) | **READ-ONLY** | Prevents system modification |
| `/workspace` | READ-WRITE | Mounted test worktree |
| `/tmp` | READ-WRITE | Ephemeral tmpfs storage |
| `/run/secrets` | READ-ONLY | API credentials |

Agents can **only** modify files in `/workspace`, which maps to the
test worktree on the host. All other filesystem changes are blocked
by the `read_only: true` setting in docker-compose.yaml.

## Fault Injection with Toxiproxy

Toxiproxy enables network fault injection for adversarial testing:

```bash
# Start Toxiproxy (only when needed)
docker compose --profile fault-injection up -d toxiproxy

# Configure a proxy with latency
curl -X POST http://localhost:8474/proxies \
  -H "Content-Type: application/json" \
  -d '{"name": "slow-api", "listen": "0.0.0.0:9000", "upstream": "api.example.com:443"}'

# Add latency toxic
curl -X POST http://localhost:8474/proxies/slow-api/toxics \
  -H "Content-Type: application/json" \
  -d '{"name": "latency", "type": "latency", "attributes": {"latency": 3000}}'

# Stop Toxiproxy
docker compose --profile fault-injection down
```

## Troubleshooting

### Container fails to start

**Check secrets files exist:**
```bash
ls -la ../config/secrets/
# All .txt files should exist
```

**Create missing placeholder files:**
```bash
for f in claude_api_key github_token cursor_api_key gemini_api_key \
         opencode_api_key qwen_api_key kilocode_api_key augment_api_key; do
  touch "../config/secrets/${f}.txt"
done
```

### Network issues

**Verify internal network exists:**
```bash
docker network ls | grep agent-test-internal
```

**Inspect network settings:**
```bash
docker network inspect tests-agentic-containers_agent-test-internal
# "Internal" should be true
```

### Build failures

**Force clean rebuild:**
```bash
docker compose build --no-cache agent-runner
```

**Check Docker daemon is running:**
```bash
docker info
```

**Clear Docker build cache:**
```bash
docker builder prune -f
```

### spec-kitty not found

**Verify PyPI installation:**
```bash
docker compose run --rm agent-runner "pip show spec-kitty"
```

**Check for editable install (should not exist):**
```bash
docker compose run --rm agent-runner "pip show spec-kitty | grep -i editable"
# Should return nothing
```

### Memory/CPU limits not working

Resource limits require Docker with cgroups support. On some systems:
```bash
# Check if limits are being applied
docker compose run --rm agent-runner "cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || cat /sys/fs/cgroup/memory.max 2>/dev/null"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SPEC_KITTY_VERSION` | `latest` | Version to install from PyPI |
| `WORKTREE_PATH` | `.` | Host path to mount as /workspace |

## Files

| File | Purpose |
|------|---------|
| `Dockerfile.base` | Universal base image with spec-kitty |
| `docker-compose.yaml` | Service definitions and network config |
| `README.md` | This documentation |
