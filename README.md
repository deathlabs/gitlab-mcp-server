# GitLab MCP Server

[![CI](https://github.com/deathlabs/gitlab-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/deathlabs/gitlab-mcp-server/actions/workflows/ci.yml)

GitLab MCP Server exposes tools to create, fetch, update, and delete project issues through GitLab REST API v4. Azure Agent Governance Toolkit checks every tool call before the request reaches GitLab.

## Configuration

Set `GITLAB_TOKEN` to a GitLab access token with the `api` scope and permission to manage issues in the target project. Set `GITLAB_URL` to your instance URL, such as `https://gitlab.example.com`. It defaults to `https://gitlab.com`. Keep tokens out of source control.

```sh
export GITLAB_TOKEN="your-access-token"
export GITLAB_URL="https://gitlab.com"
make start-container
```

Connect an MCP client to `http://localhost:8003/mcp`. The health endpoint is `http://localhost:8003/api/v1/health`.

## Issue tools

- `create_issue(project_id, title, description?, labels?, assignee_ids?)` creates an issue.
- `fetch_issue(project_id, issue_iid)` reads an issue.
- `update_issue(project_id, issue_iid, title?, description?, labels?, assignee_ids?, state_event?)` changes supplied fields. Empty descriptions and lists clear those fields. `state_event` accepts `close` or `reopen`.
- `delete_issue(project_id, issue_iid)` permanently deletes an issue.

Use a numeric project ID or a namespace/project path for `project_id`. Use the issue's project-scoped IID for `issue_iid`, rather than its global ID. The configured policy allows these four tools and denies other actions. GitLab also enforces the token's project permissions.

## Verification

Run focused tests without contacting GitLab:

```sh
uv sync --project mcp-server/gitlab_mcp_server --frozen
mcp-server/gitlab_mcp_server/.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

`make test-container` builds and scans the container, starts the server, and verifies MCP tool discovery. It requires the configured GitLab token but does not mutate GitLab issues.
