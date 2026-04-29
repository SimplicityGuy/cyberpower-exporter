# CLAUDE.md - Development Guide

## Project Overview

**cyberpower-exporter** is a Python 3.13+ Prometheus exporter that reads CyberPower UPS status from the `pwrstatd` Unix socket and exposes metrics on port 9200. It is shipped as a multi-arch Docker image to GHCR.

The implementation is derived from Mike Shoup's [`shouptech/cyberpower_exporter`](https://github.com/shouptech/cyberpower_exporter) and is licensed under Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

> **CRITICAL**: Use **[uv](https://github.com/astral-sh/uv)** exclusively for all Python operations. **Never use pip, python, pytest, or mypy directly** — always prefix with `uv run`.

## AI Development Rules

- **ALWAYS use `uv run`** for any Python command (ruff, mypy, bandit, pytest, python).
- **Open a PR for every change** — never push directly to `main`.
- **Run `pre-commit run --all-files`** before committing.
- **Emojis in GitHub Actions** step names; single quotes inside `${{ }}` expressions, double quotes for YAML strings.
- **Preserve attribution.** The Apache 2.0 header in `src/cyberpower_exporter/exporter.py` must remain. Any new source file derived from upstream must carry the same header.
- **Type-clean.** Mypy runs in strict mode (`disallow_untyped_defs`, `warn_unreachable`, etc.). New code must pass.
- **Bandit B104** (binding 0.0.0.0) is intentionally skipped — the exporter must bind all interfaces inside the container. Do not change without justification.

## Repository Layout

```
src/cyberpower_exporter/
    __init__.py           Package init; re-exports main()
    exporter.py           Prometheus exporter
    py.typed              PEP 561 marker so downstream type checkers see our types
pyproject.toml            Project metadata, ruff/mypy/bandit/coverage/pytest config, uv environments
uv.lock                   Pinned dependency lockfile (committed)
Dockerfile                uv-based multi-stage build → distroless-ish slim runtime
LICENSE                   Apache 2.0
NOTICE                    Upstream attribution required by Apache 2.0 §4(d)
.pre-commit-config.yaml   ruff, mypy (local), bandit, hadolint, shellcheck, shfmt, actionlint, yamllint
.github/workflows/        Build (quality + GHCR), cleanup-cache (PR close), cleanup-images (monthly)
.github/dependabot.yml    github-actions, docker, pip ecosystems
```

## uv Commands

```bash
uv sync --all-groups           # Install runtime + dev deps
uv add package-name            # Add runtime dependency
uv add --dev package-name      # Add dev dependency
uv run ruff check .            # Lint
uv run ruff format .           # Format
uv run mypy .                  # Type check
uv run bandit -c pyproject.toml -r src/   # Security scan
uv run cyberpower-exporter     # Run the exporter (entry point from pyproject.toml)
uv lock --upgrade-package name # Update specific package
```

## How It Works

1. Container starts; `pwrstatd.ipc` Unix socket is mounted from the host.
2. `start_http_server(9200)` exposes `/metrics`.
3. Every `POLL_INTERVAL` seconds, a `STATUS\n\n` command is sent over the socket. The reply is parsed as `key=value` lines and pushed into Prometheus collectors.
4. Errors during polling are logged but do not exit the process — the next tick retries.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `POLL_INTERVAL` | `5` | Seconds between UPS status polls |

The container runs as a non-root `exporter` user in the `root` group so it can read the host-owned socket.

## CI/CD

- **`build.yml`** — runs on push to `main`, on PRs, and weekly. Builds and pushes a multi-tag image to `ghcr.io/<owner>/cyberpower-exporter` with OCI labels populated from build args. PRs build but do not push.
- **`cleanup-cache.yml`** — purges PR-scoped Actions caches when a PR closes.
- **`cleanup-images.yml`** — runs the 15th of each month, keeps the 2 newest tagged versions, deletes images older than 30 days and any untagged manifests.

## Local Commands

```bash
# Build the image
docker build -t cyberpower-exporter:dev .

# Run against a host socket
docker run --rm -v /var/pwrstatd.ipc:/var/pwrstatd.ipc -p 9200:9200 cyberpower-exporter:dev

# Pre-commit
pre-commit install
pre-commit run --all-files

# Lint just the Dockerfile
hadolint Dockerfile
```
