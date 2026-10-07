# `gitlab-mcp-server`

[![CI Pipeline](https://github.com/deathlabs/gitlab-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/deathlabs/gitlab-mcp-server/actions/workflows/ci.yml)

An MCP server for creating, fetching, updating, and deleting GitLab project issues through GitLab REST API v4. Microsoft's [Agent Governance Toolkit (AGT)](https://github.com/microsoft/agent-governance-toolkit) checks every tool call before the request reaches GitLab.

## Quickstart

The instructions below assume you have [Git](https://git-scm.com/downloads), [Make](https://www.gnu.org/software/make/), [Docker with Docker Compose](https://docs.docker.com/compose/install/), [uv](https://docs.astral.sh/uv/), [Ruff](https://docs.astral.sh/ruff/), [Semgrep](https://semgrep.dev/), [TruffleHog](https://github.com/trufflesecurity/trufflehog), [Hadolint](https://github.com/hadolint/hadolint), [Syft](https://github.com/anchore/syft#installation), [Grype](https://github.com/anchore/grype#installation), and [yq](https://github.com/mikefarah/yq) installed. The Makefile uses these tools to build, scan, start, and test the server. You also need an MCP client to try the [demo](#demo).

**Step 1.** Clone the repository.

```bash
git clone https://github.com/deathlabs/gitlab-mcp-server.git
```

**Step 2.** Change to the repository directory.

```bash
cd gitlab-mcp-server
```

**Step 3.** Copy the environment template and configure GitLab access.

Set `GITLAB_TOKEN` to a GitLab access token with the `api` scope and permission to manage issues in the target project. Set `GITLAB_URL` to your instance URL, such as `https://gitlab.example.com`. It defaults to `https://gitlab.com`. Keep tokens out of source control.

```bash
cp .env.example .env
```

Edit `.env` to fill in `GITLAB_TOKEN` and change `GITLAB_URL` if needed. Docker Compose reads this root `.env` file, which Git ignores.

You can also export the settings in your shell. Exported values take precedence over `.env`:

```bash
export GITLAB_TOKEN="your-access-token"
export GITLAB_URL="https://gitlab.com"
```

**Step 4.** Use the Makefile to build, scan, start, and test the server.

```bash
make test-container
```

This checks server availability and MCP tool discovery without making GitLab requests. CI supplies a non-secret dummy token for these checks. Use `make start-container` to build, scan, and start the server without the discovery test.

**Step 5.** Connect your MCP client and [try the demo](#demo).

Connect an MCP client to `http://localhost:8003/mcp`. The health endpoint is `http://localhost:8003/api/v1/health`.

### Demo

**Step 1.** Watch the server logs.

```bash
docker logs gitlab_mcp_server_mcp -f
```

**Step 2.** Enter this prompt in your connected MCP client. Replace `group/project` with a project your token can access.

> Use fetch_issues to list the first page of opened issues in group/project with per_page set to 20. Summarize their project-scoped IIDs and titles, then use fetch_issue to read the first returned issue if the list is not empty.

The demo reads existing issues through GitLab. Your token's project permissions and the server's governance policy apply to each call.

## Cleaning Up

Stop the server, remove its container, and delete its container image:

```bash
make clean
```
