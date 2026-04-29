# CLAUDE.md - Development Guide

## Project Overview

**cyberpower-exporter** is a single-file Python Prometheus exporter that reads CyberPower UPS status from the `pwrstatd` Unix socket and exposes metrics on port 9200. It is shipped as a Docker image only — there is no Python package, no test suite, and no service composition.

The implementation is derived from Mike Shoup's [`shouptech/cyberpower_exporter`](https://github.com/shouptech/cyberpower_exporter) and is licensed under Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## AI Development Rules

- **Open a PR for every change** — never push directly to `main`.
- **Run `pre-commit run --all-files`** before committing. The suite includes hadolint, shellcheck, shfmt, actionlint, and yamllint.
- **Emojis in GitHub Actions** step names; single quotes inside `${{ }}` expressions, double quotes for YAML strings (matches the discogsography style).
- **Keep it small.** This project intentionally does not depend on uv, pyproject.toml, or a multi-stage build. If adding tooling, justify why a single Dockerfile + single Python file is no longer sufficient.
- **Preserve attribution.** The Apache 2.0 header in `exporter.py` must remain. Any new source file derived from upstream must carry the same header.

## Repository Layout

```
exporter.py              Single-file Prometheus exporter
Dockerfile               Slim Python image, runs as non-root in root group for socket access
LICENSE                  Apache 2.0
NOTICE                   Upstream attribution required by Apache 2.0 §4(d)
.pre-commit-config.yaml  hadolint, shellcheck, shfmt, actionlint, yamllint, standard hygiene hooks
.github/workflows/       Build (GHCR), cleanup-cache (PR close), cleanup-images (monthly)
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
