# Changelog

Notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added

- Streamable HTTP Model Context Protocol (MCP) server with a health check endpoint.
- GitLab project issue creation, fetching, updating, and deletion with API token authentication and policy checks before requests.
- `fetch_issues` tool for listing project issues with state filtering and pagination.
- Configurable GitLab instance URL for hosted and self-hosted installations.
- Docker Compose setup and Make targets for building, testing, and scanning the server.
- Root `.env.example` template for configuring the GitLab instance and API token.

### Fixed

- CI environment setup uses the root template and runs `make test-container` with a non-secret token for health and tool discovery checks.

### Removed

- Bundled agent skills and sample record tools.
