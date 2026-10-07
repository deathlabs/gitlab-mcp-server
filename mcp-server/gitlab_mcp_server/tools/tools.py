# Standard library imports.
from os import environ, getenv
from typing import Any
from urllib.parse import quote, urlsplit

# Third party imports.
import httpx

# Constants.
REQUEST_TIMEOUT = 30.0


def validate_target(project_id: str | int, issue_iid: int | None = None) -> None:
    """Validate a GitLab project identifier and project-scoped issue number."""
    if isinstance(project_id, bool) or not isinstance(project_id, (str, int)):
        raise TypeError("project_id must be a positive ID or namespace/project path.")
    if isinstance(project_id, int):
        valid = project_id > 0
    else:
        parts = project_id.split("/")
        valid = bool(project_id.strip()) and project_id == project_id.strip()
        valid = valid and not any(part in ("", ".", "..") for part in parts)
        valid = valid and not any(character in project_id for character in "?#\\")
        valid = valid and not any(ord(character) < 32 for character in project_id)
        if project_id.isdecimal():
            valid = valid and int(project_id) > 0
    if not valid:
        raise ValueError("project_id must be a positive ID or namespace/project path.")
    if issue_iid is not None and (
        isinstance(issue_iid, bool) or not isinstance(issue_iid, int) or issue_iid <= 0
    ):
        raise ValueError("issue_iid must be a positive project-scoped issue number.")


def get_configuration() -> tuple[str, str]:
    """Read and validate the GitLab instance URL and required API token."""
    instance_url = getenv("GITLAB_URL", "https://gitlab.com").rstrip("/")
    parsed_url = urlsplit(instance_url)
    if (
        parsed_url.scheme not in ("http", "https")
        or not parsed_url.hostname
        or parsed_url.username
        or parsed_url.password
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise ValueError(
            "GITLAB_URL must be an HTTP(S) instance URL without credentials, query, or fragment."
        )
    token = environ.get("GITLAB_TOKEN", "")
    if not token.strip():
        raise ValueError("GITLAB_TOKEN must contain a GitLab API token.")
    return instance_url, token


def request_issue(
    method: str,
    project_id: str | int,
    issue_iid: int | None = None,
    fields: dict[str, Any] | None = None,
    params: dict[str, str | int] | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Send a GitLab issue request without exposing credentials in errors."""
    listing = method == "GET" and issue_iid is None and params is not None
    if method in ("GET", "PUT", "DELETE") and issue_iid is None and not listing:
        raise ValueError("issue_iid must be a positive project-scoped issue number.")
    validate_target(project_id, issue_iid)
    instance_url, token = get_configuration()
    endpoint = (
        f"{instance_url}/api/v4/projects/{quote(str(project_id), safe='')}/issues"
    )
    if issue_iid is not None:
        endpoint += f"/{issue_iid}"
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=False) as client:
            response = client.request(
                method,
                endpoint,
                headers={"PRIVATE-TOKEN": token},
                json=fields,
                params=params,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"GitLab {method} issue request failed with HTTP {error.response.status_code}."
        ) from None
    except httpx.RequestError:
        raise RuntimeError(
            "GitLab issue request failed to reach the configured instance."
        ) from None
    if method == "DELETE":
        return {"project_id": project_id, "issue_iid": issue_iid, "deleted": True}
    try:
        result = response.json()
    except ValueError:
        raise RuntimeError("GitLab returned an invalid JSON issue response.") from None
    if listing:
        if not isinstance(result, list) or not all(
            isinstance(issue, dict) for issue in result
        ):
            raise TypeError("GitLab returned an unexpected issues response.")
    elif not isinstance(result, dict):
        raise TypeError("GitLab returned an unexpected issue response.")
    return result


def create_issue(
    project_id: str | int,
    title: str,
    description: str | None = None,
    labels: list[str] | None = None,
    assignee_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Create a GitLab project issue. The title must contain text."""
    if not title.strip():
        raise ValueError("title must contain text.")
    fields = {"title": title}
    if description is not None:
        fields["description"] = description
    if labels is not None:
        fields["labels"] = ",".join(labels)
    if assignee_ids is not None:
        fields["assignee_ids"] = assignee_ids
    return request_issue("POST", project_id, fields=fields)


def fetch_issue(project_id: str | int, issue_iid: int) -> dict[str, Any]:
    """Fetch an issue using its project-scoped IID, not its global issue ID."""
    return request_issue("GET", project_id, issue_iid)


def fetch_issues(
    project_id: str | int,
    state: str = "all",
    page: int = 1,
    per_page: int = 20,
) -> list[dict[str, Any]]:
    """Fetch one page of project issues. State accepts all, opened, or closed.

    Pages start at 1. Each page contains up to per_page issues (1 to 100).
    """
    if state not in ("all", "opened", "closed"):
        raise ValueError("state must be all, opened, or closed.")
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError("page must be a positive integer.")
    if (
        isinstance(per_page, bool)
        or not isinstance(per_page, int)
        or not 1 <= per_page <= 100
    ):
        raise ValueError("per_page must be an integer between 1 and 100.")
    return request_issue(
        "GET", project_id, params={"state": state, "page": page, "per_page": per_page}
    )


def update_issue(
    project_id: str | int,
    issue_iid: int,
    title: str | None = None,
    description: str | None = None,
    labels: list[str] | None = None,
    assignee_ids: list[int] | None = None,
    state_event: str | None = None,
) -> dict[str, Any]:
    """Update supplied fields. Empty descriptions or lists clear those fields."""
    fields: dict[str, Any] = {}
    if title is not None:
        if not title.strip():
            raise ValueError("title must contain text.")
        fields["title"] = title
    if description is not None:
        fields["description"] = description
    if labels is not None:
        fields["labels"] = ",".join(labels)
    if assignee_ids is not None:
        fields["assignee_ids"] = assignee_ids or [0]
    if state_event is not None:
        if state_event not in ("close", "reopen"):
            raise ValueError("state_event must be close or reopen.")
        fields["state_event"] = state_event
    if not fields:
        raise ValueError("Supply at least one issue field to update.")
    return request_issue("PUT", project_id, issue_iid, fields)


def delete_issue(project_id: str | int, issue_iid: int) -> dict[str, Any]:
    """Permanently delete a GitLab project issue."""
    return request_issue("DELETE", project_id, issue_iid)
